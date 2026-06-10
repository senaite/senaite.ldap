# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.LDAP.
#
# Copyright 2025 by it's authors.
# Some rights reserved, see README and LICENSE.

"""ILDAPProps / ILDAPUsersConfig / ILDAPGroupsConfig adapters.

Vendored from `pas.plugins.ldap.properties` minus the
`BasePropertiesForm` YAFOWIL view (we have our own native control
panel at `@@senaite_ldapcontrolpanel`).

Each accessor is a `property` built by `propproxy(key)` whose getter
reads ``plugin.settings.get(key, DEFAULTS[key])`` and whose setter
writes ``plugin.settings[key] = value``. The `settings` attribute is
an `OOBTree` on the `LDAPPlugin` instance, so configuration changes
made via the control panel persist on the plugin itself.
"""

from node.ext.ldap.interfaces import ILDAPGroupsConfig
from node.ext.ldap.interfaces import ILDAPProps
from node.ext.ldap.interfaces import ILDAPUsersConfig
from node.ext.ldap.properties import BINARY_DEFAULTS
from node.ext.ldap.properties import MULTIVALUED_DEFAULTS
from senaite.ldap.pas.defaults import DEFAULTS
from senaite.ldap.pas.interfaces import ICacheSettingsRecordProvider
from senaite.ldap.pas.interfaces import ILDAPPlugin
from zope.component import adapter
from zope.component import queryUtility
from zope.interface import implementer


def propproxy(ckey):
    """Build a `property` descriptor backed by `plugin.settings[ckey]`.

    :param ckey: Dotted settings key (e.g. ``"server.uri"``).
    :returns: A `property` whose getter / setter delegate to the
        adapter's underlying `LDAPPlugin.settings` BTree.
    """
    def _getter(context):
        return context.plugin.settings.get(ckey, DEFAULTS[ckey])

    def _setter(context, value):
        context.plugin.settings[ckey] = value

    return property(_getter, _setter)


@implementer(ILDAPProps)
@adapter(ILDAPPlugin)
class LDAPProps(object):
    """Adapter exposing `ILDAPProps` over the plugin's settings BTree."""

    def __init__(self, plugin):
        self.plugin = plugin

    # TLS / retry fields are not yet wired up in our control panel;
    # leave them as class-level defaults until we expose them.
    tls_cacertfile = ""
    tls_cacertdir = ""
    tls_clcertfile = ""
    tls_clkeyfile = ""
    retry_max = 3
    retry_delay = 5

    uri = propproxy("server.uri")
    user = propproxy("server.user")
    password = propproxy("server.password")
    start_tls = propproxy("server.start_tls")
    ignore_cert = propproxy("server.ignore_cert")
    page_size = propproxy("server.page_size")
    conn_timeout = propproxy("server.conn_timeout")
    op_timeout = propproxy("server.op_timeout")
    cache = propproxy("cache.cache")
    timeout = propproxy("cache.timeout")

    @property
    def memcached(self):
        record_provider = queryUtility(ICacheSettingsRecordProvider)
        if record_provider is not None:
            return record_provider().value
        return u"feature not available"

    @memcached.setter
    def memcached(self, value):
        record_provider = queryUtility(ICacheSettingsRecordProvider)
        if record_provider is not None:
            record_provider().value = value

    binary_attributes = BINARY_DEFAULTS
    multivalued_attributes = MULTIVALUED_DEFAULTS


@implementer(ILDAPUsersConfig)
@adapter(ILDAPPlugin)
class UsersConfig(object):
    """Adapter exposing `ILDAPUsersConfig` over the plugin's settings."""

    def __init__(self, plugin):
        self.plugin = plugin

    strict = False
    defaults = dict()
    baseDN = propproxy("users.baseDN")
    attrmap = propproxy("users.attrmap")
    scope = propproxy("users.scope")
    queryFilter = propproxy("users.queryFilter")
    objectClasses = propproxy("users.objectClasses")
    defaults = propproxy("users.defaults")
    memberOfSupport = propproxy("users.memberOfSupport")
    recursiveGroups = propproxy("users.recursiveGroups")
    memberOfExternalGroupDNs = propproxy(
        "users.memberOfExternalGroupDNs")
    account_expiration = propproxy("users.account_expiration")
    _expiresAttr = propproxy("users.expires_attr")
    _expiresUnit = propproxy("users.expires_unit")

    @property
    def expiresAttr(self):
        return self.account_expiration and self._expiresAttr or None

    @property
    def expiresUnit(self):
        return self.account_expiration and self._expiresUnit or 0


@implementer(ILDAPGroupsConfig)
@adapter(ILDAPPlugin)
class GroupsConfig(object):
    """Adapter exposing `ILDAPGroupsConfig` over the plugin's settings.
    """

    def __init__(self, plugin):
        self.plugin = plugin

    strict = False
    defaults = dict()
    baseDN = propproxy("groups.baseDN")
    attrmap = propproxy("groups.attrmap")
    scope = propproxy("groups.scope")
    queryFilter = propproxy("groups.queryFilter")
    objectClasses = propproxy("groups.objectClasses")
    defaults = propproxy("groups.defaults")
    memberOfSupport = propproxy("groups.memberOfSupport")
    recursiveGroups = propproxy("groups.recursiveGroups")
    memberOfExternalGroupDNs = propproxy(
        "groups.memberOfExternalGroupDNs")
    expiresAttr = propproxy("groups.expires_attr")
    expiresUnit = propproxy("groups.expires_unit")
