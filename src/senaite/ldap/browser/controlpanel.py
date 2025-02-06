# -*- coding: utf-8 -*-

from pas.plugins.ldap.plonecontrolpanel.controlpanel import LDAPControlPanel


class SenaiteLDAPControlPanel(LDAPControlPanel):
    """SENAITE LDAP Control Panel View
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request
