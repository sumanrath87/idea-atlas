/* IDEA Atlas report assistant.
   A few questions, then a finished report for a family, a school leader, or a researcher, ready to print or save as a PDF.
   Everything happens in the browser: the report reuses each district page's own sentences, chart data, and tables. */
(function () {
  "use strict";
  var A = null, ES = false, tr = null, esc = null, BASE = "/";

  var TOPICS = [
    { id: "s-who", en: "Who is served", es: "Quiénes reciben servicios", keys: ["id_rate", "pct_504"], chart: "range", trend: "i", terms: ["iep", "504", "per100", "typical"] },
    { id: "s-where", en: "Where students learn", es: "Dónde aprenden", keys: ["env_80plus", "env_lt40", "env_separate"], chart: "settings", terms: ["settings"] },
    { id: "s-leave", en: "Leaving school", es: "Al terminar la escuela", keys: ["grad_regular", "dropout"], chart: "exit", terms: ["leaving"] },
    { id: "s-disc", en: "Discipline and safety", es: "Disciplina y seguridad", keys: ["oos_idea", "oos_nodis", "oos_504", "expulsion_idea", "restraint_physical_idea", "restraint_mechanical_idea", "seclusion_idea", "referral_idea", "arrest_idea"], chart: "range", trend: "d", terms: ["discipline"] },
    { id: "s-fund", en: "Funding", es: "Fondos", keys: ["spend_per_pupil", "idea_federal_per_student"], chart: "range", trend: "s", terms: ["spending", "idea_money"] },
    { id: "s-comm", en: "Community", es: "Comunidad", keys: ["child_poverty"], chart: "range", trend: "p", terms: ["poverty"] },
    { id: "hist", en: "Over the years: your state and the nation", es: "A lo largo de los años: su estado y el país", keys: [], terms: ["years"] }
  ];
  var AUD = {
    family: { en: ["A family", "A clear guide in plain words, with pictures, explanations of every term, and the questions you want to bring to a meeting."],
              es: ["Una familia", "Una guía clara en palabras sencillas, con dibujos, explicaciones de cada término y las preguntas que quiere llevar a una reunión."] },
    leader: { en: ["A school leader", "A district profile with a one-page summary, the district beside its state, the nation, and districts you choose, and trends over time."],
              es: ["Un líder escolar", "Un perfil del distrito con un resumen de una página, el distrito junto a su estado, el país y los distritos que elija, y las tendencias."] },
    research: { en: ["A researcher", "Every figure with its status, the full detail tables, trend tables, the data dictionary, methods, and the citation."],
                es: ["Un investigador", "Cada cifra con su estado, las tablas detalladas, las tablas de tendencias, el diccionario de datos, los métodos y la cita."] }
  };
  var DOI = "10.5281/zenodo.24083644";

  function L(o) { return ES ? o.es : o.en; }
  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function fetchDoc(url) { return fetch(url).then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); }).then(function (t) { return new DOMParser().parseFromString(t, "text/html"); }); }
  function getJSON(url) { return fetch(url).then(function (r) { return r.json(); }); }
  function cdOf(doc) { var s = doc.getElementById("chart-data"); return s ? JSON.parse(s.textContent) : {}; }
  function districtUrl(id, es) { return BASE + (es ? "es/distrito/" : "district/") + id + "/"; }
  function today() {
    var d = new Date(), m = ES ? ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
      : ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    return ES ? d.getDate() + " de " + m[d.getMonth()] + " de " + d.getFullYear() : m[d.getMonth()] + " " + d.getDate() + ", " + d.getFullYear();
  }

  /* ------------------------------------------------------------ the assistant */
  var state = { step: 0, aud: "family", id: null, name: "", topics: TOPICS.map(function (t) { return t.id; }), comps: [], asks: null, own: "", tables: true, dict: true };
  var STEPS = function () {
    return [tr("Who it is for", "Para quién es"), tr("District", "Distrito"), tr("Topics", "Temas"),
      state.aud === "family" ? tr("Your questions", "Sus preguntas") : state.aud === "leader" ? tr("Compare", "Comparar") : tr("Detail", "Detalle"),
      tr("Review", "Revisar")];
  };

  function init() {
    A = window.ATLAS; if (!A) return;
    var root = $("#rpt-app"); if (!root) return;
    ES = A.ES; tr = A.tr; esc = A.esc; BASE = A.BASE;
    var q = new URLSearchParams(location.search);
    if (q.get("aud") && AUD[q.get("aud")]) state.aud = q.get("aud");
    if (q.get("id")) state.id = q.get("id");
    if (q.get("topics")) state.topics = q.get("topics").split(",");
    if (q.get("comps")) state.comps = q.get("comps").split(",").filter(Boolean);
    if (q.get("own")) state.own = q.get("own");
    if (q.get("tables") === "0") state.tables = false;
    if (q.get("dict") === "0") state.dict = false;
    var go = q.get("go") === "1";
    root.innerHTML = '<nav aria-label="' + tr("Steps", "Pasos") + '"><ol class="rpt-steps"></ol></nav><form id="rpt-form" novalidate><div id="rpt-step"></div>' +
      '<p id="rpt-msg" class="rpt-msg" aria-live="assertive"></p><div class="rpt-nav"><button type="button" class="secondary" id="rpt-back">' + tr("Back", "Atrás") +
      '</button><button type="submit" id="rpt-next">' + tr("Next", "Siguiente") + "</button></div></form>";
    $("#rpt-back").addEventListener("click", function () { save(); if (state.step > 0) { state.step--; show(true); } });
    $("#rpt-form").addEventListener("submit", function (e) { e.preventDefault(); next(); });
    if (state.id) {
      A.load().then(function () {
        var i = A.index()[state.id];
        if (i != null) state.name = A.data().names[i][0];
        if (go) build(); else show(false);
      });
    } else show(false);
  }

  function stepsNav() {
    var s = STEPS();
    $(".rpt-steps").innerHTML = s.map(function (t, i) {
      return '<li' + (i === state.step ? ' aria-current="step" class="on"' : i < state.step ? ' class="done"' : "") + '><span class="n">' + (i + 1) + "</span>" + esc(t) + "</li>";
    }).join("");
  }

  function show(focus) {
    stepsNav();
    $("#rpt-msg").textContent = "";
    $("#rpt-back").hidden = state.step === 0;
    $("#rpt-next").textContent = state.step === 4 ? tr("Create my report", "Crear mi informe") : tr("Next", "Siguiente");
    var box = $("#rpt-step"), h = "";
    var head = function (t, sub) { return '<legend><span class="rpt-k">' + tr("Step ", "Paso ") + (state.step + 1) + tr(" of 5", " de 5") + "</span>" + esc(t) + "</legend>" + (sub ? '<p class="hint">' + esc(sub) + "</p>" : ""); };
    if (state.step === 0) {
      h = '<fieldset class="rpt-fs">' + head(tr("Who is the report for?", "¿Para quién es el informe?"), tr("Each report is written for its reader.", "Cada informe está escrito para quien lo va a leer.")) +
        '<div class="rpt-cards">' + Object.keys(AUD).map(function (k) {
          var a = L(AUD[k]);
          return '<label class="rpt-card"><input type="radio" name="aud" value="' + k + '"' + (state.aud === k ? " checked" : "") + '><span class="t">' + esc(a[0]) + '</span><span class="d">' + esc(a[1]) + "</span></label>";
        }).join("") + "</div></fieldset>";
    } else if (state.step === 1) {
      h = '<fieldset class="rpt-fs">' + head(tr("Which district?", "¿Qué distrito?"), tr("Search by ZIP code or name, then choose the district.", "Busque por código postal o nombre y elija el distrito.")) +
        (state.id ? '<p class="rpt-chosen">' + tr("Chosen: ", "Elegido: ") + "<strong>" + esc(state.name) + "</strong></p>" : "") +
        '<label for="rpt-q">' + tr("ZIP code or district name", "Código postal o nombre del distrito") + '</label><div class="row"><input id="rpt-q" type="search" autocomplete="off">' +
        '<button type="button" class="secondary" id="rpt-find">' + tr("Search", "Buscar") + '</button></div><div id="rpt-res" aria-live="polite"></div></fieldset>';
    } else if (state.step === 2) {
      h = '<fieldset class="rpt-fs">' + head(tr("Which topics?", "¿Qué temas?"), tr("All are chosen. Untick any you do not need.", "Todos están elegidos. Desmarque los que no necesite.")) +
        '<div class="rpt-checks">' + TOPICS.map(function (t) {
          return '<label class="rpt-check"><input type="checkbox" name="topic" value="' + t.id + '"' + (state.topics.indexOf(t.id) >= 0 ? " checked" : "") + ">" + esc(L(t)) + "</label>";
        }).join("") + "</div></fieldset>";
    } else if (state.step === 3 && state.aud === "family") {
      h = '<fieldset class="rpt-fs">' + head(tr("Which questions do you want to bring?", "¿Qué preguntas quiere llevar?"), tr("They will be printed with space for your notes.", "Se imprimirán con espacio para sus notas.")) +
        '<div class="rpt-checks" id="rpt-asks"><p>' + tr("Loading…", "Cargando…") + '</p></div><label for="rpt-own">' + tr("Add your own questions, one on each line", "Agregue sus propias preguntas, una en cada línea") +
        '</label><textarea id="rpt-own" rows="3">' + esc(state.own) + "</textarea></fieldset>";
    } else if (state.step === 3 && state.aud === "leader") {
      h = '<fieldset class="rpt-fs">' + head(tr("Compare with up to three districts", "Compare con hasta tres distritos"), tr("Districts like this one are suggested. You can also search for others.", "Se sugieren distritos parecidos. También puede buscar otros.")) +
        '<div class="rpt-checks" id="rpt-comps"><p>' + tr("Finding districts like this one…", "Buscando distritos parecidos…") + '</p></div>' +
        '<label for="rpt-cq">' + tr("Add another district by ZIP code or name", "Agregue otro distrito por código postal o nombre") + '</label><div class="row"><input id="rpt-cq" type="search" autocomplete="off">' +
        '<button type="button" class="secondary" id="rpt-cfind">' + tr("Search", "Buscar") + '</button></div><div id="rpt-cres" aria-live="polite"></div></fieldset>';
    } else if (state.step === 3) {
      h = '<fieldset class="rpt-fs">' + head(tr("How much detail?", "¿Cuánto detalle?")) + '<div class="rpt-checks">' +
        '<label class="rpt-check"><input type="checkbox" id="rpt-tables"' + (state.tables ? " checked" : "") + ">" + tr("Full detail tables (every count behind the figures)", "Tablas detalladas (cada conteo detrás de las cifras)") + "</label>" +
        '<label class="rpt-check"><input type="checkbox" id="rpt-dict"' + (state.dict ? " checked" : "") + ">" + tr("Data dictionary and methods", "Diccionario de datos y métodos") + "</label></div></fieldset>";
    } else {
      var a = L(AUD[state.aud]);
      h = '<fieldset class="rpt-fs">' + head(tr("Review your report", "Revise su informe")) + '<dl class="rpt-review">' +
        "<div><dt>" + tr("For", "Para") + "</dt><dd>" + esc(a[0]) + "</dd></div><div><dt>" + tr("District", "Distrito") + "</dt><dd>" + esc(state.name) + "</dd></div>" +
        "<div><dt>" + tr("Topics", "Temas") + "</dt><dd>" + esc(TOPICS.filter(function (t) { return state.topics.indexOf(t.id) >= 0; }).map(L).join(", ")) + "</dd></div>" +
        (state.aud === "leader" ? "<div><dt>" + tr("Compared with", "Comparado con") + "</dt><dd>" + (state.comps.length ? esc(state.comps.map(nameOf).join(", ")) : tr("Only the state and the nation", "Solo el estado y el país")) + "</dd></div>" : "") +
        "</dl>" + '<fieldset class="rpt-sub"><legend>' + tr("Language of the report", "Idioma del informe") + '</legend><div class="rpt-checks rpt-row">' +
        '<label class="rpt-check"><input type="radio" name="lang" value="en"' + (!ES ? " checked" : "") + '>English</label>' +
        '<label class="rpt-check"><input type="radio" name="lang" value="es"' + (ES ? " checked" : "") + '>Español</label></div></fieldset></fieldset>';
    }
    box.innerHTML = h;
    if (state.step === 1) wireSearch("#rpt-q", "#rpt-find", "#rpt-res", function (i) {
      var D = A.data(); state.id = D.ids[i]; state.name = D.names[i][0]; state.comps = []; state.asks = null;
      $("#rpt-res").innerHTML = '<p class="rpt-chosen">' + tr("Chosen: ", "Elegido: ") + "<strong>" + esc(state.name) + "</strong>. " + tr("Press Next to continue.", "Pulse Siguiente para continuar.") + "</p>";
    });
    if (state.step === 3 && state.aud === "family") loadAsks();
    if (state.step === 3 && state.aud === "leader") loadComps();
    if (focus) { var lg = $("#rpt-step legend"); if (lg) { lg.tabIndex = -1; lg.focus(); } }
  }

  function nameOf(id) { var D = A.data(), i = A.index()[id]; return i == null ? id : D.names[i][0]; }

  function wireSearch(qs, bs, rs, pick) {
    var run = function () {
      var text = $(qs).value.trim(), out = $(rs);
      if (!text) { out.innerHTML = "<p>" + tr("Type a ZIP code or a district name.", "Escriba un código postal o el nombre de un distrito.") + "</p>"; return; }
      out.innerHTML = "<p>" + tr("Searching…", "Buscando…") + "</p>";
      A.load().then(function () {
        var D = A.data(), I = A.index();
        var render = function (list) {
          if (!list.length) { out.innerHTML = "<p>" + tr("No district matched. Try another name or ZIP code.", "Ningún distrito coincide. Pruebe con otro nombre o código postal.") + "</p>"; return; }
          out.innerHTML = '<ul class="pick">' + list.slice(0, 12).map(function (i) {
            return '<li><button type="button" class="secondary" data-i="' + i + '">' + tr("Choose ", "Elegir ") + esc(D.names[i][0]) + '</button> <span class="sub">' + esc((D.names[i][2] ? D.names[i][2] + ", " : "") + D.names[i][1]) + "</span></li>";
          }).join("") + "</ul>";
          $$("button[data-i]", out).forEach(function (b) { b.addEventListener("click", function () { pick(+b.getAttribute("data-i")); }); });
          var f = $("button", out); if (f) f.focus();
        };
        if (/^\d{5}$/.test(text)) {
          getJSON(BASE + "data/zip/" + text.slice(0, 2) + ".json").then(function (z) {
            render((z[text] || []).filter(function (x) { return x[0] in I; }).map(function (x) { return I[x[0]]; }));
          }).catch(function () { render([]); });
        } else {
          var norm = function (s) { return s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9 ]/g, " ").replace(/\s+/g, " ").trim(); };
          var w = norm(text).split(" "), hits = [];
          for (var i = 0; i < D.ids.length; i++) {
            var hay = norm(D.names[i][0] + " " + D.names[i][2] + " " + D.names[i][1]);
            if (w.every(function (x) { return hay.indexOf(x) >= 0; })) hits.push(i);
          }
          hits.sort(function (a, b) { return (D.enrollment[b] || 0) - (D.enrollment[a] || 0); });
          render(hits);
        }
      });
    };
    $(bs).addEventListener("click", run);
    $(qs).addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); run(); } });
  }

  function loadAsks() {
    var box = $("#rpt-asks");
    fetchDoc(districtUrl(state.id, ES)).then(function (doc) {
      var qs = $$("ul.ask li", doc).map(function (li) { return li.textContent.trim(); });
      if (state.asks == null) state.asks = qs.slice();
      box.innerHTML = qs.map(function (q, i) {
        return '<label class="rpt-check"><input type="checkbox" name="ask" value="' + i + '"' + (state.asks.indexOf(q) >= 0 ? " checked" : "") + ">" + esc(q) + "</label>";
      }).join("");
      box.setAttribute("data-qs", JSON.stringify(qs));
    });
  }

  function similar(cd) {
    var D = A.data(), I = A.index(), pj = -1;
    D.measures.forEach(function (m, j) { if (m.key === "child_poverty") pj = j; });
    var pov = function (i) { var c = D.codes[i][pj]; return (c === "0" || c === "1") ? D.values[i][pj] : null; };
    var i0 = I[state.id]; if (i0 == null || !D.enrollment[i0] || pov(i0) == null) return [];
    var e0 = D.enrollment[i0], p0 = pov(i0), st = D.names[i0][1], hits = [];
    for (var i = 0; i < D.ids.length; i++) {
      if (i === i0 || D.names[i][1] !== st || !D.enrollment[i] || pov(i) == null) continue;
      hits.push({ i: i, d: Math.abs(Math.log(D.enrollment[i] / e0)) + Math.abs(pov(i) - p0) / 8 });
    }
    hits.sort(function (a, b) { return a.d - b.d; });
    return hits.slice(0, 5).map(function (h) { return D.ids[h.i]; });
  }

  function loadComps() {
    A.load().then(function () {
      var box = $("#rpt-comps"), sug = similar();
      state.comps.forEach(function (c) { if (sug.indexOf(c) < 0) sug.push(c); });
      var draw = function () {
        box.innerHTML = sug.length ? sug.map(function (id) {
          return '<label class="rpt-check"><input type="checkbox" name="comp" value="' + id + '"' + (state.comps.indexOf(id) >= 0 ? " checked" : "") + ">" + esc(nameOf(id)) + "</label>";
        }).join("") : "<p>" + tr("No similar districts were found. You can search for districts to add.", "No se encontraron distritos parecidos. Puede buscar distritos para agregar.") + "</p>";
      };
      if (!state.comps.length) state.comps = sug.slice(0, 3);
      draw();
      wireSearch("#rpt-cq", "#rpt-cfind", "#rpt-cres", function (i) {
        var id = A.data().ids[i];
        if (id === state.id) return;
        save();
        if (sug.indexOf(id) < 0) sug.push(id);
        if (state.comps.indexOf(id) < 0) state.comps.push(id);
        draw();
        $("#rpt-cres").innerHTML = "<p>" + esc(nameOf(id)) + tr(" added.", " agregado.") + "</p>";
      });
    });
  }

  function save() {
    var f = $("#rpt-form"); if (!f) return;
    if (state.step === 0) { var a = $('input[name="aud"]:checked', f); if (a) state.aud = a.value; }
    if (state.step === 2) state.topics = $$('input[name="topic"]:checked', f).map(function (x) { return x.value; });
    if (state.step === 3 && state.aud === "family") {
      var box = $("#rpt-asks"), qs = box && box.getAttribute("data-qs") ? JSON.parse(box.getAttribute("data-qs")) : null;
      if (qs) state.asks = $$('input[name="ask"]:checked', f).map(function (x) { return qs[+x.value]; });
      var o = $("#rpt-own"); if (o) state.own = o.value;
    }
    if (state.step === 3 && state.aud === "leader" && $("#rpt-comps input")) state.comps = $$('input[name="comp"]:checked', f).map(function (x) { return x.value; });
    if (state.step === 3 && state.aud === "research") { state.tables = $("#rpt-tables").checked; state.dict = $("#rpt-dict").checked; }
  }

  function next() {
    save();
    var msg = $("#rpt-msg");
    if (state.step === 1 && !state.id) { msg.textContent = tr("Please choose a district first.", "Primero elija un distrito."); return; }
    if (state.step === 2 && !state.topics.length) { msg.textContent = tr("Please choose at least one topic.", "Elija al menos un tema."); return; }
    if (state.step === 3 && state.aud === "leader" && state.comps.length > 3) { msg.textContent = tr("Please choose no more than three districts.", "Elija como máximo tres distritos."); return; }
    if (state.step < 4) { state.step++; show(true); return; }
    var lang = ($('input[name="lang"]:checked') || {}).value || (ES ? "es" : "en");
    if ((lang === "es") !== ES) {                    // the other language's assistant builds the report in that language
      var p = new URLSearchParams({ aud: state.aud, id: state.id, topics: state.topics.join(","), comps: state.comps.join(","), own: state.own,
        tables: state.tables ? "1" : "0", dict: state.dict ? "1" : "0", go: "1" });
      location.href = BASE + (lang === "es" ? "es/informe/" : "report/") + "?" + p.toString();
      return;
    }
    build();
  }

  /* ------------------------------------------------------------ the report */
  function build() {
    var app = $("#rpt-app"), out = $("#rpt-out");
    app.hidden = true; $(".rpt-intro") && ($(".rpt-intro").hidden = true);
    out.hidden = false;
    out.innerHTML = '<p class="rpt-wait" role="status">' + tr("Making your report…", "Preparando su informe…") + "</p>";
    var lang = ES ? "es" : "en";
    var jobs = [fetchDoc(districtUrl(state.id, ES)), fetchDoc(districtUrl(state.id, false)), getJSON(BASE + (ES ? "data/terms_es.json" : "data/terms.json")),
      getJSON(BASE + (ES ? "data/measures_es.json" : "data/measures.json")), getJSON(BASE + "data/labels.json"), A.load()];
    if (state.topics.indexOf("hist") >= 0) jobs.push(fetchDoc(BASE + (ES ? "es/historia/" : "history/"))); else jobs.push(Promise.resolve(null));
    var comps = state.aud === "leader" ? state.comps.slice(0, 3) : [];
    comps.forEach(function (c) { jobs.push(fetchDoc(districtUrl(c, false))); });
    Promise.all(jobs).then(function (r) {
      var ctx = { doc: r[0], en: r[1], terms: r[2], meas: {}, labels: r[4], hist: r[6], cd: cdOf(r[1]), comps: [] };
      r[3].forEach(function (m) { ctx.meas[m.key] = m; });
      ctx.cdL = cdOf(r[0]);
      comps.forEach(function (c, k) { ctx.comps.push({ id: c, name: nameOf(c), cd: cdOf(r[7 + k]) }); });
      render(ctx, lang);
    }).catch(function () {
      out.innerHTML = '<p class="rpt-msg">' + tr("Sorry, the report could not be made. Please try again.", "No se pudo preparar el informe. Inténtelo de nuevo.") + "</p>";
    });
  }

  function textOf(el) { return el ? el.textContent.replace(/\s+/g, " ").trim() : ""; }
  function plainItems(sec, which) {
    var uls = $$("ul.plain", sec);
    var ul = which === "trend" ? (function () { var h = $("h3.ot-h", sec); if (!h) return null; var n = h.nextElementSibling; while (n && !(n.matches && n.matches("ul.plain"))) n = n.nextElementSibling; return n; })() : uls[0];
    return ul ? $$("li", ul).map(function (li) { return li.innerHTML; }) : [];
  }
  function list(items) { return items.length ? '<ul class="plain">' + items.map(function (x) { return "<li>" + x + "</li>"; }).join("") + "</ul>" : ""; }
  function fmt(v, unit) { return v == null ? "—" : unit === "usd" ? "$" + Math.round(v).toLocaleString("en-US") : (+v).toFixed(1); }
  function statusWord(code) {
    var en = { "1": "at least", "2": "Withheld for privacy", "3": "Fewer than 10 students", "4": "Flagged for data quality", "5": "Not reported", "6": "No students in this group" };
    var es = { "1": "al menos", "2": "Retenido por privacidad", "3": "Menos de 10 estudiantes", "4": "Marcado por calidad de datos", "5": "No se informó", "6": "No hay estudiantes en este grupo" };
    return (ES ? es : en)[code] || "";
  }
  function cell(m, unit) {
    if (!m) return "—";
    if (m[1] === "0") return fmt(m[0], unit);
    if (m[1] === "1") return statusWord("1") + " " + fmt(m[0], unit);
    return statusWord(m[1]);
  }
  function chartBox(cls, caption) {
    return '<figure class="chart rpt-fig ' + cls + '" aria-hidden="true"><figcaption>' + esc(caption) + '</figcaption><div class="chart-body"></div></figure>';
  }
  function hundred(v, sentence) {
    if (!(v >= 1 && v <= 100)) return "";
    var k = Math.round(v), h = "";
    for (var i = 0; i < 100; i++) h += '<span class="' + (i < k ? "on" : "") + '"></span>';
    return '<div class="rpt-100"><div class="h100" role="img" aria-label="' + esc(tr("A picture of 100 students with " + k + " shaded.", "Un dibujo de 100 estudiantes con " + k + " sombreados.")) + '">' + h +
      '</div><p>' + esc(sentence) + "</p></div>";
  }
  function numbersTable(keys, cd, meas, cap) {
    var unit = function (k) { return (meas[k] || {}).unit; };
    var rows = keys.map(function (k) {
      var m = cd.m[k]; if (!m) return "";
      return '<tr><th scope="row">' + esc((meas[k] || {}).short || k) + "</th><td>" + esc(cell(m, unit(k))) + "</td><td>" + fmt(m[3], unit(k)) + "</td><td>" +
        (m[2] != null ? fmt(m[2], unit(k)) + tr(" to ", " a ") + fmt(m[4], unit(k)) : "—") + "</td><td>" + fmt(m[5], unit(k)) + "</td></tr>";
    }).join("");
    return '<table class="profile rpt-t"><caption>' + esc(cap) + '</caption><thead><tr><th scope="col">' + tr("Measure", "Medida") + '</th><th scope="col">' + tr("This district", "Este distrito") +
      '</th><th scope="col">' + tr("State median", "Mediana estatal") + '</th><th scope="col">' + tr("Middle half of state districts", "Mitad central del estado") + '</th><th scope="col">' + tr("National median", "Mediana nacional") +
      "</th></tr></thead><tbody>" + rows + "</tbody></table>";
  }
  function detailTables(sid, cd, labels) {
    var w = function (x) { return typeof x === "number" ? (labels[x] != null ? labels[x] : "") : x; };
    var ids = { "s-who": ["s-who-cap", "cat-cap", "fd-who"], "s-where": ["s-where-cap", "fd-where-school", "fd-where-early"], "s-leave": ["s-leave-cap", "fd-leave"],
      "s-disc": ["s-disc-cap", "fd-disc"], "s-fund": ["s-fund-cap", "fd-fund"], "s-comm": ["s-comm-cap", "fd-comm"] }[sid] || [];
    return (cd.t || []).filter(function (t) { return ids.indexOf(t.id) >= 0 && t.id !== sid + "-cap"; }).map(function (t) {
      return '<table class="profile rpt-t ' + t.k + '"><caption>' + esc(w(t.c)) + "</caption><thead><tr>" + t.h.map(function (x) { return '<th scope="col">' + esc(w(x)) + "</th>"; }).join("") +
        "</tr></thead><tbody>" + t.r.map(function (row) { return '<tr><th scope="row">' + esc(w(row[0])) + "</th>" + row.slice(1).map(function (c) { return "<td>" + esc(w(c)) + "</td>"; }).join("") + "</tr>"; }).join("") + "</tbody></table>";
    }).join("");
  }
  function trendTable(code, cd, label) {
    var pts = (cd.tr || {})[code]; if (!pts) return "";
    var yl = code === "s" ? "fy" : code === "p" ? "y" : "sy";
    var comp = (cd.tr || {})[code + "c"], cmap = {};
    (comp || []).forEach(function (p) { cmap[p[0]] = p[1]; });
    return '<table class="profile rpt-t narrow"><caption>' + esc(label) + '</caption><thead><tr><th scope="col">' + tr("Year", "Año") + '</th><th scope="col">' + esc(comp ? tr("Students with IEPs", "Estudiantes con IEP") : label) + "</th>" +
      (comp ? '<th scope="col">' + tr("Students without disabilities", "Estudiantes sin discapacidades") + "</th>" : "") + "</tr></thead><tbody>" + pts.map(function (p) {
        return '<tr><th scope="row">' + A.yearLabel(yl, p[0]) + "</th><td>" + fmt(p[1], code === "s" ? "usd" : "") + "</td>" + (comp ? "<td>" + (cmap[p[0]] != null ? fmt(cmap[p[0]]) : "—") + "</td>" : "") + "</tr>";
      }).join("") + "</tbody></table>";
  }

  function render(ctx, lang) {
    var out = $("#rpt-out"), doc = ctx.doc, cd = ctx.cd, aud = state.aud, meas = ctx.meas;
    var name = textOf($("h1", doc)), st = ctx.cdL.st || cd.st;
    var facts = $$("dl.facts > div", doc).map(function (d) { return [textOf($("dt", d)), textOf($("dd", d))]; });
    var title = { family: tr("A family guide to special education", "Guía para familias sobre la educación especial"),
      leader: tr("District profile for school leaders", "Perfil del distrito para líderes escolares"),
      research: tr("Research profile", "Perfil para investigación") }[aud];
    var chosen = TOPICS.filter(function (t) { return state.topics.indexOf(t.id) >= 0; });
    var parts = [], n = 0, toc = [];
    var sec = function (id, h, body) { n++; toc.push([id, n + ". " + h]); parts.push('<section class="rpt-sec" aria-labelledby="' + id + '"><h2 id="' + id + '"><span class="rpt-num">' + n + "</span>" + esc(h) + "</h2>" + body + "</section>"); };

    // cover
    var cover = '<section class="rpt-cover" aria-label="' + tr("Cover", "Portada") + '"><div class="rpt-brand"><span class="rpt-logo">IDEA Atlas</span><span class="rpt-by">' +
      tr("A project by Dr. Suman Rath", "Un proyecto del Dr. Suman Rath") + '</span></div><p class="rpt-kind">' + esc(title) + '</p><h1 class="rpt-title">' + esc(name) + "</h1>" +
      '<dl class="facts rpt-facts">' + facts.map(function (f) { return "<div><dt>" + esc(f[0]) + "</dt><dd>" + esc(f[1]) + "</dd></div>"; }).join("") + "</dl>" +
      '<div class="rpt-cover-foot"><p>' + tr("Prepared ", "Preparado el ") + today() + " · " + tr("Version ", "Versión ") + "2026.1</p><p>" + location.origin + BASE + (ES ? "es/distrito/" : "district/") + state.id + "/</p>" +
      "<p>" + tr("Cite as: ", "Cómo citar: ") + "Rath, S. (2026). IDEA Atlas: Special education data for every U.S. school district (Version 2026.1). https://doi.org/" + DOI + "</p></div></section>";

    // about / how to read
    var how = {
      family: tr("This guide describes what " + name + " reported to the federal government about special education. Each part starts in plain words. Figures are shown “per 100,” so a small district and a large one can be read the same way. The “typical district” is the middle district in the state. These figures are not grades, and they cannot show the quality of a district's services; your own experience and the district's own reports add what numbers cannot.",
        "Esta guía describe lo que " + name + " informó al gobierno federal sobre la educación especial. Cada parte empieza con palabras sencillas. Las cifras se muestran «de cada 100», para que un distrito pequeño y uno grande se lean igual. El «distrito típico» es el distrito del medio en el estado. Estas cifras no son calificaciones y no pueden mostrar la calidad de los servicios de un distrito; su propia experiencia y los informes del distrito agregan lo que los números no pueden."),
      leader: tr("This profile places " + name + " beside the typical district in " + st + ", the middle half of " + st + " districts, the nation, and any districts you chose. Figures are per 100 students in each group unless shown in dollars. They describe what was reported and are offered for planning and conversation, not as ratings.",
        "Este perfil coloca a " + name + " junto al distrito típico de " + st + ", la mitad central de los distritos de " + st + ", el país y los distritos que eligió. Las cifras son por cada 100 estudiantes de cada grupo, salvo las que están en dólares. Describen lo que se informó y se ofrecen para planificar y conversar, no como calificaciones."),
      research: tr("This profile lists every IDEA Atlas figure for " + name + " with its status, the medians and middle half used for context, the counts behind each figure, and the trend series. Status words mark figures that are withheld for privacy, based on fewer than 10 students, or flagged for data quality; such figures are never estimated.",
        "Este perfil enumera cada cifra de IDEA Atlas para " + name + " con su estado, las medianas y la mitad central usadas como contexto, los conteos detrás de cada cifra y las series de tendencias. Las palabras de estado señalan cifras retenidas por privacidad, con menos de 10 estudiantes o marcadas por la calidad de los datos; esas cifras nunca se estiman.")
    }[aud];

    if (aud === "family") {
      var glance = $$(".glance ul > li", doc).map(function (li) { return li.innerHTML; });
      var hund = "";
      var m = cd.m || {};
      if (m.id_rate && m.id_rate[1] === "0") hund += hundred(m.id_rate[0], tr("About " + fmt(m.id_rate[0]) + " of every 100 students have an IEP.", "Aproximadamente " + fmt(m.id_rate[0]) + " de cada 100 estudiantes tienen un IEP."));
      if (m.env_80plus && m.env_80plus[1] === "0") hund += hundred(m.env_80plus[0], tr("About " + fmt(m.env_80plus[0]) + " of every 100 students with IEPs spend most of the day in a general class.", "Aproximadamente " + fmt(m.env_80plus[0]) + " de cada 100 estudiantes con IEP pasan la mayor parte del día en una clase general."));
      if (m.grad_regular && m.grad_regular[1] === "0") hund += hundred(m.grad_regular[0], tr("About " + fmt(m.grad_regular[0]) + " of every 100 who left school earned a regular diploma.", "Aproximadamente " + fmt(m.grad_regular[0]) + " de cada 100 que salieron obtuvieron un diploma regular."));
      sec("r-glance", tr("At a glance", "De un vistazo"), list(glance) + (hund ? '<div class="rpt-100s">' + hund + "</div>" : ""));
    } else {
      // summary table of the chosen topics, and where the district stands apart (neutral wording)
      var keys = [];
      chosen.forEach(function (t) { keys = keys.concat(t.keys); });
      var diff = keys.filter(function (k) { var x = cd.m[k]; return x && x[1] === "0" && x[2] != null && (x[0] < x[2] || x[0] > x[4]); }).map(function (k) {
        var x = cd.m[k], u = (meas[k] || {}).unit;
        return (meas[k] || {}).short + ": " + fmt(x[0], u) + (x[0] > x[4] ? tr(", above the middle half of " + st + " districts (", ", por encima de la mitad central de los distritos de " + st + " (") : tr(", below the middle half of " + st + " districts (", ", por debajo de la mitad central de los distritos de " + st + " (")) + fmt(x[2], u) + tr(" to ", " a ") + fmt(x[4], u) + ").";
      });
      sec("r-sum", tr("Summary", "Resumen"), numbersTable(keys, cd, meas, tr("Key figures beside the state and the nation", "Cifras clave junto al estado y el país")) +
        "<h3>" + tr("Where this district is outside the middle half of " + st + " districts", "Dónde este distrito está fuera de la mitad central de los distritos de " + st) + "</h3>" +
        (diff.length ? list(diff.map(esc)) : "<p>" + tr("On every figure shown, this district is within the middle half of " + st + " districts.", "En todas las cifras mostradas, este distrito está dentro de la mitad central de los distritos de " + st + ".") + "</p>") +
        '<p class="rpt-note">' + tr("Being outside the middle half means a figure is less common in the state. It is not, by itself, better or worse.", "Estar fuera de la mitad central quiere decir que una cifra es menos común en el estado. No es, por sí solo, mejor ni peor.") + "</p>");
      if (aud === "leader" && ctx.comps.length) {
        var head = '<th scope="col">' + tr("Measure", "Medida") + '</th><th scope="col">' + esc(name) + "</th>" + ctx.comps.map(function (c) { return '<th scope="col">' + esc(c.name) + "</th>"; }).join("") + '<th scope="col">' + tr("State median", "Mediana estatal") + "</th>";
        var rows = keys.map(function (k) {
          var u = (meas[k] || {}).unit;
          return '<tr><th scope="row">' + esc((meas[k] || {}).short) + "</th><td>" + esc(cell(cd.m[k], u)) + "</td>" + ctx.comps.map(function (c) { return "<td>" + esc(cell((c.cd.m || {})[k], u)) + "</td>"; }).join("") + "<td>" + fmt((cd.m[k] || [])[3], u) + "</td></tr>";
        }).join("");
        sec("r-comp", tr("Compared with similar districts", "Comparado con distritos parecidos"), "<p>" + tr("Districts compared: ", "Distritos comparados: ") + esc(ctx.comps.map(function (c) { return c.name; }).join(", ")) + ".</p>" +
          '<table class="profile rpt-t compare"><caption>' + tr("Side-by-side figures, per 100 students in each group unless shown in dollars", "Cifras lado a lado, por cada 100 estudiantes de cada grupo salvo las que están en dólares") + "</caption><thead><tr>" + head + "</tr></thead><tbody>" + rows + "</tbody></table>");
      }
    }

    // topic sections
    chosen.forEach(function (t) {
      if (t.id === "hist") return;
      var s = $('section[aria-labelledby="' + t.id + '"]', doc); if (!s) return;
      var intro = $$(":scope > p:not(.source):not(.hint):not(.howto), :scope > .note", s).map(function (p) { return '<p class="' + (p.classList.contains("note") ? "note" : "rpt-intro-p") + '">' + p.innerHTML + "</p>"; }).join("");
      var body = intro + list(plainItems(s));
      body += chartBox("c-main", t.chart === "settings" ? tr("Time in a general class", "Tiempo en una clase de educación general") : t.chart === "exit" ? tr("How students with IEPs left school", "Cómo salieron de la escuela los estudiantes con IEP") : tr("Where this district sits among " + st + " districts", "Dónde se ubica este distrito entre los distritos de " + st)).replace('class="chart rpt-fig c-main"', 'class="chart rpt-fig c-main" data-kind="' + t.chart + '" data-keys="' + t.keys.join(",") + '"');
      if (t.id === "s-who" && cd.cats && cd.cats.length) body += chartBox("c-cats", tr("Students with IEPs by federal category, per 100 students with IEPs", "Estudiantes con IEP por categoría federal, por cada 100 estudiantes con IEP"));
      var ot = plainItems(s, "trend");
      if (t.trend && ot.length) body += "<h3>" + tr("Over time", "A lo largo del tiempo") + "</h3>" + list(ot) + chartBox("c-trend", textOf($('figure[data-chart="trend"] figcaption', s))).replace('class="chart rpt-fig c-trend"', 'class="chart rpt-fig c-trend" data-code="' + t.trend + '"');
      if (aud !== "family") body += numbersTable(t.keys, cd, meas, L(t) + tr(": this district, the state, and the nation", ": este distrito, el estado y el país"));
      if (aud === "research" && state.tables) body += detailTables(t.id, cd, ctx.labels) + (t.trend ? trendTable(t.trend, cd, textOf($('figure[data-chart="trend"] figcaption', s)).split(",")[0]) : "");
      var tk = t.terms.slice(); $$("details.explain[data-term]", s).forEach(function (d) { var k = d.getAttribute("data-term"); if (tk.indexOf(k) < 0) tk.push(k); });
      if (aud === "family") body += '<div class="rpt-terms"><h3>' + tr("Words to know", "Palabras clave") + "</h3><dl>" + tk.map(function (k) {
        var q = $('details.explain[data-term="' + k + '"] summary', doc);
        return ctx.terms[k] ? "<dt>" + esc(q ? textOf(q) : k) + "</dt><dd>" + esc(ctx.terms[k]) + "</dd>" : "";
      }).join("") + "</dl></div>";
      var srcs = $$(":scope > p.source", s), src = srcs[srcs.length - 1];
      if (src) body += '<p class="source">' + esc(textOf(src).replace(/About the sources\.?$|Acerca de las fuentes\.?$/, "")) + "</p>";
      sec("r-" + t.id, L(t), body);
    });

    // state and nation over the years
    if (state.topics.indexOf("hist") >= 0 && ctx.hist) {
      var stName = cd.st, tpl = ctx.hist.querySelector('template[data-state="' + stName + '"]');
      var hb = "";
      if (tpl) hb += "<p class=\"rpt-intro-p\">" + esc(tpl.getAttribute("data-say")) + "</p><figure class=\"chart rpt-fig wide\" aria-hidden=\"true\"><figcaption>" +
        tr("Students served, per 100 public school students", "Estudiantes atendidos, por cada 100 estudiantes de escuelas públicas") + "</figcaption>" + tpl.innerHTML + "</figure>";
      var hm = $('section[aria-labelledby="h-many"] ul.plain', ctx.hist), hw = $('section[aria-labelledby="h-where"] ul.plain', ctx.hist);
      if (hm) hb += "<h3>" + tr("The nation", "El país") + "</h3>" + hm.outerHTML;
      if (hw) hb += hw.outerHTML;
      sec("r-hist", L(TOPICS[6]), hb + '<p class="source">' + tr("Source: Digest of Education Statistics (National Center for Education Statistics).", "Fuente: Digest of Education Statistics (Centro Nacional de Estadísticas de Educación).") + "</p>");
    }

    if (aud === "family") {
      var asks = (state.asks || $$("ul.ask li", doc).map(function (li) { return li.textContent.trim(); })).concat(state.own.split("\n").map(function (x) { return x.trim(); }).filter(Boolean));
      sec("r-ask", tr("Questions to bring", "Preguntas para llevar"), "<p>" + tr("Bring these to a meeting with the school or district, or to an IEP meeting. There is space below each question for notes.", "Lleve estas preguntas a una reunión con la escuela o el distrito, o a una reunión del IEP. Debajo de cada pregunta hay espacio para notas.") +
        '</p><ol class="rpt-asks">' + asks.map(function (q) { return "<li><span>" + esc(q) + '</span><div class="rpt-lines" aria-hidden="true"><span></span><span></span><span></span></div></li>'; }).join("") + "</ol>");
      var help = $('section[aria-labelledby="s-ask"] p:last-of-type', doc);
      sec("r-help", tr("Where to find help", "Dónde encontrar ayuda"), "<p>" + tr("For free, one-on-one help, every state has at least one federally funded Parent Training and Information Center. Find yours at ", "Para recibir ayuda gratuita y personal, cada estado tiene al menos un Centro de Capacitación e Información para Padres con fondos federales. Busque el suyo en ") +
        "<strong>parentcenterhub.org/find-your-center</strong>.</p><p>" + tr("This guide is general information, not legal advice.", "Esta guía es información general, no asesoría legal.") + "</p>");
    }
    if (aud === "research" && state.dict) {
      var D = A.data();
      sec("r-dict", tr("Data dictionary", "Diccionario de datos"), '<table class="profile rpt-t"><caption>' + tr("Measures, groups, and sources", "Medidas, grupos y fuentes") + '</caption><thead><tr><th scope="col">' + tr("Measure", "Medida") + '</th><th scope="col">' + tr("Group it is counted against", "Grupo de referencia") + '</th><th scope="col">' + tr("Source", "Fuente") + "</th></tr></thead><tbody>" +
        D.measures.map(function (x) { return '<tr><th scope="row">' + esc(x.label) + "</th><td>" + esc(x.den) + "</td><td>" + esc(x.source) + "</td></tr>"; }).join("") + "</tbody></table>" +
        "<h3>" + tr("Methods in brief", "Métodos en breve") + "</h3>" + list([
          tr("Rates are per 100 students in each group. A rate is not shown when the group has fewer than 10 students.", "Las tasas son por cada 100 estudiantes de cada grupo. No se muestra una tasa cuando el grupo tiene menos de 10 estudiantes."),
          tr("Withheld figures are never estimated. “At least” marks a figure with a withheld part.", "Las cifras retenidas nunca se estiman. «Al menos» señala una cifra con una parte retenida."),
          tr("Civil rights figures are summed from schools to districts; a count of -9 in 2023–24 is read as zero.", "Las cifras de derechos civiles se suman de las escuelas al distrito; un conteo de -9 en 2023–24 se lee como cero."),
          tr("Medians and the middle half (25th to 75th percentile) use districts with a figure.", "Las medianas y la mitad central (percentiles 25 a 75) usan los distritos con cifra."),
          tr("Trend years where a state reported in an unusual way are left out. Spending is in 2024 dollars (CPI-U).", "Los años de tendencia en que un estado informó de forma inusual se omiten. El gasto está en dólares de 2024 (IPC-U).")
        ].map(esc)) + "<p>" + tr("Full methods: ", "Métodos completos: ") + "<strong>" + location.origin + BASE + "methods/</strong>. " + tr("Data files: ", "Archivos de datos: ") + "<strong>" + location.origin + BASE + "download/</strong> " + tr("and", "y") + " <strong>https://doi.org/" + DOI + "</strong>.</p>");
    }

    var tocHtml = '<nav class="rpt-toc" aria-labelledby="r-toc-h"><h2 id="r-toc-h">' + tr("Contents", "Contenido") + "</h2><ol>" + toc.map(function (x) { return '<li><a href="#' + x[0] + '">' + esc(x[1].replace(/^\d+\.\s/, "")) + "</a></li>"; }).join("") + "</ol>" +
      '<p class="rpt-about">' + esc(how) + "</p></nav>";
    var bar = '<div class="rpt-bar"><button type="button" id="rpt-pdf">' + tr("Save as PDF", "Guardar como PDF") + '</button><button type="button" class="secondary" id="rpt-edit">' + tr("Change my choices", "Cambiar mis opciones") +
      '</button><p class="hint">' + tr("In the print window, choose “Save as PDF” as the printer. The PDF keeps headings and text that screen readers can read.", "En la ventana de impresión, elija «Guardar como PDF» como impresora. El PDF conserva los títulos y el texto que leen los lectores de pantalla.") + "</p></div>";
    out.innerHTML = bar + '<article class="rpt" lang="' + lang + '">' + cover + tocHtml + parts.join("") +
      '<footer class="rpt-end"><p>IDEA Atlas · ' + tr("A project by Dr. Suman Rath", "Un proyecto del Dr. Suman Rath") + " · " + location.origin + BASE + "</p><p>" +
      tr("Figures describe what was reported to the federal government, not the quality of a district's services.", "Las cifras describen lo que se informó al gobierno federal, no la calidad de los servicios de un distrito.") + "</p></footer></article>";
    document.title = name + " · " + title + " | IDEA Atlas";
    document.body.classList.add("rpt-on");
    drawCharts(out, ctx);
    $("#rpt-pdf").addEventListener("click", function () { window.print(); });
    $("#rpt-edit").addEventListener("click", function () { document.body.classList.remove("rpt-on"); out.hidden = true; $("#rpt-app").hidden = false; if ($(".rpt-intro")) $(".rpt-intro").hidden = false; state.step = 4; show(true); });
    var h = $(".rpt-title"); if (h) { h.tabIndex = -1; h.focus(); }
  }

  function drawCharts(out, ctx) {
    var cd = Object.assign({}, ctx.cd, { st: ctx.cdL.st || ctx.cd.st });
    if (ES && ctx.cdL.cats) cd.cats = ctx.cdL.cats;
    $$("figure.c-main", out).forEach(function (f) {
      var body = $(".chart-body", f), k = f.getAttribute("data-kind"), ok = true;
      if (k === "range") A.rangeChart(body, f.getAttribute("data-keys").split(","), cd, ctx.meas);
      else if (k === "settings") ok = cd.set ? A.partsBar(body, [[tr("80% or more of the day", "80% o más del día"), cd.set[0]], [tr("40% to 79%", "40% a 79%"), cd.set[1]], [tr("Less than 40%", "Menos del 40%"), cd.set[2]],
        [tr("Separate school, facility, home or hospital", "Escuela o centro separado, hogar u hospital"), cd.set[3]], [tr("Other places", "Otros lugares"), cd.set[4]]], ["#0d366b", "#1c5cab", "#3987e5", "#86b6ef", "#b9b4a8"]) : false;
      else if (k === "exit") ok = cd.ex ? A.partsBar(body, [[tr("Regular diploma", "Diploma regular"), cd.ex[0]], [tr("Alternate diploma or certificate", "Diploma alternativo o certificado"), cd.ex[1]], [tr("Reached the maximum age", "Llegó a la edad máxima"), cd.ex[2]],
        [tr("Dropped out", "Abandonó la escuela"), cd.ex[3]], [tr("Died", "Falleció"), cd.ex[4]]], ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]) : false;
      if (!ok) f.remove();
    });
    $$("figure.c-cats", out).forEach(function (f) { if (!A.catsChart($(".chart-body", f), cd.cats)) f.remove(); });
    $$("figure.c-trend", out).forEach(function (f) {
      var code = f.getAttribute("data-code");
      var ok = A.trendChart($(".chart-body", f), (cd.tr || {})[code], code === "s", (cd.tr || {})[code + "c"], code === "s" ? "fy" : code === "p" ? "y" : "sy");
      if (!ok) f.remove();
      $$(".explore", f).forEach(function (e) { e.remove(); });
    });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
