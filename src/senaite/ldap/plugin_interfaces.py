# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.LDAP.
#
# Copyright 2025 by it's authors.
# Some rights reserved, see README and LICENSE.

"""Interfaces for the vendored LDAP PAS plugin.

`ILDAPPlugin` here is *not* the same interface as
``pas.plugins.ldap.interfaces.ILDAPPlugin``: separate identities
keep the global adapter registry from collapsing the two plugin
implementations onto the same `(provides, requires)` lookup key.
Existing installs that still pickle as
``pas.plugins.ldap.plugin.LDAPPlugin`` continue to use upstream's
adapters; new installs on our class use the adapters in
``senaite.ldap.plugin_properties``.
"""

from zope.interface import Interface


class ILDAPPlugin(Interface):
    """Marker interface for the senaite.ldap PAS plugin."""


class ICacheSettingsRecordProvider(Interface):
    """Provides the registry record carrying the memcached server list.

    Kept as a separate utility so the property accessor in
    `LDAPProps.memcached` can stay decoupled from `plone.app.registry`.
    """


class IPluginCacheHandler(Interface):
    """Caches the node trees the PAS plugin walks.

    See `senaite.ldap.plugin_cache` for implementations.
    """

    def get():
        """Return the cached value, or `VALUE_NOT_CACHED`."""

    def set(value):
        """Cache `value`."""

    def invalidate():
        """Drop the cached value."""


VALUE_NOT_CACHED = dict()
