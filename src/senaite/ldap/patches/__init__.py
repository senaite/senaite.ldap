# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.LDAP.
#
# Copyright 2025 by it's authors.
# Some rights reserved, see README and LICENSE.

"""Monkey patches for upstream LDAP libraries.

Each submodule patches one upstream target and exposes an ``apply()``
function. The package-level `apply_patches` is the single entry point
called from `senaite.ldap.initialize` at startup.

The patches here guard against defects that surface as hard errors in
unrelated SENAITE code paths (e.g. Client creation triggers a PAS
group lookup which iterates LDAP groups; a user authenticating
triggers a search to resolve the login attribute to a user id).
"""

from senaite.ldap.patches import ldap_session


def apply_patches():
    """Apply every registered patch.

    Idempotent: each submodule's ``apply()`` is a no-op when the
    target already points at the replacement.
    """
    ldap_session.apply()
