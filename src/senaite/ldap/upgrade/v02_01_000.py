# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.LDAP.
#
# Copyright 2025 by it's authors.
# Some rights reserved, see README and LICENSE.

"""Upgrade step 2.0.0 -> 2.1.0 for senaite.ldap."""

from senaite.core.upgrade import upgradestep
from senaite.core.upgrade.utils import UpgradeUtils
from senaite.ldap import logger
from senaite.ldap import PRODUCT_NAME
from senaite.ldap.setuphandlers import register_controlpanel


version = "2.1.0"


@upgradestep(PRODUCT_NAME, version)
def upgrade(tool):
    """Rewrite the LDAP control panel action.

    2.0.0 installs still carry the 1.x ``plone_ldapcontrolpanel``
    URL on the persistent ``portal_controlpanel`` action, because
    the 1100 -> 2000 step relied on
    ``runImportStepFromProfile("controlpanel")`` which silently
    no-ops when the site's profile version already matches ours.
    Rewrite the action directly.

    Idempotent.

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

    register_controlpanel(portal)

    logger.info("{0} upgraded to version {1}".format(
        PRODUCT_NAME, version))
    return True
