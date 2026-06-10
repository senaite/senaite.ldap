# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.LDAP.
#
# Copyright 2025 by it's authors.
# Some rights reserved, see README and LICENSE.

"""Upgrade step 1.x -> 2.0.0 for senaite.ldap."""

from node.ext.ldap.interfaces import ILDAPGroupsConfig
from node.ext.ldap.interfaces import ILDAPUsersConfig
from node.ext.ldap.scope import BASE
from node.ext.ldap.scope import SUBTREE
from Products.CMFCore.utils import getToolByName
from senaite.core.upgrade import upgradestep
from senaite.core.upgrade.utils import UpgradeUtils
from senaite.ldap import logger
from senaite.ldap import PRODUCT_NAME
from senaite.ldap.setuphandlers import REGISTRY_KEYS


version = "2.0.0"
profile = "profile-{0}:default".format(PRODUCT_NAME)

PLUGIN_ID = "pasldap"

USERS_DEFAULT_OBJECTCLASSES = [u"inetOrgPerson"]
GROUPS_DEFAULT_OBJECTCLASSES = [u"groupOfNames"]


@upgradestep(PRODUCT_NAME, version)
def upgrade(tool):
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

       - ``users.scope`` / ``groups.scope`` == ``BASE`` -> ``SUBTREE``
         (``BASE`` only ever returns the base DN entry itself.)
       - empty ``users.objectClasses`` -> ``[inetOrgPerson]``
       - empty ``groups.objectClasses`` -> ``[groupOfNames]``

       Deliberately-set values (real scope choice, non-empty
       objectClasses) are left alone. Idempotent.

    :param tool: The portal_setup tool.
    """
    portal = tool.aq_inner.aq_parent
    ut = UpgradeUtils(portal)
    ver_from = ut.getInstalledVersion(PRODUCT_NAME)

    if ut.isOlderVersion(PRODUCT_NAME, version):
        logger.info("Skipping upgrade of {0}: {1} > {2}".format(
            PRODUCT_NAME, ver_from, version))
        return True

    logger.info("Upgrading {0}: {1} -> {2}".format(
        PRODUCT_NAME, ver_from, version))

    import_controlpanel(tool)
    drop_yafowil_registry_records(portal)
    apply_sane_pasldap_defaults(portal)

    logger.info("{0} upgraded to version {1}".format(
        PRODUCT_NAME, version))
    return True


def import_controlpanel(setup_tool):
    """Re-import the ``controlpanel`` step from the default profile.

    Registers the configlet under the new
    ``@@senaite_ldapcontrolpanel`` URL.

    :param setup_tool: The portal_setup tool.
    """
    setup_tool.runImportStepFromProfile(profile, "controlpanel")
    logger.info("Re-imported senaite.ldap controlpanel profile")


def drop_yafowil_registry_records(portal):
    """Delete registry records left by the dropped YAFOWIL bundle.

    The 2.x `senaite.ldap.setuphandlers.REGISTRY_KEYS` list contains
    both the ``pas.plugins.ldap`` prefix (kept -- it's the PAS plugin
    configuration we still use) and the YAFOWIL prefixes (purged).
    The uninstall handler iterates the same list; this upgrade step
    only purges the YAFOWIL part.

    :param portal: Plone site root.
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
    """Rewrite upstream-noise ``pas.plugins.ldap`` fields to defaults.

    See `_apply_defaults` for the per-field rules.

    :param portal: Plone site root.
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
    """Return the `pasldap` PAS plugin, or None when not installed."""
    acl_users = getToolByName(portal, "acl_users", None)
    if acl_users is None:
        return None
    return getattr(acl_users, PLUGIN_ID, None)


def _apply_defaults(config, label, default_objectclasses):
    """Rewrite `scope` / `objectClasses` in place when at noise values.

    Logs every effective change so an admin can see what shifted on
    upgrade.

    :param config: `ILDAPUsersConfig` or `ILDAPGroupsConfig`.
    :param label: Short label for log messages (``"users"`` /
        ``"groups"``).
    :param default_objectclasses: Default object-class list to apply
        when the field is empty.
    """
    if getattr(config, "scope", BASE) == BASE:
        config.scope = SUBTREE
        logger.info("%s.scope was BASE -- set to SUBTREE", label)

    object_classes = list(getattr(config, "objectClasses", []) or [])
    if not object_classes:
        config.objectClasses = list(default_objectclasses)
        logger.info(
            "%s.objectClasses was empty -- set to %r",
            label, default_objectclasses)
