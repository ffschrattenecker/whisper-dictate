#!/usr/bin/env python3
"""Unit tests for dictate's pure functions. No audio, desktop session, GPU,
or network needed: python3 test_dictate.py"""

import os
import struct
import tempfile
import unittest
from pathlib import Path
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from unittest import mock

_loader = SourceFileLoader("dictate", "dictate")
_spec = spec_from_loader("dictate", _loader)
dictate = module_from_spec(_spec)
_loader.exec_module(dictate)


class ReplacementRulesTest(unittest.TestCase):
    def test_defaults_present(self):
        rules = dictate.replacement_rules({})
        self.assertEqual(rules["asterisk"], "*")
        self.assertEqual(rules["forward slash"], "/")

    def test_user_rules_merge_over_defaults(self):
        rules = dictate.replacement_rules({"replacements": {"star": "*"}})
        self.assertEqual(rules["star"], "*")
        self.assertEqual(rules["asterisk"], "*")  # default survives

    def test_null_removes_a_trigger(self):
        rules = dictate.replacement_rules({"replacements": {"asterisk": None}})
        self.assertNotIn("asterisk", rules)
        self.assertIn("question mark", rules)

    def test_empty_string_value_removes(self):
        rules = dictate.replacement_rules({"replacements": {"asterisk": "  "}})
        self.assertNotIn("asterisk", rules)

    def test_blank_spoken_phrase_ignored(self):
        rules = dictate.replacement_rules({"replacements": {"  ": "!"}})
        self.assertNotIn("  ", rules)

    def test_non_dict_replacements_ignored(self):
        rules = dictate.replacement_rules({"replacements": ["asterisk"]})
        self.assertIn("asterisk", rules)


class ApplyReplacementsTest(unittest.TestCase):
    def test_replaces_trigger(self):
        self.assertEqual(dictate.apply_replacements("use asterisk here", {}),
                         "use * here")

    def test_case_insensitive(self):
        self.assertEqual(dictate.apply_replacements("Use Asterisk here", {}),
                         "Use * here")

    def test_word_boundary(self):
        # plural must not trigger: \basterisk\b does not match "asterisks"
        self.assertEqual(dictate.apply_replacements("asterisks", {}),
                         "asterisks")
        # substring inside a longer word stays
        self.assertEqual(dictate.apply_replacements("disaster iskol x", {}),
                         "disaster iskol x")

    def test_longest_phrase_first(self):
        self.assertEqual(dictate.apply_replacements("a slash sign b", {}), "a / b")
        self.assertEqual(dictate.apply_replacements("a forward slash b", {}),
                         "a / b")

    def test_literal_escape_keeps_words(self):
        self.assertEqual(dictate.apply_replacements("type literal asterisk now", {}),
                         "type asterisk now")

    def test_literal_without_trigger_untouched(self):
        self.assertEqual(dictate.apply_replacements("in literal terms this fails", {}),
                         "in literal terms this fails")

    def test_multiple_literals(self):
        # "slash" alone is not a trigger ("slash sign" is), so it stays
        self.assertEqual(
            dictate.apply_replacements("literal asterisk and literal slash", {}),
            "asterisk and literal slash")
        self.assertEqual(
            dictate.apply_replacements("literal slash sign", {}), "slash sign")

    def test_user_override_applies(self):
        cfg = {"replacements": {"star": "*"}}
        self.assertEqual(dictate.apply_replacements("a star is born", cfg),
                         "a * is born")

    def test_user_trigger_removal(self):
        cfg = {"replacements": {"asterisk": None}}
        self.assertEqual(dictate.apply_replacements("asterisk", cfg), "asterisk")


class CleanTextTest(unittest.TestCase):
    def test_flattens_all_whitespace(self):
        self.assertEqual(dictate.clean_text("  a\n\n b \t c  ", 5.0, {}),
                         "a b c")

    def test_hallucination_on_short_clip_dropped(self):
        self.assertEqual(dictate.clean_text("Thank you.", 2.0, {}), "")

    def test_hallucination_on_long_clip_kept(self):
        # someone actually saying "thank you" for longer is transcribed
        self.assertEqual(dictate.clean_text("Thank you.", 8.0, {}), "Thank you.")

    def test_normal_short_text_kept(self):
        self.assertEqual(dictate.clean_text("hello world", 1.0, {}),
                         "hello world")

    def test_replacements_run_before_hallucination_check(self):
        self.assertEqual(dictate.clean_text("asterisk", 2.0, {}), "*")


class MultipartTest(unittest.TestCase):
    def test_body_and_header_shape(self):
        body, ctype = dictate.multipart(
            {"response_format": "json", "language": "de"},
            {"file": ("clip.wav", b"ABCD", "audio/wav")},
        )
        self.assertTrue(ctype.startswith("multipart/form-data; boundary="))
        boundary = ctype.split("=", 1)[1].encode()
        self.assertIn(b"--" + boundary + b"--\r\n", body)
        self.assertIn(b'name="language"\r\n\r\nde\r\n', body)
        self.assertIn(b'name="file"; filename="clip.wav"', body)
        self.assertIn(b"Content-Type: audio/wav\r\n\r\nABCD\r\n", body)


class WaylandWireTest(unittest.TestCase):
    def test_message_header(self):
        msg = dictate._wl_msg(3, 12, b"abcd")
        obj, opcode, size = struct.unpack("<IHH", msg[:8])
        self.assertEqual((obj, opcode, size), (3, 12, 8 + 4))
        self.assertEqual(msg[8:], b"abcd")

    def test_string_padded_to_four_bytes(self):
        raw = dictate._wl_str("ab")  # "ab\0" is 3 bytes -> padded to 4
        self.assertEqual(len(raw) % 4, 0)


class ClipPathTest(unittest.TestCase):
    def test_clip_goes_to_xdg_runtime_dir(self):
        with tempfile.TemporaryDirectory() as td, \
                mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": td}):
            p = dictate.tmp_clip_path()
            self.assertEqual(p.parent, Path(td) / "dictate")
            self.assertEqual(p.name, f"clip-{os.getpid()}.raw")
            self.assertEqual(p.parent.stat().st_mode & 0o777, 0o700)


class PidCmdlineTest(unittest.TestCase):
    def test_own_cmdline_readable(self):
        self.assertIn("test_dictate", dictate.pid_cmdline(os.getpid()))

    def test_absent_pid_is_empty(self):
        # beyond /proc/sys/kernel/pid_max: never a live process
        self.assertEqual(dictate.pid_cmdline(2 ** 31 - 1), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
