# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.LDAP.
#
# Copyright 2025 by it's authors.
# Some rights reserved, see README and LICENSE.

"""Cache insight and purge endpoints for the LDAP control panel.

Two JSON endpoints used from the Cache tab in the control panel:

- ``@@senaite_ldap_cache_stats`` — connectivity + per-server
  ``get_stats()`` from the configured memcached. The Cache tab calls
  it on activation and shows hits / misses / items / bytes / uptime
  so the admin can tell at a glance whether caching is actually
  working and how warm it is.
- ``@@senaite_ldap_cache_flush`` — POST. Calls ``flush_all`` on the
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

# Stat keys we surface on the UI — memcached returns many more
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
        """Parse the configured memcached property into a server list.

        ``props.memcached`` holds a whitespace- or comma-separated
        list of ``host:port`` entries. Empty / unset means no
        memcached configured.
        """
        raw = getattr(self.props, "memcached", "") or ""
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "replace")
        servers = []
        for token in raw.replace(",", " ").split():
            token = token.strip()
            if token:
                servers.append(token)
        return servers

    def _client(self):
        """Build a memcached client against the configured servers.

        Returns ``(cache, servers)``. ``cache`` is None when no
        memcached is configured — caller renders a "not configured"
        response in that case.
        """
        servers = self._server_list()
        if not servers:
            return None, []
        cache = MemcachedProviderFactory(servers=servers)()
        return cache, servers


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
    independently — both can disagree (e.g. configured but disabled)
    and the UI uses both signals.
    """

    def __call__(self):
        self._require_plugin()
        self.request.response.setHeader(
            "Content-Type", "application/json")

        cache, servers = self._client()
        cache_enabled = bool(getattr(self.props, "cache", False))
        if cache is None:
            return json.dumps({
                "ok": True,
                "configured": False,
                "cache_enabled": cache_enabled,
                "servers": [],
            })

        raw_stats = _safe_get_stats(cache)
        server_results = list(_pair_stats_with_servers(raw_stats, servers))

        return json.dumps({
            "ok": True,
            "configured": True,
            "cache_enabled": cache_enabled,
            "servers": server_results,
        })


class LDAPCacheFlushView(_CacheBase):
    """JSON: POST to flush every key from the configured memcached.

    Returns ``{ok, message, servers}``. GET is rejected so the action
    can't be triggered by a stray link or browser prefetch.
    """

    def __call__(self):
        self._require_plugin()
        self.request.response.setHeader(
            "Content-Type", "application/json")

        if self.request.get("REQUEST_METHOD", "GET").upper() != "POST":
            self.request.response.setStatus(405)
            return json.dumps({
                "ok": False,
                "message": "POST required.",
            })

        cache, servers = self._client()
        if cache is None:
            return json.dumps({
                "ok": False,
                "message": "No memcached server configured.",
                "servers": [],
            })

        try:
            cache.reset()
        except Exception as exc:
            logger.warning("Memcached flush_all failed: %s", exc)
            return json.dumps({
                "ok": False,
                "message": "Flush failed: {}".format(exc),
                "servers": servers,
            })

        logger.info(
            "Memcached flush_all issued via control panel (servers=%r)",
            servers)
        return json.dumps({
            "ok": True,
            "message": "Cache flushed.",
            "servers": servers,
        })


def _safe_get_stats(cache):
    """Return the underlying client's ``get_stats()`` result, or [].

    Different memcache backends (python-memcached, pylibmc, libmc)
    expose ``get_stats`` with subtle signature differences and can
    raise on unreachable servers. Treat any failure as "no stats" so
    the UI shows the server as unreachable rather than 500-ing.
    """
    try:
        return list(cache._client.get_stats() or [])
    except Exception as exc:
        logger.info("Memcached get_stats failed: %s", exc)
        return []


def _pair_stats_with_servers(raw_stats, servers):
    """Yield ``{name, ok, stats}`` per configured server.

    ``raw_stats`` from python-memcached is a list of
    ``("server (host:port)", {key: value})`` tuples — one per
    *reachable* server. Match them up by host:port substring so a
    dead server still shows up in the response (with ``ok=False``).
    """
    matched = {}
    for raw_name, raw_dict in raw_stats:
        # Names come back like ``inet:127.0.0.1:11211 (1)`` —
        # extract a host:port substring for matching against the
        # configured list, fall back to the raw name.
        matched[_stat_name_key(raw_name)] = (raw_name, raw_dict)

    for server in servers:
        entry = matched.get(server)
        if entry is None:
            yield {
                "name": server,
                "ok": False,
                "stats": {},
            }
            continue
        raw_name, raw_dict = entry
        yield {
            "name": server,
            "ok": True,
            "stats": _filter_stats(raw_dict),
            "raw_name": _safe_text(raw_name),
        }


def _stat_name_key(raw_name):
    """Best-effort extract ``host:port`` from a memcache stat label."""
    name = _safe_text(raw_name)
    for token in name.replace("(", " ").replace(")", " ").split():
        if ":" in token and not token.startswith("inet"):
            return token
        if token.startswith("inet:"):
            return token.split(":", 1)[1]
    return name


def _filter_stats(raw_dict):
    """Pick the relevant keys, coerce ints, leave the rest as text."""
    if not raw_dict:
        return {}
    out = {}
    for key in RELEVANT_STAT_KEYS:
        if key not in raw_dict:
            continue
        value = raw_dict[key]
        if isinstance(value, bytes):
            value = value.decode("utf-8", "replace")
        try:
            out[key] = int(value)
        except (TypeError, ValueError):
            out[key] = value
    # Derived: hit rate as a float in [0, 1] so the UI doesn't have
    # to do the division itself.
    hits = out.get("get_hits")
    misses = out.get("get_misses")
    if hits is not None and misses is not None:
        total = hits + misses
        out["hit_rate"] = (float(hits) / total) if total else 0.0
    return out


def _safe_text(value):
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value.decode("utf-8", "replace")
    return value if value is not None else u""
