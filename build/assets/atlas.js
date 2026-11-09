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
      groups.push("All measures", "Choose columns");
      groups.forEach(function (g) { var o = document.createElement("option"); o.value = g; o.textContent = g; gSel.appendChild(o); });
      // column picker: one checkbox per measure, grouped by topic
      var fs = document.getElementById("t-cols");
      var html = "<legend>Choose the columns to show</legend>", grp = "";
      DATA.measures.forEach(function (m) {
        if (m.group !== grp) { if (grp) html += "</div>"; grp = m.group; html += "<div class=\"colgroup\"><p class=\"colgroup-h\">" + esc(grp) + "</p>"; }
        html += "<label><input type=\"checkbox\" value=\"" + m.key + "\"> " + esc(m.short) + "</label>";
      });
      fs.innerHTML = html + "</div><p><button type=\"button\" id=\"t-apply\">Show these columns</button></p>";
      var p = new URLSearchParams(location.search);
      if (p.get("state") && ABBR[p.get("state")]) stSel.value = p.get("state");
      if (p.get("topic")) gSel.value = p.get("topic");
      (p.get("cols") || "").split(",").forEach(function (k) { var c = fs.querySelector("input[value=\"" + k + "\"]"); if (c) c.checked = true; });
      document.getElementById("t-apply").addEventListener("click", function () { sortKey = "name"; sortDir = 1; render(); status.textContent = "Showing " + picked().length + " chosen columns. " + status.textContent; });
      render();
    });
    [stSel, gSel].forEach(function (s) { s.addEventListener("change", function () { sortKey = "name"; sortDir = 1; render(); }); });
    filt.addEventListener("input", function () { draw(); });
    function picked() { return Array.prototype.map.call(document.querySelectorAll("#t-cols input:checked"), function (c) { return c.value; }); }
    function columns() {
      var g = gSel.value || "Overview";
      document.getElementById("t-cols").hidden = g !== "Choose columns";
      var keys = g === "Overview" ? ["id_rate", "pct_504", "env_80plus", "grad_regular", "oos_idea", "spend_per_pupil"] :
        g === "All measures" ? DATA.measures.map(function (m) { return m.key; }) :
        g === "Choose columns" ? (picked().length ? picked() : ["id_rate"]) :
        DATA.measures.filter(function (m) { return m.group === g; }).map(function (m) { return m.key; });
      return keys.map(function (k) { return DATA.measures.filter(function (m) { return m.key === k; })[0]; });
    }
    function render() {
      var st = stSel.value;
      document.getElementById("t-cols").hidden = gSel.value !== "Choose columns";
      history.replaceState(null, "", st ? "?state=" + st + "&topic=" + encodeURIComponent(gSel.value) + (gSel.value === "Choose columns" ? "&cols=" + picked().join(",") : "") : location.pathname);
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

  /* ------------------------------------------------------------ print and detail */
  function initTools() {
    // "Show all detail" opens the numbers and full-detail layers; explainers stay as the reader left them.
    var all = function () { return Array.prototype.slice.call(document.querySelectorAll("details.numbers, details.full, details.kids")); };
    var exp = document.querySelector("[data-expand]");
    if (exp) exp.addEventListener("click", function () {
      var open = exp.textContent.indexOf("Show") === 0;
      all().forEach(function (d) { d.open = open; });
      exp.textContent = open ? "Hide all detail" : "Show all detail";
    });
    var before = null;
    window.addEventListener("beforeprint", function () { before = all().map(function (d) { return d.open; }); all().forEach(function (d) { d.open = true; }); });
    window.addEventListener("afterprint", function () { if (before) all().forEach(function (d, i) { d.open = before[i]; }); });
    Array.prototype.forEach.call(document.querySelectorAll("[data-print]"), function (b) {
      b.addEventListener("click", function () { window.print(); });
    });
  }


  /* ------------------------------------------------------------ charts
     Drawn from small data on each page. Hidden from screen readers: the sentences and tables carry the same figures. */
  var SVGNS = "http://www.w3.org/2000/svg";
  function svgEl(tag, attrs, parent) {
    var e = document.createElementNS(SVGNS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function f1(v, unit) { return v == null ? "" : (unit === "usd" ? "$" + Math.round(v).toLocaleString("en-US") : (+v).toFixed(1)); }
  var SHAPES = ["circle", "square", "diamond", "triangle"];
  var SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#6250d6"];
  function mark(g, shape, x, y, r, fill) {
    if (shape === "circle") return svgEl("circle", { cx: x, cy: y, r: r, fill: fill, stroke: "#fbfaf6", "stroke-width": 2 }, g);
    var p;
    if (shape === "square") p = [[x - r, y - r], [x + r, y - r], [x + r, y + r], [x - r, y + r]];
    else if (shape === "diamond") p = [[x, y - r * 1.25], [x + r * 1.25, y], [x, y + r * 1.25], [x - r * 1.25, y]];
    else p = [[x, y - r * 1.2], [x + r * 1.15, y + r * .9], [x - r * 1.15, y + r * .9]];
    return svgEl("polygon", { points: p.map(function (a) { return a.join(","); }).join(" "), fill: fill, stroke: "#fbfaf6", "stroke-width": 2 }, g);
  }

  // Dot on a range: this district, the middle half of state districts, the state median, and the national median.
  function rangeChart(body, keys, cd, meas) {
    var rowH = 46, top = 8, W = 680, L = 210, R = 600;
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + (top + keys.length * rowH + 4), class: "range", focusable: "false" });
    keys.forEach(function (k, i) {
      var m = meas[k], d = cd.m[k]; if (!m || !d) return;
      var v = d[0], lo = d[2], med = d[3], hi = d[4], nat = d[5];
      var mx = Math.max(v || 0, hi || 0, nat || 0, med || 0) * 1.12 || 1;
      var X = function (x) { return L + (R - L) * Math.max(0, x) / mx; };
      var y = top + i * rowH + rowH / 2, g = svgEl("g", {}, svg);
      svgEl("title", {}, g).textContent = m.short + ": this district " + (v == null ? "not shown" : f1(v, m.unit)) +
        "; " + cd.st + " median " + f1(med, m.unit) + (lo != null ? "; middle half " + f1(lo, m.unit) + " to " + f1(hi, m.unit) : "") + "; national median " + f1(nat, m.unit);
      var lab = svgEl("text", { x: 0, y: y + 4.5, class: "lab" }, g); lab.textContent = m.short;
      svgEl("line", { x1: L, x2: R, y1: y, y2: y, class: "track" }, g);
      if (lo != null && hi != null) svgEl("rect", { x: X(lo), y: y - 6, width: Math.max(3, X(hi) - X(lo)), height: 12, rx: 6, class: "band" }, g);
      if (med != null) svgEl("line", { x1: X(med), x2: X(med), y1: y - 10, y2: y + 10, class: "smed" }, g);
      if (nat != null) svgEl("circle", { cx: X(nat), cy: y, r: 4.5, class: "nat" }, g);
      if (v != null) {
        svgEl("circle", { cx: X(v), cy: y, r: 6.5, class: "dot" }, g);
        var t = svgEl("text", { x: R + 14, y: y + 4.5, class: "val" }, g); t.textContent = (d[1] === "1" ? "≥ " : "") + f1(v, m.unit);
      } else { var n = svgEl("text", { x: R + 14, y: y + 4.5, class: "na" }, g); n.textContent = "Not shown"; }
    });
    body.appendChild(svg);
    body.insertAdjacentHTML("beforebegin", '<ul class="chart-key"><li><span class="k-dot"></span>This district</li><li><span class="k-band"></span>Middle half of ' +
      esc(cd.st) + ' districts</li><li><span class="k-med"></span>' + esc(cd.st) + ' median</li><li><span class="k-nat"></span>National median</li></ul>');
  }

  // One bar split into parts, labelled below with counts and shares.
  function partsBar(body, parts, colors) {
    var total = parts.reduce(function (a, p) { return a + (p[1] || 0); }, 0); if (!total) return false;
    var bar = '<div class="pbar">' + parts.map(function (p, i) {
      var w = 100 * (p[1] || 0) / total; if (!w) return "";
      return '<span style="flex-basis:' + w.toFixed(2) + '%;background:' + colors[i] + '" title="' + esc(p[0]) + ': ' + (100 * p[1] / total).toFixed(1) + ' per 100"></span>';
    }).join("") + "</div>";
    var key = '<ul class="pkey">' + parts.map(function (p, i) {
      if (!p[1]) return "";
      return '<li><span class="sw" style="background:' + colors[i] + '"></span><span class="pl">' + esc(p[0]) + '</span><span class="pv">' +
        (100 * p[1] / total).toFixed(1) + '<small> per 100 · ' + p[1].toLocaleString("en-US") + ' students</small></span></li>';
    }).join("") + "</ul>";
    body.innerHTML = bar + key;
    return true;
  }

  function catsChart(body, cats) {
    if (!cats.length) return false;
    var mx = Math.max.apply(null, cats.map(function (c) { return c[1]; })) || 1;
    body.innerHTML = '<ul class="hbars">' + cats.slice().sort(function (a, b) { return b[1] - a[1]; }).map(function (c) {
      return '<li><span class="hl">' + esc(c[0]) + '</span><span class="ht"><span style="width:' + (100 * c[1] / mx).toFixed(1) + '%"></span></span><span class="hv">' + c[1].toFixed(1) + '</span></li>';
    }).join("") + "</ul>";
    return true;
  }

  // Tables are stored as compact data on district pages and built here as ordinary, fully labelled tables.
  function buildTrendTables(cd) {
    Array.prototype.forEach.call(document.querySelectorAll(".jt-tr[data-k]"), function (slot, n) {
      var k = slot.getAttribute("data-k"), pts = (cd.tr || {})[k]; if (!pts) return;
      var y = slot.getAttribute("data-y"), money = k === "s", id = "ot-" + k;
      var yl = function (v) { return y === "sy" ? v + "–" + String(v + 1).slice(-2) : y === "fy" ? (v - 1) + "–" + String(v).slice(-2) : String(v); };
      var fv = function (v) { return money ? "$" + Math.round(v).toLocaleString("en-US") : (+v).toFixed(1); };
      slot.outerHTML = '<div class="table-wrap" role="region" tabindex="0" aria-labelledby="' + id + '"><table class="profile narrow"><caption id="' + id + '">' +
        esc(slot.getAttribute("data-cap")) + '</caption><thead><tr><th scope="col">Year</th><th scope="col">' + esc(slot.getAttribute("data-label")) +
        "</th></tr></thead><tbody>" + pts.map(function (p) { return '<tr><th scope="row">' + yl(p[0]) + "</th><td>" + fv(p[1]) + "</td></tr>"; }).join("") + "</tbody></table></div>";
    });
  }

  function buildTables(cd) {
    buildTrendTables(cd);
    Array.prototype.forEach.call(document.querySelectorAll(".jt[data-t]"), function (slot) {
      var d = (cd.t || [])[+slot.getAttribute("data-t")]; if (!d) return;
      var h = '<div class="table-wrap" role="region" tabindex="0" aria-labelledby="' + d.id + '"><table class="' + d.k + '"><caption id="' + d.id + '">' + esc(d.c) +
        '</caption><thead><tr>' + d.h.map(function (x) { return '<th scope="col">' + esc(x) + "</th>"; }).join("") + "</tr></thead><tbody>" +
        d.r.map(function (row) { return "<tr><th scope=\"row\">" + esc(row[0]) + "</th>" + row.slice(1).map(function (c) { return "<td>" + esc(c) + "</td>"; }).join("") + "</tr>"; }).join("") +
        "</tbody></table></div>";
      slot.outerHTML = h;
    });
  }
  // Explanations on district pages come from one shared file; until it arrives, each links to the glossary.
  function fillTerms() {
    var ds = document.querySelectorAll("details.explain[data-term]"); if (!ds.length) return;
    fetch(BASE + "data/terms.json").then(function (r) { return r.json(); }).then(function (terms) {
      Array.prototype.forEach.call(ds, function (d) { var k = d.getAttribute("data-term"); if (terms[k]) d.querySelector("p").textContent = terms[k]; });
    }).catch(function () {});
  }

  // History: swap the state chart and its sentence; the full table of every state stays one click away.
  function initHistory() {
    var sel = document.getElementById("h-st"); if (!sel) return;
    var box = document.getElementById("h-st-chart"), say = document.getElementById("h-st-say");
    var base = box.innerHTML, baseSay = say.textContent;
    sel.addEventListener("change", function () {
      var t = sel.value && document.querySelector('template[data-state="' + sel.value.replace(/"/g, '\\"') + '"]');
      box.innerHTML = t ? t.innerHTML : base;
      say.textContent = t ? t.getAttribute("data-say") : baseSay;
    });
  }

  // A district's own line over time: thin line, end values labelled, dashed across missing years.
  function trendChart(body, pts, money) {
    if (!pts || pts.length < 3) return false;
    var W = 640, H = 170, L = 10, R = 80, T = 18, B = 26;
    var x0 = pts[0][0], x1 = pts[pts.length - 1][0];
    var mx = Math.max.apply(null, pts.map(function (p) { return p[1]; })) * 1.15 || 1;
    var X = function (x) { return L + (W - L - R) * (x - x0) / Math.max(1, x1 - x0); };
    var Y = function (v) { return T + (H - T - B) * (1 - v / mx); };
    var fmtv = function (v) { return money ? "$" + Math.round(v).toLocaleString("en-US") : (+v).toFixed(1); };
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, class: "range trend", focusable: "false" });
    svgEl("line", { x1: L, x2: W - R, y1: Y(0), y2: Y(0), class: "track" }, svg);
    var seg = "M" + X(pts[0][0]) + "," + Y(pts[0][1]);
    for (var i = 1; i < pts.length; i++) {
      var a = pts[i - 1], b = pts[i];
      if (b[0] - a[0] > 3) {
        svgEl("path", { d: seg, class: "tline" }, svg);
        svgEl("line", { x1: X(a[0]), y1: Y(a[1]), x2: X(b[0]), y2: Y(b[1]), class: "tgap" }, svg);
        seg = "M" + X(b[0]) + "," + Y(b[1]);
      } else seg += " L" + X(b[0]) + "," + Y(b[1]);
    }
    svgEl("path", { d: seg, class: "tline" }, svg);
    pts.forEach(function (p, i) {
      var lone = (i > 0 && p[0] - pts[i - 1][0] > 3) && (i === pts.length - 1 || pts[i + 1][0] - p[0] > 3);
      if (i === 0 || i === pts.length - 1 || lone) {
        var c = svgEl("circle", { cx: X(p[0]), cy: Y(p[1]), r: (i === 0 || i === pts.length - 1) ? 4.5 : 3, class: "tdot" }, svg);
        svgEl("title", {}, c).textContent = p[0] + ": " + fmtv(p[1]);
      }
    });
    var f = pts[0], l = pts[pts.length - 1];
    var t1 = svgEl("text", { x: X(f[0]), y: Y(f[1]) - 9, class: "val", "text-anchor": "start" }, svg); t1.textContent = fmtv(f[1]);
    var t2 = svgEl("text", { x: X(l[0]) + 10, y: Y(l[1]) + 4.5, class: "val" }, svg); t2.textContent = fmtv(l[1]);
    var y1 = svgEl("text", { x: X(f[0]), y: H - 6, class: "lab", "text-anchor": "start" }, svg); y1.textContent = f[0];
    var y2 = svgEl("text", { x: X(l[0]), y: H - 6, class: "lab", "text-anchor": "end" }, svg); y2.textContent = l[0];
    body.appendChild(svg);
    return true;
  }

  function initCharts() {
    fillTerms();
    var el = document.getElementById("chart-data"); if (!el) return;
    var cd; try { cd = JSON.parse(el.textContent); } catch (e) { return; }
    buildTables(cd);
    fetch(BASE + "data/measures.json").then(function (r) { return r.json(); }).then(function (ms) {
      var meas = {}; ms.forEach(function (m) { meas[m.key] = m; });
      Array.prototype.forEach.call(document.querySelectorAll("figure.chart[data-chart]"), function (fig) {
        var body = fig.querySelector(".chart-body"), kind = fig.getAttribute("data-chart"), ok = true;
        if (kind === "range") rangeChart(body, fig.getAttribute("data-keys").split(","), cd, meas);
        else if (kind === "settings") ok = cd.set ? partsBar(body, [["80% or more of the day", cd.set[0]], ["40% to 79%", cd.set[1]], ["Less than 40%", cd.set[2]],
              ["Separate school, facility, home or hospital", cd.set[3]], ["Other places", cd.set[4]]], ["#0d366b", "#1c5cab", "#3987e5", "#86b6ef", "#b9b4a8"]) : false;
        else if (kind === "exit") ok = cd.ex ? partsBar(body, [["Regular diploma", cd.ex[0]], ["Alternate diploma or certificate", cd.ex[1]], ["Reached the maximum age", cd.ex[2]],
              ["Dropped out", cd.ex[3]], ["Died", cd.ex[4]]], ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]) : false;
        else if (kind === "cats") ok = catsChart(body, cd.cats || []);
        else if (kind === "trend") { var k = fig.getAttribute("data-keys"); ok = trendChart(body, (cd.tr || {})[k], k === "s"); }
        if (!ok) fig.remove();
      });
    });
  }

  // Compare: every chosen district on one scale per measure, with a different shape for each.
  function compareChart(idx) {
    var fig = document.getElementById("c-chart"); if (!fig) return;
    var body = fig.querySelector(".chart-body"); body.innerHTML = "";
    var prev = fig.querySelector(".chart-key"); if (prev) prev.remove();
    if (!idx.length) { fig.hidden = true; return; }
    var rowH = 40, W = 680, L = 210, R = 640, y0 = 6, groups = [], g0 = "";
    DATA.measures.forEach(function (m, j) { if (m.group !== g0) { g0 = m.group; groups.push([m.group, []]); } groups[groups.length - 1][1].push([m, j]); });
    var H = y0 + groups.reduce(function (a, g) { return a + 34 + g[1].length * rowH; }, 0);
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, class: "range", focusable: "false" }), y = y0;
    groups.forEach(function (gr) {
      var h = svgEl("text", { x: 0, y: y + 22, class: "grp" }, svg); h.textContent = gr[0]; y += 34;
      gr[1].forEach(function (mj) {
        var m = mj[0], j = mj[1], cy = y + rowH / 2, g = svgEl("g", {}, svg);
        var vals = idx.map(function (i) { var c = DATA.codes[i][j]; return (c === "0" || c === "1") ? DATA.values[i][j] : null; });
        var mx = Math.max.apply(null, vals.concat([m.national_median || 0]).map(function (x) { return x || 0; })) * 1.1 || 1;
        var X = function (x) { return L + (R - L) * Math.max(0, x) / mx; };
        svgEl("title", {}, g).textContent = m.short + ": " + idx.map(function (i, n) { return DATA.names[i][0] + " " + (vals[n] == null ? "not shown" : f1(vals[n], m.unit)); }).join("; ") + "; national median " + f1(m.national_median, m.unit);
        var t = svgEl("text", { x: 0, y: cy + 4.5, class: "lab" }, g); t.textContent = m.short;
        svgEl("line", { x1: L, x2: R, y1: cy, y2: cy, class: "track" }, g);
        if (m.national_median != null) svgEl("circle", { cx: X(m.national_median), cy: cy, r: 4.5, class: "nat" }, g);
        vals.forEach(function (v, n) { if (v != null) mark(g, SHAPES[n], X(v), cy, 6, SERIES[n]); });
        y += rowH;
      });
    });
    body.appendChild(svg);
    body.insertAdjacentHTML("beforebegin", '<ul class="chart-key">' + idx.map(function (i, n) {
      return '<li><svg viewBox="-8 -8 16 16" width="14" height="14" aria-hidden="true">' + (function () { var tmp = document.createElementNS(SVGNS, "g"); mark(tmp, SHAPES[n], 0, 0, 5.5, SERIES[n]); return tmp.innerHTML; })() + '</svg>' + esc(DATA.names[i][0]) + '</li>';
    }).join("") + '<li><span class="k-nat"></span>National median</li></ul>');
    fig.hidden = false;
  }

  /* ------------------------------------------------------------ compare */
  function initCompare() {
    var form = document.getElementById("c-form"); if (!form) return;
    var q = document.getElementById("c-q"), res = document.getElementById("c-results"), chosenEl = document.getElementById("c-chosen");
    var wrap = document.getElementById("c-wrap"), table = document.getElementById("c-table"), status = document.getElementById("c-status");
    var chosen = [];
    function save() { history.replaceState(null, "", chosen.length ? "?ids=" + chosen.join(",") : location.pathname); }
    function add(id) {
      if (chosen.indexOf(id) >= 0) { status.textContent = DATA.names[INDEX[id]][0] + " is already chosen."; return; }
      if (chosen.length >= 4) { status.textContent = "You can compare up to four districts. Remove one first."; return; }
      chosen.push(id); save(); draw(); res.innerHTML = "";
      status.textContent = DATA.names[INDEX[id]][0] + " added. " + chosen.length + " of 4 chosen.";
      q.value = ""; q.focus();
    }
    function remove(id) {
      chosen = chosen.filter(function (x) { return x !== id; }); save(); draw();
      status.textContent = DATA.names[INDEX[id]][0] + " removed. " + chosen.length + " chosen.";
    }
    function draw() {
      chosenEl.innerHTML = chosen.map(function (id) {
        var i = INDEX[id];
        return "<li><a href=\"" + BASE + "district/" + id + "/\">" + esc(DATA.names[i][0]) + "</a> <span class=\"sub\">" + esc(place(i)) + "</span> " +
          "<button type=\"button\" class=\"link\" data-remove=\"" + id + "\" aria-label=\"Remove " + esc(DATA.names[i][0]) + "\">Remove</button></li>";
      }).join("") || "<li class=\"sub\">None yet.</li>";
      Array.prototype.forEach.call(chosenEl.querySelectorAll("[data-remove]"), function (b) { b.addEventListener("click", function () { remove(b.getAttribute("data-remove")); }); });
      if (!chosen.length) { wrap.hidden = true; compareChart([]); return; }
      var idx = chosen.map(function (id) { return INDEX[id]; });
      compareChart(idx);
      table.tHead.innerHTML = "<tr><th scope=\"col\">Measure</th>" + idx.map(function (i) { return "<th scope=\"col\">" + esc(DATA.names[i][0]) + "<span class=\"sub\"> " + esc(DATA.names[i][1]) + "</span></th>"; }).join("") + "<th scope=\"col\">National median</th></tr>";
      var rows = "<tr><th scope=\"row\">Students enrolled</th>" + idx.map(function (i) { return "<td>" + (DATA.enrollment[i] != null ? DATA.enrollment[i].toLocaleString("en-US") : "Not reported") + "</td>"; }).join("") + "<td>—</td></tr>";
      var group = "";
      DATA.measures.forEach(function (m) {
        if (m.group !== group) { group = m.group; rows += "<tr class=\"group\"><th scope=\"rowgroup\" colspan=\"" + (idx.length + 2) + "\">" + esc(group) + "</th></tr>"; }
        rows += "<tr><th scope=\"row\">" + esc(m.label) + "</th>" + idx.map(function (i) { return "<td>" + esc(cellText(i, m)) + "</td>"; }).join("") +
          "<td>" + (m.national_median != null ? fmt(m.national_median, m.unit) : "—") + "</td></tr>";
      });
      table.tBodies[0].innerHTML = rows;
      document.getElementById("c-caption").textContent = "Side-by-side figures for " + idx.map(function (i) { return DATA.names[i][0]; }).join(", ") + ". Rates per 100 students in each group unless shown in dollars.";
      wrap.hidden = false;
    }
    load().then(function () {
      var p = new URLSearchParams(location.search);
      (p.get("ids") || "").split(",").forEach(function (id) { if (id in INDEX && chosen.length < 4 && chosen.indexOf(id) < 0) chosen.push(id); });
      draw();
      if (chosen.length) status.textContent = chosen.length + " district" + (chosen.length > 1 ? "s" : "") + " chosen." + (chosen.length < 4 ? " You can add up to " + (4 - chosen.length) + " more." : " That is the most you can compare at once.");
    });
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var text = q.value.trim(); if (!text) return;
      load().then(function () {
        var render = function (items, title) {
          if (!items.length) { res.innerHTML = "<p>No district matched. Try another name or ZIP code.</p>"; return; }
          res.innerHTML = "<h3>" + esc(title) + "</h3><ul class=\"pick\">" + items.slice(0, 15).map(function (i) {
            return "<li><button type=\"button\" data-add=\"" + DATA.ids[i] + "\">Add " + esc(DATA.names[i][0]) + "</button> <span class=\"sub\">" + esc(place(i)) + "</span></li>";
          }).join("") + "</ul>";
          Array.prototype.forEach.call(res.querySelectorAll("[data-add]"), function (b) { b.addEventListener("click", function () { add(b.getAttribute("data-add")); }); });
          var first = res.querySelector("button"); if (first) first.focus();
        };
        if (/^\d{5}$/.test(text)) {
          fetch(BASE + "data/zip/" + text.slice(0, 2) + ".json").then(function (r) { return r.ok ? r.json() : {}; }).then(function (z) {
            render((z[text] || []).filter(function (x) { return x[0] in INDEX; }).map(function (x) { return INDEX[x[0]]; }), "Districts serving ZIP code " + text);
          });
        } else {
          var words = norm(text).split(" "), hits = [];
          for (var i = 0; i < DATA.ids.length; i++) {
            var hay = norm(DATA.names[i][0] + " " + DATA.names[i][2] + " " + DATA.names[i][1]);
            if (words.every(function (w) { return hay.indexOf(w) >= 0; })) hits.push(i);
          }
          hits.sort(function (a, b) { return (DATA.enrollment[b] || 0) - (DATA.enrollment[a] || 0); });
          render(hits, hits.length + " matched" + (hits.length > 15 ? "; showing the 15 largest" : ""));
        }
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () { initTools(); initSearch(); initMap(); initTable(); initCompare(); initCharts(); initHistory(); });
})();
