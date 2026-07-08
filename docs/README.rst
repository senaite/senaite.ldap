.. image:: https://raw.githubusercontent.com/senaite/senaite.ldap/master/static/senaite.ldap-pypi.png
   :target: https://github.com/senaite/senaite.ldap#readme
   :alt: senaite.ldap
   :height: 128

*LDAP / Active Directory authentication for SENAITE LIMS*
=========================================================

.. image:: https://img.shields.io/pypi/v/senaite.ldap.svg?style=flat-square
   :target: https://pypi.python.org/pypi/senaite.ldap

.. image:: https://img.shields.io/github/issues-pr/senaite/senaite.ldap.svg?style=flat-square
   :target: https://github.com/senaite/senaite.ldap/pulls

.. image:: https://img.shields.io/github/issues/senaite/senaite.ldap.svg?style=flat-square
   :target: https://github.com/senaite/senaite.ldap/issues

.. image:: https://img.shields.io/badge/README-GitHub-blue.svg?style=flat-square
   :target: https://github.com/senaite/senaite.ldap#readme

.. image:: https://img.shields.io/badge/Built%20with-%E2%9D%A4-red.svg
   :target: https://github.com/senaite/senaite.ldap

.. image:: https://img.shields.io/badge/Made%20for%20SENAITE-%E2%AC%A1-lightgrey.svg
   :target: https://www.senaite.com


About
=====

SENAITE LDAP is a Pluggable Auth Service (PAS) Plugin for SENAITE.

It bridges SENAITE users and groups to an LDAP or Active Directory
backend via `node.ext.ldap`_, and ships a native SENAITE control panel
to configure the connection, attribute mapping, cache and group
exposure.

Features:

- Native SENAITE control panel with tabs for server, users, groups,
  cache and a live inspector.
- Server tab with base DN detection, connectivity check and live
  status indicator.
- Users and groups tabs with LDAP object class discovery, live filter
  preview and configurable member attribute mapping.
- Optional group exposure so LDAP groups become first-class SENAITE
  groups.
- Optional memcached-backed query cache with live stats and manual
  purge from the control panel.
- Inspector page for ad-hoc LDAP searches against the configured
  backend.

The PAS plugin was originally derived from `pas.plugins.ldap`_. Since
2.0.0 the plugin lives in-tree under `senaite.ldap.pas`;
`pas.plugins.ldap` is no longer a runtime dependency.


Dependencies
============

The following packages need to be installed on the server::

    apt get install build_essentials libsasl2-dev libldap2-dev libssl-dev


License
=======

**SENAITE.LDAP** Copyright (C) RIDING BYTES & NARALABS

This program is free software; you can redistribute it and/or modify it under
the terms of the `GNU General Public License version 2`_ as published
by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.


.. Links

.. _SENAITE LIMS: https://www.senaite.com
.. _GNU General Public License version 2: https://www.gnu.org/licenses/old-licenses/gpl-2.0.txt
.. _node.ext.ldap: https://github.com/conestack/node.ext.ldap
.. _pas.plugins.ldap: https://github.com/collective/pas.plugins.ldap
