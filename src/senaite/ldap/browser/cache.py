# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.LDAP.
#
# Copyright 2025 by it's authors.
# Some rights reserved, see README and LICENSE.

"""Cache insight and purge endpoints for the LDAP control panel.

Two JSON endpoints used from the Cache tab in the control panel:

- ``@@senaite_ldap_cache_stats`` -- connectivity + per-server
  ``get_stats()`` from the configured memcached. The Cache tab calls
  it on activation and shows hits / misses / items / bytes / uptime
  so the admin can tell at a glance whether caching is actually
  working and how warm it is.
- ``@@senaite_ldap_cache_flush`` -- POST. Calls ``flush_all`` on the
  configured memcached. Equivalent to the ``flush_all`` admin command
  but reachable from the control panel.

Both endpoints require ``cmf.ManagePortal``.
"""

import json

from node.ext.ldap.cache import MemcachedProviderFactory
from node.ext.ldap.interfaces import ILDAPProps
from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from senaite.ldap import logger
from zExceptions import NotFound


PLUGIN_ID = "pasldap"

# Stat keys we surface on the UI -- memcached returns many more
# (``rusage_*``, ``conn_*``, etc.) but these are the ones an admin
# typically wants to see for a "is the cache useful?" answer.
RELEVANT_STAT_KEYS = (
    "version",
    "uptime",
    "curr_items",
    "total_items",
    "bytes",
    "limit_maxbytes",
    "cmd_get",
    "cmd_set",
    "get_hits",
    "get_misses",
    "evictions",
    "curr_connections",
)


class _CacheBase(BrowserView):
    """Shared accessors for cache views."""

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

    def _server_list(self):
        """Parse `props.memcached` into a list of server addresses.

        ``props.memcached`` holds a whitespace- or comma-separated
        list of ``host:port`` entries. Empty / unset means no
        memcached configured.

        :returns: List of ``host:port`` strings, possibly empty.
        :rtype: list
        """
        raw = getattr(self.props, "memcached", "") or ""
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "replace")
        return [tok for tok in raw.replace(",", " ").split() if tok]

    def _client(self):
        """Build a memcached client against the configured servers.

        :returns: ``(cache, servers)``. `cache` is None when no
            memcached is configured -- caller renders a "not
            configured" response in that case.
        :rtype: tuple
        """
        servers = self._server_list()
        if not servers:
            return None, []
        cache = MemcachedProviderFactory(servers=servers)()
        return cache, servers

    def _json(self, payload, status=None):
        """Serialise `payload` as a JSON response.

        :param payload: Dict to serialise.
        :param status: Optional HTTP status to set on the response.
        :returns: JSON-encoded string.
        :rtype: str
        """
        self.request.response.setHeader(
            "Content-Type", "application/json")
        if status is not None:
            self.request.response.setStatus(status)
        return json.dumps(payload)


class LDAPCacheStatsView(_CacheBase):
    """JSON: per-server ``get_stats()`` from the configured memcached.

    Output shape::

        {
          "ok": true,
          "configured": true,
          "cache_enabled": true,
          "servers": [
            {
              "name": "127.0.0.1:11211",
              "ok": true,
              "stats": {"uptime": 12345, "curr_items": 42, ...}
            }
          ]
        }

    ``configured`` is false if no memcached server is set in the
    props. ``cache_enabled`` reflects the ``cache.cache`` toggle
    independently -- both can disagree (e.g. configured but disabled)
    and the UI uses both signals.
    """

    def __call__(self):
        self._require_plugin()
        cache, servers = self._client()
        cache_enabled = bool(getattr(self.props, "cache", False))

        if cache is None:
            return self._json({
                "ok": True,
                "configured": False,
                "cache_enabled": cache_enabled,
                "servers": [],
            })

        raw_stats = _safe_get_stats(cache)
        return self._json({
            "ok": True,
            "configured": True,
            "cache_enabled": cache_enabled,
            "servers": list(_pair_stats_with_servers(raw_stats, servers)),
        })


class LDAPCacheFlushView(_CacheBase):
    """JSON: POST to flush every key from the configured memcached.

    Returns ``{ok, message, servers}``. GET is rejected so the action
    can't be triggered by a stray link or browser prefetch.
    """

    def __call__(self):
        self._require_plugin()

        if not _is_post(self.request):
            return self._json(
                {"ok": False, "message": "POST required."},
                status=405)

        cache, servers = self._client()
        if cache is None:
            return self._json({
                "ok": False,
                "message": "No memcached server configured.",
                "servers": [],
            })

        error = _safe_reset(cache)
        if error is not None:
            return self._json({
                "ok": False,
                "message": "Flush failed: {}".format(error),
                "servers": servers,
            })

        logger.info(
            "Memcached flush_all issued via control panel (servers=%r)",
            servers)
        return self._json({
            "ok": True,
            "message": "Cache flushed.",
            "servers": servers,
        })


def _is_post(request):
    """Return True if `request` is a POST."""
    method = request.get("REQUEST_METHOD", "GET")
    return method.upper() == "POST"


def _safe_get_stats(cache):
    """Return the underlying client's ``get_stats()`` result, or [].

    Different memcache backends (python-memcached, pylibmc, libmc)
    expose ``get_stats`` with subtle signature differences and raise
    unrelated exception hierarchies (socket errors, library-specific
    errors). A blanket catch keeps the UI responsive: any failure
    shows the server as unreachable rather than a 500.

    :param cache: A ``bda.cache.memcached.Memcached`` instance.
    :returns: List of ``(server_name, stats_dict)`` tuples.
    :rtype: list
    """
    try:
        return list(cache._client.get_stats() or [])
    except Exception as exc:  # noqa: BLE001 -- see docstring
        logger.info("Memcached get_stats failed: %s", exc)
        return []


def _safe_reset(cache):
    """Call ``cache.reset()`` and return None on success, else the error.

    Same rationale as `_safe_get_stats` for the blanket catch: the
    underlying memcache libraries raise heterogeneous exceptions on
    unreachable servers; the admin sees a human-readable failure
    message instead of a 500.

    :param cache: A ``bda.cache.memcached.Memcached`` instance.
    :returns: None on success, or the raised exception.
    """
    try:
        cache.reset()
    except Exception as exc:  # noqa: BLE001 -- see docstring
        logger.warning("Memcached flush_all failed: %s", exc)
        return exc
    return None


def _pair_stats_with_servers(raw_stats, servers):
    """Yield one ``{name, ok, stats}`` dict per configured server.

    ``raw_stats`` from python-memcached is a list of
    ``("server (host:port)", {key: value})`` tuples -- one per
    *reachable* server. Match them up by host:port substring so a
    dead server still shows up in the response (with ``ok=False``).

    :param raw_stats: List from ``Memcached.get_stats()``.
    :param servers: Configured ``host:port`` strings.
    """
    matched = {}
    for raw_name, raw_dict in raw_stats:
        matched[_stat_name_key(raw_name)] = (raw_name, raw_dict)

    for server in servers:
        entry = matched.get(server)
        if entry is None:
            yield {"name": server, "ok": False, "stats": {}}
            continue
        raw_name, raw_dict = entry
        yield {
            "name": server,
            "ok": True,
            "stats": _filter_stats(raw_dict),
            "raw_name": _safe_text(raw_name),
        }


def _stat_name_key(raw_name):
    """Extract ``host:port`` from a memcache stat label.

    Stat labels come back in several shapes:

    - python-memcached: ``"127.0.0.1:11211 (1)"``
    - pylibmc / libmc: ``"inet:127.0.0.1:11211"``

    Strip a leading ``inet:`` if present, then return the first
    whitespace-separated token that contains a colon. Falls back to
    the original name if nothing matches.

    :param raw_name: Stat label from the memcache backend.
    :returns: A ``host:port`` string suitable for matching against
        the configured server list.
    :rtype: str
    """
    name = _safe_text(raw_name)
    if name.startswith("inet:"):
        name = name[len("inet:"):]
    for token in name.replace("(", " ").replace(")", " ").split():
        if ":" in token:
            return token
    return name


def _filter_stats(raw_dict):
    """Pick the relevant stat keys, coerce numerics, derive hit rate.

    :param raw_dict: Stats dict as returned by memcache.
    :returns: A new dict containing only `RELEVANT_STAT_KEYS` plus a
        derived ``hit_rate`` (float in ``[0, 1]``) when both
        ``get_hits`` and ``get_misses`` are present.
    :rtype: dict
    """
    if not raw_dict:
        return {}
    out = {}
    for key in RELEVANT_STAT_KEYS:
        if key in raw_dict:
            out[key] = _coerce_stat_value(raw_dict[key])
    hit_rate = _derive_hit_rate(out)
    if hit_rate is not None:
        out["hit_rate"] = hit_rate
    return out


def _coerce_stat_value(value):
    """Decode bytes and coerce numeric strings to int; pass others through.

    :param value: Raw stat value from memcache.
    :returns: Decoded / coerced value.
    """
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def _derive_hit_rate(stats):
    """Compute hit rate as a float in ``[0, 1]``.

    The UI doesn't have to do the division itself this way.

    :param stats: Stats dict with possibly ``get_hits`` /
        ``get_misses`` integers.
    :returns: Float in ``[0, 1]``, or None when either input is
        missing.
    """
    hits = stats.get("get_hits")
    misses = stats.get("get_misses")
    if hits is None or misses is None:
        return None
    total = hits + misses
    if total == 0:
        return 0.0
    return float(hits) / total


def _safe_text(value):
    """Decode bytes to text; pass through text and None-as-empty.

    :param value: Possibly-bytes value from a backend.
    :returns: Text (unicode in Python 2, str in Python 3).
    """
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value if value is not None else u""
