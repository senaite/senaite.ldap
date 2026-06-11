# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.LDAP.
#
# Copyright 2025 by it's authors.
# Some rights reserved, see README and LICENSE.

"""BBB shim for legacy `pas.plugins.ldap` and `yafowil.plone` paths.

Existing 2.x installs (and 1.x sites upgrading through 2.x) hold
ZODB-persistent references to symbols that were removed when we
dropped the upstream eggs:

- `pas.plugins.ldap.interfaces.ICacheSettingsRecordProvider`
  (utility registration in the local site manager)
- `pas.plugins.ldap.plonecontrolpanel.cache.CacheSettingsRecordProvider`
  (persistent utility instance backing the registration)
- `pas.plugins.ldap.plugin.LDAPPlugin`
  (the persisted `acl_users.pasldap` instance)
- `yafowil.plone.interfaces.IYafowilLayer`
  (browser-layer registration left over from 1.x)

When ZODB unpickles these references, dotted-path resolution
fails and Zope substitutes a broken-object placeholder. Symptoms:

- `AttributeError: type object 'ICacheSettingsRecordProvider' has
  no attribute '__iro__'` from `zope.interface.adapter.LookupBase.
  add_extendor` -- crashes any request that touches the local
  site manager.
- Red prohibition icon on `acl_users/pasldap` in the ZMI; the
  1100 -> 2000 migration step can't find a plugin to migrate.

Install minimal aliases in `sys.modules` so the legacy dotted
paths resolve to the corresponding vendored symbols (or, for the
inert YAFOWIL layer, to an empty `Interface` subclass). Same
object identity end to end -- ZODB unpickles the persisted
instances straight into our classes, which is effectively the
migration itself since every field that mattered (`settings`,
`plugin_caching`) is just an instance attribute and is preserved
by the unpickle.

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
    "yafowil",
    "yafowil.plone",
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
    _alias_plugin_module()
    _alias_plonecontrolpanel_cache_module()
    _alias_yafowil_plone_interfaces_module()


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


def _alias_plugin_module():
    """Alias the plugin class so persisted `pasldap` instances unpickle
    cleanly.

    Without this, the `acl_users.pasldap` instance comes back as a
    `OFS.Uninstalled.BrokenObject` (Zope's red prohibition icon in
    the ZMI) and the 1100 -> 2000 migration step can't find a
    `pas.plugins.ldap.plugin.LDAPPlugin` to migrate. Aliasing the
    class makes ZODB unpickle the persisted instance straight into
    our class -- which is effectively the migration itself, since
    every field that mattered (`settings`, `plugin_caching`) is
    just an instance attribute and is preserved by the unpickle.
    """
    from senaite.ldap.pas import plugin as real

    mod = types.ModuleType("pas.plugins.ldap.plugin")
    mod.LDAPPlugin = real.LDAPPlugin
    mod.manage_addLDAPPlugin = real.manage_addLDAPPlugin
    sys.modules["pas.plugins.ldap.plugin"] = mod
    sys.modules["pas.plugins.ldap"].plugin = mod


def _alias_yafowil_plone_interfaces_module():
    """Alias the YAFOWIL Plone browser-layer interface.

    1.x sites have a `yafowil.plone.interfaces.IYafowilLayer`
    browser-layer registration in the persistent registry. We don't
    use YAFOWIL anywhere, but the registration still gets resolved
    on every page render. Expose a dummy `Interface` subclass so
    resolution succeeds; the layer is otherwise inert (no view is
    registered against it).
    """
    from zope.interface import Interface

    class IYafowilLayer(Interface):
        """Inert BBB stand-in for `yafowil.plone.interfaces`."""

    mod = types.ModuleType("yafowil.plone.interfaces")
    mod.IYafowilLayer = IYafowilLayer
    sys.modules["yafowil.plone.interfaces"] = mod
    sys.modules["yafowil.plone"].interfaces = mod
