# -*- coding: utf-8 -*-
"""Monkey patches for upstream LDAP libraries.

The patches here guard against defects that surface as hard errors in
unrelated SENAITE code paths (e.g. Client creation triggers a PAS group
lookup which iterates LDAP groups).
"""

from node.ext.ldap import session as _ldap_session

from senaite.ldap import logger


_ORIGINAL_LDAP_SESSION_SEARCH = _ldap_session.LDAPSession.search


def safe_ldap_session_search(self, *args, **kwargs):
    """Wrap LDAPSession.search to tolerate empty paged responses.

    node.ext.ldap 1.2 unconditionally unpacks the communicator response
    into ``(results, cookie)`` when a page size is set
    (``session.py`` line 55). If the LDAP server returns no results or
    omits the paged-results control cookie, the unpacking raises
    ``ValueError: need more than 0 values to unpack`` and breaks any
    caller that enumerates groups via PAS, including Client creation.

    Treat that as an empty result instead of propagating the error.
    """
    try:
        return _ORIGINAL_LDAP_SESSION_SEARCH(self, *args, **kwargs)
    except ValueError as exc:
        logger.warning(
            "LDAP search failed to unpack paged response (%s); "
            "treating as empty result. Check your LDAP server's "
            "paged-results support and the configured page size.",
            exc,
        )
        if kwargs.get("page_size"):
            return [], None
        return []


def apply_patches():
    """Apply all monkey patches.
    """
    if _ldap_session.LDAPSession.search is safe_ldap_session_search:
        return
    _ldap_session.LDAPSession.search = safe_ldap_session_search
    logger.info("Patched node.ext.ldap.session.LDAPSession.search")
