# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.LDAP.
#
# Copyright 2025 by it's authors.
# Some rights reserved, see README and LICENSE.

"""LDAP control panel.

A self-contained replacement for the YAFOWIL-based control panel from
`pas.plugins.ldap.plonecontrolpanel`. Reads and writes the same
`node.ext.ldap.interfaces.ILDAPProps`, `ILDAPUsersConfig` and
`ILDAPGroupsConfig` attributes; depends only on Plone primitives.
"""

from node.ext.ldap.interfaces import ILDAPGroupsConfig
from node.ext.ldap.interfaces import ILDAPProps
from node.ext.ldap.interfaces import ILDAPUsersConfig
from node.ext.ldap.scope import BASE
from node.ext.ldap.scope import ONELEVEL
from node.ext.ldap.scope import SUBTREE
from node.ext.ldap.session import LDAPSession
from odict import odict
from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from Products.statusmessages.interfaces import IStatusMessage
from senaite.ldap import logger
from senaite.ldap import messageFactory as _
from zExceptions import NotFound


PLUGIN_ID = "pasldap"

SCOPES = (
    (BASE, "BASE"),
    (ONELEVEL, "ONELEVEL"),
    (SUBTREE, "SUBTREE"),
)

EXPIRES_UNITS = (
    (0, "Days since epoch"),
    (1, "Seconds since epoch"),
)


def _to_text(value):
    """Coerce a request value to ``unicode``.

    The persistent registry-backed fields used by ``pas.plugins.ldap``
    are typed as ``zope.schema.TextLine`` and reject ``str``. Request
    values come in as ``str`` under Py2, so every textual field needs
    to be normalised before being written.
    """
    if value is None:
        return u""
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def _split_lines(value):
    """Parse a textarea value as a list of non-empty stripped lines."""
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        return [line.strip() for line in value if line and line.strip()]
    return [line.strip() for line in value.splitlines() if line.strip()]


def _to_text_list(value):
    return [_to_text(v) for v in _split_lines(value)]


def _parse_attrmap(value):
    """Parse a textarea value as ``key=value`` lines into an odict.

    Blank lines and lines without ``=`` are silently skipped.
    Keys and values are normalised to ``unicode`` because the
    persisted fields are typed as ``zope.schema.TextLine`` and reject
    byte strings under Py2.
    """
    result = odict()
    for line in _split_lines(value):
        if "=" not in line:
            continue
        key, _sep, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        if not key:
            continue
        result[_to_text(key)] = _to_text(val)
    return result


def _format_attrmap(value):
    """Render an attribute map (odict / dict) as ``key=value\\n`` lines."""
    if not value:
        return ""
    return "\n".join("{}={}".format(k, v) for k, v in value.items())


def _format_lines(value):
    """Render a sequence as one entry per line."""
    if not value:
        return ""
    return "\n".join(value)


def _to_int(value, default=0):
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_bool(value):
    if isinstance(value, bool):
        return value
    if value in (None, "", "0", "false", "False", "off", "no"):
        return False
    return True


class LDAPControlPanel(BrowserView):
    """SENAITE LDAP control panel.
    """

    def __call__(self):
        if self.plugin is None:
            raise NotFound(
                "LDAP PAS plugin '{}' is not installed".format(PLUGIN_ID))

        if self.request.method == "POST":
            action = self.request.form.get("form.action", "save")
            if action == "test":
                self._handle_test()
            else:
                self._handle_save()
            return self.request.response.redirect(self.context.absolute_url()
                                                  + "/@@plone_ldapcontrolpanel")
        return self.index()

    # ------------------------------------------------------------------
    # plugin / config accessors
    # ------------------------------------------------------------------

    @property
    def plugin(self):
        acl_users = getToolByName(self.context, "acl_users", None)
        if acl_users is None:
            return None
        return getattr(acl_users, PLUGIN_ID, None)

    @property
    def props(self):
        return ILDAPProps(self.plugin)

    @property
    def users(self):
        return ILDAPUsersConfig(self.plugin)

    @property
    def groups(self):
        return ILDAPGroupsConfig(self.plugin)

    # ------------------------------------------------------------------
    # template helpers
    # ------------------------------------------------------------------

    def scope_choices(self):
        return [(str(value), label) for value, label in SCOPES]

    def expires_unit_choices(self):
        return [(str(value), label) for value, label in EXPIRES_UNITS]

    def server_data(self):
        props = self.props
        anonymous = not bool(getattr(props, "user", "")
                             or getattr(props, "password", ""))
        return {
            "uri": getattr(props, "uri", "") or "",
            "anonymous": anonymous,
            "user": getattr(props, "user", "") or "",
            "password": getattr(props, "password", "") or "",
            "ignore_cert": bool(getattr(props, "ignore_cert", False)),
            "conn_timeout": getattr(props, "conn_timeout", 0) or 0,
            "op_timeout": getattr(props, "op_timeout", 0) or 0,
            "page_size": getattr(props, "page_size", 1000) or 1000,
        }

    def cache_data(self):
        props = self.props
        return {
            "cache": bool(getattr(props, "cache", False)),
            "memcached": getattr(props, "memcached", "") or "",
            "timeout": getattr(props, "timeout", 0) or 0,
        }

    def users_data(self):
        users = self.users
        return {
            "baseDN": getattr(users, "baseDN", "") or "",
            "scope": str(getattr(users, "scope", SUBTREE)),
            "queryFilter": getattr(users, "queryFilter", "") or "",
            "objectClasses": _format_lines(
                getattr(users, "objectClasses", []) or []),
            "memberOfSupport": bool(getattr(users, "memberOfSupport", False)),
            "recursiveGroups": bool(getattr(users, "recursiveGroups", False)),
            "memberOfExternalGroupDNs": _format_lines(
                getattr(users, "memberOfExternalGroupDNs", []) or []),
            "account_expiration": bool(
                getattr(users, "account_expiration", False)),
            "expiresAttr": getattr(users, "_expiresAttr", "") or "",
            "expiresUnit": str(getattr(users, "_expiresUnit", 0) or 0),
            "attrmap": _format_attrmap(getattr(users, "attrmap", None)),
        }

    def groups_data(self):
        groups = self.groups
        return {
            "baseDN": getattr(groups, "baseDN", "") or "",
            "scope": str(getattr(groups, "scope", SUBTREE)),
            "queryFilter": getattr(groups, "queryFilter", "") or "",
            "objectClasses": _format_lines(
                getattr(groups, "objectClasses", []) or []),
            "memberOfSupport": bool(
                getattr(groups, "memberOfSupport", False)),
            "attrmap": _format_attrmap(getattr(groups, "attrmap", None)),
        }

    def connection_test(self):
        """Run a non-destructive connectivity probe against the
        configured LDAP server. Returns ``(ok, message)``.
        """
        try:
            session = LDAPSession(self.props)
            return session.checkServerProperties()
        except Exception as exc:
            return (False, str(exc))

    # ------------------------------------------------------------------
    # save handler
    # ------------------------------------------------------------------

    def _handle_save(self):
        form = self.request.form
        props = self.props
        users = self.users
        groups = self.groups

        # Server
        props.uri = _to_text(form.get("server.uri", "").strip())
        anonymous = _to_bool(form.get("server.anonymous"))
        if anonymous:
            props.user = u""
            props.password = u""
        else:
            props.user = _to_text(form.get("server.user", "").strip())
            password = form.get("server.password", "")
            # Don't wipe the stored password on an empty input — the
            # form never echoes the existing one.
            if password:
                props.password = _to_text(password)
        props.ignore_cert = _to_bool(form.get("server.ignore_cert"))
        props.conn_timeout = _to_int(form.get("server.conn_timeout"), 0)
        props.op_timeout = _to_int(form.get("server.op_timeout"), 0)
        props.page_size = max(_to_int(form.get("server.page_size"), 1000), 1)

        # Cache
        props.cache = _to_bool(form.get("cache.cache"))
        props.memcached = _to_text(form.get("cache.memcached", "").strip())
        props.timeout = _to_int(form.get("cache.timeout"), 0)

        # Users
        users.baseDN = _to_text(form.get("users.baseDN", "").strip())
        users.attrmap = _parse_attrmap(form.get("users.attrmap", ""))
        # The principal id attribute must map to itself or LDAP lookups
        # break later on. Replicate the safeguard from upstream.
        id_attr = users.attrmap.get("id")
        if id_attr and id_attr not in users.attrmap:
            users.attrmap[id_attr] = id_attr
        users.scope = _to_int(form.get("users.scope"), SUBTREE)
        users.queryFilter = _to_text(
            form.get("users.queryFilter", "").strip())
        users.objectClasses = _to_text_list(
            form.get("users.objectClasses", ""))
        users.memberOfSupport = _to_bool(form.get("users.memberOfSupport"))
        users.recursiveGroups = _to_bool(form.get("users.recursiveGroups"))
        users.memberOfExternalGroupDNs = _to_text_list(
            form.get("users.memberOfExternalGroupDNs", ""))
        users.account_expiration = _to_bool(
            form.get("users.account_expiration"))
        users._expiresAttr = _to_text(
            form.get("users.expiresAttr", "").strip())
        users._expiresUnit = _to_int(form.get("users.expiresUnit"), 0)

        # Groups
        groups.baseDN = _to_text(form.get("groups.baseDN", "").strip())
        groups.attrmap = _parse_attrmap(form.get("groups.attrmap", ""))
        groups.scope = _to_int(form.get("groups.scope"), SUBTREE)
        groups.queryFilter = _to_text(
            form.get("groups.queryFilter", "").strip())
        groups.objectClasses = _to_text_list(
            form.get("groups.objectClasses", ""))
        groups.memberOfSupport = _to_bool(
            form.get("groups.memberOfSupport"))
        groups.recursiveGroups = False
        groups.memberOfExternalGroupDNs = []

        IStatusMessage(self.request).add(
            _(u"LDAP settings saved."), type="info")
        logger.info("LDAP settings saved by user")

    # ------------------------------------------------------------------
    # connection test handler
    # ------------------------------------------------------------------

    def _handle_test(self):
        ok, message = self.connection_test()
        IStatusMessage(self.request).add(
            _(u"LDAP connection: ${state} (${message})",
              mapping={
                  "state": ok and u"OK" or u"ERROR",
                  "message": message,
              }),
            type=ok and "info" or "error")
