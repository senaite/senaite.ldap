# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.LDAP.
#
# Copyright 2025 by it's authors.
# Some rights reserved, see README and LICENSE.

import unittest2 as unittest

from senaite.ldap.browser.controlpanel import _format_attrmap
from senaite.ldap.browser.controlpanel import _format_lines
from senaite.ldap.browser.controlpanel import _parse_attrmap
from senaite.ldap.browser.controlpanel import _split_lines
from senaite.ldap.browser.controlpanel import _to_bool
from senaite.ldap.browser.controlpanel import _to_int


class TestSplitLines(unittest.TestCase):

    def test_empty(self):
        self.assertEqual(_split_lines(""), [])
        self.assertEqual(_split_lines(None), [])

    def test_strips_each_line(self):
        self.assertEqual(
            _split_lines("  a  \n  b  \n c "),
            ["a", "b", "c"])

    def test_drops_blank_lines(self):
        self.assertEqual(
            _split_lines("a\n\n\nb\n   \nc"),
            ["a", "b", "c"])

    def test_accepts_list(self):
        self.assertEqual(_split_lines(["a", "", "  b ", None]), ["a", "b"])


class TestParseAttrmap(unittest.TestCase):

    def test_basic(self):
        result = _parse_attrmap("id=uid\nlogin=uid\nemail=mail")
        self.assertEqual(result["id"], "uid")
        self.assertEqual(result["login"], "uid")
        self.assertEqual(result["email"], "mail")

    def test_preserves_order(self):
        result = _parse_attrmap("a=1\nb=2\nc=3")
        self.assertEqual(list(result.keys()), ["a", "b", "c"])

    def test_strips_whitespace(self):
        result = _parse_attrmap("  id  =  uid  ")
        self.assertEqual(result["id"], "uid")

    def test_skips_lines_without_equals(self):
        result = _parse_attrmap("ok=1\ngarbage\nid=uid")
        self.assertEqual(list(result.keys()), ["ok", "id"])

    def test_skips_empty_keys(self):
        result = _parse_attrmap("=value")
        self.assertEqual(len(result), 0)

    def test_format_round_trip(self):
        original = _parse_attrmap("id=uid\nlogin=uid\nemail=mail")
        formatted = _format_attrmap(original)
        again = _parse_attrmap(formatted)
        self.assertEqual(list(again.items()), list(original.items()))


class TestFormatHelpers(unittest.TestCase):

    def test_format_lines(self):
        self.assertEqual(_format_lines(["a", "b", "c"]), "a\nb\nc")
        self.assertEqual(_format_lines([]), "")
        self.assertEqual(_format_lines(None), "")

    def test_format_attrmap_empty(self):
        self.assertEqual(_format_attrmap(None), "")
        self.assertEqual(_format_attrmap({}), "")


class TestCoercion(unittest.TestCase):

    def test_to_int(self):
        self.assertEqual(_to_int("42"), 42)
        self.assertEqual(_to_int(42), 42)
        self.assertEqual(_to_int(""), 0)
        self.assertEqual(_to_int(None), 0)
        self.assertEqual(_to_int("garbage"), 0)
        self.assertEqual(_to_int("garbage", default=7), 7)

    def test_to_bool(self):
        # Truthy
        self.assertTrue(_to_bool(True))
        self.assertTrue(_to_bool("1"))
        self.assertTrue(_to_bool("yes"))
        self.assertTrue(_to_bool("on"))
        # Falsy
        self.assertFalse(_to_bool(False))
        self.assertFalse(_to_bool(None))
        self.assertFalse(_to_bool(""))
        self.assertFalse(_to_bool("0"))
        self.assertFalse(_to_bool("false"))
        self.assertFalse(_to_bool("False"))
        self.assertFalse(_to_bool("off"))
        self.assertFalse(_to_bool("no"))


def test_suite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTests(loader.loadTestsFromTestCase(TestSplitLines))
    suite.addTests(loader.loadTestsFromTestCase(TestParseAttrmap))
    suite.addTests(loader.loadTestsFromTestCase(TestFormatHelpers))
    suite.addTests(loader.loadTestsFromTestCase(TestCoercion))
    return suite
