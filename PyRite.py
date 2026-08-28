#!/usr/bin/env python3
import gi, re, os, json
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Pango, GLib

class PyRiteEditor(Gtk.Window):
    def __init__(self):
        super().__init__(title="PyRite")
        self.set_default_size(800, 550)
        
        # state
        self.vim_mode = False
        self.cur_file = None
        self.modified = False
        self.vim_state = "NORMAL"
        self.vim_cmd = ""
        self.vim_cmd_mode = False
        
        # prefs
        self.show_lines = False
        self.wrap = True
        self.syntax = False
        self.indent = "4s" # 4s, 2s, Tab
        self.words = 0
        self.deferred_id = None
        
        self.recent_path = os.path.expanduser("~/.pyrite_recents.json")
        self.recents = self.load_recents()

        # css
        css = b"""
        window { background-color: #1e1e1e; }
        .top-bar { background-color: #252526; padding: 4px 8px; border-bottom: 1px solid #1a1a1a; }
        .pill-button {
            background-color: #333333; color: #abb2bf; border-radius: 10px;
            padding: 2px 10px; border: none; font-family: 'SF Mono', 'JetBrains Mono', monospace;
            font-size: 9pt; outline: none;
        }
        .pill-button:hover { background-color: #3e3e3e; color: #ffffff; }
        .pill-button:active, .pill-button:checked {
            background-color: #d19a66; color: #1e1e1e; font-weight: bold;
        }
        .pill-button:checked:hover {
            background-color: #e0a878; color: #1e1e1e;
        }

        textview text { 
            background-color: #1e1e1e; color: #e0e0e0; 
            font-family: 'JetBrains Mono', 'Fira Code', 'SF Mono', monospace; 
            font-size: 11pt; caret-color: #d19a66; 
        }
        textview text:active, textview text:focus, textview text:hover {
            background-color: #1e1e1e; color: #e0e0e0;
        }
        textview selection { background-color: rgba(209, 154, 102, 0.25); color: #ffffff; }
        .line-numbers { background-color: #1e1e1e; color: #4a4a4a; font-size: 9pt; }
        .line-numbers:active, .line-numbers:focus { background-color: #1e1e1e; }

        .status-bar { 
            background-color: #252526; color: #abb2bf; padding: 2px 8px; 
            border-top: 1px solid #333333; font-family: 'JetBrains Mono', monospace; font-size: 9pt; 
        }
        .status-bar label { margin-right: 12px; }

        scrollbar { background-color: #1e1e1e; }
        scrollbar slider { background-color: #4a4a4a; border-radius: 3px; min-width: 6px; min-height: 6px; }
        scrollbar slider:hover { background-color: #5a5a5a; }
        scrollbar button { border: none; background: none; padding: 0; }

        menu { background-color: #252526; border: 1px solid #333333; }
        menuitem { color: #abb2bf; padding: 2px 8px; font-size: 9pt; }
        menuitem:hover, menuitem:active { background-color: #333333; color: #ffffff; }
        menuitem check { background-color: #1e1e1e; }
        
        .find-bar { background-color: #252526; border-top: 1px solid #333333; padding: 4px; }
        entry { 
            background-color: #1e1e1e; color: #e0e0e0; border: 1px solid #333333; 
            border-radius: 3px; padding: 2px 6px; font-size: 9pt;
        }
        entry:focus { border-color: #d19a66; }
        paned separator { background-color: #1a1a1a; min-width: 1px; }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(main_box)

        # top bar
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        top_bar.get_style_context().add_class("top-bar")
        main_box.pack_start(top_bar, False, False, 0)

        self.menu = Gtk.Menu()
        self.build_menu()
        
        self.btn_opts = Gtk.MenuButton(label="Options")
        self.btn_opts.get_style_context().add_class("pill-button")
        self.btn_opts.set_popup(self.menu)
        top_bar.pack_start(self.btn_opts, False, False, 0)

        self.btn_vim = Gtk.ToggleButton(label="Vim")
        self.btn_vim.get_style_context().add_class("pill-button")
        self.btn_vim.connect("toggled", self.toggle_vim)
        
        self.btn_render = Gtk.Button(label="Render")
        self.btn_render.get_style_context().add_class("pill-button")
        self.btn_render.connect("clicked", self.toggle_render)
        
        top_bar.pack_end(self.btn_vim, False, False, 0)
        top_bar.pack_end(self.btn_render, False, False, 0)

        # editor split
        self.paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        main_box.pack_start(self.paned, True, True, 0)

        ed_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        
        self.line_nums = Gtk.TextView()
        self.line_nums.get_style_context().add_class("line-numbers")
        self.line_nums.set_editable(False)
        self.line_nums.set_cursor_visible(False)
        self.line_nums_buf = self.line_nums.get_buffer()
        ed_box.pack_start(self.line_nums, False, False, 0)
        if not self.show_lines: self.line_nums.hide()

        self.scroll = Gtk.ScrolledWindow()
        ed_box.pack_start(self.scroll, True, True, 0)

        self.tview = Gtk.TextView()
        self.tview.set_wrap_mode(Gtk.WrapMode.WORD if self.wrap else Gtk.WrapMode.NONE)
        self.tview.set_left_margin(15)
        self.tview.set_right_margin(15)
        self.tview.set_top_margin(10)
        self.tview.set_bottom_margin(10)
        
        self.buf = self.tview.get_buffer()
        
        # tags
        self.buf.create_tag("bold", weight=Pango.Weight.BOLD)
        self.buf.create_tag("italic", style=Pango.Style.ITALIC)
        # search-match created last so its colors beat the syntax tags (later = higher priority)
        self.buf.create_tag("syn_keyword", foreground="#56b6c2")
        self.buf.create_tag("syn_string", foreground="#98c379")
        self.buf.create_tag("syn_comment", foreground="#5c6370", style=Pango.Style.ITALIC)
        self.buf.create_tag("search-match", background="#d19a66", foreground="#1e1e1e")
        
        self.scroll.add(self.tview)
        self.paned.pack1(ed_box, resize=True, shrink=False)

        # render view
        self.render_scroll = Gtk.ScrolledWindow()
        self.r_view = Gtk.TextView()
        self.r_view.set_editable(False)
        self.r_view.set_cursor_visible(False)
        self.r_view.set_left_margin(15)
        self.r_view.set_right_margin(15)
        self.r_view.set_top_margin(10)
        self.r_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.r_buf = self.r_view.get_buffer()
        self.r_buf.create_tag("r_bold", weight=Pango.Weight.BOLD)
        self.r_buf.create_tag("r_italic", style=Pango.Style.ITALIC)
        self.render_scroll.add(self.r_view)
        self.paned.pack2(self.render_scroll, resize=False, shrink=False)
        self.render_scroll.hide()

        # find bar
        self.find_rev = Gtk.Revealer()
        find_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        find_box.get_style_context().add_class("find-bar")
        
        self.find_entry = Gtk.Entry()
        self.find_entry.set_placeholder_text("Find...")
        self.find_entry.connect("changed", self.on_search)
        self.find_entry.connect("key-press-event", self.on_search_key)
        
        btn_close = Gtk.Button(label="Close")
        btn_close.connect("clicked", lambda w: self.find_rev.set_reveal_child(False))
        
        find_box.pack_start(self.find_entry, True, True, 0)
        find_box.pack_start(btn_close, False, False, 0)
        self.find_rev.add(find_box)
        main_box.pack_start(self.find_rev, False, False, 0)

        # status bar
        s_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        s_bar.get_style_context().add_class("status-bar")
        main_box.pack_end(s_bar, False, False, 0)

        self.lbl_status = Gtk.Label(label="")
        self.lbl_status.set_xalign(0)
        s_bar.pack_start(self.lbl_status, False, False, 0)
        
        self.btn_indent = Gtk.Button(label=self.indent)
        self.btn_indent.get_style_context().add_class("pill-button")
        self.btn_indent.set_relief(Gtk.ReliefStyle.NONE)
        self.btn_indent.set_size_request(30, -1)
        self.btn_indent.connect("clicked", self.toggle_indent)
        s_bar.pack_end(self.btn_indent, False, False, 0)

        # signals
        self.tview.connect("key-press-event", self.handle_vim_key)
        self.tview.connect("key-press-event", self.handle_keys)
        self.buf.connect("modified-changed", self.on_modified)
        self.buf.connect("changed", self.on_text_changed)
        self.buf.connect("notify::cursor-position", lambda b, p: self.update_status())
        
        self.scroll.get_vadjustment().connect("value-changed", lambda adj: self.line_nums.get_vadjustment().set_value(adj.get_value()))
        
        self.accel = Gtk.AccelGroup()
        self.add_accel_group(self.accel)
        self.btn_render.add_accelerator("clicked", self.accel, ord('r'), Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)

        self.update_status()

    def build_menu(self):
        for c in self.menu.get_children(): self.menu.remove(c)
        
        items = [
            ("New", self.new_file),
            ("Open", self.open_file),
            ("Save", self.save_file),
            ("Save As...", self.save_as)
        ]
        for label, cb in items:
            item = Gtk.MenuItem(label=label)
            item.connect("activate", cb)
            self.menu.append(item)
            
        self.menu.append(Gtk.SeparatorMenuItem())

        # recents
        rec_menu = Gtk.Menu()
        if not self.recents:
            empty_item = Gtk.MenuItem(label="No recent files")
            empty_item.set_sensitive(False)
            rec_menu.append(empty_item)
        else:
            for f in self.recents[:5]:
                item = Gtk.MenuItem(label=os.path.basename(f))
                item.connect("activate", lambda w, p=f: self.open_file(path=p))
                rec_menu.append(item)
        
        rec_item = Gtk.MenuItem(label="Recent Files")
        rec_item.set_submenu(rec_menu)
        self.menu.append(rec_item)
        self.menu.append(Gtk.SeparatorMenuItem())

        # toggles
        self.chk_lines = Gtk.CheckMenuItem(label="Show Line Numbers")
        self.chk_lines.set_active(self.show_lines)
        self.chk_lines.connect("toggled", self.toggle_lines)
        self.menu.append(self.chk_lines)

        self.chk_wrap = Gtk.CheckMenuItem(label="Word Wrap")
        self.chk_wrap.set_active(self.wrap)
        self.chk_wrap.connect("toggled", self.toggle_wrap)
        self.menu.append(self.chk_wrap)

        self.chk_syn = Gtk.CheckMenuItem(label="Syntax Highlighting")
        self.chk_syn.set_active(self.syntax)
        self.chk_syn.connect("toggled", self.toggle_syntax)
        self.menu.append(self.chk_syn)
        
        self.menu.append(Gtk.SeparatorMenuItem())
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self.quit_app)
        self.menu.append(quit_item)
        self.menu.show_all()

    def load_recents(self):
        try:
            with open(self.recent_path) as f: data = json.load(f)
            return [p for p in data if isinstance(p, str)] if isinstance(data, list) else []
        except Exception:
            return []

    def save_recents(self):
        try:
            with open(self.recent_path, "w") as f: json.dump(self.recents, f)
        except Exception as ex:
            print(f"Could not save recents: {ex}")

    def add_recent(self, path):
        if path in self.recents: self.recents.remove(path)
        self.recents.insert(0, path)
        self.recents = self.recents[:5]
        self.save_recents()
        self.build_menu()

    def toggle_lines(self, w=None):
        new = w.get_active() if w else not self.show_lines
        if new == self.show_lines: return  # guard: set_active below re-emits "toggled"
        self.show_lines = new
        if self.show_lines:
            self.line_nums.show()
            self.sync_line_nums()
        else:
            self.line_nums.hide()

    def toggle_wrap(self, w=None):
        new = w.get_active() if w else not self.wrap
        if new == self.wrap: return  # guard: set_active below re-emits "toggled"
        self.wrap = new
        self.tview.set_wrap_mode(Gtk.WrapMode.WORD if self.wrap else Gtk.WrapMode.NONE)
        self.chk_wrap.set_active(self.wrap)

    def toggle_syntax(self, w=None):
        new = w.get_active() if w else not self.syntax
        if new == self.syntax: return  # guard: set_active below re-emits "toggled"
        self.syntax = new
        if not self.syntax:
            s, e = self.buf.get_bounds()
            for tag in ["syn_keyword", "syn_string", "syn_comment"]:
                self.buf.remove_tag_by_name(tag, s, e)
        else:
            self.do_syntax()
        self.chk_syn.set_active(self.syntax)
        
    def toggle_indent(self, w=None):
        self.indent = "2s" if self.indent == "4s" else "Tab" if self.indent == "2s" else "4s"
        self.btn_indent.set_label(self.indent)
        self.update_status()

    def toggle_render(self, w=None):
        if self.render_scroll.get_visible():
            self.render_scroll.hide()
        else:
            self.render_scroll.show()
            self.render_tags()
            # give the newly revealed pane real width or GtkPaned can collapse it to zero
            if self.paned.get_realized():
                self.paned.set_position(self.paned.get_allocated_width() // 2)

    def on_modified(self, w):
        self.modified = self.buf.get_modified()
        self.update_status()

    def on_text_changed(self, w):
        self.update_status()

        # Clear stuck search highlights on text change
        s, e = self.buf.get_bounds()
        self.buf.remove_tag_by_name("search-match", s, e)

        if self.show_lines: self.sync_line_nums()

        # One throttled job for everything O(document): syntax, word count, live render
        if self.deferred_id: GLib.source_remove(self.deferred_id)
        self.deferred_id = GLib.timeout_add(300, self._deferred_update)

    def _deferred_update(self):
        self.deferred_id = None
        if self.syntax: self.do_syntax()
        s, e = self.buf.get_bounds()
        self.words = len(self.buf.get_text(s, e, True).split())
        if self.render_scroll.get_visible(): self.render_tags()
        self.update_status()
        return False

    def sync_line_nums(self, w=None):
        # counts logical lines, so wrapped rows desync the numbering; switch to GtkSourceView's built-in line numbers if that becomes an issue
        lines = self.buf.get_line_count()
        text = "\n".join(str(i+1) for i in range(lines))
        self.line_nums_buf.set_text(text)
        adj = self.scroll.get_vadjustment()
        self.line_nums.get_vadjustment().set_value(adj.get_value())

    def handle_keys(self, w, event):
        key = Gdk.keyval_to_lower(event.keyval)
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK

        if ctrl:
            if key == Gdk.KEY_f:
                self.find_rev.set_reveal_child(True)
                self.find_entry.grab_focus()
                return True
            if key == Gdk.KEY_n: self.new_file(); return True
            if key == Gdk.KEY_o: self.open_file(); return True
            if key == Gdk.KEY_s: self.save_file(); return True
            return False

        # alt+z wrap
        if key == Gdk.KEY_z and (event.state & Gdk.ModifierType.MOD1_MASK):
            self.toggle_wrap()
            return True

        # auto-indent
        if key == Gdk.KEY_Return and not self.vim_mode:
            def _indent():
                # compute at execution time, or two rapid Enters stack their indents
                buf = self.buf
                itr = buf.get_iter_at_mark(buf.get_insert())
                ln = itr.get_line()
                if ln > 0:
                    ps = buf.get_iter_at_line(ln - 1)
                    pe = ps.copy()
                    pe.forward_to_line_end()
                    prev = buf.get_text(ps, pe, True)
                    indent = prev[:len(prev) - len(prev.lstrip(" \t"))]
                    if prev.rstrip().endswith(":"):
                        sz = 4 if self.indent == "4s" else 2 if self.indent == "2s" else 1
                        indent += (" " if "s" in self.indent else "\t") * sz
                    if indent: buf.insert_at_cursor(indent)
                return False  # one-shot idle
            GLib.idle_add(_indent)

        return False

    def toggle_vim(self, w=None):
        self.vim_mode = self.btn_vim.get_active()
        if self.vim_mode:
            self.vim_state = "NORMAL"
            self.vim_cmd_mode = False
            self.vim_cmd = ""
            self.btn_vim.set_label("Vim: ON")
        else:
            self.btn_vim.set_label("Vim")
        self.update_status()

    def handle_vim_key(self, w, event):
        if not self.vim_mode: return False

        # let global shortcuts (Ctrl+S/O/N/F, Alt+Z) through even in vim mode;
        # vim has no modifier bindings here, so never swallow them
        if event.state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.MOD1_MASK):
            return False

        keyval = event.keyval
        keyname = Gdk.keyval_name(keyval)
        char = chr(Gdk.keyval_to_unicode(keyval)) if Gdk.keyval_to_unicode(keyval) != 0 else ""

        if self.vim_cmd_mode:
            if keyname == "Return":
                self.run_vim_cmd()
                return True
            elif keyname == "Escape":
                self.vim_cmd_mode = False
                self.vim_cmd = ""
            elif keyname == "BackSpace":
                self.vim_cmd = self.vim_cmd[:-1]
                if not self.vim_cmd: self.vim_cmd_mode = False
            else:
                self.vim_cmd += char
            self.update_status()
            return True

        if self.vim_state == "INSERT":
            if keyname == "Escape":
                self.vim_state = "NORMAL"
                self.update_status()
                return True
            return False

        if keyname == "Escape":
            self.vim_state = "NORMAL"
            self.update_status()
            return True

        if char == ':':
            self.vim_cmd_mode = True
            self.vim_cmd = ":"
            self.update_status()
            return True
        elif char == 'i':
            self.vim_state = "INSERT"
            self.update_status()
            return True
        elif char in ['h', 'j', 'k', 'l', 'x']:
            mark = self.buf.get_insert()
            itr = self.buf.get_iter_at_mark(mark)
            if char == 'h': itr.backward_char()
            elif char == 'l': itr.forward_char()
            elif char == 'j': itr.forward_line()
            elif char == 'k': itr.backward_line()
            elif char == 'x':
                if not itr.ends_line():  # never eat the newline joining lines
                    end = itr.copy()
                    end.forward_char()
                    self.buf.delete(itr, end)
            self.buf.place_cursor(itr)
            self.tview.scroll_to_mark(mark, 0.0, True, 0.0, 0.0)
            return True
        return True

    def run_vim_cmd(self):
        cmd = self.vim_cmd.strip(":").strip()
        if cmd == "w":
            self.save_file()
        elif cmd == "q":
            self.quit_app()
        elif cmd == "wq":
            if self.save_file() is not False:
                self.quit_app()
        self.vim_cmd_mode = False
        self.vim_cmd = ""
        self.update_status()

    def render_tags(self, w=None):
        s, e = self.buf.get_bounds()
        content = self.buf.get_text(s, e, False)
        parts = re.split(r'(<ts=[^>]*>|</ts=[^>]*>|<italic>|</italic>|<bold>|</bold>)', content)
        
        self.r_buf.set_text("")
        tags = []
        table = self.r_buf.get_tag_table()
        
        for p in parts:
            if not p: continue
            if p == "<bold>": tags.append("r_bold")
            elif p == "</bold>" and "r_bold" in tags: tags.remove("r_bold")
            elif p == "<italic>": tags.append("r_italic")
            elif p == "</italic>" and "r_italic" in tags: tags.remove("r_italic")
            elif re.match(r'<ts=[^>]*>', p):
                sz = p[4:-1]
                tname = "r_ts_" + re.sub(r'[^0-9A-Za-z_.]', '_', sz)
                if not table.lookup(tname):
                    try:
                        scale = float(sz) / 11.0
                    except ValueError:
                        scale = 1.0
                    if not (0 < scale <= 10): scale = 1.0
                    self.r_buf.create_tag(tname, scale=scale)
                tags.append(tname)
            elif re.match(r'</ts=[^>]*>', p):
                for i in range(len(tags)-1, -1, -1):
                    if tags[i].startswith("r_ts_"):
                        tags.pop(i)
                        break
            else:
                self.r_buf.insert_with_tags_by_name(self.r_buf.get_end_iter(), p, *tags)

    def do_syntax(self):
        if not self.syntax: return  # a pending timer must not resurrect highlighting
        s, e = self.buf.get_bounds()
        for tag in ["syn_keyword", "syn_string", "syn_comment"]:
            self.buf.remove_tag_by_name(tag, s, e)

        # include hidden chars so regex offsets line up with buffer offsets
        text = self.buf.get_text(s, e, True)

        # strings before comments in one pass, so '#' inside a string stays string-colored.
        # Remember their spans so keywords inside them aren't mis-highlighted.
        # TODO: this regex lexer has no triple-quote or nesting awareness; swap in a real tokenizer if that becomes a problem
        literal_spans = []
        for m in re.finditer(r'("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')|(#.*?$)', text, re.MULTILINE):
            tag = "syn_string" if m.group(1) else "syn_comment"
            ms, me = self.buf.get_iter_at_offset(m.start()), self.buf.get_iter_at_offset(m.end())
            self.buf.apply_tag_by_name(tag, ms, me)
            literal_spans.append((m.start(), m.end()))

        # keywords (skip any that fall inside a string or comment)
        kws = ["def", "class", "return", "if", "else", "elif", "import", "from", "while", "for", "in", "not", "and", "or", "True", "False", "None"]
        for m in re.finditer(r'\b(' + '|'.join(kws) + r')\b', text):
            ks, ke = m.start(1), m.end(1)
            if any(ks >= ls and ke <= le for ls, le in literal_spans):
                continue
            ms, me = self.buf.get_iter_at_offset(ks), self.buf.get_iter_at_offset(ke)
            self.buf.apply_tag_by_name("syn_keyword", ms, me)

    def on_search(self, w):
        q = self.find_entry.get_text()
        s, e = self.buf.get_bounds()
        self.buf.remove_tag_by_name("search-match", s, e)
        
        if q:
            i = s.copy()
            first = None
            while True:
                m = i.forward_search(q, Gtk.TextSearchFlags.CASE_INSENSITIVE, e)
                if not m: break
                self.buf.apply_tag_by_name("search-match", m[0], m[1])
                if first is None: first = m
                i = m[1]
            if first is not None:
                self.buf.select_range(first[0], first[1])
                self.tview.scroll_to_iter(first[0], 0.0, True, 0.0, 0.0)

    def on_search_key(self, w, event):
        if event.keyval == Gdk.keyval_from_name("Escape"):
            s, e = self.buf.get_bounds()
            self.buf.remove_tag_by_name("search-match", s, e)
            self.find_rev.set_reveal_child(False)
            self.tview.grab_focus()
            return True
        return False

    def new_file(self, w=None):
        if not self.confirm_discard(): return
        self.buf.set_text("")
        self.cur_file = None
        self.buf.set_modified(False)
        self.words = 0
        self.update_status()

    def open_file(self, w=None, path=None):
        if not self.confirm_discard(): return
        if path:
            self.open_specific_file(path)
            return

        dlg = Gtk.FileChooserNative.new("Open File", self, Gtk.FileChooserAction.OPEN, "_Open", "_Cancel")
        filt = Gtk.FileFilter()
        filt.set_name("Text/Python Files")
        filt.add_mime_type("text/plain")
        filt.add_pattern("*.py")
        dlg.add_filter(filt)
        if dlg.run() == Gtk.ResponseType.ACCEPT:
            self.open_specific_file(dlg.get_filename())
        dlg.destroy()

    def open_specific_file(self, path):
        if not os.path.exists(path):
            print(f"Error: {path} no longer exists.")
            if path in self.recents:
                self.recents.remove(path)
                self.save_recents()
                self.build_menu()
            return
            
        try:
            with open(path, encoding="utf-8", errors="replace") as f: content = f.read()
            self.buf.set_text(content)
            self.cur_file = path
            self.buf.set_modified(False)
            self.words = len(content.split())
            self.add_recent(path)
            self.update_status()
        except Exception as ex:
            print(f"Failed to open: {ex}")

    def save_file(self, w=None):
        if not self.cur_file:
            return self.save_as()
            
        try:
            s, e = self.buf.get_bounds()
            with open(self.cur_file, "w", encoding="utf-8") as f:
                f.write(self.buf.get_text(s, e, False))
            self.buf.set_modified(False)
            self.add_recent(self.cur_file)
            return True
        except Exception as ex:
            print(f"Save failed: {ex}")
            dlg = Gtk.MessageDialog(transient_for=self, modal=True,
                                    message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE,
                                    text=f"Save failed: {ex}")
            dlg.run(); dlg.destroy()
            return False

    def confirm_discard(self):
        if not self.buf.get_modified(): return True
        name = os.path.basename(self.cur_file) if self.cur_file else "untitled"
        dlg = Gtk.MessageDialog(transient_for=self, modal=True,
                                message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.NONE,
                                text=f"'{name}' has unsaved changes. Discard them?")
        dlg.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dlg.add_button("Discard", Gtk.ResponseType.OK)
        r = dlg.run(); dlg.destroy()
        return r == Gtk.ResponseType.OK

    def quit_app(self, w=None):
        if self.confirm_discard():
            Gtk.main_quit()
            return False
        return True  # blocks window delete-event

    def save_as(self, w=None):
        dlg = Gtk.FileChooserNative.new("Save File As", self, Gtk.FileChooserAction.SAVE, "_Save", "_Cancel")
        dlg.set_do_overwrite_confirmation(True)
        accepted = dlg.run() == Gtk.ResponseType.ACCEPT
        dlg.destroy()
        if accepted:
            self.cur_file = dlg.get_filename()
            return self.save_file()
        return False

    def update_status(self):
        raw = os.path.basename(self.cur_file) if self.cur_file else "untitled"
        fname = GLib.markup_escape_text(raw)
        mod = '<span foreground="#e06c75">●</span>' if self.modified else '<span foreground="#3e3e3e">●</span>'
        
        if not self.vim_mode:
            mode = '<span foreground="#abb2bf">[STANDARD]</span>'
        elif self.vim_cmd_mode:
            mode = f'<span foreground="#d19a66">[{GLib.markup_escape_text(self.vim_cmd)}]</span>'
        elif self.vim_state == "NORMAL":
            mode = '<span foreground="#d19a66">[NORMAL]</span>'
        else:
            mode = '<span foreground="#56b6c2">[INSERT]</span>'
            
        itr = self.buf.get_iter_at_mark(self.buf.get_insert())
        line = itr.get_line() + 1
        col = itr.get_line_offset() + 1

        self.lbl_status.set_markup(f"{mode} {fname} {mod}  |  Ln {line}, Col {col}  |  Words: {self.words}  |  UTF-8")
        self.set_title(f"{'● ' if self.modified else ''}{raw} - PyRite")

if __name__ == "__main__":
    win = PyRiteEditor()
    win.connect("delete-event", win.quit_app)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    # show_all() reveals every child; re-hide the panes that start disabled
    if not win.show_lines: win.line_nums.hide()
    win.render_scroll.hide()
    Gtk.main()
