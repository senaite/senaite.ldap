# -*- coding: utf-8 -*-

from Products.PluggableAuthService.interfaces.plugins \
    import IUserAdderPlugin
from senaite.ldap import logger

DEPENDENCIES = [
    "pas.plugins.ldap",
]

REGISTRY_KEYS = [
    "pas.plugins.ldap",
    "yafowil",
    "plone.bundles/yafowil",
]

PLUGIN_ID = "pasldap"


def install(context):
    """Install handler
    """
    if context.readDataFile("senaite.ldap.txt") is None:
        return
    logger.info("SENAITE LDAP install handler [BEGIN]")
    portal = context.getSite()  # noqa
    install_pas_plugin(portal)
    deactivate_user_adder(portal)
    logger.info("SENAITE LDAP install handler [DONE]")


def deactivate_user_adder(portal):
    """Deactivate `IUserAdderPlugin` on the `pasldap` plugin.

    `pas.plugins.ldap` registers an `IUserAdderPlugin` (`doAddUser`)
    on the LDAP plugin, but the implementation is a stub that always
    returns False (see ``pas/plugins/ldap/plugin.py``: the body is
    ``# XXX`` + ``return False``). Leaving it active misleads admins:
    the "User_Adder" checkbox shows up in the ZMI Activate tab and
    the Plone "add user" form looks like it should create LDAP users
    when it actually falls through to the local user store.

    Idempotent: no-op when already deactivated.

    :param portal: Plone site root.
    """
    plugins = _pas_plugin_registry(portal)
    if plugins is None:
        return
    try:
        active_ids = plugins.listPluginIds(IUserAdderPlugin)
    except KeyError:
        return
    if PLUGIN_ID not in active_ids:
        return
    plugins.deactivatePlugin(IUserAdderPlugin, PLUGIN_ID)
    logger.info(
        "Deactivated IUserAdderPlugin on %r (doAddUser is a stub)",
        PLUGIN_ID)


def _pas_plugin_registry(portal):
    """Return the `acl_users.plugins` registry, or None."""
    acl_users = getattr(portal, "acl_users", None)
    if acl_users is None:
        return None
    return getattr(acl_users, "plugins", None)


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
