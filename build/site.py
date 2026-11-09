"""Stage 3: build the IDEA Atlas website as plain static files.

Reads   clean/output/districts.csv, clean/output/zip_lookup.json, build/geo/*.json
Writes  site/tools/idea-atlas/...   (upload this folder as is)

Run:    python build/site.py [--preview]
        --preview adds "noindex" so search engines skip the private preview.
"""
from __future__ import annotations

import csv
import html
import json
import math
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measures import (BASE, CATEGORIES, MAP_MEASURES, MEASURES, SITE, SOURCES, STATUS,  # noqa: E402
                      STATE_NOTES, STATUS_TEXT, VERSION)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / BASE.strip("/")
ASSETS = Path(__file__).resolve().parent / "assets"
PREVIEW = "--preview" in sys.argv
E = html.escape

KEEP_UPPER = {"ISD", "CISD", "USD", "ROE", "BOCES", "KIPP", "CSD", "SD", "ESD", "II", "III", "IV", "VI", "JT",
              "NYC", "PS", "HS", "MS", "LLC", "INC", "LEA", "UFSD", "CUSD", "CCSD", "SAU", "RSU", "MSAD", "CUD",
              "UHSD", "ESC", "IU", "STEM", "STEAM", "DC", "USA", "US", "PK", "K-12", "K-8", "ISD#", "R-I", "R-II"}


def nice_name(name: str) -> str:
    """Districts reported in all capitals are shown in title case; others as reported."""
    if not isinstance(name, str):
        return ""
    if name != name.upper() or not re.search(r"[A-Z]{3}", name):
        return name
    out = []
    for w in name.split(" "):
        core = re.sub(r"[^A-Z0-9#\-]", "", w)
        if core in KEEP_UPPER or re.fullmatch(r"[A-Z]?\d+[A-Z]?|#\d+|[A-Z]-\d+", core):
            out.append(w)
        else:
            out.append(re.sub(r"[A-Za-z]+", lambda m: m.group(0).capitalize(), w.lower()))
    s = " ".join(out)
    return re.sub(r"\b(Of|And|The|In|For|At)\b", lambda m: m.group(0).lower(), s).replace("Mc", "Mc")


def fmt(v: float, unit: str) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    if unit == "usd":
        return f"${v:,.0f}"
    return f"{v:,.1f}"


def cell(v, status: str, unit: str) -> str:
    code, text = STATUS.get(status, ("5", "Not reported"))
    if code == "0":
        return fmt(v, unit)
    if code == "1":
        return f"at least {fmt(v, unit)}"
    return text


# ---------------------------------------------------------------- page frame

def page(title: str, body: str, *, desc: str, path: str, scripts: tuple[str, ...] = (),
         styles: tuple[str, ...] = (), crumbs: list[tuple[str, str]] | None = None) -> str:
    robots = '<meta name="robots" content="noindex, nofollow">' if PREVIEW else ""
    css = "".join(f'<link rel="stylesheet" href="{BASE}assets/{s}">' for s in styles)
    js = "".join(f'<script src="{BASE}assets/{s}" defer></script>' for s in scripts)
    nav = ""
    if crumbs:
        items = "".join(f'<li><a href="{u}">{E(t)}</a></li>' for t, u in crumbs)
        nav = f'<nav class="crumbs" aria-label="Breadcrumb"><ol>{items}<li aria-current="page">{E(title)}</li></ol></nav>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)} | IDEA Atlas</title>
<meta name="description" content="{E(desc)}">
{robots}
<link rel="canonical" href="{SITE}{path}">
<link rel="stylesheet" href="{BASE}assets/atlas.css">{css}
{js}
</head>
<body>
<a class="skip" href="#main">Skip to main content</a>
<header class="site">
  <div class="wrap">
    <a class="brand" href="{BASE}"><span class="brand-name">IDEA Atlas</span>
      <span class="brand-sub">Special education data for every U.S. school district</span></a>
    <nav aria-label="IDEA Atlas">
      <ul>
        <li><a href="{BASE}">Map and search</a></li>
        <li><a href="{BASE}table/">Table</a></li>
        <li><a href="{BASE}methods/">Methods and sources</a></li>
        <li><a href="{SITE}/tools/">All tools</a></li>
      </ul>
    </nav>
  </div>
</header>
<main id="main" class="wrap">
{nav}
{body}
</main>
<footer class="site">
  <div class="wrap">
    <p>IDEA Atlas, version {VERSION}. Built from public federal data by
      <a href="{SITE}/">Dr. Suman Rath</a>. <a href="{BASE}methods/#cite">How to cite</a> ·
      <a href="{SITE}/contact/">Report an error</a> · <a href="{BASE}download/">Download the data</a></p>
    <p>General information only, not legal advice. Figures describe what was reported, not the quality of a district's services.</p>
  </div>
</footer>
</body>
</html>
"""


def write(rel: str, text: str) -> None:
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------- data prep

def classify(values: np.ndarray) -> list[float]:
    """Five map classes. Many zeros (common for restraint or arrests) get a class of their own."""
    v = values[~np.isnan(values)]
    if len(v) == 0:
        return []
    zero_share = (v == 0).mean()
    if zero_share > 0.2:
        pos = v[v > 0]
        qs = np.unique(np.round(np.quantile(pos, [0.25, 0.5, 0.75]), 1)) if len(pos) else []
        return [0.0] + [float(q) for q in qs if q > 0]
    qs = np.unique(np.round(np.quantile(v, [0.2, 0.4, 0.6, 0.8]), 1))
    return [float(q) for q in qs]


def main() -> int:
    d = pd.read_csv(ROOT / "clean" / "output" / "districts.csv", dtype={"leaid": str, "zip": str, "part_of": str},
                    low_memory=False)
    d = d[~d.status.isin(["Closed", "Inactive", "Future"])].copy()
    d["display"] = d.name.map(nice_name)
    d = d.sort_values(["state", "display"]).reset_index(drop=True)
    keys = [m[0] for m in MEASURES]
    units = {m[0]: m[4] for m in MEASURES}

    # treat any figure flagged "at least" or ok as present for medians
    def present(k):
        st = d[k + "_status"].astype(str)
        return d[k].where(st.isin(["ok", "ok_partial", "ok_minimum"]))

    nat_med = {k: float(np.nanmedian(present(k))) if present(k).notna().any() else np.nan for k in keys}
    st_med = {k: present(k).groupby(d.state).median().to_dict() for k in keys}
    breaks = {k: classify(present(k).to_numpy(dtype=float)) for k in MAP_MEASURES}

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "data" / "zip").mkdir(parents=True)
    (OUT / "assets").mkdir(parents=True)

    # ---- assets
    for f in ASSETS.iterdir():
        if f.name == "atlas.js":
            (OUT / "assets" / f.name).write_text(f.read_text().replace('var BASE = "/tools/idea-atlas/";', f'var BASE = "{BASE}";'))
        else:
            shutil.copy(f, OUT / "assets" / f.name)
    geo = Path(__file__).resolve().parent / "geo"
    for f in ("base.json", "s.json", "states.json"):
        shutil.copy(geo / f, OUT / "data" / f)

    # ---- values.json: everything the map, search, and table need, in compact form
    vals = []
    stats = []
    for _, r in d.iterrows():
        row, codes = [], ""
        for k in keys:
            st = str(r[k + "_status"])
            code = STATUS.get(st, ("5", ""))[0]
            v = r[k]
            row.append(None if code not in ("0", "1") or pd.isna(v) else (round(float(v), 1) if units[k] != "usd" else int(round(v))))
            codes += code
        vals.append(row)
        stats.append(codes)
    payload = {
        "version": VERSION,
        "measures": [{"key": m[0], "group": m[1], "label": m[2], "short": m[3], "unit": m[4],
                      "source": f"{SOURCES[m[5]][0]}, {SOURCES[m[5]][1]}", "den": m[6],
                      "map": m[0] in MAP_MEASURES, "breaks": breaks.get(m[0], []),
                      "national_median": None if math.isnan(nat_med[m[0]]) else round(nat_med[m[0]], 1)}
                     for m in MEASURES],
        "status": STATUS_TEXT,
        "ids": d.leaid.tolist(),
        "names": [[n, s, (c or "").title() if isinstance(c, str) else ""] for n, s, c in zip(d.display, d.state, d.city)],
        "enrollment": [None if pd.isna(x) else int(x) for x in d.enrollment],
        "values": vals,
        "codes": stats,
        "check": [i for i, x in enumerate(d.crdc_count_check.fillna(False)) if bool(x)],
        "state_notes": STATE_NOTES,
    }
    (OUT / "data" / "values.json").write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")

    # ---- ZIP lookup in small files by first two digits
    zl = json.loads((ROOT / "clean" / "output" / "zip_lookup.json").read_text())
    known = set(d.leaid)
    shards = defaultdict(dict)
    for z, lst in zl.items():
        keep = [x for x in lst if x[0] in known]
        if keep:
            shards[z[:2]][z] = keep
    for k, v in shards.items():
        (OUT / "data" / "zip" / f"{k}.json").write_text(json.dumps(v, separators=(",", ":")))

    # ---- download
    dl = OUT / "download"
    dl.mkdir()
    fname = f"idea-atlas-districts-v{VERSION}.csv"
    d.drop(columns=["display"]).to_csv(dl / fname, index=False)
    write("download/index.html", download_page(fname, len(d)))

    # ---- pages
    write("index.html", home_page(len(d)))
    write("table/index.html", table_page())
    write("methods/index.html", methods_page())
    children = d[d.part_of.notna()].groupby("part_of")
    kids_of = {k: g for k, g in children}
    by_id = d.set_index("leaid")
    n = 0
    for _, r in d.iterrows():
        write(f"district/{r.leaid}/index.html", district_page(r, st_med, nat_med, kids_of, by_id))
        n += 1
    if PREVIEW:
        write("robots.txt", "User-agent: *\nDisallow: /\n")
    total = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"Built {n:,} district pages; site size {total / 1e6:,.0f} MB at {OUT}")
    return 0


# ---------------------------------------------------------------- pages

def home_page(n: int) -> str:
    body = f"""
<h1>IDEA Atlas</h1>
<p class="lede">Special education data for every U.S. school district, from public federal sources.
Search for a district by ZIP code or name, or explore the map. Every figure links to its source.</p>

<section aria-labelledby="find-h" class="panel">
  <h2 id="find-h">Find a district</h2>
  <form id="search-form" role="search" novalidate>
    <label for="q">ZIP code or district name</label>
    <div class="row">
      <input id="q" name="q" type="search" autocomplete="off" spellcheck="false" aria-describedby="q-hint">
      <button type="submit">Search</button>
    </div>
    <p id="q-hint" class="hint">For example, 07042 or Montclair.</p>
  </form>
  <div id="results" aria-live="polite"></div>
</section>

<section aria-labelledby="map-h" class="panel">
  <h2 id="map-h">Map</h2>
  <p class="hint">The map shows the same figures as the <a href="{BASE}table/">table</a>, which works well with a screen reader.
  Select a district on the map, or use the search above, to open its profile.</p>
  <div class="controls">
    <div><label for="measure">Show</label> <select id="measure"></select></div>
    <div><label for="zoom-state">Go to state</label> <select id="zoom-state"><option value="">United States</option></select></div>
    <div class="check"><input type="checkbox" id="hs-layer"> <label for="hs-layer">Show high school districts</label></div>
  </div>
  <p id="measure-note" class="note"></p>
  <div id="map" role="region" aria-label="Map of school districts. Use arrow keys to move and plus or minus to zoom." tabindex="0"></div>
  <div id="legend" aria-labelledby="legend-h"><h3 id="legend-h">Legend</h3><ul id="legend-list"></ul></div>
  <p id="map-status" class="visually-hidden" aria-live="polite"></p>
</section>

<section aria-labelledby="about-h">
  <h2 id="about-h">What this tool shows</h2>
  <p>IDEA Atlas covers {n:,} public school districts, including charter school districts. It brings together federal data on
  who receives special education services, where students learn, how students leave school, discipline and safety,
  Section 504 plans, funding, and child poverty. The figures describe what districts and states reported. They are not grades,
  and they cannot show the quality of a district's services. A family's own experience, and the district's own reports, add what numbers cannot.</p>
  <p>Read the <a href="{BASE}methods/">methods and sources</a> to see how each figure is made and what it leaves out.</p>
</section>
"""
    return page("Special education data for every U.S. school district", body,
                desc="Search any U.S. school district by ZIP code to see federal special education data: students served, settings, graduation, discipline, Section 504, funding, and poverty.",
                path=BASE, scripts=("maplibre-gl.js", "atlas.js"), styles=("maplibre-gl.css",))


def table_page() -> str:
    body = f"""
<h1>Table of districts</h1>
<p class="lede">Choose a state and a topic to see every district's figures in a sortable table. You can download what you see.</p>
<div class="controls">
  <div><label for="t-state">State</label> <select id="t-state"><option value="">Choose a state</option></select></div>
  <div><label for="t-group">Topic</label> <select id="t-group"></select></div>
  <div><label for="t-filter">Filter by name</label> <input id="t-filter" type="search" autocomplete="off"></div>
  <div><button type="button" id="t-download" disabled>Download this table (CSV)</button></div>
</div>
<p id="t-status" aria-live="polite" class="hint">Choose a state to begin.</p>
<div id="t-wrap" class="table-wrap" tabindex="0" role="region" aria-labelledby="t-caption" hidden>
  <table id="t-table"><caption id="t-caption"></caption><thead></thead><tbody></tbody></table>
</div>
<p class="hint">Column headings are buttons: press one to sort by that column, and again to reverse the order.
Words such as "Withheld for privacy" explain why a figure is not shown. See <a href="{BASE}methods/#rules">data rules</a>.</p>
"""
    return page("Table of districts", body, desc="Sortable table of special education figures for every school district in a state.",
                path=BASE + "table/", scripts=("atlas.js",), crumbs=[("IDEA Atlas", BASE)])


def download_page(fname: str, n: int) -> str:
    body = f"""
<h1>Download the data</h1>
<p class="lede">The full data set, one row per district ({n:,} rows), as a CSV file you can open in Excel or any statistics program.</p>
<p><a class="button" href="{BASE}download/{fname}" download>Download {E(fname)}</a></p>
<p>Each measure has a matching column ending in <code>_status</code> that says whether the figure is a real number
or why it is not shown. The <a href="{BASE}methods/#dictionary">data dictionary</a> describes every column.
Code and processed data are shared under a Creative Commons Attribution 4.0 license. The original federal data are in the public domain.</p>
<p>Please <a href="{BASE}methods/#cite">cite IDEA Atlas</a> with its version number ({VERSION}) so others can find the same figures.</p>
"""
    return page("Download the data", body, desc="Download the full IDEA Atlas data set as a CSV file.",
                path=BASE + "download/", crumbs=[("IDEA Atlas", BASE)])


def compare_row(label: str, k: str, unit: str, r, st_med, nat_med) -> str:
    v, s = r[k], str(r[k + "_status"])
    sm = st_med[k].get(r.state, np.nan)
    nm = nat_med[k]
    return (f"<tr><th scope=\"row\">{E(label)}</th><td>{E(cell(v, s, unit))}</td>"
            f"<td>{E(fmt(sm, unit)) or '—'}</td><td>{E(fmt(nm, unit)) or '—'}</td></tr>")


def section(title: str, intro: str, rows: list[str], src: list[str], sid: str, unit_note: str, extra: str = "") -> str:
    sources = "; ".join(f"{SOURCES[s][0]}, {SOURCES[s][1]}" for s in src)
    return f"""
<section aria-labelledby="{sid}">
  <h2 id="{sid}">{E(title)}</h2>
  {intro}
  <div class="table-wrap" role="region" tabindex="0" aria-labelledby="{sid}-cap">
  <table class="profile">
    <caption id="{sid}-cap">{E(title)}: {E(unit_note)}</caption>
    <thead><tr><th scope="col">Measure</th><th scope="col">This district</th><th scope="col">State median</th><th scope="col">National median</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
  </div>
  {extra}
  <p class="source">Source: {E(sources)}. <a href="{BASE}methods/#sources">About the sources</a></p>
</section>"""


def district_page(r, st_med, nat_med, kids_of, by_id) -> str:
    name = r.display
    lab = {m[0]: m[2] for m in MEASURES}
    unit = {m[0]: m[4] for m in MEASURES}
    meta = []
    if isinstance(r.city, str) and r.city:
        meta.append(f"{r.city.title()}, {r.state_name.title()}")
    if isinstance(r.district_type, str):
        meta.append(r.district_type)
    if isinstance(r.grade_low, str) and isinstance(r.grade_high, str):
        meta.append(f"Grades {r.grade_low} to {r.grade_high}")
    if pd.notna(r.enrollment):
        meta.append(f"{r.enrollment:,.0f} students enrolled (2024–25)")
    meta.append(f"NCES district ID {r.leaid}")
    parent = ""
    if isinstance(r.part_of, str) and r.part_of in by_id.index:
        p = by_id.loc[r.part_of]
        parent = (f'<p class="note">This district is part of <a href="{BASE}district/{r.part_of}/">{E(p.display)}</a>. '
                  f"Civil rights, finance, and poverty figures are reported for {E(p.display)} as a whole.</p>")
    kids = ""
    if r.leaid in kids_of:
        g = kids_of[r.leaid]
        items = "".join(f'<li><a href="{BASE}district/{k.leaid}/">{E(k.display)}</a></li>' for k in g.itertuples())
        kids = (f'<details class="kids"><summary>This record combines {len(g)} districts</summary>'
                f"<p>Enrollment and IDEA figures add up these districts. Other sources report the city as one district.</p><ul>{items}</ul></details>")

    # at a glance
    glance = []
    if str(r.id_rate_status) == "ok":
        glance.append(f"In 2024–25, {fmt(r.id_rate, 'per100')} of every 100 students enrolled had an IEP served by the district.")
    if str(r.env_80plus_status) == "ok":
        glance.append(f"{fmt(r.env_80plus, 'per100')} of every 100 students with IEPs spent at least 80% of the day in a general class.")
    if str(r.grad_regular_status) == "ok":
        glance.append(f"Of students with IEPs who left school in 2023–24, {fmt(r.grad_regular, 'per100')} of every 100 left with a regular diploma.")
    if str(r.oos_idea_status) == "ok" and str(r.oos_nodis_status) == "ok":
        glance.append(f"In 2023–24, {fmt(r.oos_idea, 'per100')} of every 100 students with IEPs received an out-of-school suspension, "
                      f"compared with {fmt(r.oos_nodis, 'per100')} of every 100 students without disabilities.")
    glance_html = ("<section aria-labelledby=\"g-h\" class=\"glance\"><h2 id=\"g-h\">At a glance</h2><ul>"
                   + "".join(f"<li>{E(x)}</li>" for x in glance) + "</ul></section>") if glance else ""

    def rows(ks):
        return [compare_row(lab[k], k, unit[k], r, st_med, nat_med) for k in ks]

    cat_rows = []
    order = sorted(CATEGORIES, key=lambda c: -(r[c[0]] if str(r[c[0] + "_status"]) == "ok" and pd.notna(r[c[0]]) else -1))
    for k, label in order:
        cat_rows.append(f"<tr><th scope=\"row\">{E(label)}</th><td>{E(cell(r[k], str(r[k + '_status']), 'per100'))}</td></tr>")
    cats = f"""
  <div class="table-wrap" role="region" tabindex="0" aria-labelledby="cat-cap">
  <table class="profile narrow"><caption id="cat-cap">Disability categories, largest first, per 100 school-age students with IEPs</caption>
  <thead><tr><th scope="col">Federal category</th><th scope="col">This district</th></tr></thead>
  <tbody>{''.join(cat_rows)}</tbody></table></div>"""

    check = ""
    if bool(r.crdc_count_check) if pd.notna(r.crdc_count_check) else False:
        check = ('<p class="note"><strong>Please check with the district.</strong> The number of students with IEPs in the civil rights data '
                 f"({r.crdc_enr_idea:,.0f}) is very different from the IDEA count ({r.idea_count:,.0f}). "
                 "The figures in this section use the civil rights count, so they may not be reliable.</p>")
    partial = ""
    if bool(r.crdc_partial) if pd.notna(r.crdc_partial) else False:
        partial = '<p class="note">Some schools in this district withheld or did not report an item, so the figures in this section are minimums.</p>'

    det = r.determination_2026 if isinstance(r.determination_2026, str) else "Not available"
    state_note = f'<p class="note">{E(STATE_NOTES[r.state])}</p>' if r.state in STATE_NOTES else ""
    body = f"""
<h1>{E(name)}</h1>
<p class="meta">{E(' · '.join(meta))}</p>
{parent}{kids}
{glance_html}
{section("Who is served", state_note, rows(["id_rate", "pct_504"]), ["idea_cc", "ccd", "crdc"], "s-who", "per 100 students enrolled", cats)}
{section("Where students learn", "<p>Share of school-age students with IEPs in each setting.</p>", rows(["env_80plus", "env_lt40", "env_separate"]), ["idea_env"], "s-where", "per 100 students with IEPs, ages 5 to 21")}
{section("Leaving school", "<p>How students with IEPs, ages 14 to 21, left school during the year.</p>", rows(["grad_regular", "dropout"]), ["idea_exit"], "s-leave", "per 100 students with IEPs who left school")}
{section("Discipline and safety", check + partial, rows(["oos_idea", "oos_nodis", "oos_504", "expulsion_idea", "restraint_physical_idea", "restraint_mechanical_idea", "seclusion_idea", "referral_idea", "arrest_idea"]), ["crdc"], "s-disc", "per 100 students in each group")}
{section("Funding", "", rows(["spend_per_pupil", "idea_federal_per_student"]), ["fin", "idea_cc"], "s-fund", "dollars")}
{section("Community", "", rows(["child_poverty"]), ["saipe"], "s-comm", "per 100 children ages 5 to 17")}
<section aria-labelledby="s-state">
  <h2 id="s-state">State IDEA rating</h2>
  <p>Each year the U.S. Department of Education rates how each state carries out IDEA. In 2026, {E(r.state_name.title())} was rated <strong>{E(det)}</strong>.
  The rating describes the state, not this district. <a href="{BASE}methods/#det">What the ratings mean</a></p>
  <p class="source">Source: {E(SOURCES['det'][0])}, {E(SOURCES['det'][1])}.</p>
</section>
<section aria-labelledby="s-more">
  <h2 id="s-more">Using these figures</h2>
  <p>Medians are the middle value of districts with a figure: half of districts are above and half below.
  They give context, not a target. Some figures come from different school years. See <a href="{BASE}methods/">methods and sources</a>.</p>
  <p>Cite this page: Rath, S. (2026). <cite>IDEA Atlas: Special education data for every U.S. school district</cite> (Version {VERSION}). {E(name)}. {SITE}{BASE}district/{r.leaid}/</p>
</section>
"""
    desc = f"Special education data for {name}, {r.state_name.title()}: students with IEPs, settings, graduation, discipline, Section 504, funding, and child poverty."
    return page(f"{name}, {r.state}", body, desc=desc, path=f"{BASE}district/{r.leaid}/",
                crumbs=[("IDEA Atlas", BASE), (r.state_name.title(), f"{BASE}table/?state={r.state}")])


def methods_page() -> str:
    src_rows = "".join(f"<tr><th scope=\"row\">{E(v[0])}</th><td>{E(v[1])}</td><td>{E(v[2])}</td></tr>" for v in SOURCES.values())
    dict_rows = "".join(f"<tr><th scope=\"row\"><code>{m[0]}</code></th><td>{E(m[2])}</td><td>{E(m[6])}</td></tr>" for m in MEASURES)
    status_rows = "".join(f"<tr><th scope=\"row\"><code>{k}</code></th><td>{E(v[1] or 'A real figure')}</td></tr>" for k, v in STATUS.items())
    body = f"""
<h1>Methods and sources</h1>
<p class="lede">How every figure in IDEA Atlas is made, where it comes from, and what it cannot tell you.</p>

<nav aria-label="On this page" class="toc"><ul>
<li><a href="#what">What the tool shows</a></li><li><a href="#sources">Sources</a></li><li><a href="#rules">Data rules</a></li>
<li><a href="#measures">How each measure is calculated</a></li><li><a href="#zip">ZIP code search</a></li>
<li><a href="#det">State ratings</a></li><li><a href="#limits">Known limits</a></li><li><a href="#dictionary">Data dictionary</a></li>
<li><a href="#updates">Updates and versions</a></li><li><a href="#cite">How to cite</a></li></ul></nav>

<section aria-labelledby="what"><h2 id="what">What the tool shows</h2>
<p>I built IDEA Atlas so that families, educators, and researchers can see, in one place, what public federal data say about special education
in each school district. It shows who is served, where students learn, how students leave school, discipline and safety, Section 504 plans,
funding, and child poverty. It does not rank or grade districts. The figures describe what was reported.</p></section>

<section aria-labelledby="sources"><h2 id="sources">Sources</h2>
<p>Every figure comes from a public federal source. Each file is downloaded unchanged, dated, and checked, and a copy is kept.</p>
<div class="table-wrap" role="region" tabindex="0" aria-labelledby="src-cap"><table><caption id="src-cap">Sources and school years</caption>
<thead><tr><th scope="col">Source</th><th scope="col">Year</th><th scope="col">Agency</th></tr></thead><tbody>{src_rows}</tbody></table></div>
<p>The finance figures come from the Census Bureau's Annual Survey of School System Finances. It is the same district finance collection that the
National Center for Education Statistics publishes as the F-33 file, and the Census Bureau releases it about a year sooner.</p></section>

<section aria-labelledby="rules"><h2 id="rules">Data rules</h2>
<ul>
<li><strong>Rates per 100.</strong> Most figures are shown per 100 students in a group, so districts of different sizes can be read the same way.</li>
<li><strong>Minimum group of 10.</strong> A rate is not shown when the group it describes has fewer than 10 students.</li>
<li><strong>Withheld for privacy.</strong> Agencies withhold small numbers to protect students. These cells are never estimated.</li>
<li><strong>At least.</strong> When a small part of a figure is withheld, the rest is shown as a minimum ("at least").</li>
<li><strong>Civil rights skip codes.</strong> In the 2023–24 civil rights files, a student count of -9 means the question was skipped because the school reported no incidents. It is read as zero.</li>
<li><strong>Combined records.</strong> New York City is reported as one district in some files and as 32 geographic districts in others. IDEA Atlas shows one combined New York City record and keeps the 32 districts as linked records.</li>
<li><strong>Count check.</strong> When a district's civil rights count of students with IEPs is very different from its IDEA count, its discipline figures carry a note.</li>
</ul>
<div class="table-wrap" role="region" tabindex="0" aria-labelledby="st-cap"><table><caption id="st-cap">Status words used in the data</caption>
<thead><tr><th scope="col">Status</th><th scope="col">Meaning on the site</th></tr></thead><tbody>{status_rows}</tbody></table></div></section>

<section aria-labelledby="measures"><h2 id="measures">How each measure is calculated</h2>
<p>Each rate is the number of students in a category divided by the number in the group, times 100. The group for each measure is listed in the
<a href="#dictionary">data dictionary</a>. Discipline rates count students, not incidents, and add students who received one suspension to those who received more than one.
Spending per student is current spending divided by fall enrollment from the finance survey. Federal IDEA money per student is federal IDEA revenue the district received through the state, divided by its IDEA count.</p>
<p>The map sorts districts into five shades from light to dark. Each shade holds about the same number of districts. When many districts report zero, zero has its own shade.
Shades show more or less of something. They do not mean better or worse.</p></section>

<section aria-labelledby="zip"><h2 id="zip">ZIP code search</h2>
<p>ZIP codes and school districts do not share borders. IDEA Atlas uses the Census ZIP code areas and the NCES district boundary files to list every district
that covers part of a ZIP code, starting with the one that covers the most land. Charter school districts have no boundary, so search them by name.</p></section>

<section aria-labelledby="det"><h2 id="det">State ratings</h2>
<p>Each year the U.S. Department of Education reviews how each state carries out IDEA and gives one of four ratings: meets requirements,
needs assistance, needs intervention, or needs substantial intervention. The 2026 ratings are based on federal fiscal year 2024 data.
A rating describes the state, not any one district.</p></section>

<section aria-labelledby="limits"><h2 id="limits">Known limits</h2>
<ul>
<li>Sources cover different school years. Each figure shows its own year.</li>
<li>Federal files reflect what states and districts reported. Reporting errors carry through, and agencies sometimes revise files.</li>
<li>The IDEA count can include children the district serves who are not enrolled, such as preschoolers and students placed in private schools by their parents. This raises the rate per 100 enrolled in some places.</li>
<li>Small districts often have withheld figures.</li>
{''.join(f'<li>{E(v)}</li>' for v in STATE_NOTES.values())}
<li>In the 2023–24 civil rights data, counts of nonbinary students were withheld by the Department of Education. Totals include students reported as male or female.</li>
<li>ZIP code areas are approximations of mail routes.</li>
<li>The figures describe what was reported, not the quality of a district's services.</li>
<li>This is general information, not legal advice.</li>
</ul></section>

<section aria-labelledby="dictionary"><h2 id="dictionary">Data dictionary</h2>
<div class="table-wrap" role="region" tabindex="0" aria-labelledby="dd-cap"><table><caption id="dd-cap">Measures in the download file</caption>
<thead><tr><th scope="col">Column</th><th scope="col">Measure</th><th scope="col">Group it is counted against</th></tr></thead><tbody>{dict_rows}</tbody></table></div></section>

<section aria-labelledby="updates"><h2 id="updates">Updates and versions</h2>
<p>A check runs every month. When an agency posts a new file, IDEA Atlas is rebuilt and reviewed before it goes live, and the version number changes.
This is version {VERSION}.</p></section>

<section aria-labelledby="cite"><h2 id="cite">How to cite</h2>
<p>Rath, S. (2026). <cite>IDEA Atlas: Special education data for every U.S. school district</cite> (Version {VERSION}) [Online tool and data set]. {SITE}{BASE}</p>
<p>To report an error, please use the <a href="{SITE}/contact/">contact page</a>.</p></section>
"""
    return page("Methods and sources", body, desc="How IDEA Atlas figures are made: sources, data rules, calculations, limits, and data dictionary.",
                path=BASE + "methods/", crumbs=[("IDEA Atlas", BASE)])


if __name__ == "__main__":
    sys.exit(main())
