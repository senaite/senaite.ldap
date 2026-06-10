# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.LDAP.
#
# Copyright 2025 by it's authors.
# Some rights reserved, see README and LICENSE.

"""Live LDAP search / inspector.

Provides a small UI plus two JSON endpoints for browsing the
configured LDAP directory from the control panel. Replaces the
`@@senaite_ldapinspector` view from the dropped
`pas.plugins.ldap.plonecontrolpanel` subtree.

- ``@@senaite_ldapsearch`` — main page (HTML form + results table).
- ``@@senaite_ldapsearch_results`` — JSON: search results for a
  base + filter.
- ``@@senaite_ldapsearch_attrs`` — JSON: full attribute dump for a
  single DN.
"""

import json

from node.ext.ldap import LDAPNode
from node.ext.ldap.interfaces import ILDAPGroupsConfig
from node.ext.ldap.interfaces import ILDAPProps
from node.ext.ldap.interfaces import ILDAPUsersConfig
from node.ext.ldap.scope import BASE
from node.ext.ldap.scope import ONELEVEL
from node.ext.ldap.scope import SUBTREE
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode
from Products.Five.browser import BrowserView
from senaite.ldap import logger
from zExceptions import NotFound

import six


PLUGIN_ID = "pasldap"

DEFAULT_FILTER = u"(objectClass=*)"
RESULT_LIMIT = 200

SCOPES = {
    "base": BASE,
    "one": ONELEVEL,
    "sub": SUBTREE,
}


def _safe_unicode(value):
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return u"(non-utf8 bytes)"
    return safe_unicode(value) if value is not None else u""


class _LDAPSearchBase(BrowserView):
    """Shared helpers for the search page and JSON endpoints."""

    @property
    def plugin(self):
        acl_users = getToolByName(self.context, "acl_users", None)
        if acl_users is None:
            return None
        return getattr(acl_users, PLUGIN_ID, None)

    def _require_plugin(self):
        if self.plugin is None:
            raise NotFound(
                "LDAP PAS plugin '{}' is not installed".format(PLUGIN_ID))

    @property
    def props(self):
        return ILDAPProps(self.plugin)

    def base_for(self, choice):
        """Resolve the base DN for the given choice.

        choice is one of ``users`` / ``groups`` / ``custom``. For
        ``custom`` the caller supplies the literal DN via the request.
        """
        if choice == "users":
            return ILDAPUsersConfig(self.plugin).baseDN or u""
        if choice == "groups":
            return ILDAPGroupsConfig(self.plugin).baseDN or u""
        # custom
        return _safe_unicode(self.request.get("base_dn", "")).strip()


class LDAPSearchView(_LDAPSearchBase):
    """HTML page that renders the search form + results container.

    The container is empty on first render; the front-end JS calls
    `@@senaite_ldapsearch_results` and `@@senaite_ldapsearch_attrs`
    incrementally.
    """

    def __call__(self):
        self._require_plugin()
        return self.index()

    def users_base(self):
        return _safe_unicode(self.base_for("users"))

    def groups_base(self):
        return _safe_unicode(self.base_for("groups"))


class LDAPSearchResultsView(_LDAPSearchBase):
    """JSON: search the directory and return up to RESULT_LIMIT DNs.

    Query params:
      - ``base`` — one of ``users`` / ``groups`` / ``custom``
      - ``base_dn`` — literal DN, used only when base is ``custom``
      - ``filter`` — RFC4515 filter, defaults to ``(objectClass=*)``
      - ``scope`` — ``base`` / ``one`` / ``sub``, default ``sub``
    """

    def __call__(self):
        self._require_plugin()
        self.request.response.setHeader(
            "Content-Type", "application/json")

        base_choice = self.request.get("base", "users")
        base_dn = self.base_for(base_choice)
        query_filter = (
            _safe_unicode(self.request.get("filter", "")).strip()
            or DEFAULT_FILTER
        )
        scope = SCOPES.get(self.request.get("scope", "sub"), SUBTREE)

        if not base_dn:
            return json.dumps({
                "ok": False,
                "error": "No base DN configured for this choice.",
                "dns": [],
            })

        try:
            node = LDAPNode(base_dn, self.props)
            node.search_scope = scope
            dns = node.search(
                queryFilter=query_filter,
            )
        except Exception as exc:
            logger.warn(
                "LDAP search failed: base=%r filter=%r scope=%r — %s",
                base_dn, query_filter, scope, exc)
            return json.dumps({
                "ok": False,
                "error": str(exc),
                "dns": [],
            })

        truncated = False
        if len(dns) > RESULT_LIMIT:
            dns = dns[:RESULT_LIMIT]
            truncated = True

        return json.dumps({
            "ok": True,
            "base": _safe_unicode(base_dn),
            "filter": query_filter,
            "count": len(dns),
            "truncated": truncated,
            "dns": [_safe_unicode(dn) for dn in dns],
        })


class LDAPNodeAttrsView(_LDAPSearchBase):
    """JSON: full attribute dump for a single DN within a configured base.

    Query params:
      - ``base`` — one of ``users`` / ``groups`` / ``custom``
        (controls which baseDN to anchor the lookup on)
      - ``base_dn`` — literal DN when base is ``custom``
      - ``dn`` — the DN whose attributes to fetch
    """

    def __call__(self):
        self._require_plugin()
        self.request.response.setHeader(
            "Content-Type", "application/json")

        base_choice = self.request.get("base", "users")
        base_dn = self.base_for(base_choice)
        target_dn = _safe_unicode(self.request.get("dn", "")).strip()

        if not base_dn or not target_dn:
            return json.dumps({
                "ok": False,
                "error": "Both base and dn are required.",
                "attrs": {},
            })

        try:
            root = LDAPNode(base_dn, self.props)
            node = root.node_by_dn(target_dn, strict=True)
        except Exception as exc:
            logger.warn(
                "LDAP node lookup failed: base=%r dn=%r — %s",
                base_dn, target_dn, exc)
            return json.dumps({
                "ok": False,
                "error": str(exc),
                "attrs": {},
            })

        attrs = {}
        is_binary = node.attrs.is_binary
        for key, value in node.attrs.items():
            try:
                k = _safe_unicode(key)
                if is_binary(key):
                    attrs[k] = u"(binary, {} bytes)".format(len(value))
                elif isinstance(value, (list, tuple)):
                    attrs[k] = [_safe_unicode(v) for v in value]
                else:
                    attrs[k] = _safe_unicode(value)
            except Exception as exc:
                attrs[_safe_unicode(key)] = u"! ({})".format(exc)

        return json.dumps({
            "ok": True,
            "dn": target_dn,
            "attrs": attrs,
        })
