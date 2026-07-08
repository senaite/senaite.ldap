<div align="center">
  <a href="https://github.com/senaite/senaite.ldap">
    <img src="../static/senaite.ldap.png" alt="SENAITE LDAP" height="64" />
  </a>
  <p>PAS Plugin for AD/LDAP</p>

  <div>
    <a href="https://pypi.python.org/pypi/senaite.ldap">
      <img src="https://img.shields.io/pypi/v/senaite.ldap.svg?style=flat-square" alt="pypi-version" />
    </a>
    <a href="https://github.com/senaite/senaite.ldap/pulls">
      <img src="https://img.shields.io/github/issues-pr/senaite/senaite.ldap.svg?style=flat-square" alt="open PRs" />
    </a>
    <a href="https://github.com/senaite/senaite.ldap/issues">
      <img src="https://img.shields.io/github/issues/senaite/senaite.ldap.svg?style=flat-square" alt="open Issues" />
    </a>
    <a href="#">
      <img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square" alt="pr" />
    </a>
    <a href="https://www.senaite.com">
      <img src="https://img.shields.io/badge/Made%20for%20SENAITE-%E2%AC%A1-lightgrey.svg" alt="Made for SENAITE" />
    </a>
  </div>
</div>


## About

SENAITE LDAP is a Pluggable Auth Service (PAS) Plugin for SENAITE.

It bridges SENAITE users and groups to an LDAP or Active Directory
backend via [node.ext.ldap](https://github.com/conestack/node.ext.ldap),
and ships a native SENAITE control panel to configure the connection,
attribute mapping, cache and group exposure.

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

The PAS plugin was originally derived from
[pas.plugins.ldap](https://github.com/collective/pas.plugins.ldap).
Since 2.0.0 the plugin lives in-tree under `senaite.ldap.pas`;
`pas.plugins.ldap` is no longer a runtime dependency.


## License

**SENAITE.LDAP** Copyright (C) RIDING BYTES & NARALABS

This program is free software; you can redistribute it and/or modify it under
the terms of the [GNU General Public License version
2](https://github.com/senaite/senaite.ldap/blob/master/docs/LICENSE.md)
as published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.
