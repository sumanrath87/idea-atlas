/* IDEA Atlas: search, map, and table. Plain JavaScript, no outside requests. */
(function () {
  "use strict";
  var BASE = "/tools/idea-atlas/";
  var COLORS = ["#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"]; // one hue, light to dark
  var NODATA = "#dcd9d0";
  var STATES = {"01":["AL","Alabama"],"02":["AK","Alaska"],"04":["AZ","Arizona"],"05":["AR","Arkansas"],"06":["CA","California"],"08":["CO","Colorado"],"09":["CT","Connecticut"],"10":["DE","Delaware"],"11":["DC","District of Columbia"],"12":["FL","Florida"],"13":["GA","Georgia"],"15":["HI","Hawaii"],"16":["ID","Idaho"],"17":["IL","Illinois"],"18":["IN","Indiana"],"19":["IA","Iowa"],"20":["KS","Kansas"],"21":["KY","Kentucky"],"22":["LA","Louisiana"],"23":["ME","Maine"],"24":["MD","Maryland"],"25":["MA","Massachusetts"],"26":["MI","Michigan"],"27":["MN","Minnesota"],"28":["MS","Mississippi"],"29":["MO","Missouri"],"30":["MT","Montana"],"31":["NE","Nebraska"],"32":["NV","Nevada"],"33":["NH","New Hampshire"],"34":["NJ","New Jersey"],"35":["NM","New Mexico"],"36":["NY","New York"],"37":["NC","North Carolina"],"38":["ND","North Dakota"],"39":["OH","Ohio"],"40":["OK","Oklahoma"],"41":["OR","Oregon"],"42":["PA","Pennsylvania"],"44":["RI","Rhode Island"],"45":["SC","South Carolina"],"46":["SD","South Dakota"],"47":["TN","Tennessee"],"48":["TX","Texas"],"49":["UT","Utah"],"50":["VT","Vermont"],"51":["VA","Virginia"],"53":["WA","Washington"],"54":["WV","West Virginia"],"55":["WI","Wisconsin"],"56":["WY","Wyoming"],"60":["AS","American Samoa"],"66":["GU","Guam"],"69":["MP","Northern Mariana Islands"],"72":["PR","Puerto Rico"],"78":["VI","U.S. Virgin Islands"]};
  var ABBR = {}; Object.keys(STATES).forEach(function (f) { ABBR[STATES[f][0]] = STATES[f][1]; });

  var DATA = null, INDEX = {};
  function load() {
    if (DATA) return Promise.resolve(DATA);
    return fetch(BASE + "data/values.json").then(function (r) { return r.json(); }).then(function (d) {
      DATA = d; d.ids.forEach(function (id, i) { INDEX[id] = i; });
      d.checkSet = {}; d.check.forEach(function (i) { d.checkSet[i] = true; });
      return d;
    });
  }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]; }); }
  function fmt(v, unit) {
    if (v == null) return "";
    return unit === "usd" ? "$" + Math.round(v).toLocaleString("en-US") : Number(v).toLocaleString("en-US", {minimumFractionDigits: 1, maximumFractionDigits: 1});
  }
  function cellText(i, m) {
    var mi = DATA.measures.indexOf(m), code = DATA.codes[i].charAt(mi), v = DATA.values[i][mi];
    if (code === "0") return fmt(v, m.unit);
    if (code === "1") return "at least " + fmt(v, m.unit);
    return DATA.status[code] || "Not reported";
  }
  function place(i) { var n = DATA.names[i]; return (n[2] ? n[2] + ", " : "") + n[1]; }

  /* ------------------------------------------------------------ search */
  function initSearch() {
    var form = document.getElementById("search-form"); if (!form) return;
    var out = document.getElementById("results"), q = document.getElementById("q");
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var text = q.value.trim();
      if (!text) { out.innerHTML = "<p>Please type a ZIP code or a district name.</p>"; return; }
      out.innerHTML = "<p>Searching…</p>";
      load().then(function () {
        if (/^\d{5}$/.test(text)) return zipSearch(text, out);
        nameSearch(text, out);
      }).catch(function () { out.innerHTML = "<p>Sorry, the data could not be loaded. Please try again.</p>"; });
    });
  }
  function listHTML(items, intro) {
    return "<h3>" + esc(intro) + "</h3><ul>" + items.map(function (it) {
      var i = it.i;
      return "<li><a href=\"" + BASE + "district/" + DATA.ids[i] + "/\">" + esc(DATA.names[i][0]) + "</a><div class=\"sub\">" +
        esc(place(i)) + (DATA.enrollment[i] != null ? " · " + DATA.enrollment[i].toLocaleString("en-US") + " students" : "") +
        (it.note ? " · " + esc(it.note) : "") + "</div></li>";
    }).join("") + "</ul>";
  }
  function zipSearch(zip, out) {
    return fetch(BASE + "data/zip/" + zip.slice(0, 2) + ".json").then(function (r) { return r.ok ? r.json() : {}; }).then(function (z) {
      var rows = (z[zip] || []).filter(function (x) { return x[0] in INDEX; });
      if (!rows.length) { out.innerHTML = "<p>No school district was found for ZIP code " + esc(zip) + ". Try the district name instead.</p>"; return; }
      var items = rows.map(function (x, k) {
        var note = rows.length > 1 && x[1] != null ? (k === 0 ? "covers the most of this ZIP code" : "covers part of this ZIP code") : "";
        return {i: INDEX[x[0]], note: note};
      });
      out.innerHTML = listHTML(items, items.length === 1 ? "1 district serves ZIP code " + zip : items.length + " districts serve parts of ZIP code " + zip);
    });
  }
  function norm(s) { return s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9 ]/g, " ").replace(/\s+/g, " ").trim(); }
  function nameSearch(text, out) {
    var words = norm(text).split(" "), hits = [];
    for (var i = 0; i < DATA.ids.length; i++) {
      var hay = norm(DATA.names[i][0] + " " + DATA.names[i][2] + " " + DATA.names[i][1]);
      if (words.every(function (w) { return hay.indexOf(w) >= 0; })) {
        var score = (norm(DATA.names[i][0]).indexOf(words[0]) === 0 ? 0 : 1);
        hits.push({i: i, s: score, e: -(DATA.enrollment[i] || 0)});
      }
    }
    hits.sort(function (a, b) { return a.s - b.s || a.e - b.e; });
    if (!hits.length) { out.innerHTML = "<p>No district matched “" + esc(text) + "”. Check the spelling, or try a ZIP code.</p>"; return; }
    var shown = hits.slice(0, 25);
    out.innerHTML = listHTML(shown, hits.length > 25 ? hits.length + " districts matched; showing the 25 largest" : (hits.length === 1 ? "1 district matched" : hits.length + " districts matched"));
  }

  /* ------------------------------------------------------------ map */
  function initMap() {
    var el = document.getElementById("map"); if (!el || !window.maplibregl) return;
    var sel = document.getElementById("measure"), stSel = document.getElementById("zoom-state"), hs = document.getElementById("hs-layer");
    var legend = document.getElementById("legend-list"), note = document.getElementById("measure-note"), live = document.getElementById("map-status");
    Object.keys(STATES).sort(function (a, b) { return STATES[a][1].localeCompare(STATES[b][1]); }).forEach(function (f) {
      var o = document.createElement("option"); o.value = f; o.textContent = STATES[f][1]; stSel.appendChild(o);
    });
    el.removeAttribute("tabindex");
    var map = new maplibregl.Map({
      container: el, center: [-96, 38.5], zoom: 3.3, minZoom: 2, maxZoom: 11, attributionControl: false,
      style: {version: 8, sources: {}, layers: [{id: "bg", type: "background", paint: {"background-color": "#f3f1ea"}}]}
    });
    map.addControl(new maplibregl.NavigationControl({showCompass: false}), "top-right");
    map.getCanvas().setAttribute("aria-label", "Map of school districts. Use arrow keys to move and plus or minus to zoom. The table page lists the same figures.");
    var fill = ["match", ["coalesce", ["feature-state", "c"], -1], 0, COLORS[0], 1, COLORS[1], 2, COLORS[2], 3, COLORS[3], 4, COLORS[4], NODATA];

    Promise.all([load(), new Promise(function (res) { map.on("load", res); })]).then(function () {
      DATA.measures.filter(function (m) { return m.map; }).reduce(function (groups, m) {
        var g = groups[m.group] || (groups[m.group] = document.createElement("optgroup"));
        g.label = m.group; var o = document.createElement("option"); o.value = m.key; o.textContent = m.short; g.appendChild(o);
        if (!g.parentNode) sel.appendChild(g); return groups;
      }, {});
      map.addSource("base", {type: "geojson", data: BASE + "data/base.json", promoteId: "id"});
      map.addSource("hs", {type: "geojson", data: BASE + "data/s.json", promoteId: "id"});
      map.addSource("states", {type: "geojson", data: BASE + "data/states.json"});
      map.addLayer({id: "base-fill", type: "fill", source: "base", paint: {"fill-color": fill, "fill-opacity": 0.92}});
      map.addLayer({id: "hs-fill", type: "fill", source: "hs", layout: {visibility: "none"}, paint: {"fill-color": fill, "fill-opacity": 0.92}});
      map.addLayer({id: "base-line", type: "line", source: "base", paint: {"line-color": "#ffffff", "line-width": ["interpolate", ["linear"], ["zoom"], 3, 0.15, 8, 1]}});
      map.addLayer({id: "hs-line", type: "line", source: "hs", layout: {visibility: "none"}, paint: {"line-color": "#ffffff", "line-width": ["interpolate", ["linear"], ["zoom"], 3, 0.2, 8, 1]}});
      map.addLayer({id: "state-line", type: "line", source: "states", paint: {"line-color": "#474d55", "line-width": ["interpolate", ["linear"], ["zoom"], 3, 0.6, 8, 1.6]}});
      map.addLayer({id: "hover", type: "line", source: "base", paint: {"line-color": "#1d2126", "line-width": 2}, filter: ["==", ["get", "id"], ""]});
      map.once("idle", paint);
      sel.addEventListener("change", paint);
      hs.addEventListener("change", function () {
        var on = hs.checked;
        map.setLayoutProperty("hs-fill", "visibility", on ? "visible" : "none");
        map.setLayoutProperty("hs-line", "visibility", on ? "visible" : "none");
        live.textContent = on ? "High school districts are shown on top." : "High school districts are hidden.";
      });
      stSel.addEventListener("change", function () { zoomState(map, stSel.value); });
    });

    function measure() { return DATA.measures.filter(function (m) { return m.key === sel.value; })[0]; }
    function classOf(v, br) { if (v == null) return -1; var c = 0; for (var k = 0; k < br.length; k++) if (v > br[k]) c++; return Math.min(c, 4); }
    function paint() {
      if (!DATA || !map.getSource("base")) return;
      var m = measure(), mi = DATA.measures.indexOf(m), br = m.breaks;
      DATA.ids.forEach(function (id, i) {
        var code = DATA.codes[i].charAt(mi), v = code === "0" || code === "1" ? DATA.values[i][mi] : null;
        var st = {c: classOf(v, br)};
        try { map.setFeatureState({source: "base", id: id}, st); map.setFeatureState({source: "hs", id: id}, st); } catch (e) { /* no shape */ }
      });
      var labels = [], lo = null;
      if (br[0] === 0) { labels.push("0"); for (var k = 1; k <= br.length; k++) labels.push(k < br.length ? "Above " + (k === 1 ? "0" : fmt(br[k - 1], m.unit)) + " to " + fmt(br[k], m.unit) : "Above " + fmt(br[k - 1], m.unit)); }
      else { for (var j = 0; j <= br.length; j++) labels.push(j === 0 ? fmt(br[0], m.unit) + " or less" : j < br.length ? "Above " + fmt(br[j - 1], m.unit) + " to " + fmt(br[j], m.unit) : "Above " + fmt(br[j - 1], m.unit)); }
      legend.innerHTML = labels.map(function (t, k) { return "<li><span class=\"swatch\" style=\"background:" + COLORS[k] + "\"></span>" + esc(t) + "</li>"; }).join("") +
        "<li><span class=\"swatch nodata\"></span>No figure (withheld, fewer than 10 students, or not reported)</li>";
      note.textContent = m.label + (m.unit === "usd" ? " (dollars). " : ". ") + "Group: " + m.den + " Source: " + m.source + "." +
        (m.national_median != null ? " National median: " + fmt(m.national_median, m.unit) + "." : "");
      live.textContent = "Map now shows " + m.short + ".";
    }
    var popup = new maplibregl.Popup({closeButton: false, closeOnClick: false, offset: 8});
    function popupHTML(id, link) {
      var i = INDEX[id]; if (i == null) return null;
      var m = measure();
      return "<strong>" + esc(DATA.names[i][0]) + "</strong>" + esc(m.short) + ": " + esc(cellText(i, m)) +
        (link ? "<br><a href=\"" + BASE + "district/" + id + "/\">Open district profile</a>" : "");
    }
    ["base-fill", "hs-fill"].forEach(function (layer) {
      map.on("mousemove", layer, function (e) {
        var f = e.features && e.features[0]; if (!f) return;
        map.getCanvas().style.cursor = "pointer";
        var h = popupHTML(f.properties.id, false); if (!h) return;
        popup.setLngLat(e.lngLat).setHTML(h).addTo(map);
        map.setFilter("hover", ["==", ["get", "id"], f.properties.id]);
      });
      map.on("mouseleave", layer, function () { map.getCanvas().style.cursor = ""; popup.remove(); map.setFilter("hover", ["==", ["get", "id"], ""]); });
      map.on("click", layer, function (e) {
        var f = e.features && e.features[0]; if (!f) return;
        var h = popupHTML(f.properties.id, true); if (!h) return;
        new maplibregl.Popup({offset: 8}).setLngLat(e.lngLat).setHTML(h).addTo(map);
      });
    });
  }
  function zoomState(map, fips) {
    if (!fips) { map.flyTo({center: [-96, 38.5], zoom: 3.3}); return; }
    zoomState.cache = zoomState.cache || fetch(BASE + "data/states.json").then(function (r) { return r.json(); });
    zoomState.cache.then(function (gj) {
      var f = (gj.features || []).filter(function (x) { return x.properties.st === fips; })[0]; if (!f) return;
      var b = [180, 90, -180, -90];
      (function walk(c) { if (typeof c[0] === "number") { if (fips === "02" && c[0] > 0) c = [c[0] - 360, c[1]]; b[0] = Math.min(b[0], c[0]); b[1] = Math.min(b[1], c[1]); b[2] = Math.max(b[2], c[0]); b[3] = Math.max(b[3], c[1]); } else c.forEach(walk); })(f.geometry.coordinates);
      map.fitBounds([[b[0], b[1]], [b[2], b[3]]], {padding: 24, duration: 600});
    });
  }

  /* ------------------------------------------------------------ table */
  function initTable() {
    var stSel = document.getElementById("t-state"); if (!stSel) return;
    var gSel = document.getElementById("t-group"), filt = document.getElementById("t-filter"), dl = document.getElementById("t-download");
    var wrap = document.getElementById("t-wrap"), table = document.getElementById("t-table"), status = document.getElementById("t-status"), cap = document.getElementById("t-caption");
    var sortKey = "name", sortDir = 1, rows = [], cols = [];
    Object.keys(STATES).map(function (f) { return STATES[f]; }).sort(function (a, b) { return a[1].localeCompare(b[1]); }).forEach(function (s) {
      var o = document.createElement("option"); o.value = s[0]; o.textContent = s[1]; stSel.appendChild(o);
    });
    load().then(function () {
      var groups = ["Overview"]; DATA.measures.forEach(function (m) { if (groups.indexOf(m.group) < 0) groups.push(m.group); });
      groups.forEach(function (g) { var o = document.createElement("option"); o.value = g; o.textContent = g; gSel.appendChild(o); });
      var p = new URLSearchParams(location.search);
      if (p.get("state") && ABBR[p.get("state")]) stSel.value = p.get("state");
      if (p.get("topic")) gSel.value = p.get("topic");
      render();
    });
    [stSel, gSel].forEach(function (s) { s.addEventListener("change", function () { sortKey = "name"; sortDir = 1; render(); }); });
    filt.addEventListener("input", function () { draw(); });
    function columns() {
      var g = gSel.value || "Overview";
      var keys = g === "Overview" ? ["id_rate", "pct_504", "env_80plus", "grad_regular", "oos_idea", "spend_per_pupil"] :
        DATA.measures.filter(function (m) { return m.group === g; }).map(function (m) { return m.key; });
      return keys.map(function (k) { return DATA.measures.filter(function (m) { return m.key === k; })[0]; });
    }
    function render() {
      var st = stSel.value;
      history.replaceState(null, "", st ? "?state=" + st + "&topic=" + encodeURIComponent(gSel.value) : location.pathname);
      if (!st) { wrap.hidden = true; dl.disabled = true; status.textContent = "Choose a state to begin."; return; }
      cols = columns();
      rows = []; DATA.ids.forEach(function (id, i) { if (DATA.names[i][1] === st) rows.push(i); });
      var head = "<tr><th scope=\"col\" data-k=\"name\"><button type=\"button\">District</button></th><th scope=\"col\" data-k=\"enr\"><button type=\"button\">Enrollment</button></th>" +
        cols.map(function (m) { return "<th scope=\"col\" data-k=\"" + m.key + "\"><button type=\"button\">" + esc(m.short) + "</button></th>"; }).join("") + "</tr>";
      table.tHead.innerHTML = head;
      Array.prototype.forEach.call(table.tHead.querySelectorAll("th"), function (th) {
        th.querySelector("button").addEventListener("click", function () {
          var k = th.getAttribute("data-k"); sortDir = sortKey === k ? -sortDir : (k === "name" ? 1 : -1); sortKey = k; draw();
          status.textContent = "Sorted by " + th.textContent + (sortDir > 0 ? ", lowest first." : ", highest first.");
        });
      });
      wrap.hidden = false; dl.disabled = false; draw();
    }
    function val(i, k) {
      if (k === "name") return DATA.names[i][0];
      if (k === "enr") return DATA.enrollment[i];
      var mi = DATA.measures.findIndex(function (m) { return m.key === k; }), c = DATA.codes[i].charAt(mi);
      return c === "0" || c === "1" ? DATA.values[i][mi] : null;
    }
    function visible() {
      var f = norm(filt.value || "");
      var list = rows.filter(function (i) { return !f || norm(DATA.names[i][0] + " " + DATA.names[i][2]).indexOf(f) >= 0; });
      return list.sort(function (a, b) {
        var x = val(a, sortKey), y = val(b, sortKey);
        if (x == null && y == null) return 0; if (x == null) return 1; if (y == null) return -1;
        return (typeof x === "string" ? x.localeCompare(y) : x - y) * sortDir;
      });
    }
    function draw() {
      var list = visible(), st = stSel.value;
      Array.prototype.forEach.call(table.tHead.querySelectorAll("th"), function (th) {
        if (th.getAttribute("data-k") === sortKey) th.setAttribute("aria-sort", sortDir > 0 ? "ascending" : "descending"); else th.removeAttribute("aria-sort");
      });
      var html = list.map(function (i) {
        var flag = DATA.checkSet[i] && cols.some(function (m) { return m.group === "Discipline and safety" || m.key === "oos_idea"; }) ? " (check: civil rights count differs)" : "";
        return "<tr><th scope=\"row\"><a href=\"" + BASE + "district/" + DATA.ids[i] + "/\">" + esc(DATA.names[i][0]) + "</a>" + esc(flag) + "</th><td>" +
          (DATA.enrollment[i] != null ? DATA.enrollment[i].toLocaleString("en-US") : "Not reported") + "</td>" +
          cols.map(function (m) { return "<td>" + esc(cellText(i, m)) + "</td>"; }).join("") + "</tr>";
      }).join("");
      table.tBodies[0].innerHTML = html;
      cap.textContent = ABBR[st] + ": " + (gSel.value || "Overview") + ". " + list.length.toLocaleString("en-US") + " districts. Figures per 100 students in each group unless shown in dollars.";
      if (!filt.value) status.textContent = list.length.toLocaleString("en-US") + " districts in " + ABBR[st] + "." + (DATA.state_notes[st] ? " " + DATA.state_notes[st] : "");
      else status.textContent = list.length + " districts match “" + filt.value + "”.";
    }
    dl.addEventListener("click", function () {
      var list = visible();
      var lines = [["District", "NCES ID", "Enrollment"].concat(cols.map(function (m) { return m.label; }))];
      list.forEach(function (i) { lines.push([DATA.names[i][0], DATA.ids[i], DATA.enrollment[i] == null ? "" : DATA.enrollment[i]].concat(cols.map(function (m) { return cellText(i, m); }))); });
      var csv = lines.map(function (r) { return r.map(function (x) { x = String(x); return /[",\n]/.test(x) ? "\"" + x.replace(/"/g, "\"\"") + "\"" : x; }).join(","); }).join("\r\n");
      var a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob(["﻿" + csv], {type: "text/csv"}));
      a.download = "idea-atlas-" + stSel.value + "-" + (gSel.value || "overview").toLowerCase().replace(/\W+/g, "-") + ".csv";
      document.body.appendChild(a); a.click(); a.remove();
      status.textContent = "Download started: " + list.length + " districts.";
    });
  }

  document.addEventListener("DOMContentLoaded", function () { initSearch(); initMap(); initTable(); });
})();
