# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.LDAP.
#
# Copyright 2025 by it's authors.
# Some rights reserved, see README and LICENSE.

"""Vendored PAS plugin and supporting modules.

Submodules:

- `interfaces` -- marker interface, `IPluginCacheHandler`, settings
  utility marker, `VALUE_NOT_CACHED` sentinel.
- `defaults` -- built-in defaults for the plugin's settings BTree.
- `properties` -- `ILDAPProps` / `ILDAPUsersConfig` /
  `ILDAPGroupsConfig` adapters and the `propproxy` descriptor.
- `cache` -- `cacheProviderFactory`, `SenaiteLdapMemcached`,
  `get_plugin_cache` and the per-request cache handlers.
- `sheet` -- `LDAPUserPropertySheet`.
- `plugin` -- the `LDAPPlugin` class plus the programmatic
  `manage_addLDAPPlugin` add hook.
"""
