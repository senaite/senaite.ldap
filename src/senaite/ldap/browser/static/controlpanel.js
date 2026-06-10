/*
 * SENAITE LDAP control panel
 *
 * Two small modules:
 *   (1) Discovery + live filter preview + base-DN detect + Users→Groups mirror
 *   (2) Live LDAP search/inspector (the Search tab)
 *
 * Both modules read configuration from the #ls-bridge element in the
 * template:
 *   data-users-base   - configured Users baseDN
 *   data-groups-base  - configured Groups baseDN
 *   data-self-url     - URL of the control-panel view, used to derive
 *                       the URL prefix for the JSON endpoints
 *
 * Wired up only when #ls-bridge is present so this file is safe to
 * include on any page.
 */

(function () {
  "use strict";

  var bridge = document.getElementById("ls-bridge");
  if (!bridge) return;

  var USERS_BASE = bridge.getAttribute("data-users-base") || "";
  var GROUPS_BASE = bridge.getAttribute("data-groups-base") || "";
  var SELF_URL = bridge.getAttribute("data-self-url") || "";
  var BASE_URL = SELF_URL.replace(/\/@@senaite_ldapcontrolpanel$/, "");

  // ====================================================================
  // 1) Discovery + filter preview + base-DN detect + Users→Groups mirror
  // ====================================================================

  function textareaValue(id) {
    var ta = document.getElementById(id);
    return ta ? ta.value : "";
  }

  function setTextareaLines(id, items) {
    var ta = document.getElementById(id);
    if (!ta) return;
    ta.value = items.join("\n");
    ta.dispatchEvent(new Event("change"));
  }

  function parseLines(value) {
    return (value || "").split("\n")
      .map(function (s) { return s.trim(); })
      .filter(Boolean);
  }

  function syncTextareaFromPicker(picker) {
    var targetId = picker.getAttribute("data-target");
    var selected = Array.from(picker.selectedOptions)
                        .map(function (o) { return o.value; });
    setTextareaLines(targetId, selected);
  }

  function populatePicker(picker, available, selected) {
    // Merge available + currently-selected so currently-saved values
    // that aren't in the discovered set still show up.
    var merged = {};
    available.forEach(function (oc) { merged[oc] = true; });
    selected.forEach(function (oc) { merged[oc] = true; });
    var keys = Object.keys(merged).sort();

    while (picker.firstChild) picker.removeChild(picker.firstChild);
    keys.forEach(function (oc) {
      var opt = document.createElement("option");
      opt.value = oc;
      opt.textContent = oc;
      if (selected.indexOf(oc) !== -1) opt.selected = true;
      picker.appendChild(opt);
    });
  }

  function discoverObjectClasses(picker, statusEl) {
    var which = picker.getAttribute("data-which");
    statusEl.textContent = "Loading…";
    fetch(BASE_URL + "/@@senaite_ldapdiscover_objectclasses?which=" +
          encodeURIComponent(which),
          { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) {
          statusEl.textContent = "Discovery failed: " + data.error;
          return;
        }
        var targetId = picker.getAttribute("data-target");
        var current = parseLines(textareaValue(targetId));
        populatePicker(picker, data.object_classes, current);
        statusEl.textContent =
          "Found " + data.object_classes.length +
          " object class(es) from " + data.sampled + " sampled entries.";
      })
      .catch(function (err) {
        statusEl.textContent = "Discovery failed: " + err;
      });
  }

  function discoverGroups(picker, statusEl) {
    statusEl.textContent = "Loading groups…";
    fetch(BASE_URL + "/@@senaite_ldapdiscover_groups",
          { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) {
          statusEl.textContent = "Group discovery failed: " + data.error;
          return;
        }
        var targetId = picker.getAttribute("data-target");
        var current = parseLines(textareaValue(targetId));
        var dns = data.groups.map(function (g) { return g.dn; });
        populatePicker(picker, dns, current);
        var cnByDn = {};
        data.groups.forEach(function (g) { cnByDn[g.dn] = g.cn; });
        Array.from(picker.options).forEach(function (opt) {
          var cn = cnByDn[opt.value];
          if (cn) opt.textContent = cn + "  —  " + opt.value;
        });
        var truncated = data.truncated ? " (truncated)" : "";
        statusEl.textContent =
          "Found " + data.count + " group(s)" + truncated;
      })
      .catch(function (err) {
        statusEl.textContent = "Group discovery failed: " + err;
      });
  }

  function detectBaseDn(btn) {
    var targetId = btn.getAttribute("data-target");
    var prefix = btn.getAttribute("data-suggest-prefix") || "";
    var input = document.getElementById(targetId);
    var status = document.querySelector(
      "[data-status='" + targetId + "-status']");
    if (!input) return;
    if (status) status.textContent = "Detecting…";

    fetch(BASE_URL + "/@@senaite_ldapdiscover_naming_contexts",
          { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) {
          if (status) status.textContent = "Detection failed: " + data.error;
          return;
        }
        var ncs = data.naming_contexts || [];
        if (ncs.length === 0) {
          if (status) {
            status.textContent =
              "No namingContexts published by the server.";
          }
          return;
        }
        var suggested = prefix ? prefix + "," + ncs[0] : ncs[0];
        input.value = suggested;
        input.dispatchEvent(new Event("input"));
        if (status) {
          status.textContent =
            "Set to " + suggested + ". Found " + ncs.length +
            " naming context(s).";
        }
      })
      .catch(function (err) {
        if (status) status.textContent = "Detection failed: " + err;
      });
  }

  function findStatus(picker) {
    var statusId = picker.id.replace(/-picker$/, "-status");
    return document.querySelector("[data-status='" + statusId + "']");
  }

  function initPicker(picker) {
    var targetId = picker.getAttribute("data-target");
    var current = parseLines(textareaValue(targetId));
    populatePicker(picker, [], current);
    picker.addEventListener("change", function () {
      syncTextareaFromPicker(picker);
    });
  }

  // Wire up the three multi-select pickers.
  ["f-users-oc-picker", "f-groups-oc-picker",
   "f-users-extgroups-picker"].forEach(function (id) {
    var picker = document.getElementById(id);
    if (picker) initPicker(picker);
  });

  // Object-class discovery buttons.
  document.querySelectorAll("[data-action='discover-oc']")
    .forEach(function (btn) {
      btn.addEventListener("click", function () {
        var picker = document.getElementById(btn.getAttribute("data-picker"));
        if (!picker) return;
        var status = findStatus(picker);
        if (status) discoverObjectClasses(picker, status);
      });
    });

  // Group discovery buttons.
  document.querySelectorAll("[data-action='discover-groups']")
    .forEach(function (btn) {
      btn.addEventListener("click", function () {
        var picker = document.getElementById(btn.getAttribute("data-picker"));
        if (!picker) return;
        var status = findStatus(picker);
        if (status) discoverGroups(picker, status);
      });
    });

  // Base-DN detect buttons.
  document.querySelectorAll("[data-action='detect-basedn']")
    .forEach(function (btn) {
      btn.addEventListener("click", function () { detectBaseDn(btn); });
    });

  // Mirror Users → Groups: when the Groups base DN is empty and the
  // Users base DN is filled, derive a sensible Groups base by
  // replacing "ou=people" with "ou=groups".
  (function () {
    var usersInput = document.getElementById("f-users-basedn");
    var groupsInput = document.getElementById("f-groups-basedn");
    if (!usersInput || !groupsInput) return;
    usersInput.addEventListener("blur", function () {
      if (groupsInput.value.trim()) return;
      var u = usersInput.value.trim();
      if (!u) return;
      var suggested = u.replace(/^ou=people,/i, "ou=groups,");
      if (suggested !== u) groupsInput.value = suggested;
    });
  })();

  // "edit raw" links: reveal the underlying textarea.
  document.querySelectorAll("a.reveal-textarea")
    .forEach(function (link) {
      link.addEventListener("click", function (ev) {
        ev.preventDefault();
        var id = link.getAttribute("data-target");
        var ta = document.getElementById(id);
        if (ta) ta.classList.toggle("d-none");
      });
    });

  // ---- Live filter preview ----
  function buildFilter(which) {
    var ocId = "f-" + which + "-oc";
    var queryId = which === "users" ? "f-users-query" : "f-groups-query";
    var ocs = parseLines(textareaValue(ocId));
    var query = (document.getElementById(queryId) || {}).value || "";
    query = query.trim();

    var ocPart = "";
    if (ocs.length === 1) {
      ocPart = "(objectClass=" + ocs[0] + ")";
    } else if (ocs.length > 1) {
      ocPart = "(|" + ocs.map(function (oc) {
        return "(objectClass=" + oc + ")";
      }).join("") + ")";
    }

    if (ocPart && query) return "(&" + ocPart + query + ")";
    return ocPart || query || "(objectClass=*)";
  }

  function updatePreviews() {
    document.querySelectorAll("[data-filter-preview]")
      .forEach(function (el) {
        var which = el.getAttribute("data-filter-preview");
        el.textContent = buildFilter(which);
      });
  }

  ["f-users-oc", "f-users-query",
   "f-groups-oc", "f-groups-query"].forEach(function (id) {
    var el = document.getElementById(id);
    if (el) {
      el.addEventListener("input", updatePreviews);
      el.addEventListener("change", updatePreviews);
    }
  });
  updatePreviews();

  // ---- Live connection status dot on the Server tab ----
  //
  // Probe @@senaite_ldap_status on load and colour the dot green
  // (connected) or red (error). On a fetch failure, leave the dot
  // in its default state and surface the error via the title
  // tooltip.
  (function () {
    var dot = document.querySelector("a[href='#tab-server'] .conn-dot");
    if (!dot) return;
    dot.title = "Checking…";
    fetch(BASE_URL + "/@@senaite_ldap_status",
          { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        dot.classList.remove("is-on", "is-off", "is-bad");
        if (data.ok) {
          dot.classList.add("is-on");
          dot.title = "Connected" +
            (data.message ? " — " + data.message : "");
        } else {
          dot.classList.add("is-bad");
          dot.title = "Not connected" +
            (data.message ? " — " + data.message : "");
        }
      })
      .catch(function (err) {
        dot.classList.remove("is-on", "is-off", "is-bad");
        dot.classList.add("is-bad");
        dot.title = "Status check failed: " + err;
      });
  })();

  // ====================================================================
  // 2) LDAP search / inspector (Search tab)
  // ====================================================================
  //
  // DOM is built via createElement throughout so the file would still
  // load fine even if it ever got inlined into a Chameleon template.

  window.ldapSearch = {

    onBaseChange: function () {
      var base = document.getElementById("ls-base").value;
      var input = document.getElementById("ls-base-dn");
      if (base === "users") {
        input.value = USERS_BASE;
        input.disabled = true;
      } else if (base === "groups") {
        input.value = GROUPS_BASE;
        input.disabled = true;
      } else {
        input.disabled = false;
        input.focus();
      }
    },

    setStatus: function (msg, level) {
      var status = document.getElementById("ls-status");
      while (status.firstChild) status.removeChild(status.firstChild);
      if (!msg) return;
      var div = document.createElement("div");
      div.className = "alert alert-" + (level || "info") + " py-2 mb-0";
      div.textContent = msg;
      status.appendChild(div);
    },

    run: function () {
      var base = document.getElementById("ls-base").value;
      var baseDn = document.getElementById("ls-base-dn").value;
      var filter = document.getElementById("ls-filter").value;
      var scope = document.getElementById("ls-scope").value;

      var url = BASE_URL + "/@@senaite_ldapsearch_results"
              + "?base=" + encodeURIComponent(base)
              + "&base_dn=" + encodeURIComponent(baseDn)
              + "&filter=" + encodeURIComponent(filter)
              + "&scope=" + encodeURIComponent(scope);

      this.setStatus("Searching…", "secondary");

      var self = this;
      fetch(url, { credentials: "same-origin" })
        .then(function (r) { return r.json(); })
        .then(function (data) { self.render(data); })
        .catch(function (err) {
          self.setStatus("Request failed: " + err, "danger");
        });
    },

    render: function (data) {
      var table = document.getElementById("ls-results");
      var tbody = table.querySelector("tbody");
      while (tbody.firstChild) tbody.removeChild(tbody.firstChild);

      if (!data.ok) {
        this.setStatus(data.error || "Unknown error", "danger");
        table.classList.add("d-none");
        return;
      }

      var msg = data.count + " result" +
                (data.count === 1 ? "" : "s") +
                " from " + data.base;
      if (data.truncated) msg += " (truncated)";
      this.setStatus(msg, data.count ? "info" : "secondary");

      if (data.count === 0) {
        table.classList.add("d-none");
        return;
      }

      for (var i = 0; i < data.dns.length; i++) {
        var dn = data.dns[i];
        // Defensive: if the server slipped a (dn, attrs) tuple
        // through, JSON-encodes it as an array — pick the DN element
        // so textContent doesn't render ",[object Object]".
        if (Array.isArray(dn)) dn = String(dn[0] != null ? dn[0] : "");
        var tr = document.createElement("tr");
        tr.className = "result-row";
        tr.setAttribute("data-dn", dn);
        var td = document.createElement("td");
        td.className = "text-monospace";
        td.textContent = dn;
        tr.appendChild(td);
        tr.addEventListener("click", this.toggleRow.bind(this, tr));
        tbody.appendChild(tr);
      }
      table.classList.remove("d-none");
    },

    toggleRow: function (tr, event) {
      if (event && event.target.closest(".attrs-cell")) return;
      var next = tr.nextElementSibling;
      if (next && next.classList.contains("attrs-row")) {
        tr.classList.remove("is-open");
        next.remove();
        return;
      }
      tr.classList.add("is-open");
      var base = document.getElementById("ls-base").value;
      var dn = tr.getAttribute("data-dn");
      var url = BASE_URL + "/@@senaite_ldapsearch_attrs"
              + "?base=" + encodeURIComponent(base)
              + "&dn=" + encodeURIComponent(dn);

      var attrTr = document.createElement("tr");
      attrTr.className = "attrs-row";
      var attrTd = document.createElement("td");
      attrTd.className = "attrs-cell";
      attrTd.textContent = "Loading…";
      attrTr.appendChild(attrTd);
      tr.parentNode.insertBefore(attrTr, tr.nextSibling);

      fetch(url, { credentials: "same-origin" })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          while (attrTd.firstChild) attrTd.removeChild(attrTd.firstChild);
          attrTd.appendChild(buildAttrsBlock(data));
        })
        .catch(function (err) {
          attrTd.textContent = "Failed: " + err;
        });
    }
  };

  function buildAttrsBlock(data) {
    if (!data.ok) {
      var span = document.createElement("span");
      span.className = "text-danger";
      span.textContent = data.error || "Unknown error";
      return span;
    }
    var attrs = data.attrs || {};
    var keys = Object.keys(attrs).sort();
    if (keys.length === 0) {
      var em = document.createElement("em");
      em.className = "text-muted";
      em.textContent = "No attributes";
      return em;
    }
    var table = document.createElement("table");
    table.className = "attrs-table";
    keys.forEach(function (key) {
      var tr = document.createElement("tr");
      var th = document.createElement("th");
      th.textContent = key;
      tr.appendChild(th);
      var td = document.createElement("td");
      var val = attrs[key];
      if (Array.isArray(val)) {
        val.forEach(function (v, i) {
          if (i > 0) td.appendChild(document.createElement("br"));
          td.appendChild(document.createTextNode(v));
        });
      } else {
        td.textContent = val;
      }
      tr.appendChild(td);
      table.appendChild(tr);
    });
    return table;
  }

  // ====================================================================
  // Shared DOM / fetch helpers (used by modules 3 and 4 below)
  // ====================================================================

  function clearChildren(node) {
    if (!node) return;
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  function setStatus(selector, text) {
    var el = document.querySelector(selector);
    if (el) el.textContent = text;
  }

  function fetchJSON(url, opts) {
    var options = { credentials: "same-origin" };
    if (opts && opts.method) options.method = opts.method;
    return fetch(url, options).then(function (r) { return r.json(); });
  }

  // ====================================================================
  // 3) Cache insights + purge (Cache tab)
  // ====================================================================

  var CACHE_STATUS = "[data-status='cache-status']";
  var STAT_LABELS = {
    version: "Server version",
    uptime: "Uptime",
    curr_items: "Items",
    total_items: "Total items written",
    bytes: "Bytes used",
    limit_maxbytes: "Bytes available",
    cmd_get: "GET commands",
    cmd_set: "SET commands",
    get_hits: "Hits",
    get_misses: "Misses",
    hit_rate: "Hit rate",
    evictions: "Evictions",
    curr_connections: "Connections"
  };

  function formatUptime(seconds) {
    var s = Number(seconds);
    if (!isFinite(s)) return String(seconds);
    var d = Math.floor(s / 86400);
    var h = Math.floor((s % 86400) / 3600);
    var m = Math.floor((s % 3600) / 60);
    var parts = [];
    if (d) parts.push(d + "d");
    if (h) parts.push(h + "h");
    if (m) parts.push(m + "m");
    if (!parts.length) parts.push((s % 60) + "s");
    return parts.join(" ");
  }

  function formatBytes(n) {
    var units = ["B", "KiB", "MiB", "GiB", "TiB"];
    var v = Number(n);
    if (!isFinite(v)) return String(n);
    var i = 0;
    while (v >= 1024 && i < units.length - 1) {
      v /= 1024;
      i += 1;
    }
    return v.toFixed(i === 0 ? 0 : 1) + " " + units[i];
  }

  // Dispatch table keeps formatStat flat: one entry per key that
  // needs special rendering, default falls through to toLocaleString
  // for numbers and String() for the rest.
  var STAT_FORMATTERS = {
    uptime: formatUptime,
    bytes: formatBytes,
    limit_maxbytes: formatBytes,
    hit_rate: function (v) { return (v * 100).toFixed(1) + "%"; }
  };

  function formatStat(key, value) {
    if (value == null) return "";
    var fmt = STAT_FORMATTERS[key];
    if (fmt) return fmt(value);
    if (typeof value === "number") return value.toLocaleString();
    return String(value);
  }

  function setCacheSectionVisible(visible) {
    var section = document.getElementById("cache-status-section");
    if (section) section.style.display = visible ? "" : "none";
  }

  function renderCacheStats(data) {
    var panel = document.getElementById("cache-stats-panel");
    if (!panel) return;
    clearChildren(panel);

    // Hide the whole Cache status block when memcache isn't in use —
    // no point showing an empty table or a "not configured" notice.
    if (!data.configured || !data.cache_enabled) {
      setCacheSectionVisible(false);
      return;
    }
    setCacheSectionVisible(true);

    if (!data.servers || data.servers.length === 0) {
      panel.appendChild(makeMutedText("No servers reported."));
      return;
    }
    data.servers.forEach(function (srv) {
      panel.appendChild(renderServerCard(srv));
    });
  }

  function makeMutedText(text) {
    var p = document.createElement("p");
    p.className = "text-muted small mb-0";
    p.textContent = text;
    return p;
  }

  function renderServerCardHeader(srv) {
    var header = document.createElement("div");
    header.className = "card-header py-2 d-flex align-items-center";
    var name = document.createElement("span");
    name.className = "text-monospace mr-2";
    name.textContent = srv.name;
    header.appendChild(name);
    var badge = document.createElement("span");
    badge.className = "badge " +
      (srv.ok ? "badge-success" : "badge-danger");
    badge.textContent = srv.ok ? "reachable" : "unreachable";
    header.appendChild(badge);
    return header;
  }

  function renderStatRow(key, value) {
    var tr = document.createElement("tr");
    var th = document.createElement("th");
    th.className = "pl-3";
    th.style.width = "12rem";
    th.textContent = STAT_LABELS[key];
    tr.appendChild(th);
    var td = document.createElement("td");
    td.className = "text-monospace";
    td.textContent = formatStat(key, value);
    tr.appendChild(td);
    return tr;
  }

  function renderStatsTable(stats) {
    var table = document.createElement("table");
    table.className = "table table-sm mb-0";
    Object.keys(STAT_LABELS).forEach(function (key) {
      if (key in stats) table.appendChild(renderStatRow(key, stats[key]));
    });
    return table;
  }

  function renderServerCard(srv) {
    var card = document.createElement("div");
    card.className = "card mb-2";
    card.appendChild(renderServerCardHeader(srv));

    var hasStats = srv.ok && srv.stats &&
                   Object.keys(srv.stats).length > 0;
    if (!hasStats) {
      var body = document.createElement("div");
      body.className = "card-body py-2 text-muted small";
      body.textContent = srv.ok ?
        "Reachable but reported no stats." :
        "Could not contact this server.";
      card.appendChild(body);
      return card;
    }
    card.appendChild(renderStatsTable(srv.stats));
    return card;
  }

  function loadCacheStats() {
    setStatus(CACHE_STATUS, "Loading…");
    fetchJSON(BASE_URL + "/@@senaite_ldap_cache_stats")
      .then(function (data) {
        setStatus(CACHE_STATUS, "");
        renderCacheStats(data);
      })
      .catch(function (err) {
        setStatus(CACHE_STATUS, "Stats failed: " + err);
      });
  }

  function flushCache() {
    if (!window.confirm(
        "Purge ALL keys from the configured memcached? Every cached " +
        "LDAP lookup will be evicted; the next request rebuilds the " +
        "cache from scratch.")) {
      return;
    }
    setStatus(CACHE_STATUS, "Purging…");
    fetchJSON(BASE_URL + "/@@senaite_ldap_cache_flush", { method: "POST" })
      .then(function (data) {
        setStatus(CACHE_STATUS, data.message || "");
        if (data.ok) loadCacheStats();
      })
      .catch(function (err) {
        setStatus(CACHE_STATUS, "Purge failed: " + err);
      });
  }

  function bindCacheActions() {
    document.querySelectorAll("[data-action='cache-refresh']")
      .forEach(function (btn) {
        btn.addEventListener("click", loadCacheStats);
      });
    document.querySelectorAll("[data-action='cache-flush']")
      .forEach(function (btn) {
        btn.addEventListener("click", flushCache);
      });
  }

  bindCacheActions();

  // Always load once on page init: the stats response also drives
  // section visibility, so we need it even when the Cache tab isn't
  // the active one (e.g. restored from sticky tab state, where no
  // click / shown.bs.tab fires).
  if (document.querySelector("[href='#tab-cache']")) {
    loadCacheStats();
  }

  // ====================================================================
  // 4) Sticky active tab across reloads via ?tab= URL parameter
  // ====================================================================

  // Whitelist the characters allowed in a tab id so a hostile ?tab=
  // value can't break the CSS selector below (`querySelector` throws
  // on a malformed selector and would abort the IIFE init).
  var TAB_ID_RE = /^[A-Za-z0-9_-]+$/;

  var tabLinks = document.querySelectorAll(
    ".senaite-ldap-form .nav-tabs a.nav-link[data-toggle='tab']");

  function deactivateAllTabs() {
    tabLinks.forEach(function (l) { l.classList.remove("active"); });
    document.querySelectorAll(".senaite-ldap-form .tab-pane")
      .forEach(function (p) { p.classList.remove("active", "show"); });
  }

  function activateTab(href) {
    var link = document.querySelector(
      ".senaite-ldap-form .nav-tabs a.nav-link[href='" + href + "']");
    if (!link) return;

    // Prefer Bootstrap's own tab plugin when jQuery is present:
    // it keeps internal state (aria-selected, focus, shown.bs.tab)
    // in sync. Manual class toggling alone leaves the nav-link
    // visually inactive even though the pane shows.
    var $ = window.jQuery;
    if ($ && typeof $(link).tab === "function") {
      $(link).tab("show");
      return;
    }

    var pane = document.querySelector(".senaite-ldap-form " + href);
    if (!pane) return;
    deactivateAllTabs();
    link.classList.add("active");
    pane.classList.add("active", "show");
  }

  function recordTabInUrl(href) {
    var url = new URL(window.location.href);
    url.searchParams.set("tab", href.replace(/^#/, ""));
    window.history.replaceState({}, "", url.toString());
  }

  tabLinks.forEach(function (link) {
    link.addEventListener("click", function () {
      var href = link.getAttribute("href");
      if (href) recordTabInUrl(href);
    });
  });

  var urlTab = new URL(window.location.href).searchParams.get("tab");
  if (urlTab && TAB_ID_RE.test(urlTab)) activateTab("#" + urlTab);
})();
