# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.LDAP.
#
# Copyright 2025 by it's authors.
# Some rights reserved, see README and LICENSE.

"""Upgrade step 2.0.0 -> 2.1.0 for senaite.ldap."""

from senaite.core.upgrade import upgradestep
from senaite.ldap import logger
from senaite.ldap import PRODUCT_NAME
from senaite.ldap.setuphandlers import register_controlpanel


version = "2.1.0"


@upgradestep(PRODUCT_NAME, version)
def upgrade(tool):
    """Rewrite the LDAP control panel action.

    2.0.0 installs still carry the 1.x `plone_ldapcontrolpanel`
    URL on the persistent `portal_controlpanel` action, because
    the 1100 -> 2000 step relied on
    `runImportStepFromProfile("controlpanel")` which silently
    no-ops when the site's profile version already matches ours.
    Rewrite the action directly.

    Idempotent. No inner `isOlderVersion` guard: comparing a
    dotted setup.py version ("2.1.0") against a 4-digit metadata
    version ("2000") via `pkg_resources.parse_version` gives
    "2.1.0 < 2000" (release tuple (2, 1, 0) < (2000,)), which
    would incorrectly short-circuit the handler. `portal_setup`
    already gates the step through the ZCML `source` /
    `destination` values, so the inner check is also redundant.

    :param tool: The portal_setup tool.
    """
    portal = tool.aq_inner.aq_parent

    logger.info(
        "Upgrading {0} to version {1}".format(PRODUCT_NAME, version))
    register_controlpanel(portal)
    logger.info(
        "{0} upgraded to version {1}".format(PRODUCT_NAME, version))
    return True
