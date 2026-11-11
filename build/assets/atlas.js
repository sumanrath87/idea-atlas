/* IDEA Atlas: search, map, and table. Plain JavaScript, no outside requests. */
(function () {
  "use strict";
  var BASE = "/tools/idea-atlas/";
  // Spanish pages (lang="es") use the same scripts with Spanish words.
  var ES = (document.documentElement.lang || "en") === "es";
  function tr(en, es) { return ES ? es : en; }
  var STATUS_ES = {"at least": "al menos", "Withheld for privacy": "Retenido por privacidad", "Fewer than 10 students": "Menos de 10 estudiantes",
    "Flagged for data quality": "Marcado por calidad de datos", "Not reported": "No se informó", "No students in this group": "No hay estudiantes en este grupo"};
  var COLORS = ["#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"]; // one hue, light to dark
  function MAPDARK() { return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches; }
  function MAPLINE() { return MAPDARK() ? "#16181b" : "#ffffff"; }
  var NODATA = MAPDARK() ? "#3b3e43" : "#dcd9d0";
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
    if (code === "1") return tr("at least ", "al menos ") + fmt(v, m.unit);
    var s_ = DATA.status[code] || "Not reported";
    return ES ? (STATUS_ES[s_] || s_) : s_;
  }
  // Two-letter state codes in words, in the page's language.
  var ST_NAME = {}; Object.keys(STATES).forEach(function (f) { ST_NAME[STATES[f][0]] = STATES[f][1]; });
  ST_NAME.BI = "Bureau of Indian Education";
  var ST_ES = {"New Jersey": "Nueva Jersey", "New York": "Nueva York", "New Mexico": "Nuevo México", "New Hampshire": "Nuevo Hampshire",
    "North Carolina": "Carolina del Norte", "South Carolina": "Carolina del Sur", "North Dakota": "Dakota del Norte", "South Dakota": "Dakota del Sur",
    "Pennsylvania": "Pensilvania", "Louisiana": "Luisiana", "Missouri": "Misuri", "Mississippi": "Misisipi", "West Virginia": "Virginia Occidental",
    "Hawaii": "Hawái", "District of Columbia": "Distrito de Columbia", "Michigan": "Míchigan", "Oregon": "Oregón",
    "Bureau of Indian Education": "Oficina de Educación Indígena", "U.S. Virgin Islands": "Islas Vírgenes de EE. UU.",
    "Northern Mariana Islands": "Islas Marianas del Norte", "American Samoa": "Samoa Estadounidense"};
  function stName(code) { var n = ST_NAME[code] || code; return ES ? (ST_ES[n] || n) : n; }
  function place(i) { var n = DATA.names[i]; return (n[2] ? n[2] + ", " : "") + stName(n[1]); }

  /* ------------------------------------------------------------ search */
  function initSearch() {
    var form = document.getElementById("search-form"); if (!form) return;
    var out = document.getElementById("results"), q = document.getElementById("q");
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var text = q.value.trim();
      if (!text) { out.innerHTML = tr("<p>Please type a ZIP code or a district name.</p>", "<p>Escriba un código postal o el nombre de un distrito.</p>"); return; }
      out.innerHTML = tr("<p>Searching…</p>", "<p>Buscando…</p>");
      load().then(function () {
        if (/^\d{5}$/.test(text)) return zipSearch(text, out);
        nameSearch(text, out);
      }).catch(function () { out.innerHTML = tr("<p>Sorry, the data could not be loaded. Please try again.</p>", "<p>No se pudieron cargar los datos. Inténtelo de nuevo.</p>"); });
    });
  }
  function listHTML(items, intro) {
    return "<h3>" + esc(intro) + "</h3><ul>" + items.map(function (it) {
      var i = it.i;
      return "<li><a href=\"" + BASE + (ES ? "es/distrito/" : "district/") + DATA.ids[i] + "/\">" + esc(DATA.names[i][0]) + "</a><div class=\"sub\">" +
        esc(place(i)) + (DATA.enrollment[i] != null ? " · " + DATA.enrollment[i].toLocaleString("en-US") + tr(" students", " estudiantes") : "") +
        (it.note ? " · " + esc(it.note) : "") + "</div></li>";
    }).join("") + "</ul>";
  }
  function zipSearch(zip, out) {
    return fetch(BASE + "data/zip/" + zip.slice(0, 2) + ".json").then(function (r) { return r.ok ? r.json() : {}; }).then(function (z) {
      var rows = (z[zip] || []).filter(function (x) { return x[0] in INDEX; });
      if (!rows.length) { out.innerHTML = tr("<p>No school district was found for ZIP code " + esc(zip) + ". Try the district name instead.</p>",
        "<p>No se encontró ningún distrito escolar para el código postal " + esc(zip) + ". Pruebe con el nombre del distrito.</p>"); return; }
      var items = rows.map(function (x, k) {
        var note = rows.length > 1 && x[1] != null ? (k === 0 ? tr("covers the most of this ZIP code", "cubre la mayor parte de este código postal") : tr("covers part of this ZIP code", "cubre parte de este código postal")) : "";
        return {i: INDEX[x[0]], note: note};
      });
      out.innerHTML = listHTML(items, items.length === 1 ? tr("1 district serves ZIP code " + zip, "1 distrito atiende el código postal " + zip) :
        tr(items.length + " districts serve parts of ZIP code " + zip, items.length + " distritos atienden partes del código postal " + zip));
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
    if (!hits.length) { out.innerHTML = tr("<p>No district matched “" + esc(text) + "”. Check the spelling, or try a ZIP code.</p>",
      "<p>Ningún distrito coincide con «" + esc(text) + "». Revise la ortografía o pruebe con un código postal.</p>"); return; }
    var shown = hits.slice(0, 25);
    out.innerHTML = listHTML(shown, hits.length > 25 ? tr(hits.length + " districts matched; showing the 25 largest", hits.length + " distritos coinciden; se muestran los 25 más grandes") :
      (hits.length === 1 ? tr("1 district matched", "1 distrito coincide") : tr(hits.length + " districts matched", hits.length + " distritos coinciden")));
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
      style: {version: 8, sources: {}, layers: [{id: "bg", type: "background", paint: {"background-color": (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) ? "#1d2024" : "#f3f1ea"}}]}
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
      map.addLayer({id: "base-line", type: "line", source: "base", paint: {"line-color": MAPLINE(), "line-width": ["interpolate", ["linear"], ["zoom"], 3, 0.15, 8, 1]}});
      map.addLayer({id: "hs-line", type: "line", source: "hs", layout: {visibility: "none"}, paint: {"line-color": MAPLINE(), "line-width": ["interpolate", ["linear"], ["zoom"], 3, 0.2, 8, 1]}});
      map.addLayer({id: "state-line", type: "line", source: "states", paint: {"line-color": MAPDARK() ? "#cdc8be" : "#474d55", "line-width": ["interpolate", ["linear"], ["zoom"], 3, 0.6, 8, 1.6]}});
      map.addLayer({id: "hover", type: "line", source: "base", paint: {"line-color": MAPDARK() ? "#ffffff" : "#1d2126", "line-width": 2}, filter: ["==", ["get", "id"], ""]});
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
      var open = exp.getAttribute("data-open") !== "1";
      all().forEach(function (d) { d.open = open; });
      exp.setAttribute("data-open", open ? "1" : "0");
      exp.textContent = open ? tr("Hide all detail", "Ocultar los detalles") : tr("Show all detail", "Mostrar todos los detalles");
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
  var DARK = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  function PAPER() { return DARK ? "#16181b" : "#fbfaf6"; }
  function mark(g, shape, x, y, r, fill) {
    if (shape === "circle") return svgEl("circle", { cx: x, cy: y, r: r, fill: fill, stroke: PAPER(), "stroke-width": 2 }, g);
    var p;
    if (shape === "square") p = [[x - r, y - r], [x + r, y - r], [x + r, y + r], [x - r, y + r]];
    else if (shape === "diamond") p = [[x, y - r * 1.25], [x + r * 1.25, y], [x, y + r * 1.25], [x - r * 1.25, y]];
    else p = [[x, y - r * 1.2], [x + r * 1.15, y + r * .9], [x - r * 1.15, y + r * .9]];
    return svgEl("polygon", { points: p.map(function (a) { return a.join(","); }).join(" "), fill: fill, stroke: PAPER(), "stroke-width": 2 }, g);
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
      svgEl("title", {}, g).textContent = m.short + (cd.state ? "" : tr(": this district ", ": este distrito ") + (v == null ? tr("not shown", "sin dato") : f1(v, m.unit))) +
        tr("; " + cd.st + " median ", "; mediana de " + cd.st + " ") + f1(med, m.unit) + (lo != null ? tr("; middle half ", "; mitad central ") + f1(lo, m.unit) + tr(" to ", " a ") + f1(hi, m.unit) : "") +
        tr("; national median ", "; mediana nacional ") + f1(nat, m.unit);
      var lab = svgEl("text", { x: 0, y: y + 4.5, class: "lab" }, g); lab.textContent = m.short;
      svgEl("line", { x1: L, x2: R, y1: y, y2: y, class: "track" }, g);
      if (lo != null && hi != null) svgEl("rect", { x: X(lo), y: y - 6, width: Math.max(3, X(hi) - X(lo)), height: 12, rx: 6, class: "band" }, g);
      if (med != null) svgEl("line", { x1: X(med), x2: X(med), y1: y - 10, y2: y + 10, class: "smed" }, g);
      if (nat != null) svgEl("circle", { cx: X(nat), cy: y, r: 4.5, class: "nat" }, g);
      if (cd.state) {
        var sv = svgEl("text", { x: R + 14, y: y + 4.5, class: med == null ? "na" : "val" }, g); sv.textContent = med == null ? tr("Not shown", "Sin dato") : f1(med, m.unit);
      } else if (v != null) {
        svgEl("circle", { cx: X(v), cy: y, r: 6.5, class: "dot" }, g);
        var t = svgEl("text", { x: R + 14, y: y + 4.5, class: "val" }, g); t.textContent = (d[1] === "1" ? "≥ " : "") + f1(v, m.unit);
      } else { var n = svgEl("text", { x: R + 14, y: y + 4.5, class: "na" }, g); n.textContent = tr("Not shown", "Sin dato"); }
    });
    body.appendChild(svg);
    body.insertAdjacentHTML("beforebegin", '<ul class="chart-key">' + (cd.state ? "" : '<li><span class="k-dot"></span>' + tr("This district", "Este distrito") + "</li>") + '<li><span class="k-band"></span>' +
      tr("Middle half of " + esc(cd.st) + " districts", "Mitad central de los distritos de " + esc(cd.st)) + '</li><li><span class="k-med"></span>' +
      tr(esc(cd.st) + " median", "Mediana de " + esc(cd.st)) + '</li><li><span class="k-nat"></span>' + tr("National median", "Mediana nacional") + '</li></ul>');
  }

  // One bar split into parts, labelled below with counts and shares.
  function partsBar(body, parts, colors) {
    var total = parts.reduce(function (a, p) { return a + (p[1] || 0); }, 0); if (!total) return false;
    var bar = '<div class="pbar">' + parts.map(function (p, i) {
      var w = 100 * (p[1] || 0) / total; if (!w) return "";
      return '<span style="flex-basis:' + w.toFixed(2) + '%;background:' + colors[i] + '" title="' + esc(p[0]) + ': ' + (100 * p[1] / total).toFixed(1) + tr(' per 100', ' por cada 100') + '"></span>';
    }).join("") + "</div>";
    var key = '<ul class="pkey">' + parts.map(function (p, i) {
      if (!p[1]) return "";
      return '<li><span class="sw" style="background:' + colors[i] + '"></span><span class="pl">' + esc(p[0]) + '</span><span class="pv">' +
        (100 * p[1] / total).toFixed(1) + '<small>' + tr(' per 100 · ', ' por cada 100 · ') + p[1].toLocaleString("en-US") + tr(' students', ' estudiantes') + '</small></span></li>';
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

  // Race and ethnicity, 2023-24: each group's rate beside the rate for all other students (counts from the Civil Rights Data Collection).
  var GROUP_NAMES = { AM: ["American Indian or Alaska Native", "Indígena americano o nativo de Alaska"], AS: ["Asian", "Asiático"], BL: ["Black or African American", "Negro o afroamericano"],
    HI: ["Hispanic or Latino", "Hispano o latino"], HP: ["Native Hawaiian or Other Pacific Islander", "Nativo de Hawái u otras islas del Pacífico"], TR: ["Two or more races", "Dos o más razas"], WH: ["White", "Blanco"] };
  function groupTable(cd, which, cls) {
    var rg = cd.rg; if (!rg || !rg.length) return "";
    var iep = which === "iep", num = iep ? 2 : 3, den = iep ? 1 : 2;
    var ok = rg.every(function (g) { return g[num] != null && g[den] != null; });
    var tn = 0, td = 0; rg.forEach(function (g) { tn += g[num] || 0; td += g[den] || 0; });
    var n0 = function (v) { return v == null ? tr("Withheld or not reported", "Retenido o no informado") : v.toLocaleString("en-US"); };
    var r100 = function (a, b) { return b == null || a == null ? "—" : b < 10 ? tr("Fewer than 10 students", "Menos de 10 estudiantes") : (100 * a / b).toFixed(1); };
    var rows = rg.map(function (g) {
      var nm = GROUP_NAMES[g[0]] ? (ES ? GROUP_NAMES[g[0]][1] : GROUP_NAMES[g[0]][0]) : g[0];
      return '<tr><th scope="row">' + esc(nm) + "</th><td>" + n0(g[den]) + "</td><td>" + n0(g[num]) + "</td><td>" + r100(g[num], g[den]) + "</td><td>" +
        (ok && g[den] != null ? r100(tn - g[num], td - g[den]) : "—") + "</td></tr>";
    }).join("");
    var cap = iep ? tr("Students with IEPs by race and ethnicity, 2023–24", "Estudiantes con IEP por raza y origen étnico, 2023–24")
      : tr("Out-of-school suspensions of students with IEPs, by race and ethnicity, 2023–24", "Suspensiones fuera de la escuela de estudiantes con IEP, por raza y origen étnico, 2023–24");
    var head = iep ? [tr("Group", "Grupo"), tr("Students enrolled", "Estudiantes inscritos"), tr("Students with IEPs", "Estudiantes con IEP"), tr("Per 100 students in the group", "Por cada 100 estudiantes del grupo"), tr("Per 100 all other students", "Por cada 100 de todos los demás estudiantes")]
      : [tr("Group", "Grupo"), tr("Students with IEPs", "Estudiantes con IEP"), tr("Received one or more out-of-school suspensions", "Recibieron una o más suspensiones fuera de la escuela"), tr("Per 100 students with IEPs in the group", "Por cada 100 estudiantes con IEP del grupo"), tr("Per 100 all other students with IEPs", "Por cada 100 de todos los demás estudiantes con IEP")];
    return '<table class="' + (cls || "profile") + '"><caption>' + esc(cap) + "</caption><thead><tr>" + head.map(function (h) { return '<th scope="col">' + esc(h) + "</th>"; }).join("") + "</tr></thead><tbody>" + rows + "</tbody></table>";
  }
  function fillGroups(cd) {
    Array.prototype.forEach.call(document.querySelectorAll(".jg[data-g]"), function (slot) {
      var t = groupTable(cd, slot.getAttribute("data-g"));
      slot.outerHTML = t ? '<div class="table-wrap" role="region" tabindex="0" aria-label="' + esc(slot.getAttribute("data-g") === "iep" ? tr("Students with IEPs by race and ethnicity", "Estudiantes con IEP por raza y origen étnico") : tr("Suspensions by race and ethnicity", "Suspensiones por raza y origen étnico")) + '">' + t + "</div>" : "";
    });
  }

  function buildTables(cd) {
    buildTrendTables(cd);
    fillGroups(cd);
    if (!document.querySelector(".jt[data-t]")) return;
    // repeated words are stored once in data/labels.json; numbers in the table data point into that list
    fetch(BASE + "data/labels.json").then(function (r) { return r.json(); }).then(function (L) { fillTables(cd, L); }).catch(function () { fillTables(cd, []); });
  }
  function fillTables(cd, L) {
    var w = function (x) { return typeof x === "number" ? (L[x] != null ? L[x] : "") : x; };
    Array.prototype.forEach.call(document.querySelectorAll(".jt[data-t]"), function (slot) {
      var d0 = (cd.t || [])[+slot.getAttribute("data-t")]; if (!d0) return;
      var d = {id: d0.id, k: d0.k, c: w(d0.c), h: d0.h.map(w), r: d0.r.map(function (row) { return row.map(w); })};
      var h = '<div class="table-wrap" role="region" tabindex="0" aria-labelledby="' + d.id + '"><table class="' + d.k + '"><caption id="' + d.id + '">' + esc(d.c) +
        '</caption><thead><tr>' + d.h.map(function (x) { return '<th scope="col">' + esc(x) + "</th>"; }).join("") + "</tr></thead><tbody>" +
        d.r.map(function (row) { return "<tr><th scope=\"row\">" + esc(row[0]) + "</th>" + row.slice(1).map(function (c) { return "<td>" + esc(c) + "</td>"; }).join("") + "</tr>"; }).join("") +
        "</tbody></table></div>";
      slot.outerHTML = h;
    });
  }
  // Explanations on district pages come from two shared files (questions and answers), so each page
  // carries only the term names. The questions are built as the same closed <details> a reader can open.
  function fillTerms() {
    var boxes = document.querySelectorAll(".explainers[data-terms]");
    var ds = document.querySelectorAll("details.explain[data-term]");
    if (!boxes.length && !ds.length) return;
    var sfx = ES ? "_es.json" : ".json";
    Promise.all([fetch(BASE + "data/terms_q" + sfx).then(function (r) { return r.json(); }),
                 fetch(BASE + "data/terms" + sfx).then(function (r) { return r.json(); })]).then(function (res) {
      var q = res[0], a = res[1];
      Array.prototype.forEach.call(boxes, function (box) {
        var keys = box.getAttribute("data-terms").split(" ").filter(function (k) { return q[k] && a[k]; });
        if (!keys.length) return;
        box.innerHTML = keys.map(function (k) {
          return '<details class="explain" data-term="' + k + '"><summary>' + esc(q[k]) + "</summary><p>" + esc(a[k]) + "</p></details>";
        }).join("");
      });
      Array.prototype.forEach.call(ds, function (d) { var k = d.getAttribute("data-term"); if (a[k]) d.querySelector("p").textContent = a[k]; });
    }).catch(function () {});
  }

  // History timeline: a year slider and milestone buttons; the panel below is read aloud when the year changes.
  function initTimeline() {
    var el = document.getElementById("tl-data"); if (!el) return;
    var D = JSON.parse(el.textContent), box = el.parentNode, range = document.getElementById("tl-range"), out = document.getElementById("tl-out");
    var panel = document.getElementById("tl-panel"), now = box.querySelector(".tl-now"), es = D.lang === "es";
    box.hidden = false;
    var intro = box.parentNode.querySelector(".tl-intro"); if (intro) intro.hidden = false;
    var list = box.parentNode.querySelector("ol.timeline"); if (list) list.classList.add("tl-static");
    var X = function (y) { return D.L + (D.W - D.L - D.R) * (y - D.x0) / (D.x1 - D.x0); };
    function show(i, quiet) {
      var y = D.years[i], d = D.y[String(y)], sy = y + "–" + String(y + 1).slice(-2);
      range.value = i; out.textContent = y; range.setAttribute("aria-valuetext", String(y) + (d.m ? (es ? ", momento clave" : ", milestone") : ""));
      now.setAttribute("transform", "translate(" + X(y) + ",0)");
      Array.prototype.forEach.call(box.querySelectorAll(".tl-btn"), function (b) { b.setAttribute("aria-current", +b.getAttribute("data-y") === y ? "true" : "false"); });
      Array.prototype.forEach.call(box.querySelectorAll(".tl-ms"), function (c) { c.classList.toggle("on", +c.getAttribute("data-y") === y); });
      var h = '<p class="tl-y">' + y + "</p>";
      if (d.m) h += '<p class="tl-m">' + esc(d.m) + "</p>";
      if (d.f.length) h += '<p class="tl-sub">' + (es ? "En el año escolar " + sy + ":" : "In the " + sy + " school year:") + "</p><ul class=\"plain\">" +
        d.f.map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("") + "</ul>";
      else h += '<p class="tl-sub">' + (es ? "Las tablas federales no tienen cifras nacionales para este año." : "The federal tables have no national figures for this year.") + "</p>";
      if (quiet) panel.setAttribute("aria-live", "off");
      panel.innerHTML = h;
      if (quiet) setTimeout(function () { panel.setAttribute("aria-live", "polite"); }, 0);
    }
    range.addEventListener("input", function () { show(+range.value); });
    Array.prototype.forEach.call(box.querySelectorAll(".tl-btn"), function (b) {
      b.addEventListener("click", function () { show(D.years.indexOf(+b.getAttribute("data-y"))); });
    });
    Array.prototype.forEach.call(box.querySelectorAll(".tl-ms"), function (c) {
      c.addEventListener("click", function () { show(D.years.indexOf(+c.getAttribute("data-y"))); });
    });
    show(0, true);
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
      initHistoryCharts(box.closest("section"));
    });
  }


  /* ------------------------------------------------------------ interactive layer
     Every part works with the keyboard and a screen reader; pictures stay hidden from screen readers and the
     same information is given in words. */

  function yearLabel(kind, y) {
    if (kind === "fy") return (y - 1) + "–" + String(y).slice(-2);
    if (kind === "y") return String(y);
    if (kind === "fall") return (ES ? "Otoño de " : "Fall ") + y;
    return y + "–" + String(y + 1).slice(-2);
  }

  // 1. Explore a line chart year by year: arrow keys (slider) or pointer; a crosshair and a short note show the values.
  function makeExplorer(fig, geo, visible, fmtv) {
    var svg = fig.querySelector("svg"); if (!svg || fig.querySelector(".explore")) return;
    var years = [];
    geo.series.forEach(function (s) { s.pts.forEach(function (p) { if (years.indexOf(p[0]) < 0) years.push(p[0]); }); });
    years.sort(function (a, b) { return a - b; });
    if (years.length < 2) return;
    var X = function (y) { return geo.L + (geo.w - geo.L - geo.R) * (y - geo.x0) / Math.max(1, geo.x1 - geo.x0); };
    var Y = function (v) { return geo.T + (geo.h - geo.T - geo.B) * (1 - v / geo.vmax); };
    fmtv = fmtv || function (v) { return (+v).toFixed(1); };
    var g = svgEl("g", { class: "xhair", visibility: "hidden" }, svg);
    var line = svgEl("line", { y1: geo.T, y2: geo.h - geo.B, class: "xh-line" }, g);
    var dots = svgEl("g", {}, g);
    var box = svgEl("g", {}, g), rect = svgEl("rect", { rx: 6, class: "xh-box" }, box), txt = svgEl("text", { class: "xh-text" }, box);
    var ctl = document.createElement("div");
    ctl.className = "explore"; ctl.tabIndex = 0; ctl.setAttribute("role", "slider");
    ctl.setAttribute("aria-label", tr("Explore this chart by year. Use the left and right arrow keys.", "Recorra este gráfico por año. Use las flechas izquierda y derecha."));
    ctl.setAttribute("aria-valuemin", "0"); ctl.setAttribute("aria-valuemax", String(years.length - 1));
    ctl.innerHTML = '<span class="explore-hint" aria-hidden="true">' + tr("Explore by year: focus here and use the arrow keys, or point at the chart.", "Recorra por año: enfoque aquí y use las flechas, o señale el gráfico.") + "</span>";
    fig.appendChild(ctl);
    var idx = years.length - 1;
    function at(i, quiet) {
      idx = Math.max(0, Math.min(years.length - 1, i));
      var y = years[idx], parts = [], lines = [];
      while (dots.firstChild) dots.removeChild(dots.firstChild);
      while (txt.firstChild) txt.removeChild(txt.firstChild);
      geo.series.forEach(function (s, si) {
        if (!visible(si)) return;
        var p = s.pts.filter(function (q) { return q[0] === y; })[0];
        if (!p) return;
        svgEl("circle", { cx: X(y), cy: Y(p[1]), r: 4.5, class: "xh-dot" }, dots);
        parts.push((geo.series.length > 1 ? s.label + ": " : "") + fmtv(p[1]) + (geo.unit || ""));
        lines.push((geo.series.length > 1 ? s.label + ": " : "") + fmtv(p[1]) + (geo.unit || ""));
      });
      var head = yearLabel(geo.yl, y);
      var say = head + ": " + (parts.length ? parts.join("; ") : tr("no figure", "sin cifra"));
      ctl.setAttribute("aria-valuenow", String(idx)); ctl.setAttribute("aria-valuetext", say);
      line.setAttribute("x1", X(y)); line.setAttribute("x2", X(y));
      [head].concat(lines.length ? lines : [tr("no figure", "sin cifra")]).forEach(function (l, k) {
        var ts = svgEl("tspan", { x: 0, dy: k ? 16 : 0, class: k ? "" : "xh-head" }, txt); ts.textContent = l;
      });
      var bb = txt.getBBox(), bx = X(y) + 12, by = geo.T + 6;
      if (X(y) > geo.L + (geo.w - geo.L - geo.R) * 0.6 || bx + bb.width + 16 > geo.w) bx = X(y) - bb.width - 28;
      txt.setAttribute("transform", "translate(" + (bx + 8) + "," + (by + 14) + ")");
      rect.setAttribute("x", bx); rect.setAttribute("y", by); rect.setAttribute("width", bb.width + 16); rect.setAttribute("height", bb.height + 10);
      g.setAttribute("visibility", quiet ? "hidden" : "visible");
    }
    at(idx, true);
    ctl.addEventListener("focus", function () { at(idx); });
    ctl.addEventListener("blur", function () { g.setAttribute("visibility", "hidden"); });
    ctl.addEventListener("keydown", function (e) {
      var k = e.key, step = { ArrowLeft: -1, ArrowDown: -1, ArrowRight: 1, ArrowUp: 1, PageDown: -5, PageUp: 5 }[k];
      if (step) { at(idx + step); e.preventDefault(); }
      else if (k === "Home") { at(0); e.preventDefault(); }
      else if (k === "End") { at(years.length - 1); e.preventDefault(); }
    });
    svg.addEventListener("pointermove", function (e) {
      var r = svg.getBoundingClientRect(), px = (e.clientX - r.left) * geo.w / r.width;
      var y = geo.x0 + (px - geo.L) / (geo.w - geo.L - geo.R) * (geo.x1 - geo.x0), best = 0;
      years.forEach(function (yy, i) { if (Math.abs(yy - y) < Math.abs(years[best] - y)) best = i; });
      at(best);
    });
    svg.addEventListener("pointerleave", function () { if (document.activeElement !== ctl) g.setAttribute("visibility", "hidden"); });
    ctl.refresh = function () { if (g.getAttribute("visibility") === "visible") at(idx); };
    return ctl;
  }

  // History charts: explorer plus legend buttons that show or hide a line.
  function initHistoryCharts(root) {
    Array.prototype.forEach.call((root || document).querySelectorAll("figure.explorable svg.hchart[data-geo]"), function (svg) {
      var fig = svg.closest("figure"), geo = JSON.parse(svg.getAttribute("data-geo"));
      var shown = function (si) { var b = fig.querySelector('.k-btn[data-s="' + si + '"]'); return !b || b.getAttribute("aria-pressed") === "true"; };
      var old = fig.querySelector(".explore"); if (old) old.remove();
      var ctl = makeExplorer(fig, geo, shown);
      Array.prototype.forEach.call(fig.querySelectorAll(".k-btn"), function (b) {
        b.setAttribute("aria-label", b.textContent + tr(": shown. Press to hide this line.", ": visible. Pulse para ocultar esta línea."));
        b.onclick = function () {
          var on = b.getAttribute("aria-pressed") !== "true", si = b.getAttribute("data-s");
          b.setAttribute("aria-pressed", on ? "true" : "false");
          b.setAttribute("aria-label", b.textContent + (on ? tr(": shown. Press to hide this line.", ": visible. Pulse para ocultar esta línea.") : tr(": hidden. Press to show this line.", ": oculta. Pulse para mostrar esta línea.")));
          Array.prototype.forEach.call(svg.querySelectorAll('[data-s="' + si + '"]'), function (el) { el.style.display = on ? "" : "none"; });
          if (ctl && ctl.refresh) ctl.refresh();
        };
      });
    });
  }

  // 2. "See it as 100 students": a 10 by 10 picture beside sentences that say "of every 100".
  function initHundred() {
    var n = 0;
    Array.prototype.forEach.call(document.querySelectorAll("ul.plain li, .glance li"), function (li) {
      var t = li.textContent, f = li.querySelector(".fig");
      if (!f || /\$/.test(t) || !/(of every 100|de cada 100)/.test(t)) return;
      var v = parseFloat(f.textContent.replace(/,/g, "")); if (!(v >= 1 && v <= 100)) return;
      var k = Math.round(v), id = "h100-" + (++n);
      var b = document.createElement("button"); b.type = "button"; b.className = "h100-btn"; b.setAttribute("aria-expanded", "false"); b.setAttribute("aria-controls", id);
      b.textContent = tr("See it as 100 students", "Verlo como 100 estudiantes");
      var grid = document.createElement("div"); grid.className = "h100"; grid.id = id; grid.hidden = true;
      grid.setAttribute("role", "img");
      grid.setAttribute("aria-label", tr("A picture of 100 students with " + k + " shaded, about " + v + " of every 100.", "Un dibujo de 100 estudiantes con " + k + " sombreados, aproximadamente " + v + " de cada 100."));
      var h = ""; for (var i = 0; i < 100; i++) h += '<span class="' + (i < k ? "on" : "") + '"></span>';
      grid.innerHTML = h;
      b.addEventListener("click", function () { var o = grid.hidden; grid.hidden = !o; b.setAttribute("aria-expanded", o ? "true" : "false"); });
      li.appendChild(document.createTextNode(" ")); li.appendChild(b); li.appendChild(grid);
    });
  }

  // 3. Questions for an IEP meeting: tick, add your own, print or copy.
  function initAsk() {
    var ul = document.querySelector("ul.ask"); if (!ul) return;
    var qs = Array.prototype.map.call(ul.querySelectorAll("li"), function (li) { return li.textContent; });
    var name = (document.querySelector("h1") || {}).textContent || "";
    var fs = document.createElement("fieldset"); fs.className = "askfs";
    fs.innerHTML = "<legend>" + tr("Choose the questions you want to bring", "Elija las preguntas que quiere llevar") + "</legend>" +
      qs.map(function (q, i) { return '<div class="ask-row"><input type="checkbox" id="ask-' + i + '" checked><label for="ask-' + i + '">' + esc(q) + "</label></div>"; }).join("") +
      '<label for="ask-own" class="ask-own-l">' + tr("Add your own questions, one on each line", "Agregue sus propias preguntas, una en cada línea") + '</label><textarea id="ask-own" rows="3"></textarea>' +
      '<div class="ask-tools"><button type="button" data-ask="print">' + tr("Print my questions", "Imprimir mis preguntas") + '</button>' +
      '<button type="button" class="secondary" data-ask="copy">' + tr("Copy my questions", "Copiar mis preguntas") + '</button></div><p class="hint" aria-live="polite" id="ask-status"></p>';
    ul.replaceWith(fs);
    function chosen() {
      var out = [];
      qs.forEach(function (q, i) { if (document.getElementById("ask-" + i).checked) out.push(q); });
      document.getElementById("ask-own").value.split("\n").forEach(function (l) { if (l.trim()) out.push(l.trim()); });
      return out;
    }
    var st = document.getElementById("ask-status");
    fs.querySelector('[data-ask="copy"]').addEventListener("click", function () {
      var list = chosen(), text = tr("Questions for my IEP meeting", "Preguntas para mi reunión del IEP") + " (" + name + ")\n\n" + list.map(function (q, i) { return (i + 1) + ". " + q; }).join("\n");
      var done = function () { st.textContent = tr("Copied " + list.length + " questions.", "Se copiaron " + list.length + " preguntas."); };
      if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, function () { st.textContent = tr("Copying is not allowed here. Use Print instead.", "Aquí no se puede copiar. Use Imprimir."); });
    });
    fs.querySelector('[data-ask="print"]').addEventListener("click", function () {
      var list = chosen(), box = document.getElementById("my-q") || document.body.appendChild(Object.assign(document.createElement("div"), { id: "my-q" }));
      box.innerHTML = "<h1>" + tr("Questions for my IEP meeting", "Preguntas para mi reunión del IEP") + "</h1><p>" + esc(name) + "</p><ol>" +
        list.map(function (q) { return "<li>" + esc(q) + '<div class="ans"></div></li>'; }).join("") + "</ol><p class=\"src\">IDEA Atlas · " + location.href + "</p>";
      document.body.classList.add("print-q");
      var off = function () { document.body.classList.remove("print-q"); window.removeEventListener("afterprint", off); };
      window.addEventListener("afterprint", off);
      window.print();
      setTimeout(off, 1500);
    });
  }

  // 4. Districts like this one: same state, similar enrollment and child poverty; one click to compare.
  function initLike() {
    var btn = document.querySelector("[data-like]"); if (!btn) return;
    var el = document.getElementById("chart-data"), cd = el ? JSON.parse(el.textContent) : {}, out = document.querySelector(".like-out");
    btn.addEventListener("click", function () {
      out.innerHTML = "<p>" + tr("Looking…", "Buscando…") + "</p>";
      load().then(function () {
        var i0 = INDEX[cd.id], pj = -1;
        DATA.measures.forEach(function (m, j) { if (m.key === "child_poverty") pj = j; });
        var pov = function (i) { var c = DATA.codes[i][pj]; return (c === "0" || c === "1") ? DATA.values[i][pj] : null; };
        if (i0 == null || !DATA.enrollment[i0] || pov(i0) == null) { out.innerHTML = "<p>" + tr("This district does not have the enrollment and poverty figures needed to find similar districts.", "Este distrito no tiene las cifras de inscripción y pobreza necesarias para buscar distritos parecidos.") + "</p>"; return; }
        var e0 = DATA.enrollment[i0], p0 = pov(i0), st = DATA.names[i0][1], hits = [];
        for (var i = 0; i < DATA.ids.length; i++) {
          if (i === i0 || DATA.names[i][1] !== st || !DATA.enrollment[i] || pov(i) == null) continue;
          hits.push({ i: i, d: Math.abs(Math.log(DATA.enrollment[i] / e0)) + Math.abs(pov(i) - p0) / 8 });
        }
        hits.sort(function (a, b) { return a.d - b.d; });
        var top = hits.slice(0, 5);
        if (!top.length) { out.innerHTML = "<p>" + tr("No similar districts were found in this state.", "No se encontraron distritos parecidos en este estado.") + "</p>"; return; }
        out.innerHTML = "<h3>" + tr(top.length + " districts like this one", top.length + " distritos parecidos a este") + "</h3><ul class=\"like-list\">" + top.map(function (h) {
          var i = h.i;
          return '<li><a href="' + BASE + (ES ? "es/distrito/" : "district/") + DATA.ids[i] + '/">' + esc(DATA.names[i][0]) + "</a> <span class=\"sub\">" +
            DATA.enrollment[i].toLocaleString("en-US") + tr(" students · ", " estudiantes · ") + pov(i).toFixed(1) + tr(" of every 100 children in poverty", " de cada 100 niños en la pobreza") + "</span></li>";
        }).join("") + "</ul><p><a class=\"button\" href=\"" + BASE + "compare/?ids=" + [cd.id].concat(top.slice(0, 3).map(function (h) { return DATA.ids[h.i]; })).join(",") + "\">" +
          tr("Compare this district with the first three", "Comparar este distrito con los tres primeros") + "</a>" + (ES ? ' <span class="sub">(en inglés)</span>' : "") + "</p>";
      });
    });
  }

  // A district's own line over time: thin line, end values labelled, dashed across missing years.
  function trendChart(body, pts, money, comp, yfmt, labels) {
    var L1 = labels && labels[0] || tr("Students with IEPs", "Estudiantes con IEP"), L2 = labels && labels[1] || tr("Students without disabilities", "Estudiantes sin discapacidades");
    if (!pts || pts.length < 3) return false;
    var W = 640, H = 170, L = 10, R = 80, T = 18, B = 26;
    var x0 = pts[0][0], x1 = pts[pts.length - 1][0];
    var all = pts.concat(comp || []);
    var mx = Math.max.apply(null, all.map(function (p) { return p[1]; })) * 1.15 || 1;
    if (comp) { x0 = Math.min(x0, comp[0][0]); x1 = Math.max(x1, comp[comp.length - 1][0]); }
    var X = function (x) { return L + (W - L - R) * (x - x0) / Math.max(1, x1 - x0); };
    var Y = function (v) { return T + (H - T - B) * (1 - v / mx); };
    var fmtv = function (v) { return money ? "$" + Math.round(v).toLocaleString("en-US") : (+v).toFixed(1); };
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, class: "range trend", focusable: "false" });
    svgEl("line", { x1: L, x2: W - R, y1: Y(0), y2: Y(0), class: "track" }, svg);
    if (comp && comp.length > 1) {
      svgEl("path", { d: comp.map(function (p, i) { return (i ? "L" : "M") + X(p[0]) + "," + Y(p[1]); }).join(" "), class: "tcomp" }, svg);
      var cl = comp[comp.length - 1], ct = svgEl("text", { x: X(cl[0]) + 10, y: Y(cl[1]) + 4.5, class: "lab" }, svg); ct.textContent = fmtv(cl[1]);
      body.insertAdjacentHTML("beforebegin", '<ul class="chart-key"><li><span class="k-line" style="background:var(--accent)"></span>' + esc(L1) +
        '</li><li><span class="k-line k-comp"></span>' + esc(L2) + "</li></ul>");
    }
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
    svg.setAttribute("aria-hidden", "true");
    body.appendChild(svg);
    var key = body.previousElementSibling; if (key && key.classList.contains("chart-key")) key.setAttribute("aria-hidden", "true");
    var ser = [{ label: L1, pts: pts }];
    if (comp && comp.length > 1) ser.push({ label: L2, pts: comp });
    var fig = body.closest("figure");
    if (fig) makeExplorer(fig, { yl: yfmt || "sy", x0: x0, x1: x1, vmax: mx, L: L, R: R, T: T, B: B, w: W, h: H, unit: "", series: comp && comp.length > 1 ? ser : [{ label: "", pts: pts }] }, function () { return true; }, fmtv);
    return true;
  }

  function initCharts() {
    fillTerms();
    var el = document.getElementById("chart-data"); if (!el) return;
    var cd; try { cd = JSON.parse(el.textContent); } catch (e) { return; }
    buildTables(cd);
    fetch(BASE + (ES ? "data/measures_es.json" : "data/measures.json")).then(function (r) { return r.json(); }).then(function (ms) {
      var meas = {}; ms.forEach(function (m) { meas[m.key] = m; });
      Array.prototype.forEach.call(document.querySelectorAll("figure.chart[data-chart]"), function (fig) {
        var body = fig.querySelector(".chart-body"), kind = fig.getAttribute("data-chart"), ok = true;
        if (kind === "range") rangeChart(body, fig.getAttribute("data-keys").split(","), cd, meas);
        else if (kind === "settings") ok = cd.set ? partsBar(body, [[tr("80% or more of the day", "80% o más del día"), cd.set[0]], [tr("40% to 79%", "40% a 79%"), cd.set[1]], [tr("Less than 40%", "Menos del 40%"), cd.set[2]],
              [tr("Separate school, facility, home or hospital", "Escuela o centro separado, hogar u hospital"), cd.set[3]], [tr("Other places", "Otros lugares"), cd.set[4]]], ["#0d366b", "#1c5cab", "#3987e5", "#86b6ef", "#b9b4a8"]) : false;
        else if (kind === "exit") ok = cd.ex ? partsBar(body, [[tr("Regular diploma", "Diploma regular"), cd.ex[0]], [tr("Alternate diploma or certificate", "Diploma alternativo o certificado"), cd.ex[1]], [tr("Reached the maximum age", "Llegó a la edad máxima"), cd.ex[2]],
              [tr("Dropped out", "Abandonó la escuela"), cd.ex[3]], [tr("Died", "Falleció"), cd.ex[4]]], ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]) : false;
        else if (kind === "cats") ok = catsChart(body, cd.cats || []);
        else if (kind === "trend") { var k = fig.getAttribute("data-keys"); var lb = fig.getAttribute("data-labels"); ok = trendChart(body, (cd.tr || {})[k], k === "s", (cd.tr || {})[k + "c"], fig.getAttribute("data-years") || (k === "s" ? "fy" : k === "p" ? "y" : "sy"), lb ? lb.split("|") : null); }
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
      var h = svgEl("text", { x: 0, y: y + 22, class: "grp" }, svg); h.textContent = cGroup(gr[0]); y += 34;
      gr[1].forEach(function (mj) {
        var m = mj[0], j = mj[1], cy = y + rowH / 2, g = svgEl("g", {}, svg);
        var vals = idx.map(function (i) { var c = DATA.codes[i][j]; return (c === "0" || c === "1") ? DATA.values[i][j] : null; });
        var mx = Math.max.apply(null, vals.concat([m.national_median || 0]).map(function (x) { return x || 0; })) * 1.1 || 1;
        var X = function (x) { return L + (R - L) * Math.max(0, x) / mx; };
        svgEl("title", {}, g).textContent = cShort(m) + ": " + idx.map(function (i, n) { return DATA.names[i][0] + " " + (vals[n] == null ? tr("not shown", "no se muestra") : f1(vals[n], m.unit)); }).join("; ") + tr("; national median ", "; mediana nacional ") + f1(m.national_median, m.unit);
        var t = svgEl("text", { x: 0, y: cy + 4.5, class: "lab" }, g); t.textContent = cShort(m);
        svgEl("line", { x1: L, x2: R, y1: cy, y2: cy, class: "track" }, g);
        if (m.national_median != null) svgEl("circle", { cx: X(m.national_median), cy: cy, r: 4.5, class: "nat" }, g);
        vals.forEach(function (v, n) { if (v != null) mark(g, SHAPES[n], X(v), cy, 6, SERIES[n]); });
        y += rowH;
      });
    });
    body.appendChild(svg);
    body.insertAdjacentHTML("beforebegin", '<ul class="chart-key">' + idx.map(function (i, n) {
      return '<li><svg viewBox="-8 -8 16 16" width="14" height="14" aria-hidden="true">' + (function () { var tmp = document.createElementNS(SVGNS, "g"); mark(tmp, SHAPES[n], 0, 0, 5.5, SERIES[n]); return tmp.innerHTML; })() + '</svg>' + esc(DATA.names[i][0]) + '</li>';
    }).join("") + '<li><span class="k-nat"></span>' + tr("National median", "Mediana nacional") + '</li></ul>');
    fig.hidden = false;
  }

  /* ------------------------------------------------------------ compare */
  var C_ES = {}, C_GROUP_ES = {"Who is served": "Quiénes reciben servicios", "Where students learn": "Dónde aprenden los estudiantes", "Leaving school": "Al salir de la escuela",
    "Discipline and safety": "Disciplina y seguridad", "Funding": "Fondos", "Community": "Comunidad"};
  function cShort(m) { return ES ? (C_ES[m.key] || m.short) : m.short; }
  function cGroup(g) { return ES ? (C_GROUP_ES[g] || g) : g; }
  function initCompare() {
    var form = document.getElementById("c-form"); if (!form) return;
    var q = document.getElementById("c-q"), res = document.getElementById("c-results"), chosenEl = document.getElementById("c-chosen");
    var wrap = document.getElementById("c-wrap"), table = document.getElementById("c-table"), status = document.getElementById("c-status");
    var chosen = [];
    function save() { history.replaceState(null, "", chosen.length ? "?ids=" + chosen.join(",") : location.pathname); }
    function add(id) {
      if (chosen.indexOf(id) >= 0) { status.textContent = DATA.names[INDEX[id]][0] + tr(" is already chosen.", " ya está elegido."); return; }
      if (chosen.length >= 4) { status.textContent = tr("You can compare up to four districts. Remove one first.", "Puede comparar hasta cuatro distritos. Quite uno primero."); return; }
      chosen.push(id); save(); draw(); res.innerHTML = "";
      status.textContent = DATA.names[INDEX[id]][0] + tr(" added. ", " agregado. ") + chosen.length + tr(" of 4 chosen.", " de 4 elegidos.");
      q.value = ""; q.focus();
    }
    function remove(id) {
      chosen = chosen.filter(function (x) { return x !== id; }); save(); draw();
      status.textContent = DATA.names[INDEX[id]][0] + tr(" removed. ", " quitado. ") + chosen.length + tr(" chosen.", " elegidos.");
    }
    function draw() {
      chosenEl.innerHTML = chosen.map(function (id) {
        var i = INDEX[id];
        return "<li><a href=\"" + BASE + tr("district/", "es/distrito/") + id + "/\">" + esc(DATA.names[i][0]) + "</a> <span class=\"sub\">" + esc(place(i)) + "</span> " +
          "<button type=\"button\" class=\"link\" data-remove=\"" + id + "\" aria-label=\"" + tr("Remove ", "Quitar ") + esc(DATA.names[i][0]) + "\">" + tr("Remove", "Quitar") + "</button></li>";
      }).join("") || "<li class=\"sub\">" + tr("None yet.", "Ninguno todavía.") + "</li>";
      Array.prototype.forEach.call(chosenEl.querySelectorAll("[data-remove]"), function (b) { b.addEventListener("click", function () { remove(b.getAttribute("data-remove")); }); });
      if (!chosen.length) { wrap.hidden = true; compareChart([]); return; }
      var idx = chosen.map(function (id) { return INDEX[id]; });
      compareChart(idx);
      table.tHead.innerHTML = "<tr><th scope=\"col\">" + tr("Measure", "Medida") + "</th>" + idx.map(function (i) { return "<th scope=\"col\">" + esc(DATA.names[i][0]) + "<span class=\"sub\"> " + esc(stName(DATA.names[i][1])) + "</span></th>"; }).join("") + "<th scope=\"col\">" + tr("National median", "Mediana nacional") + "</th></tr>";
      var rows = "<tr><th scope=\"row\">" + tr("Students enrolled", "Estudiantes inscritos") + "</th>" + idx.map(function (i) { return "<td>" + (DATA.enrollment[i] != null ? DATA.enrollment[i].toLocaleString("en-US") : tr("Not reported", "No se informó")) + "</td>"; }).join("") + "<td>—</td></tr>";
      var group = "";
      DATA.measures.forEach(function (m) {
        if (m.group !== group) { group = m.group; rows += "<tr class=\"group\"><th scope=\"rowgroup\" colspan=\"" + (idx.length + 2) + "\">" + esc(cGroup(group)) + "</th></tr>"; }
        rows += "<tr><th scope=\"row\">" + esc(ES ? cShort(m) : m.label) + "</th>" + idx.map(function (i) { return "<td>" + esc(cellText(i, m)) + "</td>"; }).join("") +
          "<td>" + (m.national_median != null ? fmt(m.national_median, m.unit) : "—") + "</td></tr>";
      });
      table.tBodies[0].innerHTML = rows;
      document.getElementById("c-caption").textContent = tr("Side-by-side figures for ", "Cifras lado a lado de ") + idx.map(function (i) { return DATA.names[i][0]; }).join(", ") + tr(". Rates per 100 students in each group unless shown in dollars.", ". Tasas por cada 100 estudiantes de cada grupo, salvo las cifras en dólares.");
      wrap.hidden = false;
    }
    (ES ? fetch(BASE + "data/measures_es.json").then(function (r) { return r.json(); }).then(function (ms) { ms.forEach(function (x) { C_ES[x.key] = x.short; }); }) : Promise.resolve()).then(load).then(function () {
      var p = new URLSearchParams(location.search);
      (p.get("ids") || "").split(",").forEach(function (id) { if (id in INDEX && chosen.length < 4 && chosen.indexOf(id) < 0) chosen.push(id); });
      draw();
      if (chosen.length) status.textContent = ES ? (chosen.length + (chosen.length > 1 ? " distritos elegidos." : " distrito elegido.") + (chosen.length < 4 ? " Puede agregar hasta " + (4 - chosen.length) + " más." : " Es el máximo que puede comparar a la vez.")) : (chosen.length + " district" + (chosen.length > 1 ? "s" : "") + " chosen." + (chosen.length < 4 ? " You can add up to " + (4 - chosen.length) + " more." : " That is the most you can compare at once."));
    });
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var text = q.value.trim(); if (!text) return;
      load().then(function () {
        var render = function (items, title) {
          if (!items.length) { res.innerHTML = "<p>" + tr("No district matched. Try another name or ZIP code.", "Ningún distrito coincide. Pruebe otro nombre o código postal.") + "</p>"; return; }
          res.innerHTML = "<h3>" + esc(title) + "</h3><ul class=\"pick\">" + items.slice(0, 15).map(function (i) {
            return "<li><button type=\"button\" data-add=\"" + DATA.ids[i] + "\">" + tr("Add ", "Agregar ") + esc(DATA.names[i][0]) + "</button> <span class=\"sub\">" + esc(place(i)) + "</span></li>";
          }).join("") + "</ul>";
          Array.prototype.forEach.call(res.querySelectorAll("[data-add]"), function (b) { b.addEventListener("click", function () { add(b.getAttribute("data-add")); }); });
          var first = res.querySelector("button"); if (first) first.focus();
        };
        if (/^\d{5}$/.test(text)) {
          fetch(BASE + "data/zip/" + text.slice(0, 2) + ".json").then(function (r) { return r.ok ? r.json() : {}; }).then(function (z) {
            render((z[text] || []).filter(function (x) { return x[0] in INDEX; }).map(function (x) { return INDEX[x[0]]; }), tr("Districts serving ZIP code ", "Distritos que atienden el código postal ") + text);
          });
        } else {
          var words = norm(text).split(" "), hits = [];
          for (var i = 0; i < DATA.ids.length; i++) {
            var hay = norm(DATA.names[i][0] + " " + DATA.names[i][2] + " " + DATA.names[i][1]);
            if (words.every(function (w) { return hay.indexOf(w) >= 0; })) hits.push(i);
          }
          hits.sort(function (a, b) { return (DATA.enrollment[b] || 0) - (DATA.enrollment[a] || 0); });
          render(hits, hits.length + tr(" matched", " coinciden") + (hits.length > 15 ? tr("; showing the 15 largest", "; se muestran los 15 más grandes") : ""));
        }
      });
    });
  }

  // Shared with the report assistant (report.js), so reports draw the same charts as the site.
  window.ATLAS = { BASE: BASE, ES: ES, tr: tr, esc: esc, load: load, data: function () { return DATA; }, index: function () { return INDEX; },
    rangeChart: rangeChart, partsBar: partsBar, catsChart: catsChart, trendChart: trendChart, groupTable: groupTable, yearLabel: yearLabel, svgEl: svgEl };


  // Wide screens: an "On this page" list of the page's sections in the empty right-hand column,
  // marking the section being read. Built from the h2 headings, so the page itself carries no extra text.
  function initOnPage() {
    var main = document.getElementById("main"); if (!main || main.querySelector("nav.onpage, nav.toc, .toc")) return;
    var hs = Array.prototype.filter.call(main.querySelectorAll(":scope > section > h2[id], :scope > article > section > h2[id]"), function (h) { return h.offsetParent !== null; });
    if (hs.length < 4) return;
    var nav = document.createElement("nav");
    nav.className = "onpage"; nav.setAttribute("aria-label", ES ? "En esta página" : "On this page");
    var items = hs.map(function (h) { return '<li><a href="#' + h.id + '">' + esc(h.textContent) + "</a></li>"; }).join("");
    // Wide screens: a list beside the text. Phones and tablets: a small "Jump to a section" menu under the title.
    nav.innerHTML = '<div class="onpage-in"><p class="onpage-h" aria-hidden="true">' + (ES ? "En esta página" : "On this page") + "</p><ul>" + items + "</ul></div>" +
      '<details class="onpage-fold"><summary>' + (ES ? "Ir a una sección" : "Jump to a section") + "</summary><ul>" + items + "</ul></details>";
    var fold = nav.querySelector(".onpage-fold");
    fold.addEventListener("click", function (e) { if (e.target.tagName === "A") fold.open = false; });
    var lede = main.querySelector(":scope > .lede"), ex = lede && lede.nextElementSibling;
    var after = main.querySelector(":scope > .page-tools") || main.querySelector(":scope > article > .byline") ||
      (lede ? (ex && ex.classList.contains("explainers") ? ex : lede) : null) || main.querySelector(":scope > h1");
    if (after) after.parentNode.insertBefore(nav, after.nextSibling); else main.insertBefore(nav, main.firstChild);
    document.documentElement.classList.add("has-onpage");
    var links = nav.querySelectorAll(".onpage-in a"), current = null, ticking = false;
    function mark() {
      ticking = false;
      var line = window.innerHeight * 0.3, id = hs[0].id;
      hs.forEach(function (h) { if (h.getBoundingClientRect().top <= line) id = h.id; });
      if (id === current) return; current = id;
      Array.prototype.forEach.call(links, function (a) {
        if (a.getAttribute("href") === "#" + id) a.setAttribute("aria-current", "true"); else a.removeAttribute("aria-current");
      });
    }
    window.addEventListener("scroll", function () { if (!ticking) { ticking = true; requestAnimationFrame(mark); } }, { passive: true });
    mark();
  }

  // Long lists of districts: a filter box that hides rows that do not match, and says how many remain.
  function initFilters() {
    Array.prototype.forEach.call(document.querySelectorAll("[data-filter-for]"), function (box) {
      var t = document.getElementById(box.getAttribute("data-filter-for")); if (!t) return;
      var input = box.querySelector("input"), out = box.querySelector("output"), rows = t.tBodies[0].rows;
      input.addEventListener("input", function () {
        var q = input.value.trim().toLowerCase(), n = 0;
        Array.prototype.forEach.call(rows, function (r) { var hit = !q || r.cells[0].textContent.toLowerCase().indexOf(q) >= 0 || (r.cells[1] && r.cells[1].textContent.toLowerCase().indexOf(q) >= 0); r.hidden = !hit; if (hit) n++; });
        out.textContent = q ? (ES ? n + " de " + rows.length + " distritos" : n + " of " + rows.length + " districts") : "";
      });
    });
  }

  // Phones: the site menu folds behind one button so the page starts with its content.
  // Without scripts, or on wider screens, the full list shows as before.
  function initMenu() {
    var nav = document.querySelector("header.site nav"), ul = nav && nav.querySelector("ul"); if (!ul || nav.querySelector(".menu-btn")) return;
    ul.id = ul.id || "site-menu";
    var b = document.createElement("button");
    b.type = "button"; b.className = "menu-btn"; b.setAttribute("aria-expanded", "false"); b.setAttribute("aria-controls", ul.id);
    b.textContent = ES ? "Menú" : "Menu";
    nav.insertBefore(b, ul);
    nav.classList.add("can-fold");
    b.addEventListener("click", function () {
      var open = b.getAttribute("aria-expanded") === "true";
      b.setAttribute("aria-expanded", open ? "false" : "true");
      nav.classList.toggle("open", !open);
      if (!open) { var a = ul.querySelector("a"); if (a) a.focus(); }
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && b.getAttribute("aria-expanded") === "true") { b.click(); b.focus(); }
    });
  }
  // "Embed this district" box, built from a small placeholder on each district page.
  function initEmbed() {
    var el = document.querySelector("[data-embed]"); if (!el) return;
    var id = el.getAttribute("data-embed"), name = el.getAttribute("data-name") || "";
    var origin = location.origin.indexOf("localhost") >= 0 ? "https://atlas.sumanrath.org" : location.origin;
    var src = origin + BASE + "embed/?id=" + id + (ES ? "&lang=es" : "");
    var title = ES ? "Datos de educación especial de " + name + ", IDEA Atlas" : "Special education data for " + name + ", IDEA Atlas";
    var code = '<iframe src="' + src + '" title="' + esc(title) + '" width="100%" height="430" style="border:0;max-width:480px" loading="lazy"></iframe>';
    el.innerHTML = '<details class="embed"><summary>' + tr("Embed this district on your website", "Insertar este distrito en su sitio web") + '</summary><p>' +
      tr("Copy this code into your website or blog to show a card with four key figures for this district and a link back to this page.",
         "Copie este código y péguelo en su sitio web o blog para mostrar una tarjeta con cuatro cifras clave de este distrito y un enlace a esta página.") +
      '</p><label for="emb-code">' + tr("Embed code", "Código para insertar") + '</label><textarea id="emb-code" readonly rows="4"></textarea></details>';
    el.querySelector("textarea").value = code;
  }
  // Text that is the same on every district page is stored once (data/shared_*.json) and filled in here.
  function initShared() {
    var slots = document.querySelectorAll("[data-shared]"); if (!slots.length) return;
    fetch(BASE + "data/shared_" + (ES ? "es" : "en") + ".json").then(function (r) { return r.json(); }).then(function (t) {
      Array.prototype.forEach.call(slots, function (el) { var k = el.getAttribute("data-shared"); if (t[k]) el.outerHTML = t[k]; });
      initAsk();
    }).catch(function () {});
  }
  document.addEventListener("DOMContentLoaded", function () { initShared(); initEmbed(); initMenu(); initOnPage(); initFilters(); initTools(); initSearch(); initMap(); initTable(); initCompare(); initCharts(); initHistory(); initTimeline(); initHistoryCharts(); initHundred(); initAsk(); initLike(); });
})();
