#!/usr/bin/env python3
"""
PyRite — A minimal dark-mode text editor for GTK-based Linux desktops.
Version 2.1
"""
import gi
import re
import os
import json
import argparse
from collections import deque

gi.require_version("Gtk", "3.0")
gi.require_version("GtkSource", "4")
from gi.repository import Gtk, Gdk, Pango, GLib, Gio, GtkSource

# ── Paths ──────────────────────────────────────────────────────────────────

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "pyrite")
RECENT_PATH = os.path.join(CONFIG_DIR, "recents.json")
ACCENT_PATH = os.path.join(CONFIG_DIR, "accent.json")
MAX_RECENTS = 10

# ── Helpers ────────────────────────────────────────────────────────────────


def ensure_config_dir():
    os.makedirs(CONFIG_DIR, mode=0o700, exist_ok=True)


def load_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def save_json(path, data):
    ensure_config_dir()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def lighten(hex_color, amount=0.18):
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    return "#{:02x}{:02x}{:02x}".format(
        int(r + (255 - r) * amount),
        int(g + (255 - g) * amount),
        int(b + (255 - b) * amount),
    )


def valid_hex(color):
    return bool(re.match(r"^#[0-9a-fA-F]{6}$", color))


# ── Theme ──────────────────────────────────────────────────────────────────

CSS_TEMPLATE = """
window {{ background-color: #101315; }}

.top-bar {{
    background-color: #0c0e10; padding: 4px 8px;
    border-bottom: 1px solid #080a0b;
}}

.pill-button {{
    background: #343d41; color: #cacccc; border-radius: 4px;
    padding: 2px 10px; border: none; box-shadow: none;
    font-family: 'JetBrains Mono', monospace; font-size: 9pt; outline: none;
}}
.pill-button:hover {{ background: #4b4e55; color: #fff; }}
.pill-button:active, .pill-button:checked {{
    background: #343d41; color: {accent}; font-weight: bold;
}}
.pill-button:checked:hover {{ background: #4b4e55; color: {accent}; }}

.status-bar {{
    background-color: #0c0e10; color: #a5aeb4; padding: 4px 10px;
    border-top: 1px solid #343d41;
    font-family: 'JetBrains Mono', monospace; font-size: 9pt;
}}
.status-bar label {{ margin-right: 20px; }}

scrollbar {{ background-color: #101315; }}
scrollbar slider {{
    background-color: #4b4e55; border-radius: 3px;
    min-width: 6px; min-height: 6px;
}}
scrollbar slider:hover {{ background-color: {accent}; }}
scrollbar button {{ border: none; background: none; padding: 0; }}

menu {{ background-color: #0c0e10; border: 1px solid #343d41; }}
menuitem {{ color: #a5aeb4; padding: 2px 8px; font-size: 9pt; }}
menuitem:hover, menuitem:active {{ background-color: #343d41; color: #fff; }}
menuitem check, menuitem:checked check {{ color: {accent}; background: transparent; }}

.search-bar {{
    background-color: #0c0e10; border-top: 1px solid #343d41; padding: 4px;
}}
entry {{
    background-color: #101315; color: #cacccc;
    border: 1px solid #343d41; border-radius: 3px;
    padding: 2px 6px; font-size: 9pt;
}}
entry:focus {{ border-color: {accent}; }}
paned separator {{ background-color: #080a0b; min-width: 1px; }}

sourceview {{
    background-color: #101315; color: #cacccc;
    font-family: 'JetBrains Mono', monospace; font-size: 11pt;
}}

.notification {{
    background-color: #343d41; color: {accent};
    border-radius: 4px; padding: 4px 12px;
    font-family: 'JetBrains Mono', monospace; font-size: 9pt;
    margin: 4px;
}}
"""


# ── Vim Mode ───────────────────────────────────────────────────────────────


class VimMode:
    """Minimal vim keybinding handler — NORMAL, INSERT, COMMAND."""

    STATES = ("NORMAL", "INSERT", "COMMAND")
    NAVIGATORS = {"h", "j", "k", "l", "w", "b", "e", "0", "$", "G", "g"}
    OPERATORS = {"d", "y"}

    def __init__(self, buffer, view, on_status_change):
        self.buf = buffer
        self.view = view
        self.on_status_change = on_status_change

        self.active = False
        self.state = "NORMAL"
        self.count = ""
        self.pending_op = ""
        self.yank_register = ""
        self.cmd_text = ""

    def reset(self):
        self.count = ""
        self.pending_op = ""

    def get_count(self):
        return int(self.count) if self.count else 1

    # ── dispatch ──

    def handle_key(self, event):
        """Return True if key was consumed."""
        if not self.active:
            return False
        if event.state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.MOD1_MASK):
            return False

        keyval = event.keyval
        keyname = Gdk.keyval_name(keyval) or ""
        char = chr(Gdk.keyval_to_unicode(keyval)) if Gdk.keyval_to_unicode(keyval) else ""

        # ── command mode ──
        if self.state == "COMMAND":
            if keyname == "Return":
                self._run_command()
            elif keyname == "Escape" or keyname == "BackSpace" and not self.cmd_text[1:]:
                self.state = "NORMAL"
                self.cmd_text = ""
            elif keyname == "BackSpace":
                self.cmd_text = self.cmd_text[:-1]
            else:
                self.cmd_text += char
            self.on_status_change()
            return True

        # ── insert mode ──
        if self.state == "INSERT":
            if keyname == "Escape":
                self.state = "NORMAL"
                self.reset()
                self.on_status_change()
                return True
            return False

        # ── normal mode ──
        if keyname == "Escape":
            self.reset()
            self.on_status_change()
            return True

        # count prefix
        if char.isdigit() and char != "0" and not self.pending_op:
            self.count += char
            self.on_status_change()
            return True

        count = self.get_count()
        self.count = ""

        # enter command mode
        if char == ":":
            self.state = "COMMAND"
            self.cmd_text = ":"
            self.on_status_change()
            return True

        # enter insert mode variants
        if char == "i":
            self.state = "INSERT"
            self.on_status_change()
            return True
        if char == "a":
            self._move_forward_char()
            self.state = "INSERT"
            self.on_status_change()
            return True
        if char == "A":
            self._move_line_end()
            self.state = "INSERT"
            self.on_status_change()
            return True
        if char == "o":
            self._open_line_below()
            self.state = "INSERT"
            self.on_status_change()
            return True
        if char == "O":
            self._open_line_above()
            self.state = "INSERT"
            self.on_status_change()
            return True

        # navigation
        if char in ("h", "j", "k", "l"):
            self._move_hjkl(char, count)
            self.on_status_change()
            return True
        if char == "w":
            self._move_word_forward(count)
            self.on_status_change()
            return True
        if char == "b":
            self._move_word_backward(count)
            self.on_status_change()
            return True
        if char == "e":
            self._move_word_end(count)
            self.on_status_change()
            return True
        if char == "0":
            self._move_line_start()
            self.on_status_change()
            return True
        if char == "$":
            self._move_line_end()
            self.on_status_change()
            return True
        if char == "G":
            self._move_end_of_doc()
            self.on_status_change()
            return True
        if char == "g":
            if self.pending_op == "g":
                self.pending_op = ""
                self._move_start_of_doc()
            else:
                self.pending_op = "g"
            self.on_status_change()
            return True

        # operators (d, y) — wait for second key
        if char in self.OPERATORS:
            if self.pending_op == char:
                # dd or yy — operate on current line
                self._op_line(char)
                self.pending_op = ""
            else:
                self.pending_op = char
            self.on_status_change()
            return True

        # x — delete char under cursor
        if char == "x":
            self._delete_char(count)
            self.on_status_change()
            return True

        # p — paste
        if char == "p" and self.yank_register:
            self._paste_after()
            self.on_status_change()
            return True

        # u — undo
        if char == "u":
            self.buf.undo()
            self.on_status_change()
            return True

        # V — visual line (select current line)
        if char == "V":
            self._select_current_line()
            self.on_status_change()
            return True

        self.pending_op = ""
        return True

    # ── movements ──

    def _cursor(self):
        return self.buf.get_iter_at_mark(self.buf.get_insert())

    def _place(self, itr):
        self.buf.place_cursor(itr)
        mark = self.buf.get_insert()
        self.view.scroll_to_mark(mark, 0.0, True, 0.0, 0.0)

    def _move_forward_char(self):
        itr = self._cursor()
        if not itr.ends_line():
            itr.forward_char()
            self._place(itr)

    def _move_line_end(self):
        itr = self._cursor()
        itr.forward_to_line_end()
        self._place(itr)

    def _move_line_start(self):
        itr = self._cursor()
        itr.set_line_offset(0)
        self._place(itr)

    def _move_hjkl(self, ch, count):
        itr = self._cursor()
        for _ in range(count):
            if ch == "h" and itr.get_line_offset() > 0:
                itr.backward_char()
            elif ch == "l" and not itr.ends_line():
                itr.forward_char()
            elif ch == "j":
                if not itr.forward_line():
                    break
            elif ch == "k":
                if not itr.backward_line():
                    break
        self._place(itr)

    def _move_word_forward(self, count):
        itr = self._cursor()
        for _ in range(count):
            self._skip_word_forward(itr)
        self._place(itr)

    def _move_word_backward(self, count):
        itr = self._cursor()
        for _ in range(count):
            self._skip_word_backward(itr)
        self._place(itr)

    def _move_word_end(self, count):
        itr = self._cursor()
        for _ in range(count):
            self._skip_word_end(itr)
        self._place(itr)

    def _move_start_of_doc(self):
        self._place(self.buf.get_start_iter())

    def _move_end_of_doc(self):
        self._place(self.buf.get_end_iter())

    @staticmethod
    def _is_word_char(ch):
        return ch not in (" ", "\t", "\n", "") and not ch.isspace()

    def _skip_word_forward(self, itr):
        # if on whitespace, skip it
        while not itr.ends_line() and not self._is_word_char(itr.get_char()):
            if not itr.forward_char():
                return
        # skip word chars
        while not itr.ends_line() and self._is_word_char(itr.get_char()):
            if not itr.forward_char():
                return
        # skip trailing whitespace to land on next word
        while not itr.ends_line() and not self._is_word_char(itr.get_char()):
            if not itr.forward_char():
                return

    def _skip_word_backward(self, itr):
        if itr.get_line_offset() == 0:
            if not itr.backward_line():
                return
            itr.forward_to_line_end()
            if not itr.backward_char():
                return
        else:
            if not itr.backward_char():
                return
        # skip whitespace backward
        while itr.get_line_offset() > 0 and not self._is_word_char(itr.get_char()):
            if not itr.backward_char():
                return
        # skip word chars backward
        while itr.get_line_offset() > 0 and self._is_word_char(itr.get_char()):
            if not itr.backward_char():
                return
        # land on first char of word
        if itr.get_line_offset() > 0 or self._is_word_char(itr.get_char()):
            if not self._is_word_char(itr.get_char()):
                itr.forward_char()

    def _skip_word_end(self, itr):
        if not itr.ends_line():
            itr.forward_char()
        while not itr.ends_line() and not self._is_word_char(itr.get_char()):
            if not itr.forward_char():
                return
        while not itr.ends_line() and self._is_word_char(itr.get_char()):
            if not itr.forward_char():
                return
        # back up to last word char
        if not itr.starts_line():
            itr.backward_char()

    # ── editing ──

    def _delete_char(self, count):
        for _ in range(count):
            itr = self._cursor()
            if itr.ends_line():
                break
            end = itr.copy()
            end.forward_char()
            self.buf.delete(itr, end)

    def _op_line(self, op):
        """dd or yy on current line."""
        itr = self._cursor()
        start = itr.copy()
        start.set_line_offset(0)
        end = itr.copy()
        if not end.ends_line():
            end.forward_to_line_end()
        else:
            # if on empty last line, don't delete it
            if end.is_end():
                return

        line_text = self.buf.get_text(start, end, True)

        if op == "y":
            self.yank_register = line_text + "\n"
            return

        # dd
        self.yank_register = line_text + "\n"
        self.buf.delete(start, end)
        # clean up leftover empty line if not at end
        itr2 = self._cursor()
        if not itr2.is_end() and itr2.get_char() == "\n":
            end_nl = itr2.copy()
            end_nl.forward_char()
            self.buf.delete(itr2, end_nl)

    def _paste_after(self):
        text = self.yank_register
        if not text:
            return
        itr = self._cursor()
        if text.endswith("\n"):
            # line paste: go to end of current line, insert
            itr.forward_to_line_end()
            self.buf.place_cursor(itr)
            self.buf.insert_at_cursor(text)
        else:
            # char paste: go past current char
            if not itr.ends_line():
                itr.forward_char()
            self.buf.place_cursor(itr)
            self.buf.insert_at_cursor(text)

    def _open_line_below(self):
        itr = self._cursor()
        itr.forward_to_line_end()
        self.buf.place_cursor(itr)
        self.buf.insert_at_cursor("\n")

    def _open_line_above(self):
        itr = self._cursor()
        start = itr.copy()
        start.set_line_offset(0)
        self.buf.place_cursor(start)
        self.buf.insert_at_cursor("\n")
        # move cursor up to the new empty line
        itr2 = self._cursor()
        itr2.backward_line()
        self._place(itr2)

    def _select_current_line(self):
        itr = self._cursor()
        start = itr.copy()
        start.set_line_offset(0)
        end = itr.copy()
        end.forward_to_line_end()
        self.buf.select_range(start, end)

    # ── commands ──

    def _run_command(self):
        cmd = self.cmd_text.strip(":").strip()
        self.state = "NORMAL"
        self.cmd_text = ""
        # return command via callback
        self._pending_cmd = cmd
        GLib.idle_add(self._dispatch_cmd)

    def _dispatch_cmd(self):
        cmd = getattr(self, "_pending_cmd", "")
        self._pending_cmd = ""
        # the editor will check this
        self.on_status_change()
        return False

    def pop_command(self):
        """Non-blocking command retrieval. Returns and clears the pending command."""
        cmd = getattr(self, "_pending_cmd", "")
        self._pending_cmd = ""
        return cmd

    # ── status ──

    def status_label(self, accent, accent_hover):
        if not self.active:
            return '<span foreground="#a5aeb4">[STANDARD]</span>'
        if self.state == "COMMAND":
            escaped = GLib.markup_escape_text(self.cmd_text)
            return f'<span foreground="{accent}">[{escaped}]</span>'
        if self.state == "INSERT":
            return f'<span foreground="{accent_hover}">[INSERT]</span>'
        return f'<span foreground="{accent}">[NORMAL]</span>'


# ── Editor ─────────────────────────────────────────────────────────────────


class PyRiteEditor(Gtk.Window):
    def __init__(self, file_path=None):
        super().__init__(title="PyRite")
        self.set_default_size(920, 640)

        # state
        self.cur_file = None
        self.words = 0
        self.wrap = True
        self._deferred_id = None
        self._status_id = None
        self._reload_id = None
        self._monitor = None
        self._monitor_sig = None
        self._notification_id = None

        # config
        ensure_config_dir()
        self.accent = self._load_accent()
        self.recents = load_json(RECENT_PATH, [])

        # theme
        self.css_provider = Gtk.CssProvider()
        self._apply_theme()

        # vim
        self.vim = VimMode(self.buf if hasattr(self, "buf") else None,
                           self.tview if hasattr(self, "tview") else None,
                           self._schedule_status)
        # will be properly wired after widget creation below

        # build ui
        self._build_ui()

        # wire vim to actual widgets
        self.vim.buf = self.buf
        self.vim.view = self.tview

        # syntax
        self.lang_manager = GtkSource.LanguageManager.get_default()
        self.style_manager = GtkSource.StyleSchemeManager.get_default()
        self._apply_style_scheme()

        # keyboard
        self._setup_accelerators()
        self.connect("key-press-event", self._on_key)
        self.buf.connect("notify::cursor-position", lambda *a: self._schedule_status())

        # drag and drop
        self.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        self.drag_dest_add_uri_targets()
        self.connect("drag-data-received", self._on_drag_data)

        # open file if given
        if file_path:
            self._open_path(file_path)
        self._update_status()

    # ── UI construction ──

    def _build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(root)

        # top bar
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        top.get_style_context().add_class("top-bar")
        root.pack_start(top, False, False, 0)

        self.menu = Gtk.Menu()
        self._build_menu()
        self.btn_opts = Gtk.MenuButton(label="Options")
        self.btn_opts.get_style_context().add_class("pill-button")
        self.btn_opts.set_popup(self.menu)
        top.pack_start(self.btn_opts, False, False, 0)

        self.btn_vim = Gtk.ToggleButton(label="Vim")
        self.btn_vim.get_style_context().add_class("pill-button")
        self.btn_vim.connect("toggled", self._toggle_vim)

        self.btn_render = Gtk.Button(label="Render")
        self.btn_render.get_style_context().add_class("pill-button")
        self.btn_render.connect("clicked", self._toggle_render)

        top.pack_end(self.btn_vim, False, False, 0)
        top.pack_end(self.btn_render, False, False, 0)

        # editor + render paned
        self.paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        root.pack_start(self.paned, True, True, 0)

        # source view
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
        self.buf.connect("modified-changed", self._schedule_status)
        self.buf.connect("changed", self._on_text_changed)

        self.scroll.add(self.tview)
        self.paned.pack1(self.scroll, resize=True, shrink=False)

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
        self._r_ts_tags = set()
        self.render_scroll.add(self.r_view)
        self.paned.pack2(self.render_scroll, resize=False, shrink=False)
        self.render_scroll.hide()

        # search bar
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

        btn_repl = Gtk.Button(label="Replace")
        btn_repl.connect("clicked", lambda w: self._replace_one())
        btn_all = Gtk.Button(label="Replace All")
        btn_all.connect("clicked", lambda w: self._replace_all())
        btn_close = Gtk.Button(label="✕")
        btn_close.connect("clicked", lambda w: self._close_search())

        search_box.pack_start(self.search_entry, True, True, 0)
        search_box.pack_start(self.replace_entry, False, False, 0)
        search_box.pack_start(btn_repl, False, False, 0)
        search_box.pack_start(btn_all, False, False, 0)
        search_box.pack_start(btn_close, False, False, 0)
        self.search_rev.add(search_box)
        root.pack_start(self.search_rev, False, False, 0)

        # status bar
        sbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        sbar.get_style_context().add_class("status-bar")
        root.pack_end(sbar, False, False, 0)

        self.lbl_status = Gtk.Label(label="")
        self.lbl_status.set_xalign(0)
        sbar.pack_start(self.lbl_status, False, False, 0)

        self.btn_indent = Gtk.Button(label="4 spaces")
        self.btn_indent.get_style_context().add_class("pill-button")
        self.btn_indent.set_relief(Gtk.ReliefStyle.NONE)
        self.btn_indent.set_size_request(55, -1)
        self.btn_indent.connect("clicked", self._cycle_indent)
        sbar.pack_end(self.btn_indent, False, False, 0)

    # ── theme ──

    def _load_accent(self):
        c = load_json(ACCENT_PATH, {}).get("accent", "#61A03C")
        return c if valid_hex(c) else "#61A03C"

    def _save_accent(self):
        save_json(ACCENT_PATH, {"accent": self.accent})

    def _apply_theme(self):
        accent = self.accent
        css = CSS_TEMPLATE.format(accent=accent)
        self.css_provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _apply_style_scheme(self):
        for sid in ("oblivion", "classic"):
            scheme = self.style_manager.get_scheme(sid)
            if scheme:
                self.buf.set_style_scheme(scheme)
                break

    # ── menu ──

    def _build_menu(self):
        for c in list(self.menu.get_children()):
            self.menu.remove(c)

        for label, cb in [
            ("New", self._new_file),
            ("Open", self._open_file),
            ("Save", self._save_file),
            ("Save As…", self._save_as),
        ]:
            item = Gtk.MenuItem(label=label)
            item.connect("activate", cb)
            self.menu.append(item)

        self.menu.append(Gtk.SeparatorMenuItem())

        # recent files
        rec_menu = Gtk.Menu()
        if not self.recents:
            empty = Gtk.MenuItem(label="No recent files")
            empty.set_sensitive(False)
            rec_menu.append(empty)
        else:
            for path in self.recents[:MAX_RECENTS]:
                item = Gtk.MenuItem(label=os.path.basename(path))
                if not os.path.isfile(path):
                    item.set_sensitive(False)
                else:
                    item.connect("activate", lambda w, p=path: self._open_path(p))
                rec_menu.append(item)
        rec_item = Gtk.MenuItem(label="Recent Files")
        rec_item.set_submenu(rec_menu)
        self.menu.append(rec_item)

        self.menu.append(Gtk.SeparatorMenuItem())

        self.chk_wrap = Gtk.CheckMenuItem(label="Word Wrap")
        self.chk_wrap.set_active(self.wrap)
        self.chk_wrap.connect("toggled", self._toggle_wrap)
        self.menu.append(self.chk_wrap)

        self.menu.append(Gtk.SeparatorMenuItem())

        acc_item = Gtk.MenuItem(label="Accent Color…")
        acc_item.connect("activate", self._choose_accent)
        self.menu.append(acc_item)

        self.menu.append(Gtk.AboutMenuItem())

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
        self._clear_search_highlights()
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
        dlg = Gtk.FileChooserNative.new(
            "Open File", self, Gtk.FileChooserAction.OPEN, "_Open", "_Cancel"
        )
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
            self._notify(f"Not a file: {path}")
            return
        try:
            loader = GtkSource.FileLoader(
                buffer=self.buf, file=Gio.File.new_for_path(path)
            )
            loader.load_async(GLib.PRIORITY_DEFAULT, None, self._on_file_loaded, path)
        except Exception as ex:
            self._notify(f"Open failed: {ex}")

    def _on_file_loaded(self, loader, result, path):
        try:
            loader.load_finish(result)
        except Exception as ex:
            self._notify(f"Open failed: {ex}")
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
            saver = GtkSource.FileSaver(
                buffer=self.buf, file=Gio.File.new_for_path(self.cur_file)
            )
            saver.save_async(
                GLib.PRIORITY_DEFAULT, None, self._on_file_saved, None
            )
            return True
        except Exception as ex:
            self._notify(f"Save failed: {ex}")
            return False

    def _on_file_saved(self, saver, result, _data):
        try:
            saver.save_finish(result)
            self.buf.set_modified(False)
            self._add_recent(self.cur_file)
            self._update_status()
        except Exception as ex:
            self._notify(f"Save failed: {ex}")

    def _save_as(self, w=None):
        dlg = Gtk.FileChooserNative.new(
            "Save As", self, Gtk.FileChooserAction.SAVE, "_Save", "_Cancel"
        )
        dlg.set_do_overwrite_confirmation(True)
        if dlg.run() == Gtk.ResponseType.ACCEPT:
            filename = dlg.get_filename()
            dlg.destroy()
            self.cur_file = filename
            self._detect_language()
            return self._save_file()
        dlg.destroy()
        return False

    # ── file monitoring ──

    def _start_monitor(self, path):
        self._stop_monitor()
        try:
            f = Gio.File.new_for_path(path)
            self._monitor = f.monitor_file(Gio.FileMonitorFlags.NONE, None)
            self._monitor_sig = self._monitor.connect("changed", self._on_file_changed)
        except OSError:
            pass

    def _stop_monitor(self):
        if self._monitor:
            if self._monitor_sig:
                self._monitor.disconnect(self._monitor_sig)
                self._monitor_sig = None
            self._monitor.cancel()
            self._monitor = None

    def _on_file_changed(self, _monitor, _file, _other, event):
        if event in (Gio.FileMonitorEvent.DELETED, Gio.FileMonitorEvent.MOVED):
            self._notify("File deleted or moved on disk")
            return
        if event == Gio.FileMonitorEvent.CHANGED and not self.buf.get_modified():
            # debounce — don't spam
            if self._reload_id:
                GLib.source_remove(self._reload_id)
            self._reload_id = GLib.timeout_add(600, self._prompt_reload)

    def _prompt_reload(self):
        self._reload_id = None
        dlg = Gtk.MessageDialog(
            transient_for=self, modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.NONE,
            text="File changed on disk. Reload?",
        )
        dlg.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dlg.add_button("Reload", Gtk.ResponseType.OK)
        response = dlg.run()
        dlg.destroy()
        if response == Gtk.ResponseType.OK:
            self._open_path(self.cur_file)
        return False

    # ── search ──

    def _open_search(self, w=None):
        self.search_rev.set_reveal_child(True)
        self.search_entry.grab_focus()

    def _close_search(self, w=None):
        self._clear_search_highlights()
        self.search_rev.set_reveal_child(False)
        self.tview.grab_focus()

    def _clear_search_highlights(self):
        tag = self.buf.get_tag_table().lookup("search-match")
        if tag:
            s, e = self.buf.get_bounds()
            self.buf.remove_tag(tag, s, e)

    def _ensure_search_tag(self):
        if not self.buf.get_tag_table().lookup("search-match"):
            self.buf.create_tag("search-match", background=self.accent, foreground="#101315")

    def _on_search(self, entry):
        self._clear_search_highlights()
        query = entry.get_text()
        if not query:
            return
        self._ensure_search_tag()
        s, e = self.buf.get_bounds()
        itr = s.copy()
        first = None
        while True:
            m = itr.forward_search(query, Gtk.TextSearchFlags.CASE_INSENSITIVE, e)
            if not m:
                break
            self.buf.apply_tag_by_name("search-match", m[0], m[1])
            if first is None:
                first = m
            itr = m[1]
        if first:
            self.buf.select_range(first[0], first[1])
            self.tview.scroll_to_iter(first[0], 0.0, True, 0.0, 0.0)

    def _search_next(self):
        query = self.search_entry.get_text()
        if not query:
            return
        cur = self.buf.get_iter_at_mark(self.buf.get_insert())
        s, e = self.buf.get_bounds()
        m = cur.forward_search(query, Gtk.TextSearchFlags.CASE_INSENSITIVE, e)
        if not m:
            m = s.forward_search(query, Gtk.TextSearchFlags.CASE_INSENSITIVE, e)
            if m:
                self._notify("Search wrapped")
        if m:
            self.buf.select_range(m[0], m[1])
            self.tview.scroll_to_iter(m[0], 0.0, True, 0.0, 0.0)

    def _search_prev(self):
        query = self.search_entry.get_text()
        if not query:
            return
        cur = self.buf.get_iter_at_mark(self.buf.get_insert())
        s, e = self.buf.get_bounds()
        # walk from start, find last match before cursor
        last = None
        itr = s.copy()
        while True:
            m = itr.forward_search(query, Gtk.TextSearchFlags.CASE_INSENSITIVE, e)
            if not m or m[0].compare(cur) >= 0:
                break
            last = m
            itr = m[1]
        if last is None:
            # wrap: find last match in entire buffer
            itr = s.copy()
            while True:
                m = itr.forward_search(query, Gtk.TextSearchFlags.CASE_INSENSITIVE, e)
                if not m:
                    break
                last = m
                itr = m[1]
            if last:
                self._notify("Search wrapped")
        if last:
            self.buf.select_range(last[0], last[1])
            self.tview.scroll_to_iter(last[0], 0.0, True, 0.0, 0.0)

    def _replace_one(self):
        query = self.search_entry.get_text()
        repl = self.replace_entry.get_text()
        if not query:
            return
        cur = self.buf.get_iter_at_mark(self.buf.get_insert())
        e = self.buf.get_end_iter()
        m = cur.forward_search(query, Gtk.TextSearchFlags.CASE_INSENSITIVE, e)
        if not m:
            m = self.buf.get_start_iter().forward_search(
                query, Gtk.TextSearchFlags.CASE_INSENSITIVE, e
            )
        if m:
            self.buf.begin_user_action()
            self.buf.delete(m[0], m[1])
            self.buf.insert_at_cursor(repl)
            self.buf.end_user_action()
            # refresh highlights
            self._on_search(self.search_entry)

    def _replace_all(self):
        query = self.search_entry.get_text()
        repl = self.replace_entry.get_text()
        if not query:
            return
        s, e = self.buf.get_bounds()
        text = self.buf.get_text(s, e, True)
        if query in text:
            self.buf.begin_user_action()
            self.buf.set_text(text.replace(query, repl))
            self.buf.end_user_action()
            self._on_search(self.search_entry)

    # ── vim toggle ──

    def _toggle_vim(self, w=None):
        active = self.btn_vim.get_active()
        self.vim.active = active
        self.vim.state = "NORMAL"
        self.vim.reset()
        self.btn_vim.set_label("Vim: ON" if active else "Vim")
        self._update_status()

    # ── keyboard ──

    def _setup_accelerators(self):
        accel = Gtk.AccelGroup()
        self.add_accel_group(accel)
        bindings = {
            "n": self._new_file,
            "o": self._open_file,
            "s": self._save_file,
            "f": self._open_search,
        }
        for key, cb in bindings.items():
            accel.connect(
                Gdk.keyval_from_name(key),
                Gdk.ModifierType.CONTROL_MASK,
                Gtk.AccelFlags.VISIBLE,
                lambda *a, fn=cb: fn(),
            )

    def _on_key(self, _widget, event):
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        alt = event.state & Gdk.ModifierType.MOD1_MASK
        key = Gdk.keyval_to_lower(event.keyval)

        # ctrl shortcuts (work in both modes)
        if ctrl:
            if key == Gdk.KEY_f:
                self._open_search()
                return True
            if key == Gdk.KEY_z:
                self.buf.undo()
                return True
            if key in (Gdk.KEY_y, Gdk.KEY_r):
                self.buf.redo()
                return True
            return False

        # alt+w toggle wrap (standard mode only)
        if alt and key == Gdk.KEY_w and not self.vim.active:
            self._toggle_wrap()
            return True

        # vim mode
        if self.vim.active:
            consumed = self.vim.handle_key(event)
            if consumed:
                # check for pending :w, :q, :wq, :q!
                cmd = self.vim.pop_command()
                if cmd:
                    self._handle_vim_cmd(cmd)
                return True

        # auto-indent on enter (standard mode only)
        if key == Gdk.KEY_Return and not self.vim.active:
            self._auto_indent()
            return False

        return False

    def _handle_vim_cmd(self, cmd):
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

    # ── auto indent ──

    def _auto_indent(self):
        itr = self.buf.get_iter_at_mark(self.buf.get_insert())
        ln = itr.get_line()
        if ln == 0:
            return
        ps = self.buf.get_iter_at_line(ln - 1)
        pe = ps.copy()
        pe.forward_to_line_end()
        prev = self.buf.get_text(ps, pe, True)
        indent = prev[: len(prev) - len(prev.lstrip(" \t"))]
        if prev.rstrip().endswith((":", "then", "do", "else", "elif", "except", "finally")):
            indent += "    "
        if indent:
            self.buf.insert_at_cursor(indent)

    # ── render view ──

    def _toggle_render(self, w=None):
        visible = self.render_scroll.get_visible()
        if visible:
            self.render_scroll.hide()
        else:
            self.render_scroll.show()
            self._render_tags()
            if self.paned.get_realized():
                self.paned.set_position(self.paned.get_allocated_width() // 2)

    def _render_tags(self):
        s, e = self.buf.get_bounds()
        content = self.buf.get_text(s, e, False)

        # split by custom tags while keeping delimiters
        parts = re.split(
            r'(<ts=[^>]*>|</ts[^>]*>|<italic>|</italic>|<bold>|</bold>)',
            content,
        )

        self.r_buf.set_text("")
        table = self.r_buf.get_tag_table()

        # clean up old ts tags
        for name in self._r_ts_tags:
            tag = table.lookup(name)
            if tag:
                table.remove(tag)
        self._r_ts_tags.clear()

        tag_stack = []
        for part in parts:
            if not part:
                continue

            if part == "<bold>":
                tag_stack.append("r_bold")
            elif part == "</bold>":
                if "r_bold" in tag_stack:
                    tag_stack.remove("r_bold")
            elif part == "<italic>":
                tag_stack.append("r_italic")
            elif part == "</italic>":
                if "r_italic" in tag_stack:
                    tag_stack.remove("r_italic")
            elif part.startswith("<ts=") and part.endswith(">"):
                size_str = part[4:-1]
                safe = re.sub(r"[^0-9A-Za-z_.]", "_", size_str)
                tname = "r_ts_" + safe
                if not table.lookup(tname):
                    try:
                        scale = max(0.1, min(float(size_str) / 11.0, 10.0))
                    except ValueError:
                        scale = 1.0
                    self.r_buf.create_tag(tname, scale=scale)
                    self._r_ts_tags.add(tname)
                tag_stack.append(tname)
            elif part.startswith("</ts"):
                for i in range(len(tag_stack) - 1, -1, -1):
                    if tag_stack[i].startswith("r_ts_"):
                        tag_stack.pop(i)
                        break
            else:
                if tag_stack:
                    self.r_buf.insert_with_tags_by_name(
                        self.r_buf.get_end_iter(), part, *tag_stack
                    )
                else:
                    self.r_buf.insert_at_cursor(part)

    # ── toggles ──

    def _toggle_wrap(self, w=None):
        new = w.get_active() if w else not self.wrap
        if new == self.wrap:
            return
        self.wrap = new
        self.tview.set_wrap_mode(
            Gtk.WrapMode.WORD if self.wrap else Gtk.WrapMode.NONE
        )
        if hasattr(self, "chk_wrap"):
            self.chk_wrap.set_active(self.wrap)

    def _cycle_indent(self, w=None):
        cycle = {"4 spaces": "2 spaces", "2 spaces": "Tab", "Tab": "4 spaces"}
        current = self.btn_indent.get_label()
        new = cycle.get(current, "4 spaces")
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
            self.accent = "#{:02x}{:02x}{:02x}".format(
                round(c.red * 255), round(c.green * 255), round(c.blue * 255)
            )
            if not valid_hex(self.accent):
                self.accent = "#61A03C"
            self._save_accent()
            self._apply_theme()
            self._update_status()
        dlg.destroy()

    # ── drag & drop ──

    def _on_drag_data(self, _w, ctx, _x, _y, data, _info, time):
        uris = data.get_uris()
        if uris:
            if len(uris) > 1:
                self._notify(f"Dropped {len(uris)} files — opening first")
            path = GLib.filename_from_uri(uris[0])[0]
            if self._confirm_discard():
                self._open_path(path)
        Gtk.drag_finish(ctx, True, False, time)

    # ── confirm / quit ──

    def _confirm_discard(self):
        if not self.buf.get_modified():
            return True
        name = os.path.basename(self.cur_file) if self.cur_file else "untitled"
        dlg = Gtk.MessageDialog(
            transient_for=self, modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.NONE,
            text=f"'{name}' has unsaved changes. Discard them?",
        )
        dlg.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dlg.add_button("Discard", Gtk.ResponseType.OK)
        r = dlg.run()
        dlg.destroy()
        return r == Gtk.ResponseType.OK

    def _quit_app(self, w=None):
        if self._confirm_discard():
            self._stop_monitor()
            self.destroy()
            return False
        return True

    # ── notifications (non-blocking) ──

    def _notify(self, msg, duration=2500):
        """Show a brief inline notification in the status bar instead of a dialog."""
        escaped = GLib.markup_escape_text(msg)
        self.lbl_status.set_markup(
            f'<span foreground="{self.accent}">⚡ {escaped}</span>'
        )
        if self._notification_id:
            GLib.source_remove(self._notification_id)
        self._notification_id = GLib.timeout_add(duration, self._update_status)
        return False

    # ── status ──

    def _on_text_changed(self, _buf):
        # clear stale search highlights when user types
        self._clear_search_highlights()

        if self._deferred_id:
            GLib.source_remove(self._deferred_id)
        self._deferred_id = GLib.timeout_add(400, self._deferred_update)

    def _deferred_update(self):
        self._deferred_id = None
        s, e = self.buf.get_bounds()
        self.words = len(self.buf.get_text(s, e, True).split())
        if self.render_scroll.get_visible():
            self._render_tags()
        self._update_status()
        return False

    def _schedule_status(self):
        """Debounced status update — prevents flicker on rapid cursor moves."""
        if self._status_id:
            GLib.source_remove(self._status_id)
        self._status_id = GLib.timeout_add(30, self._do_update_status)
        return False

    def _do_update_status(self):
        self._status_id = None
        self._update_status()
        return False

    def _update_status(self):
        raw = os.path.basename(self.cur_file) if self.cur_file else "untitled"
        fname = GLib.markup_escape_text(raw)
        modified = self.buf.get_modified()
        dot = (
            f'<span foreground="{self.accent}">●</span>'
            if modified
            else '<span foreground="#343d41">●</span>'
        )
        accent_hover = lighten(self.accent)
        mode = self.vim.status_label(self.accent, accent_hover)

        itr = self.buf.get_iter_at_mark(self.buf.get_insert())
        line = itr.get_line() + 1
        col = itr.get_line_offset() + 1
        indent = self.btn_indent.get_label()

        self.lbl_status.set_markup(
            f"{mode} {fname} {dot}  │  Ln {line}, Col {col}  │  "
            f"Words: {self.words}  │  {indent}"
        )
        title_prefix = "● " if modified else ""
        self.set_title(f"{title_prefix}{raw} — PyRite")

    def _show_error(self, msg):
        self._notify(msg)


# ── Entry point ────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="PyRite — A minimal dark-mode text editor"
    )
    parser.add_argument("files", nargs="*", help="Files to open")
    args = parser.parse_args()

    win = PyRiteEditor(file_path=args.files[0] if args.files else None)
    win.connect("delete-event", win._quit_app)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    if not win.render_scroll.get_visible():
        win.render_scroll.hide()
    Gtk.main()


if __name__ == "__main__":
    main()
