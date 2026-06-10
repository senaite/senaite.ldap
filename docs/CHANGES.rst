Changelog
=========

2.0.0 (unreleased)
------------------

YAFOWIL-based control panel replaced with a native SENAITE form. The
``pas.plugins.ldap.plonecontrolpanel`` sub-package is no longer
installed. Existing ``pasldap`` plugin configuration is untouched.
See ``docs/2.x-plan.md``.

- #21 Deactivate the stub IUserAdderPlugin on the pasldap plugin
- #20 Groups tab: checkbox to expose / hide LDAP groups in SENAITE
- #19 Sticky control-panel tab: fire Bootstrap's tab plugin via synthetic click
- #18 Move monkey patches into a package with one submodule per target
- #17 Remove the LDAP / Active Directory configlet on uninstall
- #16 Move upgrade steps into a package mirroring senaite.patient layout
- #15 Refactor cache views and control-panel JS for readability
- #14 Remember active control-panel tab across reloads via ?tab= URL parameter
- #13 Cache tab: live memcached stats (hits/misses/items/bytes) + Purge button
- #12 Consolidate all 2.0.0 upgrade steps into a single 1100 → 2000 step
- #11 Handle unsolicited paged-results response (LLDAP) — fixes "always 1 result"
- #10 Apply sane defaults for users/groups scope and objectClasses on upgrade
- #9 Factor inline JS into a static file; live AJAX status dot on the Server tab
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
