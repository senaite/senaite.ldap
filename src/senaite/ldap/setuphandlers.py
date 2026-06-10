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
    """Create or migrate the `pasldap` plugin to our vendored class.

    Idempotent and called from both `install` and the 1100 -> 2000
    upgrade step. Three branches:

    1. Plugin not installed -> create a fresh
       `senaite.ldap.plugin.LDAPPlugin` and activate it on every
       interface it implements.
    2. Plugin already a `senaite.ldap.pas.plugin.LDAPPlugin` ->
       no-op.
    3. Plugin is a `pas.plugins.ldap.plugin.LDAPPlugin` -> migrate:
       snapshot settings + plugin_caching + active interface
       registrations, swap the instance, restore state.

    :param portal: Plone site root.
    """
    from senaite.ldap.pas.plugin import LDAPPlugin

    acl_users = getattr(portal, "acl_users", None)
    if acl_users is None:
        logger.warning("acl_users not found; skipping pasldap install")
        return

    existing = acl_users.objectIds()
    if PLUGIN_ID not in existing:
        _create_plugin(acl_users, LDAPPlugin)
        return

    plugin = acl_users[PLUGIN_ID]
    if isinstance(plugin, LDAPPlugin):
        logger.info(
            "pasldap already on senaite.ldap.plugin.LDAPPlugin; "
            "no migration needed")
        return

    _migrate_plugin(acl_users, plugin, LDAPPlugin)


def _create_plugin(acl_users, plugin_class):
    """Add a fresh `pasldap` plugin and activate every implemented PAS
    interface in priority order, mirroring upstream's `_addPlugin`.

    :param acl_users: The site's `acl_users` user folder.
    :param plugin_class: The `LDAPPlugin` class to instantiate.
    """
    plugin = plugin_class(PLUGIN_ID, title="LDAP plugin (senaite.ldap)")
    acl_users._setObject(PLUGIN_ID, plugin)
    plugin = acl_users[PLUGIN_ID]  # re-acquire wrapped
    for info in acl_users.plugins.listPluginTypeInfo():
        interface = info["interface"]
        if not interface.providedBy(plugin):
            continue
        acl_users.plugins.activatePlugin(interface, plugin.getId())
        # Move every OTHER plugin on this interface down so the LDAP
        # plugin runs first -- the canonical priority order PAS
        # assumes for the LDAP integration.
        others = [
            pid for pid, _obj
            in acl_users.plugins.listPlugins(interface)[:-1]
        ]
        if others:
            acl_users.plugins.movePluginsDown(interface, others)
    logger.info(
        "Installed %s as %r", plugin_class.__name__, PLUGIN_ID)


def _migrate_plugin(acl_users, old_plugin, new_class):
    """Swap `old_plugin` (an upstream LDAPPlugin) for `new_class`.

    Snapshot the persistent state first, then delete and recreate
    so the persisted class path moves from
    ``pas.plugins.ldap.plugin.LDAPPlugin`` to
    ``senaite.ldap.plugin.LDAPPlugin``. The new instance keeps the
    same id (``pasldap``), the same settings BTree contents, the
    same plugin-cache flag, and the same set of activated PAS
    interfaces (so e.g. an admin who deactivated `IUserAdderPlugin`
    via the ZMI keeps that decision after the swap).

    :param acl_users: The site's `acl_users` user folder.
    :param old_plugin: The currently-installed upstream `LDAPPlugin`.
    :param new_class: Target class.
    """
    saved_settings = dict(old_plugin.settings)
    plugin_caching = bool(getattr(old_plugin, "plugin_caching", True))
    active_interfaces = _snapshot_active_interfaces(
        acl_users.plugins, PLUGIN_ID)

    logger.info(
        "Migrating %r from %s to %s (%d settings keys, "
        "%d active interfaces)",
        PLUGIN_ID,
        old_plugin.__class__.__module__ + "."
        + old_plugin.__class__.__name__,
        new_class.__module__ + "." + new_class.__name__,
        len(saved_settings), len(active_interfaces))

    acl_users.manage_delObjects([PLUGIN_ID])
    new_plugin = new_class(
        PLUGIN_ID, title="LDAP plugin (senaite.ldap)")
    acl_users._setObject(PLUGIN_ID, new_plugin)
    new_plugin = acl_users[PLUGIN_ID]

    for key, value in saved_settings.items():
        new_plugin.settings[key] = value
    new_plugin.plugin_caching = plugin_caching

    for iface in active_interfaces:
        acl_users.plugins.activatePlugin(iface, PLUGIN_ID)

    logger.info("pasldap migration complete")


def _snapshot_active_interfaces(plugins, plugin_id):
    """Return the list of PAS interfaces `plugin_id` is registered on.

    :param plugins: The `acl_users.plugins` registry.
    :param plugin_id: Plugin id to look up.
    :returns: List of interface objects (in registry iteration
        order). The ordering doesn't matter for re-activation.
    """
    active = []
    for info in plugins.listPluginTypeInfo():
        iface = info["interface"]
        try:
            ids = plugins.listPluginIds(iface)
        except KeyError:
            continue
        if plugin_id in ids:
            active.append(iface)
    return active


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
