Changelog
=========

2.0.0 (unreleased)
------------------

- Rename all control-panel views from the ``@@plone_ldap*`` prefix
  to ``@@senaite_ldap*``. Existing 1.x or early-2.x configlets are
  rewritten by upgrade step 2000 → 2010.
- Object-class fields in the Users and Groups tabs are now
  multi-select pickers populated by sampling the live directory
  (``@@senaite_ldapdiscover_objectclasses``). The underlying
  newline-joined textarea stays available behind an *edit raw*
  link.
- New live filter preview under each tab showing the LDAP filter
  the configured object classes + query filter will produce.
- New discovery endpoint ``@@senaite_ldapdiscover_groups`` returning
  groups under the Groups base DN (used by upcoming PRs that wire
  group selection into the form).

2.x replaces the YAFOWIL-based LDAP control panel with a native
SENAITE form. The ``pas.plugins.ldap.plonecontrolpanel`` sub-package
and its profile are no longer installed; our ZCML no longer pulls in
any YAFOWIL code. The YAFOWIL eggs themselves stay on disk because
``pas.plugins.ldap`` still declares them as runtime dependencies in
its egg metadata — they are present but unused. Existing ``pasldap``
plugin configuration in the ZODB is untouched. See
``docs/2.x-plan.md`` for the full plan and follow-up work to drop the
disk footprint as well.

- Bump profile version to 2000, drop the
  ``pas.plugins.ldap.plonecontrolpanel`` profile dependency.
- Replace the YAFOWIL control panel with a native SENAITE form.
- Upgrade step 1100 → 2000 cleans up orphan YAFOWIL registry records
  on existing 1.x installs and re-imports the controlpanel profile.
- Add unit tests for the control panel form helpers.
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
