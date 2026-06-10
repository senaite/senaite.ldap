# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.LDAP.
#
# Copyright 2025 by it's authors.
# Some rights reserved, see README and LICENSE.

"""BBB shim for legacy `pas.plugins.ldap` dotted paths.

Existing 2.x installs (and 1.x sites upgrading through 2.x) have
ZODB-persistent component registry entries referencing the upstream
`pas.plugins.ldap` interfaces and classes:

- `pas.plugins.ldap.interfaces.ICacheSettingsRecordProvider`
- `pas.plugins.ldap.plonecontrolpanel.cache.CacheSettingsRecordProvider`

When the persistent registry is unpickled, zope.interface resolves
those dotted paths. With `pas.plugins.ldap` removed from
`install_requires`, the symbols disappear and unpickling falls back
to a `Broken*` placeholder. The placeholder lacks `__iro__`, so
`zope.interface.adapter.LookupBase.add_extendor` raises
``AttributeError: type object 'ICacheSettingsRecordProvider' has
no attribute '__iro__'`` -- crashes any request that touches the
local site manager.

Install minimal aliases in `sys.modules` so the legacy dotted paths
resolve to the corresponding vendored symbols. Same object identity
end to end -- the persistent registry sees a real interface again,
the broken-object fallback never fires, and queryUtility lookups
work.

`apply()` is called from `senaite.ldap` at package import time so
the shim is in place before any persistent registry unpickling.
"""

import sys
import types


_LEGACY_PACKAGES = (
    "pas",
    "pas.plugins",
    "pas.plugins.ldap",
    "pas.plugins.ldap.plonecontrolpanel",
)


def apply():
    """Install the legacy dotted-path aliases. Idempotent.

    No-op when ``pas.plugins.ldap`` is already importable from disk
    (e.g. an admin reinstated the egg manually): we don't want to
    shadow a real upstream module if it's present.
    """
    if _upstream_already_importable():
        return
    _ensure_packages()
    _alias_interfaces_module()
    _alias_plonecontrolpanel_cache_module()


def _upstream_already_importable():
    try:
        __import__("pas.plugins.ldap.interfaces")
    except ImportError:
        return False
    return True


def _ensure_packages():
    """Stub the namespace packages along the legacy path."""
    for name in _LEGACY_PACKAGES:
        if name in sys.modules:
            continue
        module = types.ModuleType(name)
        module.__path__ = []  # mark as package
        sys.modules[name] = module


def _alias_interfaces_module():
    from senaite.ldap.pas import interfaces as real

    mod = types.ModuleType("pas.plugins.ldap.interfaces")
    mod.ICacheSettingsRecordProvider = real.ICacheSettingsRecordProvider
    mod.ILDAPPlugin = real.ILDAPPlugin
    mod.IPluginCacheHandler = real.IPluginCacheHandler
    mod.VALUE_NOT_CACHED = real.VALUE_NOT_CACHED
    sys.modules["pas.plugins.ldap.interfaces"] = mod
    # Make the parent package see it as an attribute too -- some
    # resolvers walk the parent's __dict__ rather than sys.modules.
    sys.modules["pas.plugins.ldap"].interfaces = mod


def _alias_plonecontrolpanel_cache_module():
    from senaite.ldap.pas import cache as real

    mod = types.ModuleType("pas.plugins.ldap.plonecontrolpanel.cache")
    mod.CacheSettingsRecordProvider = real.CacheSettingsRecordProvider
    sys.modules["pas.plugins.ldap.plonecontrolpanel.cache"] = mod
    sys.modules["pas.plugins.ldap.plonecontrolpanel"].cache = mod
