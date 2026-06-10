# -*- coding: utf-8 -*-

import logging

# Apply BBB sys.modules aliases BEFORE any other import. The
# persistent component registry on existing installs references
# `pas.plugins.ldap.*` dotted paths; the shim makes those resolve
# to our vendored symbols. Must run before Zope unpickles the local
# site manager.
from senaite.ldap import _bbb as _bbb_shim
_bbb_shim.apply()

from bika.lims.api import get_request  # noqa: E402
from senaite.ldap.interfaces import ISenaiteLdap  # noqa: E402
from zope.i18nmessageid import MessageFactory  # noqa: E402

PRODUCT_NAME = "senaite.ldap"
PROFILE_ID = "profile-{}:default".format(PRODUCT_NAME)
UNINSTALL_PROFILE_ID = "profile-{}:uninstall".format(PRODUCT_NAME)

messageFactory = MessageFactory(PRODUCT_NAME)
logger = logging.getLogger(PRODUCT_NAME)


def is_installed():
    """Returns whether the add-on is installed or not
    """
    request = get_request()
    return ISenaiteLdap.providedBy(request)


def check_installed(default_return):
    """Decorator to prevent the function to be called if product not installed

    :param default_return: value to return if not installed
    """
    def is_installed_decorator(func):
        def wrapper(*args, **kwargs):
            if not is_installed():
                return default_return
            return func(*args, **kwargs)
        return wrapper
    return is_installed_decorator


def initialize(context):
    """Initializer called when used as a Zope 2 product
    """
    logger.info("*** Initializing SENAITE.LDAP package ***")
    from senaite.ldap.patches import apply_patches
    apply_patches()
    _register_pas_plugin(context)


def _register_pas_plugin(context):
    """Register the vendored `LDAPPlugin` with PAS.

    Done at Zope startup so the class shows up in
    ``manage_addProduct/PluggableAuthService`` and so PAS knows the
    class as a `MultiPlugin`. No plugin instances are created here;
    that's still the job of the setup handler / upgrade step.
    """
    from AccessControl.Permissions import add_user_folders
    from Products.PluggableAuthService import registerMultiPlugin
    from senaite.ldap.pas.plugin import LDAPPlugin
    from senaite.ldap.pas.plugin import manage_addLDAPPlugin

    try:
        registerMultiPlugin(LDAPPlugin.meta_type)
    except RuntimeError:
        # Idempotent: registerMultiPlugin raises if the meta_type
        # is already registered (e.g. Zope re-initialising on
        # restart in --foreground).
        pass
    context.registerClass(
        LDAPPlugin,
        permission=add_user_folders,
        constructors=(manage_addLDAPPlugin,),
        visibility=None,
    )
