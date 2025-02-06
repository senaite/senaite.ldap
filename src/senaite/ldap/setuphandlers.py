# -*- coding: utf-8 -*-

from senaite.ldap import logger


def install(context):
    """Install handler
    """
    if context.readDataFile("senaite.ldap.txt") is None:
        return
    logger.info("Install handler [BEGIN]")
    portal = context.getSite()  # noqa
    logger.info("Install handler [DONE]")
