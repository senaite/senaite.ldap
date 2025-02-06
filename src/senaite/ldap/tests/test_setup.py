# -*- coding: utf-8 -*-

from Products.CMFPlone.utils import get_installer
from senaite.ldap.interfaces import ISenaiteLdap
from senaite.ldap.tests.base import SimpleTestCase


class TestSetup(SimpleTestCase):
    """Test Setup
    """

    def test_is_addon_installed(self):
        qi = get_installer(self.portal)
        self.assertTrue(qi.is_product_installed("senaite.ldap"))

    def test_browser_layer_active(self):
        self.assertTrue(ISenaiteLdap.providedBy(self.request))


def test_suite():
    from unittest import TestSuite
    from unittest import makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestSetup))
    return suite
