# -*- coding: utf-8 -*-

from senaite.ldap import logger

DEPENDENCIES = [
    "yafowil.plone",
    "pas.plugins.ldap",
    "pas.plugins.ldap.plonecontrolpanel",
]

REGISTRY_KEYS = [
    "pas.plugins.ldap",
    # "yafowil",
    # "plone.bundles/yafowil",
]


def install(context):
    """Install handler
    """
    if context.readDataFile("senaite.ldap.txt") is None:
        return
    logger.info("SENAITE LDAP install handler [BEGIN]")
    portal = context.getSite()  # noqa
    install_pas_plugin(portal)
    logger.info("SENAITE LDAP install handler [DONE]")


def uninstall(portal_setup):
    """Runs after the last import step of the *uninstall* profile

    This handler is registered as a *post_handler* in the generic setup profile

    :param portal_setup: SetupTool
    """
    logger.info("SENAITE LDAP uninstall handler [BEGIN]")

    # https://docs.plone.org/develop/addons/components/genericsetup.html#custom-installer-code-setuphandlers-py
    profile_id = "profile-senaite.ldap:uninstall"
    context = portal_setup._getImportContext(profile_id)
    portal = context.getSite()  # noqa
    uninstall_pas_plugin(portal)
    logger.info("SENAITE LDAP uninstall handler [DONE]")


def install_pas_plugin(portal):
    """Install pas.plugins.ldap plugin
    """


def uninstall_pas_plugin(portal):
    """Uninstall pas.plugins.ldap plugin
    """
    qi = portal.portal_quickinstaller
    # manually uninstall it from the quickinstaller tool
    for dep in DEPENDENCIES:
        try:
            qi.uninstallProducts([dep])
        except AttributeError:
            pass

    # Manually remove the PAS plugin from acl_users
    aclu = portal.acl_users
    plugin = "pasldap"
    if plugin in aclu.objectIds():
        aclu.manage_delObjects(["pasldap"])

    registry = portal.portal_registry
    for key, record in registry.records.items():
        for to_delete in REGISTRY_KEYS:
            if key.startswith(to_delete):
                del registry.records[key]
