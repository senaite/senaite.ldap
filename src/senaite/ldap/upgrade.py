# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.LDAP.
#
# Copyright 2025 by it's authors.
# Some rights reserved, see README and LICENSE.

"""Upgrade handlers for senaite.ldap."""

from node.ext.ldap.interfaces import ILDAPGroupsConfig
from node.ext.ldap.interfaces import ILDAPUsersConfig
from node.ext.ldap.scope import BASE
from node.ext.ldap.scope import SUBTREE
from Products.CMFCore.utils import getToolByName
from senaite.ldap import logger
from senaite.ldap.setuphandlers import REGISTRY_KEYS


PLUGIN_ID = "pasldap"

USERS_DEFAULT_OBJECTCLASSES = [u"inetOrgPerson"]
GROUPS_DEFAULT_OBJECTCLASSES = [u"groupOfNames"]


def upgrade_2010_to_2020(setup_tool):
    """Apply opinionated defaults for the four ``pas.plugins.ldap``
    fields that ship at upstream-noise values and that the SENAITE
    control panel doesn't override on first save.

    The upstream defaults for ``users.scope`` and ``groups.scope`` are
    ``BASE`` (0), which only ever returns the base DN entry itself —
    no users, no groups. ``objectClasses`` ships empty, which makes
    member-attribute discovery fail with
    ``Can not lookup member attribute for object-classes: []``.

    This step rewrites those fields *only when they're still at the
    upstream-noise state*:

    - ``scope == BASE`` → ``SUBTREE``
    - ``objectClasses`` empty → a sensible default
      (``inetOrgPerson`` for users, ``groupOfNames`` for groups)

    A deliberately-set BASE or a non-empty ``objectClasses`` is left
    alone. Idempotent — re-running the step is a no-op once the
    fields hold real values.
    """
    portal = setup_tool.aq_inner.aq_parent
    plugin = _get_plugin(portal)
    if plugin is None:
        logger.info("pasldap plugin not installed; skipping defaults")
        return

    _apply_defaults(
        ILDAPUsersConfig(plugin),
        label="users",
        default_objectclasses=USERS_DEFAULT_OBJECTCLASSES,
    )
    _apply_defaults(
        ILDAPGroupsConfig(plugin),
        label="groups",
        default_objectclasses=GROUPS_DEFAULT_OBJECTCLASSES,
    )


def _get_plugin(portal):
    acl_users = getToolByName(portal, "acl_users", None)
    if acl_users is None:
        return None
    return getattr(acl_users, PLUGIN_ID, None)


def _apply_defaults(config, label, default_objectclasses):
    """Rewrite ``scope`` / ``objectClasses`` in place when at noise.

    Logs every effective change so an admin can see what shifted on
    upgrade.
    """
    if getattr(config, "scope", BASE) == BASE:
        config.scope = SUBTREE
        logger.info(
            "%s.scope was BASE — set to SUBTREE", label)

    object_classes = list(getattr(config, "objectClasses", []) or [])
    if not object_classes:
        config.objectClasses = list(default_objectclasses)
        logger.info(
            "%s.objectClasses was empty — set to %r",
            label, default_objectclasses)


def upgrade_1100_to_2000(setup_tool):
    """Migrate a 1.x install to 2.x.

    The 2.x line replaces the YAFOWIL-based control panel with a
    native SENAITE form. The PAS plugin (`pasldap` in `acl_users`) and
    its persistent configuration are unchanged. Only the rendering
    layer changed.

    What this step does:

    - Re-import the senaite.ldap controlpanel profile so the
      "LDAP / Active Directory" entry appears in Site Setup. The 1.x
      configlet was registered by
      ``pas.plugins.ldap.plonecontrolpanel``, which we no longer
      install; without re-importing here the configlet would silently
      disappear on upgrade.
    - Remove orphan `yafowil` / `plone.bundles/yafowil` registry
      records left by the upstream profile.
    - Leave the `pasldap` PAS plugin and its persistent
      `ILDAPProps` / `ILDAPUsersConfig` / `ILDAPGroupsConfig`
      configuration untouched.
    """
    portal = setup_tool.aq_inner.aq_parent
    import_controlpanel(setup_tool)
    drop_yafowil_registry_records(portal)


def upgrade_2000_to_2010(setup_tool):
    """Rename the controlpanel views: ``plone_ldap*`` → ``senaite_ldap*``.

    The 2.0 profile registered the configlet at
    ``@@plone_ldapcontrolpanel``. The views were renamed to drop the
    ``plone_`` prefix; re-import the controlpanel profile so existing
    Site Setup configlets point at the new URL.
    """
    import_controlpanel(setup_tool)


def import_controlpanel(setup_tool):
    """Re-import the ``controlpanel`` GenericSetup step from the
    senaite.ldap default profile so the configlet entry is registered
    (and so the title / URL update if we ever change them).
    """
    setup_tool.runImportStepFromProfile(
        "profile-senaite.ldap:default", "controlpanel")
    logger.info("Re-imported senaite.ldap controlpanel profile")


def drop_yafowil_registry_records(portal):
    """Delete every registry record matching a key in REGISTRY_KEYS
    that is *not* prefixed with ``pas.plugins.ldap``.

    The 2.x setuphandlers REGISTRY_KEYS list contains both the
    ``pas.plugins.ldap`` prefix (which we keep — it's the PAS plugin
    configuration we still use) and the YAFOWIL prefixes (which we
    purge). The uninstall handler iterates the same list; this
    upgrade step only purges the YAFOWIL part.
    """
    registry = portal.portal_registry
    yafowil_prefixes = [
        key for key in REGISTRY_KEYS
        if not key.startswith("pas.plugins.ldap")
    ]
    removed = 0
    for record_key in list(registry.records.keys()):
        for prefix in yafowil_prefixes:
            if record_key.startswith(prefix):
                del registry.records[record_key]
                removed += 1
                break
    if removed:
        logger.info(
            "Removed %d orphan YAFOWIL registry records" % removed)
    else:
        logger.info("No orphan YAFOWIL registry records to remove")
