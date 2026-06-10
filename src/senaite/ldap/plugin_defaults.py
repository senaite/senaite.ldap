# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.LDAP.
#
# Copyright 2025 by it's authors.
# Some rights reserved, see README and LICENSE.

"""Built-in default values for the vendored LDAP PAS plugin.

Used by `senaite.ldap.plugin_properties.propproxy` as the fall-back
when a key has not been written into the plugin's settings BTree.
"""

from node.ext.ldap.scope import ONELEVEL


DEFAULTS = {
    "server.uri": "ldap://127.0.0.1:12345",
    "server.user": "cn=Manager,dc=my-domain,dc=com",
    "server.password": "secret",
    "server.ignore_cert": False,
    "server.start_tls": False,
    "server.page_size": 1000,
    "server.conn_timeout": 5,
    "server.op_timeout": 600,
    "cache.cache": False,
    "cache.memcached": "127.0.0.1:11211",
    "cache.timeout": 300,
    "users.baseDN": "ou=users,dc=my-domain,dc=com",
    "users.attrmap": {
        "rdn": "uid",
        "id": "uid",
        "login": "uid",
        "fullname": "cn",
        "email": "mail",
        "location": "l",
    },
    "users.scope": ONELEVEL,
    "users.queryFilter": "(objectClass=inetOrgPerson)",
    "users.objectClasses": ["inetOrgPerson"],
    "users.defaults": {},
    "users.memberOfSupport": False,
    "users.recursiveGroups": False,
    "users.memberOfExternalGroupDNs": [],
    "users.account_expiration": False,
    "users.expires_attr": "shadowExpire",
    "users.expires_unit": 0,
    "groups.baseDN": "ou=groups,dc=my-domain,dc=com",
    "groups.attrmap": {
        "rdn": "cn",
        "id": "cn",
        "title": "o",
        "description": "description",
    },
    "groups.scope": ONELEVEL,
    "groups.queryFilter": "(objectClass=groupOfNames)",
    "groups.objectClasses": ["groupOfNames"],
    "groups.defaults": {},
    "groups.memberOfSupport": False,
    "groups.recursiveGroups": False,
    "groups.memberOfExternalGroupDNs": [],
    "groups.expires_attr": "unused",
    "groups.expires_unit": 0,
}
