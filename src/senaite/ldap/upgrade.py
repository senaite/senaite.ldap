# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.LDAP.
#
# Copyright 2025 by it's authors.
# Some rights reserved, see README and LICENSE.

"""Upgrade handlers for senaite.ldap."""

from senaite.ldap import logger
from senaite.ldap.setuphandlers import REGISTRY_KEYS


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
