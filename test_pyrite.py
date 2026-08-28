import os
import tempfile
import unittest

os.environ.setdefault("GDK_BACKEND", "x11")
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

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
            win.indent = "4s"
            win.toggle_indent(None)
            self.assertEqual(win.indent, "2s")
            win.toggle_indent(None)
            self.assertEqual(win.indent, "Tab")
            win.toggle_indent(None)
            self.assertEqual(win.indent, "4s")

        self.run_instantiated(check)


class TestToggleWrap(EditorBase):
    def test_toggle_from_alt_z_updates_checkbox_and_wrap_mode(self):
        def check(win):
            self.assertTrue(win.wrap)
            self.assertTrue(win.chk_wrap.get_active())
            win.toggle_wrap(None)
            self.assertFalse(win.wrap)
            self.assertFalse(win.chk_wrap.get_active())
            self.assertEqual(win.tview.get_wrap_mode(), Gtk.WrapMode.NONE)
            win.toggle_wrap(None)
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


class TestToggleSyntax(EditorBase):
    def test_toggle_from_alt_shortcut_updates_checkbox(self):
        def check(win):
            self.assertFalse(win.syntax)
            self.assertFalse(win.chk_syn.get_active())
            win.toggle_syntax(None)
            self.assertTrue(win.syntax)
            self.assertTrue(win.chk_syn.get_active())
            win.toggle_syntax(None)
            self.assertFalse(win.syntax)
            self.assertFalse(win.chk_syn.get_active())

        self.run_instantiated(check)


class TestRecents(EditorBase):
    def test_add_recent_dedupes_prepends_and_trims_to_five(self):
        def check(win):
            win.recent_path = os.path.join(tempfile.mkdtemp(), "recents.json")
            win.recents = []
            for name in ["a", "b", "c", "d", "e", "f"]:
                win.add_recent(name)
            self.assertEqual(win.recents, ["f", "e", "d", "c", "b"])
            win.add_recent("c")
            self.assertEqual(win.recents, ["c", "f", "e", "d", "b"])
            with open(win.recent_path) as fh:
                self.assertEqual(__import__("json").load(fh), win.recents)

        self.run_instantiated(check)

    def test_load_recents_returns_empty_for_missing_file(self):
        def check(win):
            win.recent_path = os.path.join(tempfile.mkdtemp(), "nope.json")
            self.assertEqual(win.load_recents(), [])

        self.run_instantiated(check)

    def test_load_recents_filters_non_strings(self):
        def check(win):
            win.recent_path = os.path.join(tempfile.mkdtemp(), "recents.json")
            with open(win.recent_path, "w") as fh:
                __import__("json").dump([1, "ok", None, "two"], fh)
            self.assertEqual(win.load_recents(), ["ok", "two"])

        self.run_instantiated(check)


class TestRenderTags(EditorBase):
    def test_renders_bold_italic_and_size_tags(self):
        def check(win):
            win.buf.set_text("a<bold>b</bold>c<italic>d</italic>e<ts=22>f</ts=22>g")
            win.render_tags()
            buf = win.r_buf
            text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
            self.assertEqual(text, "abcdefg")
            table = buf.get_tag_table()
            self.assertIsNotNone(table.lookup("r_ts_22"))

        self.run_instantiated(check)

    def test_bad_size_falls_back_to_default_scale(self):
        def check(win):
            win.buf.set_text("<ts=zz>hi</ts=zz>")
            win.render_tags()
            buf = win.r_buf
            table = buf.get_tag_table()
            tag = table.lookup("r_ts_zz")
            self.assertIsNotNone(tag)
            self.assertEqual(tag.props.scale, 1.0)

        self.run_instantiated(check)


class TestRunVimCmd(EditorBase):
    def test_w_calls_save_file(self):
        def check(win):
            calls = []
            win.save_file = lambda w=None: calls.append("save")
            win.quit_app = lambda w=None: calls.append("quit")
            win.vim_cmd = ":w"
            win.run_vim_cmd()
            self.assertEqual(calls, ["save"])
            self.assertEqual(win.vim_cmd_mode, False)

        self.run_instantiated(check)

    def test_wq_saves_then_quits(self):
        def check(win):
            calls = []
            win.save_file = lambda w=None: calls.append("save") or True
            win.quit_app = lambda w=None: calls.append("quit")
            win.vim_cmd = ":wq"
            win.run_vim_cmd()
            self.assertEqual(calls, ["save", "quit"])

        self.run_instantiated(check)

    def test_wq_skips_quit_if_save_fails(self):
        def check(win):
            calls = []
            win.save_file = lambda w=None: calls.append("save") or False
            win.quit_app = lambda w=None: calls.append("quit")
            win.vim_cmd = ":wq"
            win.run_vim_cmd()
            self.assertEqual(calls, ["save"])

        self.run_instantiated(check)


if __name__ == "__main__":
    unittest.main()
