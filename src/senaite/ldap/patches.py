# -*- coding: utf-8 -*-
"""Monkey patches for upstream LDAP libraries.

The patches here guard against defects that surface as hard errors in
unrelated SENAITE code paths (e.g. Client creation triggers a PAS group
lookup which iterates LDAP groups; a user authenticating triggers a
search to resolve the login attribute to a user id).
"""

from node.ext.ldap import session as _ldap_session

from senaite.ldap import logger


_ORIGINAL_LDAP_SESSION_SEARCH = _ldap_session.LDAPSession.search


def _is_valid_entry(entry):
    """Return True if ``entry`` looks like a ``(dn, attrs)`` tuple
    with a non-None DN.

    Upstream node.ext.ldap 1.2 (``session.py`` line 57) blindly does
    ``x[0] is not None`` over every result entry, which raises
    ``IndexError`` if the underlying LDAP library returns malformed
    or empty entries — observed against LLDAP for searches that
    bounce through Traefik. Be defensive: skip entries that are not
    a non-empty two-element sequence with a non-None first element.

    The 2-element check exists because upstream ``_node.search``
    line 530 (``for dn, attrs in matches:``) unpacks every entry as
    ``(dn, attrs)``. Some servers (LLDAP among them) include search
    continuations / referral chasing entries in the result that have
    more than two elements; letting those through here surfaces as
    ``ValueError: too many values to unpack`` deeper in the stack.
    """
    if not entry:
        return False
    if isinstance(entry, (bytes, str)):
        return False
    try:
        if len(entry) != 2:
            return False
        return entry[0] is not None
    except (IndexError, TypeError):
        return False


def safe_ldap_session_search(self, queryFilter='(objectClass=*)',
                             scope=_ldap_session.BASE, baseDN=None,
                             force_reload=False, attrlist=None,
                             attrsonly=0, page_size=None, cookie=None):
    """Drop-in replacement for ``LDAPSession.search``.

    Differences from upstream:

    1. The paged-results response is unpacked defensively. When
       ``page_size`` is set, upstream does ``res, cookie = res`` and
       blows up if the LDAP server omits the paged-results control
       cookie (``ValueError: need more than 0 values to unpack``).
       Here we tolerate either shape and synthesize an empty cookie
       if needed.
    2. The "skip ActiveDirectory phantom entries" filter
       (``x[0] is not None``) is replaced with ``_is_valid_entry``
       which also tolerates empty / non-sequence entries.

    Both bugs surface as cryptic crashes deep inside the PAS
    authentication chain. The patches are conservative: on the happy
    path the behaviour is identical to upstream.
    """
    if not queryFilter:
        queryFilter = '(objectClass=*)'

    raw = self._communicator.search(
        queryFilter,
        scope,
        baseDN,
        force_reload,
        attrlist,
        attrsonly,
        page_size,
        cookie,
    )

    if page_size:
        try:
            res, cookie = raw
        except (ValueError, TypeError) as exc:
            logger.warning(
                "LDAP paged-results response had no cookie (%s); "
                "treating as empty page.", exc)
            res, cookie = [], None
    else:
        res = raw

    try:
        res = [x for x in res if _is_valid_entry(x)]
    except Exception as exc:
        logger.warning(
            "LDAP result filtering failed (%s); returning empty.",
            exc)
        res = []

    if page_size:
        return res, cookie
    return res


def apply_patches():
    """Apply all monkey patches.
    """
    if _ldap_session.LDAPSession.search is safe_ldap_session_search:
        return
    _ldap_session.LDAPSession.search = safe_ldap_session_search
    logger.info("Patched node.ext.ldap.session.LDAPSession.search")
