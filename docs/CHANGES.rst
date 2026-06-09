Changelog
=========

2.0.0 (unreleased)
------------------

**Breaking**: 2.x replaces the YAFOWIL-based LDAP control panel with a
native SENAITE form. Six packages and their transitive dependencies are
no longer required: ``yafowil``, ``yafowil.plone``, ``yafowil.yaml``,
``yafowil.widget.array``, ``yafowil.widget.dict``, ``webresource``. The
``pas.plugins.ldap.plonecontrolpanel`` sub-package is also no longer
loaded (we keep the PAS plugin itself). Existing ``pasldap`` plugin
configuration in the ZODB is untouched. See ``docs/2.x-plan.md`` for
the full plan.

- Bump profile version to 2000, drop the
  ``pas.plugins.ldap.plonecontrolpanel`` profile dependency, and move
  YAFOWIL packages from ``install_requires`` to the new
  ``legacy_yafowil`` extra.


1.1.0 (2026-06-09)
------------------

- #2 Guard node.ext.ldap paged search against empty/cookie-less responses
- #1 Pin plumber for Python 2 compatibility


1.0.0 (2025-02-07)
------------------

- Add-on created
