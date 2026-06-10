# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.LDAP.
#
# Copyright 2025 by it's authors.
# Some rights reserved, see README and LICENSE.

"""User property sheet for the vendored LDAP PAS plugin.

Wraps a `UserPropertySheet` so reads / writes on a Plone member's
properties translate to reads / writes on the LDAP principal's
attribute set.
"""

from Acquisition import aq_base
from node.ext.ldap.interfaces import ILDAPGroupsConfig
from node.ext.ldap.interfaces import ILDAPUsersConfig
from Products.PlonePAS.interfaces.propertysheets \
    import IMutablePropertySheet
from Products.PluggableAuthService.UserPropertySheet \
    import UserPropertySheet
from senaite.ldap import logger
from zope.globalrequest import getRequest
from zope.interface import implementer


@implementer(IMutablePropertySheet)
class LDAPUserPropertySheet(UserPropertySheet):
    """Mutable property sheet backed by an LDAP principal's attrs."""

    def __init__(self, principal, plugin):
        """Instantiate.

        :param principal: User or group object whose id selects the
            backing LDAP principal.
        :param plugin: The `LDAPPlugin` instance.
        """
        # do not stash any non-pickleable (acquisition-wrapped)
        # attribute on `self`; the sheet may be cached.
        self._plugin = aq_base(plugin)
        self._properties = dict()
        self._attrmap = dict()
        self._ldapprincipal_id = principal.getId()
        if self._ldapprincipal_id in plugin.users:
            pcfg = ILDAPUsersConfig(plugin)
            self._ldapprincipal_type = "users"
        else:
            pcfg = ILDAPGroupsConfig(plugin)
            self._ldapprincipal_type = "groups"
        for k, v in pcfg.attrmap.items():
            # 'rdn' and 'id' are structural and not editable here.
            if k in ("rdn", "id"):
                continue
            self._attrmap[k] = v
        ldapprincipal = self._get_ldap_principal()
        request = getRequest()
        # Reload the principal's attrs once per request so stale data
        # doesn't survive across requests.
        if not request or not request.get("_ldap_props_reloaded"):
            ldapprincipal.attrs.context.load()
            if request:
                request["_ldap_props_reloaded"] = 1
        for key in self._attrmap:
            self._properties[key] = ldapprincipal.attrs.get(key, "")
        UserPropertySheet.__init__(
            self, plugin.getId(), schema=None, **self._properties)

    def _get_ldap_principal(self):
        """Fetch the live LDAP principal.

        Done lazily so no LDAP-bound state is persisted on `self`.
        """
        ldap_principals = getattr(
            self._plugin, self._ldapprincipal_type)
        return ldap_principals[self._ldapprincipal_id]

    def canWriteProperty(self, obj, id):
        return id in self._properties

    def setProperty(self, obj, id, value):
        assert id in self._properties
        ldapprincipal = self._get_ldap_principal()
        self._properties[id] = ldapprincipal.attrs[id] = value
        try:
            ldapprincipal.context()
        except Exception as exc:  # noqa: BLE001 -- backend variety
            logger.error("LDAPUserPropertySheet.setProperty: %s", exc)

    def setProperties(self, obj, mapping):
        for id in mapping:
            assert id in self._properties
        ldapprincipal = self._get_ldap_principal()
        for id in mapping:
            self._properties[id] = ldapprincipal.attrs[id] = mapping[id]
        try:
            ldapprincipal.context()
        except Exception as exc:  # noqa: BLE001 -- backend variety
            logger.error("LDAPUserPropertySheet.setProperties: %s", exc)
