# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.LDAP.
#
# Copyright 2025 by it's authors.
# Some rights reserved, see README and LICENSE.

"""Patches for `node.ext.ldap.session.LDAPSession`.

Two upstream defects are corrected:

1. Paged-results responses are unpacked defensively. When
   ``page_size`` is set, upstream does ``res, cookie = res`` and
   blows up if the LDAP server omits the paged-results control
   cookie (``ValueError: need more than 0 values to unpack``).
   We tolerate either shape and synthesize an empty cookie.

2. The "skip ActiveDirectory phantom entries" filter
   (``x[0] is not None``) is replaced with `_is_valid_entry`,
   which also tolerates empty / non-sequence entries and 3-tuples
   carrying per-entry controls.

Both bugs surface as cryptic crashes deep inside the PAS
authentication chain. The patches are conservative: on the happy
path the behaviour is identical to upstream.
"""

from node.ext.ldap import session as _ldap_session

from senaite.ldap import logger


_ORIGINAL_LDAP_SESSION_SEARCH = _ldap_session.LDAPSession.search


def _coerce_attrs(value):
    """Normalise the second element of a search result entry to a dict.

    python-ldap usually returns ``(dn, {attr: [vals]})``, but against
    some servers (LLDAP via Traefik observed) the attrs payload is a
    flat list/tuple of ``(attr, [vals])`` pairs. Upstream consumers
    like ``_node.search`` call ``six.iteritems(attrs)`` on it and
    blow up with "'tuple' object has no attribute 'iteritems'".

    Defensively coerce to dict; fall back to empty dict on failure.

    :param value: Raw attrs payload from the LDAP response.
    :returns: Dict of attributes.
    :rtype: dict
    """
    if isinstance(value, dict):
        return value
    try:
        return dict(value)
    except Exception:  # noqa: BLE001 -- heterogeneous backend errors
        return {}


def _looks_like_paged_response(raw):
    """Return True if `raw` matches the ``(results, cookie)`` shape.

    `base.LDAPCommunicator.search` produces this shape when a
    `SimplePagedResultsControl` is attached to the LDAP response.

    A real result list, by contrast, is a list of ``(dn, attrs)``
    tuples whose first element is the raw DN bytes/str. We use that
    distinction to avoid false positives: a flat result list whose
    first element happens to be a 2-tuple shouldn't be unwrapped.

    :param raw: Raw return value from `LDAPCommunicator.search`.
    :returns: True when `raw` is a ``(results, cookie)`` 2-tuple.
    :rtype: bool
    """
    if not isinstance(raw, tuple) or len(raw) != 2:
        return False
    results, cookie = raw
    if not isinstance(results, list):
        return False
    # Cookie is a bytes/str token (often empty). A real first-entry
    # would be a (dn_bytes, attrs) tuple -- definitely not bytes/str.
    return isinstance(cookie, (bytes, str))


def _is_valid_entry(entry):
    """Return True if `entry` looks like a usable search result.

    Upstream `node.ext.ldap` 1.2 (``session.py`` line 57) blindly
    does ``x[0] is not None``, which raises ``IndexError`` on empty
    or non-sequence entries. Be defensive.

    We accept entries with two **or more** elements: python-ldap
    sometimes returns ``(dn, attrs, controls)`` 3-tuples when the
    underlying response carries per-entry controls. The original
    upstream filter only checked element 0 and would pass these
    through to ``_node.search`` line 530 (``for dn, attrs in
    matches:``), which then crashes with "too many values to
    unpack". The right move is to keep these entries and coerce
    them to ``(dn, attrs)`` in `safe_ldap_session_search`, not to
    drop them.

    :param entry: One element of the search result list.
    :returns: True when the entry has a non-None DN and an attrs
        payload alongside it.
    :rtype: bool
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
    """Drop-in replacement for `LDAPSession.search`.

    See module docstring for the rationale. Signature matches
    upstream verbatim so consumers don't have to care which
    implementation is bound.
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
    # did NOT ask for paging -- LLDAP attaches a
    # SimplePagedResultsControl to every response, and
    # ``base.LDAPCommunicator`` reflexively unwraps it into a tuple.
    # Upstream's session ignores this case and treats the tuple as
    # the result list, which then iterates over
    # ``(results_list, cookie_bytes)`` and yields exactly one
    # misshapen "entry" (the *first* hit) before the cookie is
    # dropped as invalid -- the visible symptom is searches that
    # always return one result, no matter how many entries the
    # server actually sent. Detect the (results, cookie) tuple shape
    # on every call, not just when ``page_size`` is truthy.
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
    except Exception as exc:  # noqa: BLE001 -- last-resort guard
        logger.warning(
            "LDAP result filtering failed (%s); returning empty.",
            exc)
        res = []

    if page_size:
        return res, cookie
    return res


def apply():
    """Replace `LDAPSession.search` with the safe variant.

    Idempotent: returns early when already patched.
    """
    if _ldap_session.LDAPSession.search is safe_ldap_session_search:
        return
    _ldap_session.LDAPSession.search = safe_ldap_session_search
    logger.info("Patched node.ext.ldap.session.LDAPSession.search")
