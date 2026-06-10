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


def _coerce_attrs(value):
    """Normalise the second element of a search result entry to a
    dict.

    python-ldap usually returns ``(dn, {attr: [vals]})``, but against
    some servers (LLDAP via Traefik observed) the attrs payload is a
    flat list/tuple of ``(attr, [vals])`` pairs. Upstream consumers
    like ``_node.search`` call ``six.iteritems(attrs)`` on it and
    blow up with "'tuple' object has no attribute 'iteritems'".

    Defensively coerce to dict; fall back to empty dict on failure.
    """
    if isinstance(value, dict):
        return value
    try:
        return dict(value)
    except Exception:
        return {}


def _looks_like_paged_response(raw):
    """Return True if ``raw`` matches the ``(results, cookie)`` shape
    that ``base.LDAPCommunicator.search`` produces when a
    SimplePagedResultsControl is attached to the LDAP response.

    A real result list, by contrast, is a list of ``(dn, attrs)``
    tuples whose first element is the raw DN bytes/str. We use that
    distinction to avoid false positives: a flat result list whose
    first element happens to be a 2-tuple shouldn't be unwrapped.
    """
    if not isinstance(raw, tuple) or len(raw) != 2:
        return False
    results, cookie = raw
    if not isinstance(results, list):
        return False
    # Cookie is a bytes/str token (often empty). A real first-entry
    # would be a (dn_bytes, attrs) tuple — definitely not bytes/str.
    return isinstance(cookie, (bytes, str))


def _is_valid_entry(entry):
    """Return True if ``entry`` looks like a search result with a
    non-None DN and at least an attributes dict.

    Upstream node.ext.ldap 1.2 (``session.py`` line 57) blindly does
    ``x[0] is not None``, which raises ``IndexError`` on empty or
    non-sequence entries. Be defensive.

    We accept entries with two **or more** elements: python-ldap
    sometimes returns ``(dn, attrs, controls)`` 3-tuples when the
    underlying response carries per-entry controls. The original
    upstream filter only checked element 0, so it would have passed
    these through to ``_node.search`` line 530 (``for dn, attrs in
    matches:``) which would have crashed with "too many values to
    unpack" — what we'd seen against LLDAP earlier. The right move
    is to keep these entries and coerce them to ``(dn, attrs)``
    in ``safe_ldap_session_search``, not to drop them.
    """
    if not entry:
        return False
    if isinstance(entry, (bytes, str)):
        return False
    try:
        if len(entry) < 2:
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

    # The communicator can return ``(results, cookie)`` even when we
    # did NOT ask for paging — LLDAP attaches a SimplePagedResultsControl
    # to every response, and ``base.LDAPCommunicator`` reflexively
    # unwraps it into a tuple. Upstream's session ignores this case and
    # treats the tuple as the result list, which then iterates over
    # ``(results_list, cookie_bytes)`` and yields exactly one
    # misshapen "entry" (the *first* hit) before the cookie is dropped
    # as invalid — the visible symptom is searches that always return
    # one result, no matter how many entries the server actually sent.
    # Detect the (results, cookie) tuple shape on every call, not just
    # when ``page_size`` is truthy.
    if _looks_like_paged_response(raw):
        res, response_cookie = raw
    else:
        res = raw
        response_cookie = None
    if page_size:
        cookie = response_cookie

    try:
        # Coerce every retained entry to a 2-tuple (dn, attrs_dict)
        # so the upstream consumer
        # ``for dn, attrs in matches: six.iteritems(attrs)`` in
        # ``_node.search`` doesn't choke on 3-tuples (per-entry
        # controls) or on attrs payloads that aren't real dicts.
        res = [(x[0], _coerce_attrs(x[1]))
               for x in res if _is_valid_entry(x)]
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
