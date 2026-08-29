#!/usr/bin/env python3
"""PyRite — A minimal dark-mode text editor for GTK-based Linux desktops."""
import gi, re, os, json, sys, argparse
gi.require_version("Gtk", "3.0")
gi.require_version("GtkSource", "4")
from gi.repository import Gtk, Gdk, Pango, GLib, Gio, GtkSource


CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "pyrite")
RECENT_PATH = os.path.join(CONFIG_DIR, "recents.json")
ACCENT_PATH = os.path.join(CONFIG_DIR, "accent.json")
MAX_RECENTS = 10


def ensure_config_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def save_json(path, data):
    ensure_config_dir()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f)


def lighten(hex_color, amount=0.18):
    r, g, b = (int(hex_color[i:i+2], 16) for i in (1, 3, 5))
    return f"#{int(r+(255-r)*amount):02x}{int(g+(255-g)*amount):02x}{int(b+(255-b)*amount):02x}"


CSS_TEMPLATE = """
window {{ background-color: #101315; }}
.top-bar {{ background-color: #0c0e10; padding: 4px 8px; border-bottom: 1px solid #080a0b; }}
.pill-button {{
    background: #343d41; color: #cacccc; border-radius: 4px;
    padding: 2px 10px; border: none; box-shadow: none;
    font-family: 'JetBrains Mono', monospace; font-size: 9pt; outline: none;
}}
.pill-button:hover {{ background: #4b4e55; color: #ffffff; }}
.pill-button:active, .pill-button:checked {{
    background: #343d41; color: {accent}; font-weight: bold;
}}
.pill-button:checked:hover {{ background: #4b4e55; color: {accent}; }}

.status-bar {{
    background-color: #0c0e10; color: #a5aeb4; padding: 4px 10px;
    border-top: 1px solid #343d41; font-family: 'JetBrains Mono', monospace; font-size: 9pt;
}}
.status-bar label {{ margin-right: 20px; }}

scrollbar {{ background-color: #101315; }}
scrollbar slider {{ background-color: #4b4e55; border-radius: 3px; min-width: 6px; min-height: 6px; }}
scrollbar slider:hover {{ background-color: {accent}; }}
scrollbar button {{ border: none; background: none; padding: 0; }}

menu {{ background-color: #0c0e10; border: 1px solid #343d41; }}
menuitem {{ color: #a5aeb4; padding: 2px 8px; font-size: 9pt; }}
menuitem:hover, menuitem:active {{ background-color: #343d41; color: #ffffff; }}
menuitem check {{ color: {accent}; background-color: transparent; }}
menuitem:checked check {{ color: {accent}; }}

.search-bar {{ background-color: #0c0e10; border-top: 1px solid #343d41; padding: 4px; }}
entry {{
    background-color: #101315; color: #cacccc; border: 1px solid #343d41;
    border-radius: 3px; padding: 2px 6px; font-size: 9pt;
}}
entry:focus {{ border-color: {accent}; }}
paned separator {{ background-color: #080a0b; min-width: 1px; }}

sourceview {{
    background-color: #101315; color: #cacccc;
    font-family: 'JetBrains Mono', monospace; font-size: 11pt;
}}
"""


class PyRiteEditor(Gtk.Window):
    def __init__(self, file_path=None):
        super().__init__(title="PyRite")
        self.set_default_size(900, 600)

        self.cur_file = None
        self.modified = False
        self.vim_mode = False
        self.vim_state = "NORMAL"
        self.vim_cmd = ""
        self.vim_cmd_mode = False
        self.vim_count = ""
        self.vim_yank = ""
        self.wrap = True
        self.words = 0
        self.deferred_id = None
        self.file_monitor = None

        ensure_config_dir()
        self.accent = self._load_accent()
        self.accent_hover = lighten(self.accent)
        self.recents = load_json(RECENT_PATH, [])

        self.css_provider = Gtk.CssProvider()
        self._apply_theme()

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(main_box)

        # --- top bar ---
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        top_bar.get_style_context().add_class("top-bar")
        main_box.pack_start(top_bar, False, False, 0)

        self.menu = Gtk.Menu()
        self._build_menu()

        self.btn_opts = Gtk.MenuButton(label="Options")
        self.btn_opts.get_style_context().add_class("pill-button")
        self.btn_opts.set_popup(self.menu)
        top_bar.pack_start(self.btn_opts, False, False, 0)

        self.btn_vim = Gtk.ToggleButton(label="Vim")
        self.btn_vim.get_style_context().add_class("pill-button")
        self.btn_vim.connect("toggled", self._toggle_vim)

        self.btn_render = Gtk.Button(label="Render")
        self.btn_render.get_style_context().add_class("pill-button")
        self.btn_render.connect("clicked", self._toggle_render)

        top_bar.pack_end(self.btn_vim, False, False, 0)
        top_bar.pack_end(self.btn_render, False, False, 0)

        # --- source view ---
        self.paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        main_box.pack_start(self.paned, True, True, 0)

        self.scroll = Gtk.ScrolledWindow()
        self.tview = GtkSource.View()
        self.tview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.tview.set_left_margin(15)
        self.tview.set_right_margin(15)
        self.tview.set_top_margin(10)
        self.tview.set_bottom_margin(10)
        self.tview.set_show_line_numbers(True)
        self.tview.set_highlight_current_line(True)
        self.tview.set_auto_indent(True)
        self.tview.set_insert_spaces_instead_of_tabs(True)
        self.tview.set_tab_width(4)
        self.tview.set_monospace(True)

        self.buf = self.tview.get_buffer()
        self.buf.set_max_undo_levels(100)
        self.buf.connect("modified-changed", self._on_modified)
        self.buf.connect("changed", self._on_text_changed)

        # syntax highlighting
        self.lang_manager = GtkSource.LanguageManager.get_default()
        self.style_manager = GtkSource.StyleSchemeManager.get_default()
        self._apply_style_scheme()

        self.scroll.add(self.tview)
        self.paned.pack1(self.scroll, resize=True, shrink=False)

        # --- render view ---
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
        self._r_ts_tags = set()
        self.render_scroll.add(self.r_view)
        self.paned.pack2(self.render_scroll, resize=False, shrink=False)
        self.render_scroll.hide()

        # --- search bar ---
        self.search_rev = Gtk.Revealer()
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        search_box.get_style_context().add_class("search-bar")

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Find...")
        self.search_entry.connect("search-changed", self._on_search)
        self.search_entry.connect("next-match", lambda e: self._search_next())
        self.search_entry.connect("previous-match", lambda e: self._search_prev())
        self.search_entry.connect("stop-search", lambda e: self._close_search())

        self.replace_entry = Gtk.Entry()
        self.replace_entry.set_placeholder_text("Replace...")

        btn_replace_one = Gtk.Button(label="Replace")
        btn_replace_one.connect("clicked", lambda w: self._replace_one())
        btn_replace_all = Gtk.Button(label="Replace All")
        btn_replace_all.connect("clicked", lambda w: self._replace_all())

        btn_close = Gtk.Button(label="Close")
        btn_close.connect("clicked", lambda w: self._close_search())

        search_box.pack_start(self.search_entry, True, True, 0)
        search_box.pack_start(self.replace_entry, False, False, 0)
        search_box.pack_start(btn_replace_one, False, False, 0)
        search_box.pack_start(btn_replace_all, False, False, 0)
        search_box.pack_start(btn_close, False, False, 0)
        self.search_rev.add(search_box)
        main_box.pack_start(self.search_rev, False, False, 0)

        # --- status bar ---
        s_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        s_bar.get_style_context().add_class("status-bar")
        main_box.pack_end(s_bar, False, False, 0)

        self.lbl_status = Gtk.Label(label="")
        self.lbl_status.set_xalign(0)
        s_bar.pack_start(self.lbl_status, False, False, 0)

        self.btn_indent = Gtk.Button(label="4 spaces")
        self.btn_indent.get_style_context().add_class("pill-button")
        self.btn_indent.set_relief(Gtk.ReliefStyle.NONE)
        self.btn_indent.set_size_request(50, -1)
        self.btn_indent.connect("clicked", self._toggle_indent)
        s_bar.pack_end(self.btn_indent, False, False, 0)

        # --- accelerators ---
        accel = Gtk.AccelGroup()
        self.add_accel_group(accel)
        for key, cb in [
            ("n", self._new_file), ("o", self._open_file), ("s", self._save_file),
            ("f", self._open_search), ("r", self._toggle_render),
        ]:
            accel.connect(Gdk.keyval_from_name(key), Gdk.ModifierType.CONTROL_MASK,
                          Gtk.AccelFlags.VISIBLE, self._make_accel_cb(cb))

        self.connect("key-press-event", self._on_key)
        self.buf.connect("notify::cursor-position", lambda b, p: self._update_status())

        # --- drag and drop ---
        self.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        self.drag_dest_add_uri_targets()
        self.connect("drag-data-received", self._on_drag_data)

        # --- file monitor ---
        self._monitor_id = None

        if file_path:
            self._open_path(file_path)
        self._update_status()

    # ── theme ──

    def _load_accent(self):
        c = load_json(ACCENT_PATH, {}).get("accent", "#61A03C")
        return c if re.match(r'^#[0-9a-fA-F]{6}$', c) else "#61A03C"

    def _save_accent(self):
        save_json(ACCENT_PATH, {"accent": self.accent})

    def _apply_theme(self):
        css = CSS_TEMPLATE.format(accent=self.accent)
        self.css_provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _apply_style_scheme(self):
        for sid in ("oblivion", "classic"):
            scheme = self.style_manager.get_scheme(sid)
            if scheme:
                self.buf.set_style_scheme(scheme)
                break

    # ── menu ──

    def _build_menu(self):
        for c in self.menu.get_children():
            self.menu.remove(c)

        items = [
            ("New", self._new_file), ("Open", self._open_file),
            ("Save", self._save_file), ("Save As...", self._save_as),
        ]
        for label, cb in items:
            item = Gtk.MenuItem(label=label)
            item.connect("activate", cb)
            self.menu.append(item)

        self.menu.append(Gtk.SeparatorMenuItem())

        # recents submenu
        rec_menu = Gtk.Menu()
        if not self.recents:
            empty = Gtk.MenuItem(label="No recent files")
            empty.set_sensitive(False)
            rec_menu.append(empty)
        else:
            for f in self.recents[:MAX_RECENTS]:
                item = Gtk.MenuItem(label=os.path.basename(f))
                item.connect("activate", lambda w, p=f: self._open_path(p))
                rec_menu.append(item)
        rec_item = Gtk.MenuItem(label="Recent Files")
        rec_item.set_submenu(rec_menu)
        self.menu.append(rec_item)
        self.menu.append(Gtk.SeparatorMenuItem())

        # toggles
        self.chk_wrap = Gtk.CheckMenuItem(label="Word Wrap")
        self.chk_wrap.set_active(self.wrap)
        self.chk_wrap.connect("toggled", self._toggle_wrap)
        self.menu.append(self.chk_wrap)

        self.menu.append(Gtk.SeparatorMenuItem())

        self.acc_item = Gtk.MenuItem(label="Accent Color...")
        self.acc_item.connect("activate", self._choose_accent)
        self.menu.append(self.acc_item)

        about_item = Gtk.MenuItem(label="About")
        about_item.connect("activate", self._show_about)
        self.menu.append(about_item)

        self.menu.append(Gtk.SeparatorMenuItem())
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self._quit_app)
        self.menu.append(quit_item)
        self.menu.show_all()

    # ── recent files ──

    def _add_recent(self, path):
        if path in self.recents:
            self.recents.remove(path)
        self.recents.insert(0, path)
        self.recents = self.recents[:MAX_RECENTS]
        save_json(RECENT_PATH, self.recents)
        self._build_menu()

    # ── file operations ──

    def _new_file(self, w=None):
        if not self._confirm_discard():
            return
        self.buf.set_text("")
        self.cur_file = None
        self._stop_monitor()
        self.buf.set_modified(False)
        self.words = 0
        self._update_status()
        self.set_title("PyRite")

    def _open_file(self, w=None):
        if not self._confirm_discard():
            return
        dlg = Gtk.FileChooserNative.new("Open File", self, Gtk.FileChooserAction.OPEN, "_Open", "_Cancel")
        filt = Gtk.FileFilter()
        filt.set_name("Text Files")
        filt.add_mime_type("text/plain")
        filt.add_pattern("*")
        dlg.add_filter(filt)
        if dlg.run() == Gtk.ResponseType.ACCEPT:
            self._open_path(dlg.get_filename())
        dlg.destroy()

    def _open_path(self, path):
        if not os.path.isfile(path):
            return
        try:
            loader = GtkSource.FileLoader(buffer=self.buf, file=Gio.File.new_for_path(path))
            loader.load_async(GLib.PRIORITY_DEFAULT, None, self._on_file_loaded, path)
        except Exception as ex:
            self._show_error(f"Failed to open: {ex}")

    def _on_file_loaded(self, loader, result, path):
        try:
            loader.load_finish(result)
        except Exception as ex:
            self._show_error(f"Failed to open: {ex}")
            return
        self.cur_file = path
        self.buf.set_modified(False)
        self._detect_language()
        self._start_monitor(path)
        self._add_recent(path)
        self._update_status()
        self.set_title(f"{os.path.basename(path)} — PyRite")

    def _detect_language(self):
        if self.cur_file:
            lang = self.lang_manager.guess_language(self.cur_file, None)
            if lang:
                self.buf.set_language(lang)

    def _save_file(self, w=None):
        if not self.cur_file:
            return self._save_as()
        try:
            saver = GtkSource.FileSaver(buffer=self.buf, file=Gio.File.new_for_path(self.cur_file))
            saver.save_async(GLib.PRIORITY_DEFAULT, None, self._on_file_saved, None)
            return True
        except Exception as ex:
            self._show_error(f"Save failed: {ex}")
            return False

    def _on_file_saved(self, saver, result, data):
        try:
            saver.save_finish(result)
            self.buf.set_modified(False)
            self._add_recent(self.cur_file)
            self._update_status()
        except Exception as ex:
            self._show_error(f"Save failed: {ex}")

    def _save_as(self, w=None):
        dlg = Gtk.FileChooserNative.new("Save As", self, Gtk.FileChooserAction.SAVE, "_Save", "_Cancel")
        dlg.set_do_overwrite_confirmation(True)
        accepted = dlg.run() == Gtk.ResponseType.ACCEPT
        filename = dlg.get_filename() if accepted else None
        dlg.destroy()
        if filename:
            self.cur_file = filename
            self._detect_language()
            return self._save_file()
        return False

    # ── file monitoring ──

    def _start_monitor(self, path):
        self._stop_monitor()
        try:
            f = Gio.File.new_for_path(path)
            self.file_monitor = f.monitor_file(Gio.FileMonitorFlags.NONE, None)
            self._monitor_id = self.file_monitor.connect("changed", self._on_file_changed)
        except Exception:
            pass

    def _stop_monitor(self):
        if self.file_monitor:
            if self._monitor_id:
                self.file_monitor.disconnect(self._monitor_id)
                self._monitor_id = None
            self.file_monitor.cancel()
            self.file_monitor = None

    def _on_file_changed(self, monitor, file, other_file, event_type):
        if event_type == Gio.FileMonitorEvent.CHANGED and not self.buf.get_modified():
            dlg = Gtk.MessageDialog(
                transient_for=self, modal=True,
                message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.NONE,
                text="File changed on disk. Reload?")
            dlg.add_button("Cancel", Gtk.ResponseType.CANCEL)
            dlg.add_button("Reload", Gtk.ResponseType.OK)
            if dlg.run() == Gtk.ResponseType.OK:
                self.buf.set_text("")
                self._open_path(self.cur_file)
            dlg.destroy()

    # ── search ──

    def _open_search(self, w=None):
        self.search_rev.set_reveal_child(True)
        self.search_entry.grab_focus()

    def _close_search(self, w=None):
        s, e = self.buf.get_bounds()
        self.search_rev.set_reveal_child(False)
        self.tview.grab_focus()

    def _on_search(self, entry):
        query = entry.get_text()
        s, e = self.buf.get_bounds()
        # remove old tags
        self.buf.remove_tag_by_name("search-match", s, e) if self.buf.get_tag_table().lookup("search-match") else None
        if not query:
            return
        if not self.buf.get_tag_table().lookup("search-match"):
            self.buf.create_tag("search-match", background=self.accent, foreground="#101315")
        i = s.copy()
        first = None
        while True:
            m = i.forward_search(query, Gtk.TextSearchFlags.CASE_INSENSITIVE, e)
            if not m:
                break
            self.buf.apply_tag_by_name("search-match", m[0], m[1])
            if first is None:
                first = m
            i = m[1]
        if first:
            self.buf.select_range(first[0], first[1])
            self.tview.scroll_to_iter(first[0], 0.0, True, 0.0, 0.0)

    def _search_next(self):
        cur = self.buf.get_iter_at_mark(self.buf.get_insert())
        query = self.search_entry.get_text()
        if not query:
            return
        s, e = self.buf.get_bounds()
        m = cur.forward_search(query, Gtk.TextSearchFlags.CASE_INSENSITIVE, e)
        if not m:
            m = s.forward_search(query, Gtk.TextSearchFlags.CASE_INSENSITIVE, e)
        if m:
            self.buf.select_range(m[0], m[1])
            self.tview.scroll_to_iter(m[0], 0.0, True, 0.0, 0.0)

    def _search_prev(self):
        cur = self.buf.get_iter_at_mark(self.buf.get_insert())
        query = self.search_entry.get_text()
        if not query:
            return
        s, e = self.buf.get_bounds()
        # manual backward search
        i = s.copy()
        last = None
        while True:
            m = i.forward_search(query, Gtk.TextSearchFlags.CASE_INSENSITIVE, e)
            if not m or m[0].compare(cur) >= 0:
                break
            last = m
            i = m[1]
        if last is None:
            i = s.copy()
            while True:
                m = i.forward_search(query, Gtk.TextSearchFlags.CASE_INSENSITIVE, e)
                if not m:
                    break
                last = m
                i = m[1]
        if last:
            self.buf.select_range(last[0], last[1])
            self.tview.scroll_to_iter(last[0], 0.0, True, 0.0, 0.0)

    def _replace_one(self):
        query = self.search_entry.get_text()
        repl = self.replace_entry.get_text()
        if not query:
            return
        s, e = self.buf.get_bounds()
        m = s.forward_search(query, Gtk.TextSearchFlags.CASE_INSENSITIVE, e)
        if m:
            self.buf.begin_user_action()
            self.buf.delete(m[0], m[1])
            self.buf.insert_at_cursor(repl)
            self.buf.end_user_action()

    def _replace_all(self):
        query = self.search_entry.get_text()
        repl = self.replace_entry.get_text()
        if not query:
            return
        s, e = self.buf.get_bounds()
        text = self.buf.get_text(s, e, True)
        new_text = text.replace(query, repl)
        if new_text != text:
            self.buf.begin_user_action()
            self.buf.set_text(new_text)
            self.buf.end_user_action()

    # ── vim mode ──

    def _toggle_vim(self, w=None):
        self.vim_mode = self.btn_vim.get_active()
        if self.vim_mode:
            self.vim_state = "NORMAL"
            self.vim_cmd_mode = False
            self.vim_cmd = ""
            self.vim_count = ""
            self.btn_vim.set_label("Vim: ON")
        else:
            self.btn_vim.set_label("Vim")
        self._update_status()

    def _on_key(self, w, event):
        if self.vim_mode:
            return self._handle_vim(event)
        key = Gdk.keyval_to_lower(event.keyval)
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        if ctrl:
            if key == Gdk.KEY_f:
                self._open_search()
                return True
            if key == Gdk.KEY_z:
                self.buf.undo()
                return True
            if key == Gdk.KEY_y:
                self.buf.redo()
                return True
            return False
        if key == Gdk.KEY_z and (event.state & Gdk.ModifierType.MOD1_MASK):
            self._toggle_wrap()
            return True
        if key == Gdk.KEY_Return and not self.vim_mode:
            self._auto_indent()
            return False
        return False

    def _handle_vim(self, event):
        if event.state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.MOD1_MASK):
            return False

        keyval = event.keyval
        keyname = Gdk.keyval_name(keyval)
        char = chr(Gdk.keyval_to_unicode(keyval)) if Gdk.keyval_to_unicode(keyval) != 0 else ""

        # count prefix
        if self.vim_state == "NORMAL" and char.isdigit() and char != "0":
            self.vim_count += char
            self._update_status()
            return True

        count = int(self.vim_count) if self.vim_count else 1
        self.vim_count = ""

        if self.vim_cmd_mode:
            if keyname == "Return":
                self._run_vim_cmd()
                return True
            elif keyname == "Escape":
                self.vim_cmd_mode = False
                self.vim_cmd = ""
            elif keyname == "BackSpace":
                self.vim_cmd = self.vim_cmd[:-1]
                if not self.vim_cmd:
                    self.vim_cmd_mode = False
            else:
                self.vim_cmd += char
            self._update_status()
            return True

        if self.vim_state == "INSERT":
            if keyname == "Escape":
                self.vim_state = "NORMAL"
                self._update_status()
                return True
            return False

        # NORMAL mode
        if keyname == "Escape":
            self.vim_state = "NORMAL"
            self._update_status()
            return True

        if char == ':':
            self.vim_cmd_mode = True
            self.vim_cmd = ":"
            self._update_status()
            return True

        if char == 'i':
            self.vim_state = "INSERT"
            self._update_status()
            return True

        if char == 'a':
            itr = self.buf.get_iter_at_mark(self.buf.get_insert())
            if not itr.ends_line():
                itr.forward_char()
            self.buf.place_cursor(itr)
            self.vim_state = "INSERT"
            self._update_status()
            return True

        if char == 'A':
            itr = self.buf.get_iter_at_mark(self.buf.get_insert())
            itr.forward_to_line_end()
            self.buf.place_cursor(itr)
            self.vim_state = "INSERT"
            self._update_status()
            return True

        if char == 'o':
            itr = self.buf.get_iter_at_mark(self.buf.get_insert())
            itr.forward_to_line_end()
            self.buf.place_cursor(itr)
            self.buf.insert_at_cursor("\n")
            self.vim_state = "INSERT"
            self._update_status()
            return True

        if char == 'O':
            itr = self.buf.get_iter_at_mark(self.buf.get_insert())
            itr.set_line_offset(0)
            self.buf.place_cursor(itr)
            self.buf.insert_at_cursor("\n")
            itr2 = self.buf.get_iter_at_mark(self.buf.get_insert())
            itr2.backward_line()
            self.buf.place_cursor(itr2)
            self.vim_state = "INSERT"
            self._update_status()
            return True

        # navigation
        if char in ('h', 'j', 'k', 'l'):
            mark = self.buf.get_insert()
            itr = self.buf.get_iter_at_mark(mark)
            for _ in range(count):
                if char == 'h' and itr.get_line_offset() > 0:
                    itr.backward_char()
                elif char == 'l' and not itr.ends_line():
                    itr.forward_char()
                elif char == 'j':
                    itr.forward_line()
                elif char == 'k':
                    itr.backward_line()
            self.buf.place_cursor(itr)
            self.tview.scroll_to_mark(mark, 0.0, True, 0.0, 0.0)
            self._update_status()
            return True

        # word motions
        if char == 'w':
            mark = self.buf.get_insert()
            itr = self.buf.get_iter_at_mark(mark)
            for _ in range(count):
                self._word_forward(itr)
            self.buf.place_cursor(itr)
            self.tview.scroll_to_mark(mark, 0.0, True, 0.0, 0.0)
            return True

        if char == 'b':
            mark = self.buf.get_insert()
            itr = self.buf.get_iter_at_mark(mark)
            for _ in range(count):
                self._word_backward(itr)
            self.buf.place_cursor(itr)
            self.tview.scroll_to_mark(mark, 0.0, True, 0.0, 0.0)
            return True

        if char == 'e':
            mark = self.buf.get_insert()
            itr = self.buf.get_iter_at_mark(mark)
            for _ in range(count):
                self._word_end(itr)
            self.buf.place_cursor(itr)
            self.tview.scroll_to_mark(mark, 0.0, True, 0.0, 0.0)
            return True

        # delete
        if char == 'x':
            mark = self.buf.get_insert()
            itr = self.buf.get_iter_at_mark(mark)
            for _ in range(count):
                if not itr.ends_line():
                    end = itr.copy()
                    end.forward_char()
                    self.buf.delete(itr, end)
            self._update_status()
            return True

        if char == 'd':
            # dd = delete line
            if self.vim_cmd == "d":
                self.vim_cmd = ""
                mark = self.buf.get_insert()
                itr = self.buf.get_iter_at_mark(mark)
                self.vim_yank = self.buf.get_text(itr, self._line_end(itr), True) + "\n"
                start = itr.copy()
                start.set_line_offset(0)
                if not itr.ends_line():
                    itr.forward_to_line_end()
                elif itr.get_line() > 0:
                    itr.backward_line()
                    itr.forward_to_line_end()
                self.buf.delete(start, itr)
                self._update_status()
                return True
            self.vim_cmd = "d"
            self._update_status()
            return True

        # yank
        if char == 'y':
            if self.vim_cmd == "y":
                self.vim_cmd = ""
                mark = self.buf.get_insert()
                itr = self.buf.get_iter_at_mark(mark)
                self.vim_yank = self.buf.get_text(itr, self._line_end(itr), True) + "\n"
                self._update_status()
                return True
            self.vim_cmd = "y"
            self._update_status()
            return True

        # paste
        if char == 'p' and self.vim_yank:
            mark = self.buf.get_insert()
            itr = self.buf.get_iter_at_mark(mark)
            if self.vim_yank.endswith("\n"):
                itr.forward_to_line_end()
                self.buf.place_cursor(itr)
                self.buf.insert_at_cursor(self.vim_yank)
            else:
                itr.forward_char()
                self.buf.place_cursor(itr)
                self.buf.insert_at_cursor(self.vim_yank)
            self._update_status()
            return True

        # undo / redo
        if char == 'u':
            self.buf.undo()
            self._update_status()
            return True

        if char == 'r' and (event.state & Gdk.ModifierType.CONTROL_MASK):
            self.buf.redo()
            self._update_status()
            return True

        # goto
        if char == 'g' and self.vim_cmd == "g":
            self.vim_cmd = ""
            line_itr = self.buf.get_start_iter()
            self.buf.place_cursor(line_itr)
            self.tview.scroll_to_iter(line_itr, 0.0, True, 0.0, 0.0)
            self._update_status()
            return True

        if char == 'G':
            line_itr = self.buf.get_end_iter()
            self.buf.place_cursor(line_itr)
            self.tview.scroll_to_iter(line_itr, 0.0, True, 0.0, 0.0)
            self._update_status()
            return True

        if char == 'g':
            self.vim_cmd = "g"
            self._update_status()
            return True

        # 0 and $
        if char == '0':
            itr = self.buf.get_iter_at_mark(self.buf.get_insert())
            itr.set_line_offset(0)
            self.buf.place_cursor(itr)
            return True

        if char == '$':
            itr = self.buf.get_iter_at_mark(self.buf.get_insert())
            itr.forward_to_line_end()
            self.buf.place_cursor(itr)
            return True

        # visual line (V)
        if char == 'V':
            # toggle line selection
            if self.buf.get_selection_bounds():
                self.buf.select_range(self.buf.get_start_iter(), self.buf.get_end_iter())
            else:
                itr = self.buf.get_iter_at_mark(self.buf.get_insert())
                start = itr.copy()
                start.set_line_offset(0)
                end = itr.copy()
                end.forward_to_line_end()
                self.buf.select_range(start, end)
            return True

        return False

    def _word_forward(self, itr):
        if itr.starts_line() and itr.get_char() in (' ', '\t'):
            while not itr.ends_line() and itr.get_char() in (' ', '\t'):
                itr.forward_char()
        elif not itr.ends_line():
            itr.forward_char()
            while not itr.ends_line() and itr.get_char() not in (' ', '\t', '\n'):
                itr.forward_char()
            while not itr.ends_line() and itr.get_char() in (' ', '\t'):
                itr.forward_char()

    def _word_backward(self, itr):
        if itr.get_line_offset() == 0:
            if itr.get_line() > 0:
                itr.backward_line()
                itr.forward_to_line_end()
                itr.backward_char()
            return
        itr.backward_char()
        while itr.get_line_offset() > 0 and itr.get_char() in (' ', '\t'):
            itr.backward_char()
        while itr.get_line_offset() > 0 and itr.get_char() not in (' ', '\t', '\n'):
            itr.backward_char()
        if itr.get_line_offset() > 0:
            itr.forward_char()

    def _word_end(self, itr):
        if not itr.ends_line():
            itr.forward_char()
        while not itr.ends_line() and itr.get_char() in (' ', '\t'):
            itr.forward_char()
        while not itr.ends_line() and itr.get_char() not in (' ', '\t', '\n'):
            itr.forward_char()

    def _line_end(self, itr):
        end = itr.copy()
        end.forward_to_line_end()
        return end

    def _run_vim_cmd(self):
        cmd = self.vim_cmd.strip(":").strip()
        if cmd == "w":
            self._save_file()
        elif cmd == "q":
            self._quit_app()
        elif cmd == "wq":
            if self._save_file():
                self._quit_app()
        elif cmd == "q!":
            self.buf.set_modified(False)
            self._quit_app()
        self.vim_cmd_mode = False
        self.vim_cmd = ""
        self._update_status()

    # ── auto indent ──

    def _auto_indent(self):
        itr = self.buf.get_iter_at_mark(self.buf.get_insert())
        ln = itr.get_line()
        if ln > 0:
            ps = self.buf.get_iter_at_line(ln - 1)
            pe = ps.copy()
            pe.forward_to_line_end()
            prev = self.buf.get_text(ps, pe, True)
            indent = prev[:len(prev) - len(prev.lstrip(" \t"))]
            if prev.rstrip().endswith(":"):
                indent += "    "
            if indent:
                self.buf.insert_at_cursor(indent)

    # ── render ──

    def _toggle_render(self, w=None):
        if self.render_scroll.get_visible():
            self.render_scroll.hide()
        else:
            self.render_scroll.show()
            self._render_tags()
            if self.paned.get_realized():
                self.paned.set_position(self.paned.get_allocated_width() // 2)

    def _render_tags(self):
        s, e = self.buf.get_bounds()
        content = self.buf.get_text(s, e, False)
        parts = re.split(r'(<ts=[^>]*>|</ts=[^>]*>|<italic>|</italic>|<bold>|</bold>)', content)
        self.r_buf.set_text("")
        table = self.r_buf.get_tag_table()
        for name in self._r_ts_tags:
            tag = table.lookup(name)
            if tag:
                table.remove(tag)
        self._r_ts_tags.clear()
        tags = []
        for p in parts:
            if not p:
                continue
            if p == "<bold>":
                tags.append("r_bold")
            elif p == "</bold>" and "r_bold" in tags:
                tags.remove("r_bold")
            elif p == "<italic>":
                tags.append("r_italic")
            elif p == "</italic>" and "r_italic" in tags:
                tags.remove("r_italic")
            elif re.match(r'<ts=[^>]*>', p):
                sz = p[4:-1]
                tname = "r_ts_" + re.sub(r'[^0-9A-Za-z_.]', '_', sz)
                if not table.lookup(tname):
                    try:
                        scale = float(sz) / 11.0
                    except ValueError:
                        scale = 1.0
                    if not (0 < scale <= 10):
                        scale = 1.0
                    self.r_buf.create_tag(tname, scale=scale)
                    self._r_ts_tags.add(tname)
                tags.append(tname)
            elif re.match(r'</ts=[^>]*>', p):
                for i in range(len(tags) - 1, -1, -1):
                    if tags[i].startswith("r_ts_"):
                        tags.pop(i)
                        break
            else:
                self.r_buf.insert_with_tags_by_name(self.r_buf.get_end_iter(), p, *tags)

    # ── toggles ──

    def _toggle_wrap(self, w=None):
        new = w.get_active() if w else not self.wrap
        if new == self.wrap:
            return
        self.wrap = new
        self.tview.set_wrap_mode(Gtk.WrapMode.WORD if self.wrap else Gtk.WrapMode.NONE)
        self.chk_wrap.set_active(self.wrap)

    def _toggle_indent(self, w=None):
        widths = {"4 spaces": "2 spaces", "2 spaces": "Tab", "Tab": "4 spaces"}
        label = self.btn_indent.get_label()
        new = widths.get(label, "4 spaces")
        self.btn_indent.set_label(new)
        if new == "Tab":
            self.tview.set_insert_spaces_instead_of_tabs(False)
        else:
            self.tview.set_insert_spaces_instead_of_tabs(True)
            self.tview.set_tab_width(4 if new == "4 spaces" else 2)
        self._update_status()

    def _choose_accent(self, w=None):
        dlg = Gtk.ColorChooserDialog(title="Choose Accent Color", parent=self)
        dlg.set_use_alpha(False)
        rgba = Gdk.RGBA()
        rgba.parse(self.accent)
        dlg.set_rgba(rgba)
        if dlg.run() == Gtk.ResponseType.OK:
            c = dlg.get_rgba()
            self.accent = f"#{int(c.red*255):02x}{int(c.green*255):02x}{int(c.blue*255):02x}"
            self.accent_hover = lighten(self.accent)
            self._save_accent()
            self._apply_theme()
            self._update_status()
        dlg.destroy()

    # ── about ──

    def _show_about(self, w=None):
        dlg = Gtk.AboutDialog(transient_for=self, modal=True)
        dlg.set_program_name("PyRite")
        dlg.set_version("2.0")
        dlg.set_comments("A minimal dark-mode text editor for GTK-based Linux desktops")
        dlg.set_license_type(Gtk.License.MIT_X11)
        dlg.set_website("https://github.com/SulphArk/PyRite")
        dlg.set_website_label("GitHub")
        dlg.run()
        dlg.destroy()

    # ── drag & drop ──

    def _on_drag_data(self, widget, context, x, y, data, info, time):
        uris = data.get_uris()
        if uris:
            path = GLib.filename_from_uri(uris[0])[0]
            if self._confirm_discard():
                self._open_path(path)
        Gtk.drag_finish(context, True, False, time)

    # ── confirm / quit ──

    def _confirm_discard(self):
        if not self.buf.get_modified():
            return True
        name = os.path.basename(self.cur_file) if self.cur_file else "untitled"
        dlg = Gtk.MessageDialog(
            transient_for=self, modal=True,
            message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.NONE,
            text=f"'{name}' has unsaved changes. Discard them?")
        dlg.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dlg.add_button("Discard", Gtk.ResponseType.OK)
        r = dlg.run()
        dlg.destroy()
        return r == Gtk.ResponseType.OK

    def _quit_app(self, w=None):
        if self._confirm_discard():
            self._stop_monitor()
            Gtk.main_quit()
            return False
        return True

    # ── status ──

    def _on_modified(self, w):
        self.modified = self.buf.get_modified()
        self._update_status()

    def _on_text_changed(self, w):
        self._update_status()
        if self.wrap:
            pass  # GtkSourceView handles line numbers automatically

        if self.deferred_id:
            GLib.source_remove(self.deferred_id)
        self.deferred_id = GLib.timeout_add(400, self._deferred_update)

    def _deferred_update(self):
        self.deferred_id = None
        s, e = self.buf.get_bounds()
        self.words = len(self.buf.get_text(s, e, True).split())
        if self.render_scroll.get_visible():
            self._render_tags()
        self._update_status()
        return False

    def _update_status(self):
        raw = os.path.basename(self.cur_file) if self.cur_file else "untitled"
        fname = GLib.markup_escape_text(raw)
        mod = f'<span foreground="{self.accent}">●</span>' if self.modified else '<span foreground="#343d41">●</span>'

        if not self.vim_mode:
            mode = '<span foreground="#a5aeb4">[STANDARD]</span>'
        elif self.vim_cmd_mode:
            mode = f'<span foreground="{self.accent}">[{GLib.markup_escape_text(self.vim_cmd)}]</span>'
        elif self.vim_state == "NORMAL":
            mode = f'<span foreground="{self.accent}">[NORMAL]</span>'
        else:
            mode = f'<span foreground="{self.accent_hover}">[INSERT]</span>'

        itr = self.buf.get_iter_at_mark(self.buf.get_insert())
        line = itr.get_line() + 1
        col = itr.get_line_offset() + 1

        indent = self.btn_indent.get_label()
        self.lbl_status.set_markup(
            f"{mode} {fname} {mod}  |  Ln {line}, Col {col}  |  Words: {self.words}  |  {indent}")
        self.set_title(f"{'● ' if self.modified else ''}{raw} — PyRite")

    def _show_error(self, msg):
        dlg = Gtk.MessageDialog(
            transient_for=self, modal=True,
            message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE,
            text=msg)
        dlg.run()
        dlg.destroy()

    def _make_accel_cb(self, cb):
        def handler(*args):
            cb()
        return handler


def main():
    parser = argparse.ArgumentParser(description="PyRite — A minimal dark-mode text editor")
    parser.add_argument("files", nargs="*", help="Files to open")
    args = parser.parse_args()

    win = None
    first_file = args.files[0] if args.files else None

    win = PyRiteEditor(file_path=first_file)
    win.connect("delete-event", win._quit_app)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    if not win.render_scroll.get_visible():
        win.render_scroll.hide()
    Gtk.main()


if __name__ == "__main__":
    main()
