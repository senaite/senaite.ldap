# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.LDAP.
#
# Copyright 2025 by it's authors.
# Some rights reserved, see README and LICENSE.

"""Discovery endpoints for the LDAP control panel.

Two JSON endpoints that surface what is actually in the configured
directory, so the user picks from real values instead of typing them
blind:

- ``@@senaite_ldapdiscover_objectclasses`` — list of objectClass
  values seen under the Users or Groups base DN (sampled), so the
  control panel can offer a multi-select instead of a free-text
  area.
- ``@@senaite_ldapdiscover_groups`` — list of group DNs / CNs found
  under the Groups base DN matching the configured group object
  classes. Lets the Users tab restrict to specific groups via a
  picker instead of hand-crafting ``memberOf=…`` filters.
"""

import json

from node.ext.ldap import LDAPNode
from node.ext.ldap.interfaces import ILDAPGroupsConfig
from node.ext.ldap.interfaces import ILDAPProps
from node.ext.ldap.interfaces import ILDAPUsersConfig
from node.ext.ldap.scope import BASE
from node.ext.ldap.scope import SUBTREE
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode
from Products.Five.browser import BrowserView
from senaite.ldap import logger
from zExceptions import NotFound


PLUGIN_ID = "pasldap"
SAMPLE_SIZE = 100
GROUP_LIST_LIMIT = 500


def _safe_unicode(value):
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return u"(non-utf8 bytes)"
    if value is None:
        return u""
    return safe_unicode(value)


def _extract_object_classes(attrs):
    """Yield objectClass values from an attrs payload regardless of
    case or container shape.

    LDAP attribute names are case-insensitive in the protocol but
    Python dict lookups aren't, and the underlying library may
    return the dict keyed differently across servers (``objectClass``
    vs ``objectclass`` vs bytes). Iterate keys and pick whichever
    one matches case-insensitively.
    """
    if not attrs:
        return []
    try:
        items = attrs.items()
    except AttributeError:
        # node.ext.ldap node.attrs sometimes behaves like a dict via
        # __getitem__/__iter__ without exposing items(); fall back.
        items = ((k, attrs[k]) for k in attrs)
    for key, value in items:
        try:
            key_s = key.decode("utf-8") if isinstance(key, bytes) else key
        except UnicodeDecodeError:
            continue
        if key_s.lower() != u"objectclass":
            continue
        if value is None:
            continue
        if isinstance(value, (bytes, str)):
            return [value]
        try:
            return list(value)
        except TypeError:
            return [value]
    return []


def _cn_from_dn(dn):
    """Extract the leftmost RDN value (typically the CN) from a DN.

    Returns the DN itself if parsing fails — safer than blowing up.
    """
    if not dn:
        return u""
    parts = dn.split(u",", 1)
    leaf = parts[0].strip()
    if u"=" in leaf:
        return leaf.split(u"=", 1)[1].strip()
    return leaf


class _DiscoveryBase(BrowserView):
    """Common plugin/config accessors."""

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

    @property
    def users(self):
        return ILDAPUsersConfig(self.plugin)

    @property
    def groups(self):
        return ILDAPGroupsConfig(self.plugin)


class LDAPDiscoverObjectClassesView(_DiscoveryBase):
    """JSON: sample entries under a base DN and aggregate their
    ``objectClass`` values.

    Sampling instead of schema introspection so we work against any
    server, including ones that don't expose ``subschemaSubentry``.
    Returns the unique objectClass values present in real entries
    under the configured base — what the admin probably wants to
    pick from.

    Query params:
      - ``which`` — ``users`` or ``groups`` (picks which base DN to
        sample under).
    """

    def __call__(self):
        self._require_plugin()
        self.request.response.setHeader(
            "Content-Type", "application/json")

        which = self.request.get("which", "users")
        if which == "groups":
            base_dn = _safe_unicode(self.groups.baseDN)
        else:
            base_dn = _safe_unicode(self.users.baseDN)

        if not base_dn:
            return json.dumps({
                "ok": False,
                "error": "No base DN configured for '{}'".format(which),
                "object_classes": [],
            })

        from node.ext.ldap.session import LDAPSession
        session = LDAPSession(self.props)

        # Step 1: list DNs under the base (SUBTREE).
        try:
            entries = session.search(
                queryFilter=u"(objectClass=*)",
                scope=SUBTREE,
                baseDN=base_dn,
            )
        except Exception as exc:
            logger.warn(
                "Object-class discovery (listing) failed for %s "
                "base %r — %s", which, base_dn, exc)
            return json.dumps({
                "ok": False,
                "error": str(exc),
                "object_classes": [],
            })

        dns = []
        for entry in entries:
            if not entry or len(entry) < 1:
                continue
            dns.append(_safe_unicode(entry[0]))

        # Step 2: for each sampled DN, do a BASE-scope fetch for its
        # full attrs. Bypasses node.ext.ldap's tree-walking
        # abstractions which proved brittle against LLDAP — direct
        # session.search calls give us back the attrs payload our
        # patched safe_ldap_session_search has already normalised to
        # a dict via _coerce_attrs.
        seen = set()
        sampled = 0
        for dn in dns:
            if sampled >= SAMPLE_SIZE:
                break
            try:
                base_entries = session.search(
                    queryFilter=u"(objectClass=*)",
                    scope=BASE,
                    baseDN=dn,
                )
            except Exception:
                continue
            for entry in base_entries:
                if not entry or len(entry) < 2:
                    continue
                attrs = entry[1]
                for oc in _extract_object_classes(attrs):
                    seen.add(_safe_unicode(oc))
            sampled += 1

        seen.discard(u"top")  # always present, never useful to pick
        seen.discard(u"")
        return json.dumps({
            "ok": True,
            "sampled": sampled,
            "object_classes": sorted(seen),
        })


class LDAPDiscoverGroupsView(_DiscoveryBase):
    """JSON: list groups under the configured Groups base DN.

    Uses the configured group object classes (or a sensible default
    ``OR`` of the common ones) to filter. Returns ``[{dn, cn}, …]``,
    capped at ``GROUP_LIST_LIMIT`` so very large directories stay
    responsive.
    """

    DEFAULT_OBJECT_CLASSES = (
        u"groupOfNames",
        u"groupOfUniqueNames",
        u"posixGroup",
        u"group",
    )

    def __call__(self):
        self._require_plugin()
        self.request.response.setHeader(
            "Content-Type", "application/json")

        base_dn = _safe_unicode(self.groups.baseDN)
        if not base_dn:
            return json.dumps({
                "ok": False,
                "error": "No Groups base DN configured",
                "groups": [],
            })

        # Override of object classes via query param: lets the UI ask
        # for groups under a different OC set without persisting first.
        oc_csv = self.request.get("object_classes", "")
        if oc_csv:
            oc_list = [
                _safe_unicode(s).strip() for s in oc_csv.split(",")
                if s.strip()
            ]
        else:
            oc_list = list(self.groups.objectClasses or [])
            if not oc_list:
                oc_list = list(self.DEFAULT_OBJECT_CLASSES)

        filter_expr = u"(|" + u"".join(
            u"(objectClass={})".format(oc) for oc in oc_list) + u")"

        try:
            node = LDAPNode(base_dn, self.props)
            node.search_scope = SUBTREE
            dns = node.search(
                queryFilter=filter_expr,
            )
        except Exception as exc:
            logger.warn(
                "Group discovery failed for base %r filter %r — %s",
                base_dn, filter_expr, exc)
            return json.dumps({
                "ok": False,
                "error": str(exc),
                "groups": [],
            })

        truncated = False
        if len(dns) > GROUP_LIST_LIMIT:
            dns = dns[:GROUP_LIST_LIMIT]
            truncated = True

        out = []
        for dn in dns:
            dn_u = _safe_unicode(dn)
            out.append({
                "dn": dn_u,
                "cn": _cn_from_dn(dn_u),
            })
        out.sort(key=lambda x: x["cn"].lower())

        return json.dumps({
            "ok": True,
            "count": len(out),
            "truncated": truncated,
            "filter": filter_expr,
            "groups": out,
        })


class LDAPStatusView(_DiscoveryBase):
    """JSON: live connectivity probe.

    Runs ``LDAPSession.checkServerProperties`` and reports
    ``{ok, message}``. Called by the control-panel JS on page load
    to colour the *Server* tab's connection dot.
    """

    def __call__(self):
        self._require_plugin()
        self.request.response.setHeader(
            "Content-Type", "application/json")

        from node.ext.ldap.session import LDAPSession
        try:
            session = LDAPSession(self.props)
            ok, message = session.checkServerProperties()
            return json.dumps({
                "ok": bool(ok),
                "message": _safe_unicode(message),
            })
        except Exception as exc:
            return json.dumps({
                "ok": False,
                "message": _safe_unicode(str(exc)),
            })


class LDAPDiscoverNamingContextsView(_DiscoveryBase):
    """JSON: read the rootDSE's ``namingContexts`` attribute.

    Anonymous (or bound) search at ``base=""`` ``scope=BASE`` for
    ``(objectClass=*)``. Every LDAP-conformant server publishes the
    list of root naming contexts it serves there. Used to offer the
    user a starting point for Users / Groups Base DN fields.
    """

    def __call__(self):
        self._require_plugin()
        self.request.response.setHeader(
            "Content-Type", "application/json")

        try:
            from node.ext.ldap.session import LDAPSession
            from node.ext.ldap.scope import BASE
            session = LDAPSession(self.props)
            results = session.search(
                queryFilter=u"(objectClass=*)",
                scope=BASE,
                baseDN=u"",
                attrlist=[u"namingContexts"],
            )
        except Exception as exc:
            logger.warn("namingContexts lookup failed: %s", exc)
            return json.dumps({
                "ok": False,
                "error": str(exc),
                "naming_contexts": [],
            })

        contexts = set()
        for entry in results:
            if not entry or len(entry) != 2:
                continue
            _dn, attrs = entry
            for key in (u"namingContexts", b"namingContexts"):
                value = attrs.get(key)
                if not value:
                    continue
                if isinstance(value, (bytes, str)):
                    value = [value]
                for nc in value:
                    contexts.add(_safe_unicode(nc))
                break

        # Fallback: some servers (LLDAP) don't publish namingContexts
        # on the rootDSE. Derive a sensible candidate from the bind
        # DN's dc= suffix.
        fallback_used = False
        if not contexts:
            bind_dn = _safe_unicode(getattr(self.props, "user", "") or "")
            dc_suffix = u",".join(
                part.strip() for part in bind_dn.split(u",")
                if part.strip().lower().startswith(u"dc=")
            )
            if dc_suffix:
                contexts.add(dc_suffix)
                fallback_used = True

        return json.dumps({
            "ok": True,
            "naming_contexts": sorted(contexts),
            "fallback": fallback_used,
        })
