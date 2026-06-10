# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.LDAP.
#
# Copyright 2025 by it's authors.
# Some rights reserved, see README and LICENSE.

"""LDAP PAS plugin, vendored from pas.plugins.ldap.

Differences from upstream `pas.plugins.ldap.plugin`:

- `meta_type` is ``"SENAITE LDAP Plugin"`` so the Zope ZMI add menu
  does not collide with upstream while both classes are importable
  during the migration cycle.
- `manage_options` and the ZMI add-form `PageTemplateFile` are
  dropped; senaite.ldap ships its own native control panel at
  `@@senaite_ldapcontrolpanel`.
- `ILDAPPlugin` is the local marker (`senaite.ldap.plugin_interfaces`)
  so the global adapter registry can route lookups for instances of
  this class to our adapters without colliding with upstream's.
"""

import logging
import os
import time

import ldap
import six

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from BTrees import OOBTree
from node.ext.ldap.interfaces import ILDAPGroupsConfig
from node.ext.ldap.interfaces import ILDAPProps
from node.ext.ldap.interfaces import ILDAPUsersConfig
from node.ext.ldap.ugm import Ugm
from Products.PlonePAS import interfaces as plonepas_interfaces
from Products.PlonePAS.plugins.group import PloneGroup
from Products.PluggableAuthService.interfaces import plugins \
    as pas_interfaces
from Products.PluggableAuthService.permissions import ManageGroups
from Products.PluggableAuthService.permissions import ManageUsers
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from senaite.ldap.plugin_cache import get_plugin_cache
from senaite.ldap.plugin_interfaces import ILDAPPlugin
from senaite.ldap.plugin_interfaces import VALUE_NOT_CACHED
from senaite.ldap.plugin_sheet import LDAPUserPropertySheet
from six.moves import map
from zope.interface import implementer


logger = logging.getLogger("senaite.ldap.plugin")

if six.PY2:
    process_time = time.clock
else:
    process_time = time.process_time

LDAP_ERROR_LOG_TIMEOUT = float(
    os.environ.get("SENAITE_LDAP_ERROR_LOG_TIMEOUT", 300.0))
LDAP_LONG_RUNNING_LOG_THRESHOLD = float(
    os.environ.get("SENAITE_LDAP_LONG_RUNNING_LOG_THRESHOLD", 5.0))


def manage_addLDAPPlugin(dispatcher, id, title="", RESPONSE=None, **kw):
    """Programmatic add hook used by `senaite.ldap.setuphandlers`."""
    ldapplugin = LDAPPlugin(id, title, **kw)
    dispatcher._setObject(ldapplugin.getId(), ldapplugin)
    if RESPONSE is not None:
        RESPONSE.redirect("manage_workspace")


def ldap_error_handler(prefix, default=None):
    """Decorator: swallow LDAP errors, log them, and back off.

    On error, stamps `_v_ldaperror_msg` + `_v_ldaperror_timeout` on
    the plugin and returns `default` for the duration of
    `LDAP_ERROR_LOG_TIMEOUT`. After that window the wrapped method
    is retried.
    """
    def _decorator(original_method, *args, **kwargs):
        def _wrapper(self, *args, **kwargs):
            if hasattr(self, "_v_ldaperror_timeout"):
                waiting = time.time() - self._v_ldaperror_timeout
                if waiting < LDAP_ERROR_LOG_TIMEOUT:
                    logger.debug(
                        "{0}: retry wait {1:0.5f} of {2:0.0f}s -> {3}"
                        .format(prefix, waiting,
                                LDAP_ERROR_LOG_TIMEOUT,
                                self._v_ldaperror_msg))
                    return default
            try:
                start = process_time()
                result = original_method(self, *args, **kwargs)
                delta_t = process_time() - start
                msg = "Call of {0!r} took {1:0.4f}s".format(
                    original_method, delta_t)
                if delta_t < LDAP_LONG_RUNNING_LOG_THRESHOLD:
                    logger.debug(msg)
                else:
                    logger.error(msg)
                return result
            except ldap.LDAPError as exc:
                self._v_ldaperror_msg = str(exc)
                self._v_ldaperror_timeout = time.time()
                logger.exception("LDAPError in {0}".format(prefix))
                return default
            except Exception as exc:  # noqa: BLE001 -- last resort
                self._v_ldaperror_msg = str(exc)
                self._v_ldaperror_timeout = time.time()
                logger.exception("Error in {0}".format(prefix))
                return default
        return _wrapper
    return _decorator


@implementer(
    ILDAPPlugin,
    pas_interfaces.IAuthenticationPlugin,
    pas_interfaces.IGroupEnumerationPlugin,
    pas_interfaces.IGroupsPlugin,
    pas_interfaces.IPropertiesPlugin,
    pas_interfaces.IUserEnumerationPlugin,
    pas_interfaces.IRolesPlugin,
    plonepas_interfaces.capabilities.IDeleteCapability,
    plonepas_interfaces.capabilities.IGroupCapability,
    plonepas_interfaces.capabilities.IPasswordSetCapability,
    plonepas_interfaces.group.IGroupManagement,
    plonepas_interfaces.group.IGroupIntrospection,
    plonepas_interfaces.plugins.IMutablePropertiesPlugin,
    plonepas_interfaces.plugins.IUserManagement,
)
class LDAPPlugin(BasePlugin):
    """Glue layer making node.ext.ldap available to PAS."""

    security = ClassSecurityInfo()
    meta_type = "SENAITE LDAP Plugin"

    # Tell PAS not to swallow our exceptions
    _dont_swallow_my_exceptions = False

    def __init__(self, id, title=None, **kw):
        self._setId(id)
        self.title = title
        self.init_settings()
        self.plugin_caching = True

    def init_settings(self):
        self.settings = OOBTree.OOBTree()

    @security.private
    def is_plugin_active(self, iface):
        pas = self._getPAS()
        ids = pas.plugins.listPluginIds(iface)
        return self.getId() in ids

    @property
    @security.private
    def groups_enabled(self):
        return self.groups is not None

    @property
    @security.private
    def users_enabled(self):
        return self.users is not None

    @property
    def _ldap_props(self):
        return ILDAPProps(self)

    def _ugm(self):
        plugin_cache = get_plugin_cache(self)
        ugm = plugin_cache.get()
        if ugm is not VALUE_NOT_CACHED:
            return ugm
        ucfg = ILDAPUsersConfig(self)
        gcfg = ILDAPGroupsConfig(self)
        ugm = Ugm(
            props=self._ldap_props, ucfg=ucfg, gcfg=gcfg, rcfg=None)
        plugin_cache.set(ugm)
        return ugm

    @property
    @ldap_error_handler("groups")
    @security.private
    def groups(self):
        return self._ugm().groups

    @property
    @ldap_error_handler("users")
    @security.private
    def users(self):
        return self._ugm().users

    @property
    @security.protected(ManageUsers)
    def ldaperror(self):
        if hasattr(self, "_v_ldaperror_msg"):
            waiting = time.time() - self._v_ldaperror_timeout
            if waiting < LDAP_ERROR_LOG_TIMEOUT:
                return self._v_ldaperror_msg + \
                    " (for %0.2fs)" % waiting
        return False

    @security.public
    def reset(self):
        # XXX flush caches
        pass

    # ------------------------------------------------------------------
    # pas_interfaces.IAuthenticationPlugin
    # ------------------------------------------------------------------
    @ldap_error_handler("authenticateCredentials")
    @security.public
    def authenticateCredentials(self, credentials):
        """credentials -> (userid, login).

        Returns None if the credentials cannot be authenticated.
        """
        default = None
        if not self.is_plugin_active(
                pas_interfaces.IAuthenticationPlugin):
            return default
        login = credentials.get("login")
        pw = credentials.get("password")
        if not (login and pw):
            return default
        logger.debug("credentials: %s" % credentials)
        users = self.users
        if not users:
            return default
        userid = users.authenticate(login, pw)
        if userid:
            logger.info("logged in %s" % userid)
            return (userid, login)
        return default

    # ------------------------------------------------------------------
    # pas_interfaces.IGroupEnumerationPlugin
    # ------------------------------------------------------------------
    @security.private
    def enumerateGroups(self, id=None, exact_match=False, sort_by=None,
                        max_results=None, **kw):
        """-> (group_info_1, ..., group_info_N)."""
        default = ()
        if not self.is_plugin_active(
                pas_interfaces.IGroupEnumerationPlugin):
            return default
        groups = self.groups
        if not groups:
            return default
        if id:
            kw["id"] = id
        if not kw:
            matches = groups.ids
        else:
            try:
                matches = groups.search(
                    criteria=kw, exact_match=exact_match)
            except ValueError:
                # raised when exact_match and result not unique
                return default
        if sort_by == "id":
            matches = sorted(matches)
        pluginid = self.getId()
        ret = [dict(id=_id, pluginid=pluginid) for _id in matches]
        if max_results and len(ret) > max_results:
            ret = ret[:max_results]
        return ret

    # ------------------------------------------------------------------
    # pas_interfaces.IGroupsPlugin
    # ------------------------------------------------------------------
    @security.private
    def getGroupsForPrincipal(self, principal, request=None):
        """principal -> (group_1, ..., group_N)."""
        default = tuple()
        if not self.is_plugin_active(pas_interfaces.IGroupsPlugin):
            return default
        users = self.users
        if not users:
            return default
        try:
            ugm_principal = self.users[principal.getId()]
        except KeyError:
            # group-in-group would go here; UGM nodes don't yet
            # expose that, so we return early.
            return default
        try:
            return ugm_principal.group_ids
        except Exception:  # noqa: BLE001 -- UGM raises broadly
            logger.exception("Problems getting group_ids!")
        return default

    # ------------------------------------------------------------------
    # pas_interfaces.IUserEnumerationPlugin
    # ------------------------------------------------------------------
    @ldap_error_handler("enumerateUsers", default=tuple())
    @security.private
    def enumerateUsers(self, id=None, login=None, exact_match=False,
                       sort_by=None, max_results=None, **kw):
        """-> (user_info_1, ..., user_info_N)."""
        default = tuple()
        if not self.is_plugin_active(
                pas_interfaces.IUserEnumerationPlugin):
            return default
        if login:
            if not isinstance(login, six.string_types):
                raise NotImplementedError(
                    "sequence is not supported yet.")
            kw["login"] = login
        if "login" in kw and "name" in kw:
            del kw["name"]
        if id:
            if not isinstance(id, six.string_types):
                raise NotImplementedError(
                    "sequence is not supported yet.")
            kw["id"] = id
        users = self.users
        if not users:
            return default
        if not exact_match:
            for key in kw:
                value = kw[key]
                if not value.endswith("*"):
                    kw[key] = value + "*"
        try:
            matches = users.search(
                criteria=kw, attrlist=("login",),
                exact_match=exact_match)
        except ValueError:
            return default
        pluginid = self.getId()
        ret = []
        for id_, attrs in matches:
            ret.append({
                "id": id_,
                "login": attrs["login"][0],
                "pluginid": pluginid,
            })
        if max_results and len(ret) > max_results:
            ret = ret[:max_results]
        return ret

    # ------------------------------------------------------------------
    # pas_interfaces.IRolesPlugin
    # ------------------------------------------------------------------
    def getRolesForPrincipal(self, principal, request=None):
        default = ()
        users = self.users
        if not users:
            return default
        if self.enumerateUsers(id=principal.getId()):
            return ("Member",)
        return default

    @security.private
    def updateUser(self, user_id, login_name):
        """Update the login name of `user_id`.

        Plugin returns False to indicate it does not store login
        names; PAS will fall through to another plugin.
        """
        return False

    @security.private
    def updateEveryLoginName(self, quit_on_first_error=True):
        """Refresh canonical login names. Not implemented."""
        return

    # ------------------------------------------------------------------
    # plonepas_interfaces.group.IGroupManagement (mostly stubs)
    # ------------------------------------------------------------------
    @security.private
    def addGroup(self, id, **kw):
        return False

    @security.protected(ManageGroups)
    def addPrincipalToGroup(self, principal_id, group_id):
        return False

    @security.private
    def updateGroup(self, id, **kw):
        return False

    @security.private
    def setRolesForGroup(self, group_id, roles=()):
        # Even Products.PlonePAS.plugins.GroupAwareRoleManager doesn't
        # implement this -- safe to ignore.
        return False

    @security.private
    def removeGroup(self, group_id):
        return False

    @security.protected(ManageGroups)
    def removePrincipalFromGroup(self, principal_id, group_id):
        return False

    # ------------------------------------------------------------------
    # plonepas_interfaces.plugins.IMutablePropertiesPlugin
    # ------------------------------------------------------------------
    @security.private
    def getPropertiesForUser(self, user_or_group, request=None):
        """user -> IMutablePropertySheet || {}."""
        default = {}
        if not self.is_plugin_active(
                pas_interfaces.IPropertiesPlugin):
            return default
        ugid = user_or_group.getId()
        if not isinstance(ugid, six.text_type):
            ugid = ugid.decode("utf-8")
        try:
            if (self.enumerateUsers(id=ugid)
                    or self.enumerateGroups(id=ugid)):
                return LDAPUserPropertySheet(user_or_group, self)
        except KeyError:
            pass
        return default

    @security.private
    def setPropertiesForUser(self, user, propertysheet):
        """No-op: `LDAPUserPropertySheet` writes directly to LDAP."""
        pass

    @security.private
    def deleteUser(self, user_id):
        """No-op: property cleanup happens in `doDeleteUser`."""
        pass

    # ------------------------------------------------------------------
    # plonepas_interfaces.plugins.IUserManagement
    # (signature of pas_interfaces.IUserAdderPlugin)
    # ------------------------------------------------------------------
    @security.private
    def doAddUser(self, login, password):
        """Stub. senaite.ldap deactivates IUserAdderPlugin in setup
        so this is never reached by PAS.
        """
        return False

    @security.private
    def doChangeUser(self, user_id, password, **kw):
        """Reset the user's password in LDAP."""
        if self.users:
            try:
                self.users.passwd(user_id, None, password)
            except KeyError:
                msg = "{0:s} is not an LDAP user.".format(user_id)
                logger.warn(msg)
                raise RuntimeError(msg)

    @security.private
    def doDeleteUser(self, login):
        """Stub. Not implemented."""
        return False

    # ------------------------------------------------------------------
    # plonepas_interfaces.capabilities.IDeleteCapability
    # ------------------------------------------------------------------
    @security.public
    def allowDeletePrincipal(self, id):
        return False

    # ------------------------------------------------------------------
    # plonepas_interfaces.capabilities.IGroupCapability
    # ------------------------------------------------------------------
    @security.public
    def allowGroupAdd(self, principal_id, group_id):
        return False

    @security.public
    def allowGroupRemove(self, principal_id, group_id):
        return False

    # ------------------------------------------------------------------
    # plonepas_interfaces.group.IGroupIntrospection
    # ------------------------------------------------------------------
    @security.public
    def getGroupById(self, group_id):
        """portal_groupdata-ish object for `group_id`, or None."""
        default = None
        if not self.is_plugin_active(
                plonepas_interfaces.group.IGroupIntrospection):
            return default
        if group_id is None:
            return None
        if not isinstance(group_id, six.text_type):
            group_id = group_id.decode("utf8")
        groups = self.groups
        if not groups or group_id not in list(groups.keys()):
            return default
        ugmgroup = self.groups[group_id]
        title = ugmgroup.attrs.get("title", None)
        group = PloneGroup(ugmgroup.id, title).__of__(self)
        pas = self._getPAS()
        plugins = pas.plugins
        for propfinder_id, propfinder in plugins.listPlugins(
                pas_interfaces.IPropertiesPlugin):
            data = propfinder.getPropertiesForUser(group, None)
            if not data:
                continue
            group.addPropertysheet(propfinder_id, data)
        group._addGroups(
            pas._getGroupsForPrincipal(group, None, plugins=plugins))
        for rolemaker_id, rolemaker in plugins.listPlugins(
                pas_interfaces.IRolesPlugin):
            roles = rolemaker.getRolesForPrincipal(group, None)
            if not roles:
                continue
            group._addRoles(roles)
        return group

    @security.private
    def getGroups(self):
        return list(map(self.getGroupById, self.getGroupIds()))

    @security.private
    def getGroupIds(self):
        default = []
        if not self.is_plugin_active(
                plonepas_interfaces.group.IGroupIntrospection):
            return default
        return self.groups and self.groups.ids or default

    @security.private
    def getGroupMembers(self, group_id):
        default = ()
        if not self.is_plugin_active(
                plonepas_interfaces.group.IGroupIntrospection):
            return default
        try:
            group = self.groups[group_id]
        except (KeyError, TypeError):
            return default
        return tuple(group.member_ids)

    # ------------------------------------------------------------------
    # plonepas_interfaces.capabilities.IPasswordSetCapability
    # ------------------------------------------------------------------
    @security.public
    def allowPasswordSet(self, id):
        users = self.users
        if not users:
            return False
        try:
            res = self.users.search(
                criteria={"id": id}, attrlist=(), exact_match=True)
            return len(res) > 0
        except ValueError:
            return False


InitializeClass(LDAPPlugin)
