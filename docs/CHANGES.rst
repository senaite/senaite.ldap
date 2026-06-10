Changelog
=========

2.0.0 (unreleased)
------------------

YAFOWIL-based control panel replaced with a native SENAITE form. The
``pas.plugins.ldap.plonecontrolpanel`` sub-package is no longer
installed. Existing ``pasldap`` plugin configuration is untouched.
See ``docs/2.x-plan.md``.

- #8 Detect base DN, mirror Users→Groups base, group picker for memberOf external DNs
- #7 Discover LDAP object classes + live filter preview; rename @@plone_ → @@senaite_
- #6 Add live LDAP search & inspector page
- #5 Add upgrade step 1100 → 2000 and unit tests for control panel helpers
- #3 Replace YAFOWIL control panel with native SENAITE form
- Add a live LDAP search / inspector page at
  ``@@plone_ldapsearch``, linked from the control-panel status
  header. Browse the directory by Users / Groups / custom base DN,
  run arbitrary RFC 4515 filters, click a result to expand its
  full attribute set. Replaces the ``@@plone_ldapinspector`` view
  from the dropped ``plonecontrolpanel`` sub-package.


1.1.0 (2026-06-09)
------------------

- #2 Guard node.ext.ldap paged search against empty/cookie-less responses
- #1 Pin plumber for Python 2 compatibility


1.0.0 (2025-02-07)
------------------

- Add-on created
