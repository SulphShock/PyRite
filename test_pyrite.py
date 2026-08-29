import os
import tempfile
import unittest

os.environ.setdefault("GDK_BACKEND", "x11")
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GtkSource", "4")
from gi.repository import GLib, Gtk, GtkSource

import PyRite
from PyRite import PyRiteEditor


class EditorBase(unittest.TestCase):
    def run_instantiated(self, fn, *args, **kwargs):
        result = {}

        def on_start():
            win = PyRiteEditor()
            win.show_all()
            try:
                result["value"] = fn(win, *args, **kwargs)
            except Exception:
                import traceback
                result["error"] = traceback.format_exc()
            finally:
                Gtk.main_quit()

        GLib.timeout_add(10, on_start)
        Gtk.main()
        if "error" in result:
            self.fail(result["error"])
        return result.get("value")


class TestToggleIndent(EditorBase):
    def test_cycles_4s_to_2s_to_tab_and_back(self):
        def check(win):
            win.btn_indent.set_label("4 spaces")
            win._toggle_indent(None)
            self.assertEqual(win.btn_indent.get_label(), "2 spaces")
            win._toggle_indent(None)
            self.assertEqual(win.btn_indent.get_label(), "Tab")
            win._toggle_indent(None)
            self.assertEqual(win.btn_indent.get_label(), "4 spaces")

        self.run_instantiated(check)


class TestToggleWrap(EditorBase):
    def test_toggle_from_alt_z_updates_checkbox_and_wrap_mode(self):
        def check(win):
            self.assertTrue(win.wrap)
            self.assertTrue(win.chk_wrap.get_active())
            win._toggle_wrap(None)
            self.assertFalse(win.wrap)
            self.assertFalse(win.chk_wrap.get_active())
            self.assertEqual(win.tview.get_wrap_mode(), Gtk.WrapMode.NONE)
            win._toggle_wrap(None)
            self.assertTrue(win.wrap)
            self.assertTrue(win.chk_wrap.get_active())
            self.assertEqual(win.tview.get_wrap_mode(), Gtk.WrapMode.WORD)

        self.run_instantiated(check)

    def test_toggle_from_checkbox_keeps_state_consistent(self):
        def check(win):
            self.assertTrue(win.wrap)
            win.chk_wrap.set_active(False)
            self.assertFalse(win.wrap)
            self.assertEqual(win.tview.get_wrap_mode(), Gtk.WrapMode.NONE)

        self.run_instantiated(check)


class TestRecents(EditorBase):
    def test_add_recent_dedupes_prepends_and_trims(self):
        def check(win):
            win.recents = []
            for name in ["a", "b", "c", "d", "e", "f"]:
                win._add_recent(name)
            self.assertEqual(win.recents[:3], ["f", "e", "d"])
            win._add_recent("c")
            self.assertEqual(win.recents[0], "c")

        self.run_instantiated(check)


class TestVimMode(EditorBase):
    def test_vim_toggle(self):
        def check(win):
            self.assertFalse(win.vim_mode)
            win.btn_vim.set_active(True)
            self.assertTrue(win.vim_mode)
            self.assertEqual(win.vim_state, "NORMAL")
            win.btn_vim.set_active(False)
            self.assertFalse(win.vim_mode)

        self.run_instantiated(check)


class TestUndoRedo(EditorBase):
    def test_undo_redo_buffer(self):
        def check(win):
            buf = win.buf
            buf.begin_user_action()
            buf.set_text("hello")
            buf.end_user_action()
            self.assertTrue(buf.can_undo())
            buf.undo()
            self.assertEqual(buf.get_text(*buf.get_bounds(), True), "")
            buf.redo()
            self.assertEqual(buf.get_text(*buf.get_bounds(), True), "hello")

        self.run_instantiated(check)


class TestSearchReplace(EditorBase):
    def test_replace_all(self):
        def check(win):
            win.buf.set_text("foo bar foo baz foo")
            win.search_entry.set_text("foo")
            win.replace_entry.set_text("qux")
            win._replace_all()
            text = win.buf.get_text(*win.buf.get_bounds(), True)
            self.assertEqual(text, "qux bar qux baz qux")

        self.run_instantiated(check)


if __name__ == "__main__":
    unittest.main()
