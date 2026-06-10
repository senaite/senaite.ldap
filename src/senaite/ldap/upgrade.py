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


def upgrade_1100_to_2000(setup_tool):
    """Migrate a 1.x install to 2.x.

    The 2.x line replaces the YAFOWIL-based control panel with a
    native SENAITE form. The PAS plugin (``pasldap`` in ``acl_users``)
    and its persistent configuration are kept, but four upstream
    defaults that never made sense are corrected so a fresh install
    actually resolves users and groups.

    What this step does:

    1. Re-import the senaite.ldap ``controlpanel`` profile so the
       "LDAP / Active Directory" entry appears in Site Setup under
       the new ``@@senaite_ldapcontrolpanel`` URL. The 1.x configlet
       was registered by ``pas.plugins.ldap.plonecontrolpanel``,
       which we no longer install; without re-importing here the
       configlet would silently disappear on upgrade.

    2. Remove orphan ``yafowil`` / ``plone.bundles/yafowil`` registry
       records left by the upstream profile.

    3. Apply opinionated defaults for the four ``pas.plugins.ldap``
       fields that ship at upstream-noise values:

       - ``users.scope`` / ``groups.scope`` == ``BASE`` → ``SUBTREE``
         (``BASE`` only ever returns the base DN entry itself.)
       - empty ``users.objectClasses`` → ``[inetOrgPerson]``
       - empty ``groups.objectClasses`` → ``[groupOfNames]``

       Deliberately-set values (real scope choice, non-empty
       objectClasses) are left alone. Idempotent.
    """
    portal = setup_tool.aq_inner.aq_parent
    import_controlpanel(setup_tool)
    drop_yafowil_registry_records(portal)
    apply_sane_pasldap_defaults(portal)


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


def apply_sane_pasldap_defaults(portal):
    """Rewrite the four upstream-noise ``pas.plugins.ldap`` fields
    when they're still at the noise state.

    See ``_apply_defaults`` for the per-field rules.
    """
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
