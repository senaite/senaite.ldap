# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.LDAP.
#
# Copyright 2025 by it's authors.
# Some rights reserved, see README and LICENSE.

"""Upgrade step 2.1.0 -> 2.1.1 for senaite.ldap."""

from senaite.core.upgrade import upgradestep
from senaite.ldap import logger
from senaite.ldap import PRODUCT_NAME
from senaite.ldap.setuphandlers import register_controlpanel


version = "2.1.1"


@upgradestep(PRODUCT_NAME, version)
def upgrade(tool):
    """Re-run register_controlpanel for installs that ran the 2.1.0
    step while it was a no-op.

    The 2000 -> 2100 handler shipped in 2.1.0 short-circuited on
    ``UpgradeUtils.isOlderVersion``, whose PEP-440 comparison sees
    "2.1.0" as less than "2000" (release tuples (2, 1, 0) vs
    (2000,)). ``portal_setup`` still marked the profile at 2100,
    so those installs can't re-run the previous step. This one
    lifts them off the stale registration.

    Also purges the legacy ``LDAP_Configuration`` action id inherited
    from ``pas.plugins.ldap.plonecontrolpanel`` -- the new
    registration uses ``senaite.ldap`` as both action id and appId.

    Idempotent.

    :param tool: The portal_setup tool.
    """
    portal = tool.aq_inner.aq_parent
    logger.info(
        "Upgrading {0} to version {1}".format(PRODUCT_NAME, version))
    register_controlpanel(portal)
    logger.info(
        "{0} upgraded to version {1}".format(PRODUCT_NAME, version))
    return True
