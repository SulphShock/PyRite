import gi, re, os, json
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Pango, GLib, Gio

# yeet keywords to global so we don't rebuild this list on every keystroke
KWS = ["def", "class", "return", "if", "else", "elif", "import", "from", "while", "for", "in", "not", "and", "or", "True", "False", "None"]

class DarkEditor(Gtk.Window):
    def __init__(self):
        super().__init__(title="PyRite")
        self.set_default_size(800, 550)

        # state junk
        self.vim_mode = False; self.cur_file = None; self.modified = False
        self.vim_state = "NORMAL"; self.vim_cmd = ""; self.vim_cmd_mode = False
        self.show_lines = False; self.wrap = True; self.syntax = False
        self.indent = "4s"; self.syntax_timeout = None

        self.recent_path = os.path.expanduser("~/.PyRite_recent.json")
        self.recents = self.load_recents()

#if you touch this shit its fucking css dumped in a variable please dont touch otherwise you will break  but honestly i dont care"

        css = b"""
        window { background-color: #1e1e1e; }
        .top-bar { background-color: #252526; padding: 4px 8px; border-bottom: 1px solid #1a1a1a; }
        .pill-button { background-color: #333333; color: #abb2bf; border-radius: 5px; padding: 2px 10px; border: none; font-family: 'JetBrains Mono', monospace; font-size: 9pt; outline: none; }
        .pill-button:hover { background-color: #3e3e3e; color: #ffffff; }
        .pill-button:active, .pill-button:checked { background-color: #d19a66; color: #1e1e1e; font-weight: bold; }
        .pill-button:checked:hover { background-color: #e0a878; color: #1e1e1e; }
        textview text { background-color: #1e1e1e; color: #e0e0e0; font-family: 'JetBrains Mono',, monospace; font-size: 11pt; caret-color: #d19a66; }
        textview text:active, textview text:focus, textview text:hover { background-color: #1e1e1e; color: #e0e0e0; }
        textview selection { background-color: rgba(209, 154, 102, 0.25); color: #ffffff; }
        .line-numbers { background-color: #1e1e1e; color: #4a4a4a; font-size: 9pt; }
        .line-numbers:active, .line-numbers:focus { background-color: #1e1e1e; }
        .status-bar { background-color: #252526; color: #abb2bf; padding: 2px 8px; border-top: 1px solid #333333; font-family: 'JetBrains Mono', monospace; font-size: 9pt; }
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
        entry { background-color: #1e1e1e; color: #e0e0e0; border: 1px solid #333333; border-radius: 3px; padding: 2px 6px; font-size: 9pt; }
        entry:focus { border-color: #d19a66; }
        paned separator { background-color: #1a1a1a; min-width: 1px; }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # The FORKING LAYOUT DONT FORKING TOUCH THIS I MEAN YOU CAN BUT AGAIN YOULL MOST PROBABLY BREAK IT 
        m_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(m_box)
        tbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        tbar.get_style_context().add_class("top-bar")
        m_box.pack_start(tbar, False, False, 0)
        
        self.menu = Gtk.Menu()
        self.build_menu()
        self.btn_opts = Gtk.MenuButton(label="Options")
        self.btn_opts.get_style_context().add_class("pilll-button")
        self.btn_opts.set.popup(self.menu)
        tbar.pack_start(self.bin_opts, False, False, 0)

        self.btn_vim = Gtk.TggleButton(label="Vim")
        slef.btn_vim.get_style_context().add_class("pill-button")
        self.btn_vim.connect("Toggled", self.toggle_vim)
        self.btn_render = Gtk.Button(label="Render")
        self.btn_render.get_style_context().add_class("pill-button")
        self.btn_render.connect("clicked", self.toggle_render)
        tbar.pack_end(self.btn_vim, False, False, 0)
        tbar.pack_end(self.btn_render, False, False, 0)

        #EDITOR SPLIT I REPEAT EDITOR SPLIT 

        self.panned = Gtk.Panned(orientation=Gtk.Orientation.HORIZONTAL)
        m_box.pac_start(self.paned, True, True, 0)
        ed_box = Gtk.Box(oritation=Gtk.Orientation.HORIZONTAL)
        self.line_nums = Gtk.TextView()
        self.line_nums.get_style_context().add_class("Line Numbers")
        self.line_nums.set_editable(False)
        self.line_nums.set_cursor_visible(False)
        self.line_nums_buf = self.lines_nums.get_buffer()
        ed_box.pack_start(self.line_nums, False, False, 0)
        if not self.show_lines: self.line_nums.hide()

        self.scroll = Gtk.ScrollWindow()
        ed_box.pack_start(self.scroll, True, True, 0)
        self.tview = Gtk.TextView()
        self.tview.set_wrap_mode(Gtk.WrapMode.WORD if self.wrap else Gtk.WrapMode.NONE)
        self.tview.set_left_margin(15); self.tview.set_right_margin(15); self.tview.set_top_margin(10); self.tview.set_bottom_margin(10)
        self.buf = self.tview.get_buffer()

        #TAGS I WANNA TAKE MY LAPTOP AND THROW IT AGAINST WALL AT THIS POINT


        self.buf.create_tag("Bold", weight=Pango.Weight.BOLD)
        self.buf.create_tag("Italic", style=Pango.Style.ITALIC)
        self.buf.create_tag("search-match", background="#d19a66")
        self.buf.create_tag("syn_keyword", foregorund="#56b6c2")
        self.buf.create_tag("syn_string", foreground="#98c379")
        slef.buf.create_tag("syn_comment", foreground="#5c6370", style=Pango.Style.ITALIC)

        self.scroll.add(self.tview)
        self.panned.pack1(ed_box, resize=True, shrink=False)
        

        #NVM i just masterbated i dont feel the urge to throw my latop and do gencide

         # ForkingRender Of tHE VIEW
        self.render_scroll = Gtk.ScrolledWindow()
        self.r_view = Gtk.TextView()
        self.r_view.set_editable(False); self.r_view.set_cursor_visible(False); self.r_view.set_left_margin(15); self.r_view.set_right_margin(15); self.r_view.set_top_margin(10)
        self.r_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.r_buf = self.r_view.get_buffer()
        self.r_buf.create_tag("r_bold", weight=Pango.Weight.BOLD)
        self.r_buf.create_tag("r_italic", style=Pango.Style.ITALIC)
        self.render_scroll.add(self.r_view)
        self.paned.pack2(self.render_scroll, resize=False, shrink=False)
        self.render_scroll.hide()

        #Find Bar

        self.find.rev = Gtk.Revealer()
        f_box = Gtk.Box(Orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        f_box.get_style_context().add_class("Find-Bar")
        self.find_entry = Gtk.Entry()
        self.find_entry.set_placeholder_text("Find...")
        self.find_entry.connect("changed", self.on_search)
        self.find_entry.connect("key-press-event", self.on_search_key)
        btn_close = Gtk.Button(label="Close")
        btn_close.connect("clicked", lambda w: self.find_rev.set_reveal_child(False))
        f_box.pack_start(self.find_entry, True, True, 0)
        f_box.pack_start(btn_close, False, False, 0)
        self.find_rev.add(f_box)
        m_box.pack_start(self.find_rev, False, False, 0)

        #Status Bar (My tags are now better as i have stated to work on this prject seriously its  gonna be my first project)

        sbar = Gtk.Box(orientation=Gtk.Orientation.Horizontal)
        sbar.get_style_context().add_class("status-bar")
        m_box.pack_end(sbar, False, False, 0)
        self.lbl_status = Gtk.Label(label="")
        self.lbl_status.set_xalign(0)
        sbar.pack_start(self.lbl_status, False, False, 0)

        # Signals
        self.tview.connect("key-press-event", self.handel_vim_key)
        self.tview.connnect("key-press-event", self.handel_keys)
        self.buf.connect("modified-changed", self.on.modified)
        self.buf.connect("notify::cursor-position", lambda b, p: self. update_status())
        self.scroll.get_vadjustment().connect("value-changed", self.sync_line_nums)

        self.accel = Gtk.AccelGroup()
        self.add_accel_group(self.accel)
        self.btn_render.add_accelerator("clicked", self.accel, ord('R'), Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.update_status()

    def build_menu(self):
        for c in self.menu.get_children(): self.menu.remove(c)
        for lbl, cb in [("New", self.new_file), ("Open", self.open_file), ("Save", self.save_file), ("Save As...", self.save_as)]:
            i = Gtk.MenuItem(label=lbl); i.connect("activate", cb); self.menu.append(i)
        self.menu.append(Gtk.SeparatorMenuItem())

        # Recnts
        rec_mennu = Gtk.Menu()
        if not self.recents:
            i = Gtk.MenuItem(label="No recent files"); i.set_sensitive(False); rec_menu.append(i)
        else:
            for f in self.recents[:5]:
                i = Gtk.MenuItem(label=os.path.basename(f)); i.connect("activate", lambda w, p=f: self.open_file(path=p)); rec_menu.append(i)
        rec_item = Gtk.MenuItem(label="Recent Files"); rec_item.set_submenu(rec_menu); self.menu.append(rec_item)
        self.menu.append(Gtk.SeparatorMenuItem())

        # Toggles
        self.chk_lines = Gtk.CheckMenuItem(label="Show Line Numbers"); self.chk_lines.set_active(self.show_lines); self.chk_lines.connect("toggled", self.toggle_lines); self.menu.append(self.chk_lines)
        self.chk_wrap = Gtk.CheckMenuItem(label="Word Wrap"); self.chk_wrap.set_active(self

.wrap); self.chk_wrap.connect("toggled", self.toggle_wrap); self.menu.append(self.chk_wrap)
        self.chk_syn = Gtk.CheckMenuItem(label="Syntax Highlighting"); self.chk_syn.set_active(self.syntax); self.chk_syn.connect("toggled", self.toggle_syntax); self.menu.append(self.chk_syn)
        
        self.menu.append(Gtk.SeparatorMenuItem())
        q = Gtk.MenuItem(label="Quit"); q.connect("activate", Gtk.main_quit); self.menu.append(q)
        self.menu.show_all()
def load_recents(self):
        if os.path.exists(self.recent_path):
            try:
                with open(self.recent_path, "r") as f: return json.load(f)
            except: # idc
                return []
        return []

    def save_recents(self):
        with open(self.recent_path, "w") as f: json.dump(self.recents, f)

    def add_recent(self, path):
        if path in self.recents: self.recents.remove(path)
        self.recents.insert(0, path)
        self.recents = self.recents[:5]
        self.save_recents(); self.build_menu()

    def toggle_lines(self, w=None):
        self.show_lines = w.get_active() if w else not self.show_lines
        if self.show_lines: self.line_nums.show(); self.sync_line_nums()
        else: self.line_nums.hide()

    def toggle_wrap(self, w=None):
        self.wrap = not self.wrap
        self.tview.set_wrap_mode(Gtk.WrapMode.WORD if self.wrap else Gtk.WrapMode.NONE)
        if hasattr(self, 'chk_wrap'): self.chk_wrap.set_active(self.wrap)

def toggle_syntax(self, w=None):
        self.syntax = not self.syntax
        if not self.syntax:
            s, e = self.buf.get_bounds()
            for t in ["syn_keyword", "syn_string", "syn_comment"]: self.buf.remove_tag_by_name(t, s, e)
        else: self.do_syntax()
        if hasattr(self, 'chk_syn'): self.chk_syn.set_active(self.syntax)
        
    def toggle_indent(self, w=None):
        self.indent = "2s" if self.indent == "4s" else "Tab" if self.indent == "2s" else "4s"
        self.btn_indent.set_label(self.indent); self.update_status()

    def toggle_render(self, w=None):
        if self.render_scroll.get_visible(): self.render_scroll.hide()
        else: self.render_scroll.show(); self.render_tags()

def on_modified(self, w):
        self.modified = self.buf.get_modified(); self.update_status()

    def on_text_changed(self, w):
        self.update_status()
        s, e = self.buf.get_bounds()
        self.buf.remove_tag_by_name("search-match", s, e) # un-highlight search on type
        if self.show_lines: self.sync_line_nums()
        if self.syntax:
            if self.syntax_timeout: GLib.source_remove(self.syntax_timeout)
            self.syntax_timeout = GLib.timeout_add(300, self._do_syntax_timeout) # throttle this so it doesn't lag to death

         def _do_syntax_timeout(self):
        self.do_syntax(); self.syntax_timeout = None; return False

    def sync_line_nums(self, w=None):
        self.line_nums_buf.set_text("\n".join(str(i+1) for i in range(self.buf.get_line_count())))
        self.line_nums.get_vadjustment().set_value(self.scroll.get_vadjustment().get_value())

    def handle_keys(self, w, event):
        # ctrl+f
        if event.keyval == Gdk.keyval_from_name("f") and event.state & Gdk.ModifierType.CONTROL_MASK:
            self.find_rev.set_reveal_child(True); self.find_entry.grab_focus(); return True
        # alt+z
        if event.keyval == Gdk.keyval_from_name("z") and event.state & Gdk.ModifierType.MOD1_MASK:
            self.toggle_wrap(); return True

            # auto-indent hack
        if event.keyval == Gdk.keyval_from_name("Return") and not self.vim_mode:
            buf = self.buf; itr = buf.get_iter_at_mark(buf.get_insert()); ln = itr.get_line()
            if ln > 0:
                ps = buf.get_iter_at_line(ln - 1); pe = ps.copy(); pe.forward_to_line_end()
                prev = buf.get_text(ps, pe, True)
                indent = re.match(r'^[ \t]*', prev).group(0) # faster than looping chars
                
                if prev.rstrip().endswith(":"):
                    sz = 4 if self.indent == "4s" else 2 if self.indent == "2s" else 1
                    indent += (" " if "s" in self.indent else "\t") * sz
                
                if indent: GLib.idle_add(lambda: buf.insert_at_cursor(indent))
        return False

    def toggle_vim(self, w=None):
        self.vim_mode = self.btn_vim.get_active()
        if self.vim_mode:
            self.vim_state = "NORMAL"; self.vim_cmd_mode = False; self.vim_cmd = ""; self.btn_vim.set_label("Vim: ON")
        else: self.btn_vim.set_label("Vim")
        self.update_status()

    def handle_vim_key(self, w, event):
        if not self.vim_mode: return False

        keyname = Gdk.keyval_name(event.keyval)
        char = chr(Gdk.keyval_to_unicode(event.keyval)) if Gdk.keyval_to_unicode(event.keyval) != 0 else ""

        if self.vim_cmd_mode:
            if keyname == "Return": self.run_vim_cmd(); return True
            elif keyname == "Escape": self.vim_cmd_mode = False; self.vim_cmd = ""
            elif keyname == "BackSpace":
                self.vim_cmd = self.vim_cmd[:-1]
                if not self.vim_cmd: self.vim_cmd_mode = False
            else: self.vim_cmd += char
            self.update_status(); return True

        if self.vim_state == "INSERT":
            if keyname == "Escape":
                self.vim_state = "NORMAL"; self.update_status(); return True
            return False

        if keyname == "Escape": self.vim_state = "NORMAL"; self.update_status(); return True

        if char == ':': self.vim_cmd_mode = True; self.vim_cmd = ":"; self.update_status(); return True
        elif char == 'i': self.vim_state = "INSERT"; self.update_status(); return True
        elif char in ['h', 'j', 'k', 'l', 'x']:
            mark = self.buf.get_insert(); itr = self.buf.get_iter_at_mark(mark)
            if char == 'h': itr.backward_char()
            elif char == 'l': itr.forward_char()
            elif char == 'j': itr.forward_line()
            elif char == 'k': itr.backward_line()
            elif char == 'x':
                end = itr.copy()
                if not end.ends_line(): end.forward_char()
                self.buf.delete(itr, end)
            self.buf.place_cursor(itr); self.tview.scroll_to_mark(mark, 0.0, True, 0.0, 0.0); return True
        return True

    def run_vim_cmd(self):
        cmd = self.vim_cmd.strip(":").strip()
        if cmd == "w": self.save_file()
        elif cmd == "q": Gtk.main_quit()
        elif cmd == "wq": self.save_file(); Gtk.main_quit()
        self.vim_cmd_mode = False; self.vim_cmd = ""; self.update_status()

    def render_tags(self, w=None):
        s, e = self.buf.get_bounds()
        parts = re.split(r'(<ts=\d+>|</ts=\d+>|<italic>|</italic>|<bold>|</bold>)', self.buf.get_text(s, e, False))
        self.r_buf.set_text("")
        tags = []; tbl = self.r_buf.get_tag_table()
        
        for p in parts:
            if not p: continue
            if p == "<bold>": tags.append("r_bold")
            elif p == "</bold>" and "r_bold" in tags: tags.remove("r_bold")
            elif p == "<italic>": tags.append("r_italic")
            elif p == "</italic>" and "r_italic" in tags: tags.remove("r_italic")
            elif re.match(r'<ts=\d+>', p):
                sz = p.split("=")[1][:-1]; tname = f"r_ts_{sz}"
                if not tbl.lookup(tname): self.r_buf.create_tag(tname, scale=float(sz)/11.0)
                tags.append(tname)
            elif re.match(r'</ts=\d+>', p):
                for i in range(len(tags)-1, -1, -1):
                    if tags[i].startswith("r_ts_"): tags.pop(i); break
            else: self.r_buf.insert_with_tags_by_name(self.r_buf.get_end_iter(), p, *tags)

    def do_syntax(self):
        s, e = self.buf.get_bounds()
        for t in ["syn_keyword", "syn_string", "syn_comment"]: self.buf.remove_tag_by_name(t, s, e)
        text = self.buf.get_text(s, e, False)
        
        # comments
        for m in re.finditer(r'(#.*?$)', text, re.MULTILINE):
            self.buf.apply_tag_by_name("syn_comment", self.buf.get_iter_at_offset(m.start(1)), self.buf.get_iter_at_offset(m.end(1)))
        # strings
        for m in re.finditer(r'("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')', text):
            self.buf.apply_tag_by_name("syn_string", self.buf.get_iter_at_offset(m.start(1)), self.buf.get_iter_at_offset(m.end(1)))
        # keywords
        for m in re.finditer(r'\b(' + '|'.join(KWS) + r')\b', text):
            self.buf.apply_tag_by_name("syn_keyword", self.buf.get_iter_at_offset(m.start(1)), self.buf.get_iter_at_offset(m.end(1)))

    def on_search(self, w):
        q = self.find_entry.get_text()
        s, e = self.buf.get_bounds()
        self.buf.remove_tag_by_name("search-match", s, e)
        if q:
            i = s.copy()
            while True:
                m = i.forward_search(q, Gtk.TextSearchFlags.CASE_INSENSITIVE, e)
                if not m: break
                self.buf.apply_tag_by_name("search-match", m[0], m[1]); i = m[1]

        def on_search_key(self, w, event):
        if event.keyval == Gdk.keyval_from_name("Escape"):
            s, e = self.buf.get_bounds()
            self.buf.remove_tag_by_name("search-match", s, e)
            self.find_rev.set_reveal_child(False); self.tview.grab_focus(); return True
        return False

    def new_file(self, w=None):
        self.buf.set_text(""); self.cur_file = None; self.buf.set_modified(False); self.update_status()

    def open_file(self, w=None, path=None):
        if path: self.open_specific_file(path); return
        dlg = Gtk.FileChooserNative.new("Open File", self, Gtk.FileChooserAction.OPEN, "_Open", "_Cancel")
        filt = Gtk.FileFilter(); filt.set_name("Text/Python Files"); filt.add_mime_type("text/plain"); filt.add_pattern("*.py"); dlg.add_filter(filt)
        if dlg.run() == Gtk.ResponseType.ACCEPT: self.open_specific_file(dlg.get_filename())
        dlg.destroy()

    def open_specific_file(self, path):
        if not os.path.exists(path):
            print(f"Error: {path} gone.")
            if path in self.recents: self.recents.remove(path); self.save_recents(); self.build_menu()
            return
        try:
            with open(path, "r") as f: content = f.read()
            self.buf.set_text(content); self.cur_file = path; self.buf.set_modified(False); self.add_recent(path); self.update_status()
        except Exception as ex: print(f"Failed: {ex}")

    def save_file(self, w=None):
        if not self.cur_file: self.save_as(); return
        try:
            s, e = self.buf.get_bounds()
            with open(self.cur_file, "w") as f: f.write(self.buf.get_text(s, e, False))
            self.buf.set_modified(False); self.add_recent(self.cur_file); self.update_status()
        except Exception as ex: print(f"Save failed: {ex}")

    def save_as(self, w=None):
        dlg = Gtk.FileChooserNative.new("Save File As", self, Gtk.FileChooserAction.SAVE, "_Save", "_Cancel")
        dlg.set_do_overwrite_confirmation(True)
        if dlg.run() == Gtk.ResponseType.ACCEPT: self.cur_file = dlg.get_filename(); self.save_file()
        dlg.destroy()

    def update_status(self):
        fname = os.path.basename(self.cur_file) if self.cur_file else "untitled"
        mod = '<span foreground="#e06c75">●</span>' if self.modified else '<span foreground="#3e3e3e">●</span>'
        
        if not self.vim_mode: mode = '<span foreground="#abb2bf">[STANDARD]</span>'
        elif self.vim_cmd_mode: mode = f'<span foreground="#d19a66">[{self.vim_cmd}]</span>'
        elif self.vim_state == "NORMAL": mode = '<span foreground="#d19a66">[NORMAL]</span>'
        else: mode = '<span foreground="#56b6c2">[INSERT]</span>'
            
        itr = self.buf.get_iter_at_mark(self.buf.get_insert())
        s, e = self.buf.get_bounds()
        words = len(self.buf.get_text(s, e, True).split())
        
        self.lbl_status.set_markup(f"{mode} {fname} {mod}  |  Ln {itr.get_line() + 1}, Col {itr.get_line_offset() + 1}  |  Words: {words}  |  UTF-8")
        self.set_title(f"{'● ' if self.modified else ''}{fname} - DarkVim Editor")

if __name__ == "__main__":
    win = DarkEditor()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

    #I just wanted to tell you that I have been nothing but passionate about this project. I've really been giving it my all while working on i.

#This project was inspired by the operating system I use—DHH's Arch—which is really good. That aside, I know AI is controversial and all; I don't personally support it. I used it once in this project when I wanted to get help solving some bugs, I guess.

#This will probably be my second-to-last commit, as I plan to debug my code once more.

#So hey mate, if you could kindly star this repo, it would mean a lot. It took quite a while for me to complete. I'll say it again: Love you, mate 'u'
