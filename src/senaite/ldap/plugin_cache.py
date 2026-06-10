# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.LDAP.
#
# Copyright 2025 by it's authors.
# Some rights reserved, see README and LICENSE.

"""Caching helpers for the vendored LDAP PAS plugin.

Vendored from `pas.plugins.ldap.cache`. Two responsibilities:

1. `cacheProviderFactory` is registered as the
   `node.ext.ldap.interfaces.ICacheProviderFactory` global utility
   for our plugin, exposing memcached to the `node.ext.ldap` layer.

2. `get_plugin_cache(plugin)` returns the per-request /
   per-volatile cache wrapper the plugin uses to memoize its UGM
   tree lookups inside one request.
"""

import threading
import time

from bda.cache import Memcached
from bda.cache import NullCache
from node.ext.ldap.interfaces import ICacheProviderFactory
from senaite.ldap.plugin_interfaces import ICacheSettingsRecordProvider
from senaite.ldap.plugin_interfaces import ILDAPPlugin
from senaite.ldap.plugin_interfaces import IPluginCacheHandler
from senaite.ldap.plugin_interfaces import VALUE_NOT_CACHED
from zope.component import adapter
from zope.component import queryUtility
from zope.globalrequest import getRequest
from zope.interface import implementer


VOLATILE_CACHE_MAXAGE = 10  # seconds


class SenaiteLdapMemcached(Memcached):
    """`bda.cache.Memcached` subclass that remembers its server list.

    `cacheProviderFactory` compares the current server set against
    this instance's recorded set to decide whether to disconnect
    and re-create the client.
    """

    _servers = None

    def __init__(self, servers):
        self._servers = servers
        super(SenaiteLdapMemcached, self).__init__(servers)

    @property
    def servers(self):
        return self._servers

    def disconnect_all(self):
        self._client.disconnect_all()

    def __repr__(self):
        return "<{0} {1}>".format(
            self.__class__.__name__, self.servers)


@implementer(ICacheProviderFactory)
class cacheProviderFactory(object):
    """`ICacheProviderFactory` returning a thread-local memcached."""

    _thread_local = threading.local()

    @property
    def _key(self):
        return "_v_{0}_SenaiteLdapMemcached".format(
            self.__class__.__name__)

    @property
    def servers(self):
        record_provider = queryUtility(ICacheSettingsRecordProvider)
        if not record_provider:
            return ""
        value = record_provider().value or ""
        return value.split()

    @property
    def cache(self):
        servers = self.servers
        if not servers:
            return NullCache()

        key = self._key
        mcd = getattr(self._thread_local, key, None)

        if mcd and frozenset(mcd.servers) == frozenset(servers):
            return mcd
        elif mcd:
            mcd.disconnect_all()
            del mcd

        mcd = SenaiteLdapMemcached(servers)
        setattr(self._thread_local, key, mcd)
        return mcd

    def __call__(self):
        return self.cache


def get_plugin_cache(context):
    """Pick the right `IPluginCacheHandler` for the plugin instance.

    :param context: An `LDAPPlugin` instance.
    :returns: A `NullPluginCache` when `plugin_caching` is False, the
        registered `IPluginCacheHandler` adapter when present, else
        the `RequestPluginCache` fallback.
    """
    if not context.plugin_caching:
        return NullPluginCache(context)
    plugin_cache = IPluginCacheHandler(context, None)
    if plugin_cache is not None:
        return plugin_cache
    return RequestPluginCache(context)


@implementer(IPluginCacheHandler)
class NullPluginCache(object):
    """Inert cache: `get` always misses, `set` discards."""

    def __init__(self, context):
        self.context = context

    def get(self):
        return VALUE_NOT_CACHED

    def set(self, value):
        pass


@implementer(IPluginCacheHandler)
class RequestPluginCache(object):
    """Per-request cache stashed on the active `IRequest`."""

    def __init__(self, context):
        self.context = context

    def _key(self):
        return "_v_ldap_ugm_{0}_".format(self.context.getId())

    def get(self):
        request = getRequest()
        rcachekey = self._key()
        if request and rcachekey in list(request.keys()):
            return request[rcachekey]
        return VALUE_NOT_CACHED

    def set(self, value):
        request = getRequest()
        if request is not None:
            request[self._key()] = value

    def invalidate(self):
        request = getRequest()
        rcachekey = self._key()
        if request and rcachekey in list(request.keys()):
            del request[rcachekey]


@adapter(ILDAPPlugin)
class VolatilePluginCache(RequestPluginCache):
    """Thread-volatile cache with a 10-second TTL.

    Stores `(timestamp, value)` on the plugin instance under a
    `_v_*` attribute (which ZODB never persists).
    """

    def get(self):
        try:
            cachetime, value = getattr(self.context, self._key())
        except AttributeError:
            return VALUE_NOT_CACHED
        if time.time() - cachetime > VOLATILE_CACHE_MAXAGE:
            return VALUE_NOT_CACHED
        return value

    def set(self, value):
        setattr(self.context, self._key(), (time.time(), value))

    def invalidate(self):
        try:
            delattr(self.context, self._key())
        except AttributeError:
            pass
