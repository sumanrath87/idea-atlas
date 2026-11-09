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
import es_site  # noqa: E402
from measures import (ATLAS_ORIGIN, BASE, CATEGORIES, MAP_MEASURES, MEASURES, SITE, SOURCES, STATUS,  # noqa: E402
                      STATE_NOTES, STATUS_TEXT, VERSION, TERMS, PLAIN, DOI)

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


GROUPS_BY: dict = {}  # 2023-24 civil rights counts by race and ethnicity: {leaid: [[group, enrolled, with IEPs, with IEPs suspended], ...]}
TRENDS: dict = {}     # district trend lines: {leaid: {"i": iep share, "s": spending, "p": child poverty}}
LABELS: dict = {}     # words repeated on every page (table captions, headings, row names), stored once in data/labels.json
NUMERIC = re.compile(r"^(at least )?[\d$,.\-–]+$|^—$")


def shared_label(x):
    """Replace a repeated word or phrase with its number in the shared label list; leave figures as they are."""
    if not isinstance(x, str) or NUMERIC.match(x):
        return x
    if x not in LABELS:
        LABELS[x] = len(LABELS)
    return LABELS[x]


LAST_CD: dict = {}    # chart data of the district page just built, reused by the Spanish page
TABLES: list = []      # tables for the page being built; written into its data block and built in the browser
SHORT_TERMS = [False]  # district pages carry only the question; the answer comes from one shared file


def explain(*keys: str) -> str:
    """Short "What is ...?" explainers: closed by default, one click to open, read well with a screen reader.
    On district pages the answer is filled from data/terms.json; without scripts a link leads to the glossary."""
    if SHORT_TERMS[0]:
        items = "".join(f'<details class="explain" data-term="{k}"><summary>{E(TERMS[k][0])}</summary>'
                        f'<p><a href="{BASE}methods/#term-{k}">Read the explanation</a></p></details>' for k in keys)
    else:
        items = "".join(f'<details class="explain"><summary>{E(TERMS[k][0])}</summary><p>{E(TERMS[k][1])}</p></details>' for k in keys)
    return f'<div class="explainers">{items}</div>'


ZERO_VERB = {"expulsion_idea": "expelled", "restraint_physical_idea": "physically restrained", "restraint_mechanical_idea": "mechanically restrained",
             "seclusion_idea": "secluded", "referral_idea": "referred to law enforcement", "arrest_idea": "arrested at school"}
ZERO_TEXT = {"oos_nodis": "No students without disabilities received an out-of-school suspension.",
             "oos_504": "No students with Section 504 plans received an out-of-school suspension.",
             "oos_idea": "No students with IEPs received an out-of-school suspension."}


def figs(text: str) -> str:
    """Escape a plain sentence and give its figures quiet emphasis; the state comparison in brackets stays soft."""
    h = E(text)
    h = re.sub(r"(?<!\()(\$[\d,]+|\b\d[\d,]*\.\d\b)", r'<span class="fig">\1</span>', h)
    h = re.sub(r", or ((?:about|nearly|fewer than) [^.]*)\.", r', or <span class="ev">\1</span>.', h)
    return re.sub(r"\((\$?[\d,]+(?:\.\d)?)\)", r'<span class="med">(\1)</span>', h)


def everyday(v: float) -> str:
    """A rate per 100 in words a family can picture: 'about 1 in 5', 'about half', 'nearly all'."""
    if v is None or pd.isna(v) or v <= 0:
        return ""
    if v < 1:
        return "fewer than 1 in 100"
    if v >= 95:
        return "nearly all"
    if 45 <= v <= 55:
        return "about half"
    if v <= 34:
        return f"about 1 in {round(100 / v)}"
    best = min(((k, d) for d in (3, 4, 5, 10) for k in range(1, d)), key=lambda kd: (abs(kd[0] / kd[1] - v / 100), kd[1]))
    return f"about {best[0]} in {best[1]}"


def add_everyday(sent: str, fv: str, v: float) -> str:
    """Close the sentence with the everyday version: '..., or about 1 in 5.'"""
    w = everyday(v)
    return sent[:-1] + f", or {w}." if w and sent.endswith(".") else sent


def plain_lines(r, keys, st_med) -> str:
    """Layer 1: one friendly sentence per measure, with a gentle comparison to the typical district in the state."""
    unit = {m[0]: m[4] for m in MEASURES}
    short = {m[0]: m[3] for m in MEASURES}
    state = r.state_name.title() if isinstance(r.state_name, str) else "the state"
    out, zeros = [], []
    for k in keys:
        v, st = r[k], str(r[k + "_status"])
        code, text = STATUS.get(st, ("5", "Not reported"))
        if code in ("0", "1") and pd.notna(v):
            if code == "0" and v == 0 and k in ZERO_VERB:
                zeros.append(ZERO_VERB[k]); continue
            fv = fmt(v, unit[k])
            sent = ZERO_TEXT[k] if (code == "0" and v == 0 and k in ZERO_TEXT) else PLAIN[k].format(v=fv)
            if code == "1":
                sent = sent.replace("About " + fv, "At least " + fv).replace("about " + fv, "at least " + fv)
            if unit[k] == "per100" and not (code == "0" and v == 0):
                sent = add_everyday(sent, fv, v)
            sm = st_med[k].get(r.state, np.nan)
            if code == "0" and pd.notna(sm):
                if sm == 0:
                    sent += f" In the typical district in {state}, it was 0." if v else f" The same is true of the typical district in {state}."
                else:
                    tol = max(0.1 * abs(sm), 0.5 if unit[k] == "per100" else 50)
                    word = "about the same as" if abs(v - sm) <= tol else ("higher than" if v > sm else "lower than")
                    sent += f" That is {word} the typical district in {state} ({fmt(sm, unit[k])})."
            out.append(sent)
        else:
            out.append(f"{short[k]}: {text.lower() if text else 'not reported'}.".capitalize())
    if zeros:
        lst = zeros[0] if len(zeros) == 1 else ", ".join(zeros[:-1]) + (", or " if len(zeros) > 2 else " or ") + zeros[-1]
        out.append(f"No students with IEPs were {lst}.")
    return '<ul class="plain">' + "".join(f"<li>{figs(x)}</li>" for x in out) + "</ul>"


# ---------------------------------------------------------------- page frame

UI = {
    "en": {"skip": "Skip to main content", "sub": "Special education data for every U.S. school district", "nav_label": "IDEA Atlas",
           "nav": [("", "Map and search"), ("table/", "Table"), ("compare/", "Compare"), ("history/", "History"), ("report/", "Make a report"), ("methods/", "Methods and sources")],
           "all_tools": "All tools", "crumb": "Breadcrumb", "suffix": "IDEA Atlas", "version": "Version",
           "foot1": 'IDEA Atlas, version {v}. Built from public federal data by <a href="{site}/">Dr. Suman Rath</a>. <a href="{base}methods/#cite">How to cite</a> · <a href="{site}/contact/">Report an error</a> · <a href="{base}download/">Download the data</a>',
           "foot2": "General information only, not legal advice. Figures describe what was reported, not the quality of a district's services.",
           "other": "Español", "other_label": "Ver esta página en español"},
    "es": {"skip": "Saltar al contenido principal", "sub": "Datos de educación especial para cada distrito escolar de EE. UU.", "nav_label": "IDEA Atlas en español",
           "nav": [("es/", "Buscar un distrito"), ("es/historia/", "Historia"), ("es/informe/", "Crear un informe")],
           "all_tools": "", "crumb": "Ruta de navegación", "suffix": "IDEA Atlas", "version": "Versión",
           "foot1": 'IDEA Atlas, versión {v}. Creado con datos federales públicos por <a href="{site}/">Dr. Suman Rath</a>. <a href="{site}/contact/">Informar un error</a>',
           "foot2": "Información general, no asesoría legal. Las cifras describen lo que se informó, no la calidad de los servicios de un distrito.",
           "other": "English", "other_label": "View this page in English"},
}


def page(title: str, body: str, *, desc: str, path: str, scripts: tuple[str, ...] = (),
         styles: tuple[str, ...] = (), crumbs: list[tuple[str, str]] | None = None, lang: str = "en", alt: str | None = None) -> str:
    """Page frame. alt is the same page in the other language, if there is one."""
    u = UI[lang]
    robots = '<meta name="robots" content="noindex, nofollow">' if PREVIEW else ""
    css = "".join(f'<link rel="stylesheet" href="{BASE}assets/{s}">' for s in styles)
    js = "".join(f'<script src="{BASE}assets/{s}" defer></script>' for s in scripts)
    nav = ""
    if crumbs:
        items = "".join(f'<li><a href="{u_}">{E(t)}</a></li>' for t, u_ in crumbs)
        nav = f'<nav class="crumbs" aria-label="{u["crumb"]}"><ol>{items}<li aria-current="page">{E(title)}</li></ol></nav>'
    other = "es" if lang == "en" else "en"
    alt_head = (f'<link rel="alternate" hreflang="{lang}" href="{ATLAS_ORIGIN}{path}">'
                f'<link rel="alternate" hreflang="{other}" href="{ATLAS_ORIGIN}{alt}">') if alt else ""
    switch = (f'<li class="lang"><a href="{alt}" hreflang="{other}" lang="{other}" aria-label="{E(u["other_label"])}">{u["other"]}</a></li>') if alt else ""
    links = "".join(f'<li><a href="{BASE}{p_}">{E(t)}</a></li>' for p_, t in u["nav"])
    tools = f'<li><a href="{SITE}/tools/">{u["all_tools"]}</a></li>' if u["all_tools"] else ""
    home = BASE + ("es/" if lang == "es" else "")
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,">
<title>{E(title)} | {u["suffix"]}</title>
<meta name="description" content="{E(desc)}">
{robots}
<link rel="canonical" href="{ATLAS_ORIGIN}{path}">{alt_head}
<link rel="stylesheet" href="{BASE}assets/atlas.css">{css}
{js}
</head>
<body>
<a class="skip" href="#main">{u["skip"]}</a>
<header class="site">
  <div class="wrap">
    <a class="brand" href="{home}"><span class="brand-name">IDEA Atlas</span>
      <span class="brand-sub">{E(u["sub"])}</span></a>
    <nav aria-label="{E(u["nav_label"])}">
      <ul>
        {links}
        {tools}
        {switch}
      </ul>
    </nav>
  </div>
</header>
<main id="main" class="wrap">
<p class="print-only print-head">IDEA Atlas · {E(title)} · {ATLAS_ORIGIN}{path} · {u["version"]} {VERSION}</p>
{nav}
{body}
</main>
<footer class="site">
  <div class="wrap">
    <p>{u["foot1"].format(v=VERSION, site=SITE, base=BASE)}</p>
    <p>{E(u["foot2"])}</p>
  </div>
</footer>
</body>
</html>
"""


def write(rel: str, text: str) -> None:
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{2,}", "\n", text)
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
    st_q = {k: (present(k).groupby(d.state).quantile(.25).to_dict(), present(k).groupby(d.state).quantile(.75).to_dict()) for k in keys}
    st_med["_q"] = st_q
    nat_med["_q"] = {k: (float(np.nanpercentile(present(k).dropna(), 25)), float(np.nanpercentile(present(k).dropna(), 75)))
                     if present(k).notna().any() else (np.nan, np.nan) for k in keys}
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
    (OUT / "data" / "terms.json").write_text(json.dumps({k: v[1] for k, v in TERMS.items()}, separators=(",", ":"), ensure_ascii=False))
    (OUT / "data" / "measures.json").write_text(json.dumps([{"key": m[0], "short": m[3], "unit": m[4]} for m in MEASURES], separators=(",", ":")))
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
    dpath0 = ROOT / "clean" / "output" / "detail.csv.gz"
    det0 = pd.read_csv(dpath0, dtype=str, index_col=0, keep_default_na=False) if dpath0.exists() else pd.DataFrame()
    out = d.drop(columns=["display"]).copy()
    if not det0.empty:
        out = add_counts(out, det0)
    out.to_csv(dl / fname, index=False)
    dname = ""
    if not det0.empty:
        import zipfile
        nice = det0.copy()
        nice.columns = [DETAIL_PREFIX[c.split("|", 1)[0]] + ": " + c.split("|", 1)[1] for c in nice.columns]
        nice.insert(0, "state", d.set_index("leaid").state.reindex(nice.index))
        nice.insert(0, "name", d.set_index("leaid").name.reindex(nice.index))
        nice.index.name = "leaid"
        dname = f"idea-atlas-detail-v{VERSION}.zip"
        with zipfile.ZipFile(dl / dname, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"idea-atlas-detail-v{VERSION}.csv", nice.to_csv())
    tname = ""
    tp = Path(__file__).resolve().parent / "history" / "district_trends.json.gz"
    if tp.exists():
        import gzip, zipfile
        tr_all = json.loads(gzip.open(tp).read())
        lines = ["leaid,measure,year,value"]
        nm = {"i": "students_with_ieps_per_100_enrolled (fall year)", "s": "current_spending_per_student_2024_dollars (fiscal year)", "p": "children_5_17_in_poverty_per_100 (estimate year)",
              "d": "out_of_school_suspension_students_with_ieps_per_100 (fall year)", "n": "out_of_school_suspension_students_without_disabilities_per_100 (fall year)"}
        for lid, ms in sorted(tr_all.items()):
            for k, ys in ms.items():
                for y, v in sorted(ys.items(), key=lambda kv: int(kv[0])):
                    lines.append(f"{lid},{nm[k].split(' ')[0]},{y},{v}")
        tname = f"idea-atlas-trends-v{VERSION}.zip"
        with zipfile.ZipFile(dl / tname, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"idea-atlas-trends-v{VERSION}.csv", "\n".join(lines) + "\n")
    write("download/index.html", download_page(fname, len(d), dname, len(det0.columns), tname))

    # ---- pages
    write("index.html", home_page(len(d)))
    write("table/index.html", table_page())
    write("methods/index.html", methods_page())
    import history_page
    write("es/index.html", es_site.home_es(BASE=BASE, page=page, n=len(d)))
    (OUT / "data" / "terms_es.json").write_text(json.dumps({k: v[1] for k, v in es_site.TERMS_ES.items()}, ensure_ascii=False, separators=(",", ":")))
    (OUT / "data" / "measures_es.json").write_text(json.dumps([{"key": m[0], "short": es_site.SHORT_ES[m[0]], "unit": m[4]} for m in MEASURES],
                                                              ensure_ascii=False, separators=(",", ":")))
    if (Path(__file__).resolve().parent / "history" / "national.json").exists():
        write("history/index.html", history_page.render(page, explain, BASE))
        write("es/historia/index.html", history_page.render_es(page, lambda *k: es_site.explain_es(BASE, *k, full=True), BASE, es_site.STATE_ES))
    write("compare/index.html", compare_page())
    sm = Path(__file__).resolve().parent / "history" / "state_measures.json"
    if sm.exists():
        shutil.copy(sm, OUT / "data" / "state_measures.json")
    write("report/index.html", report_page())
    write("es/informe/index.html", es_site.report_es(BASE=BASE, page=page))
    children = d[d.part_of.notna()].groupby("part_of")
    kids_of = {k: g for k, g in children}
    tpath = Path(__file__).resolve().parent / "history" / "district_trends.json.gz"
    if tpath.exists():
        import gzip
        TRENDS.update(json.loads(gzip.open(tpath).read()))
    gpath = ROOT / "clean" / "output" / "groups.csv.gz"
    if gpath.exists():
        order = ["AM", "AS", "BL", "HI", "HP", "TR", "WH"]
        gdf = pd.read_csv(gpath, dtype={"leaid": str})
        gdf["o"] = gdf.group.map(order.index)
        for lid, g in gdf.sort_values(["leaid", "o"]).groupby("leaid"):
            GROUPS_BY[lid] = [[x.group, *(int(getattr(x, c)) if getattr(x, c + "_status") == "ok" else None for c in ("enr", "iep", "oos"))]
                              for x in g.itertuples() if x.enr_status != "ok" or x.enr > 0]
    by_id = d.set_index("leaid")
    dpath = ROOT / "clean" / "output" / "detail.csv.gz"
    detail = pd.read_csv(dpath, dtype=str, index_col=0, keep_default_na=False) if dpath.exists() else pd.DataFrame()
    n = 0
    for _, r in d.iterrows():
        dr = detail.loc[r.leaid] if r.leaid in detail.index else None
        write(f"district/{r.leaid}/index.html", district_page(r, st_med, nat_med, kids_of, by_id, dr, TRENDS.get(r.leaid)))
        write(f"es/distrito/{r.leaid}/index.html", es_site.district_es(r, LAST_CD, st_med, BASE=BASE, page=page, fmt=fmt, STATUS=STATUS, pd=pd,
                                                                       VERSION=VERSION, ATLAS_ORIGIN=ATLAS_ORIGIN))
        n += 1
    (OUT / "data" / "labels.json").write_text(json.dumps(list(LABELS), ensure_ascii=False, separators=(",", ":")))
    if PREVIEW:
        write("robots.txt", "User-agent: *\nDisallow: /\n")
    domain = ATLAS_ORIGIN.split("://", 1)[-1].rstrip("/")
    if BASE == "/" and domain != "www.sumanrath.org":
        write("CNAME", domain + "\n")       # custom address for GitHub Pages
        write(".nojekyll", "")
    total = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"Built {n:,} district pages; site size {total / 1e6:,.0f} MB at {OUT}")
    return 0


# ---------------------------------------------------------------- pages

def home_page(n: int) -> str:
    body = f"""
<h1>IDEA Atlas</h1>
<p class="lede">Look up any U.S. public school district and see, in plain words, how it serves students with disabilities.
Every figure comes from public federal data.</p>
{explain("idea", "iep", "504")}

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

<section aria-labelledby="paths-h">
  <h2 id="paths-h">Choose how deep to go</h2>
  <p class="hint">From simplest to most detailed.</p>
  <ul class="paths">
    <li><span class="depth" aria-hidden="true"><i class="on"></i><i></i><i></i><i></i></span>
      <a href="#q">Start simple</a><span>Search for your district. Its page opens with a few plain sentences, and you can open the numbers and the full detail whenever you like.</span></li>
    <li><span class="depth" aria-hidden="true"><i class="on"></i><i class="on"></i><i></i><i></i></span>
      <a href="{BASE}compare/">Compare districts</a><span>Put two to four districts side by side.</span></li>
    <li><span class="depth" aria-hidden="true"><i class="on"></i><i class="on"></i><i class="on"></i><i></i></span>
      <a href="{BASE}table/">Explore a whole state</a><span>Sort every district in a state by any measure, or choose your own columns.</span></li>
    <li><span class="depth" aria-hidden="true"><i class="on"></i><i class="on"></i><i class="on"></i><i class="on"></i></span>
      <a href="{BASE}download/">Work with the data</a><span>Download the full file and read how every figure is made.</span></li>
  </ul>
  <p class="more-path">Or see <a href="{BASE}history/">fifty years of special education</a>, from 1975 to today, for the nation and every state.</p>
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
  {explain("per100", "typical")}
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
                path=BASE, scripts=("maplibre-gl.js", "atlas.js"), styles=("maplibre-gl.css",), alt=BASE + "es/")


def table_page() -> str:
    body = f"""
<h1>Table of districts</h1>
<p class="lede">Choose a state and a topic to see every district's figures in a sortable table. You can download what you see.</p>
{explain("per100", "status", "years")}
<div class="controls">
  <div><label for="t-state">State</label> <select id="t-state"><option value="">Choose a state</option></select></div>
  <div><label for="t-group">Topic</label> <select id="t-group"></select></div>
  <div><label for="t-filter">Filter by name</label> <input id="t-filter" type="search" autocomplete="off"></div>
  <div><button type="button" id="t-download" disabled>Download this table (CSV)</button></div>
  <div><button type="button" data-print>Print this table</button></div>
</div>
<fieldset id="t-cols" class="cols" hidden></fieldset>
<p id="t-status" aria-live="polite" class="hint">Choose a state to begin.</p>
<div id="t-wrap" class="table-wrap" tabindex="0" role="region" aria-labelledby="t-caption" hidden>
  <table id="t-table"><caption id="t-caption"></caption><thead></thead><tbody></tbody></table>
</div>
<p class="hint">Column headings are buttons: press one to sort by that column, and again to reverse the order.
Words such as "Withheld for privacy" explain why a figure is not shown.</p>
<h2>Words used in the table</h2>
{explain("iep", "504", "settings", "leaving", "discipline", "spending", "idea_money", "poverty")}
"""
    return page("Table of districts", body, desc="Sortable table of special education figures for every school district in a state.",
                path=BASE + "table/", scripts=("atlas.js",), crumbs=[("IDEA Atlas", BASE)])


def report_page() -> str:
    body = f"""
<div class="rpt-intro">
  <h1>Make a report</h1>
  <p class="lede">Answer five short questions and get a finished report about any school district, with charts and clear headings, ready to print or save as a PDF.</p>
  <ul class="rpt-kinds">
    <li><strong>For a family:</strong> plain words, pictures, every term explained, and the questions you want to bring to a meeting.</li>
    <li><strong>For a school leader:</strong> a summary page, the district beside its state, the nation, and districts you choose, and trends over time.</li>
    <li><strong>For a researcher:</strong> every figure with its status, the detail and trend tables, the data dictionary, and the citation.</li>
  </ul>
</div>
<div id="rpt-app" class="rpt-app"><noscript><p>The report assistant needs JavaScript. Each <a href="{BASE}">district page</a> has the same information.</p></noscript></div>
<div id="rpt-out" hidden></div>"""
    return page("Make a report", body, desc="Make a printable special education report about any U.S. school district, written for a family, a school leader, or a researcher.",
                path=BASE + "report/", scripts=("atlas.js", "report.js"), crumbs=[("IDEA Atlas", BASE)], alt=BASE + "es/informe/")


def compare_page() -> str:
    body = f"""
<h1>Compare districts</h1>
<p class="lede">Choose two to four districts to see their figures side by side, with the national median for context.</p>
<form id="c-form" role="search" novalidate>
  <label for="c-q">Add a district by name or ZIP code</label>
  <div class="row"><input id="c-q" type="search" autocomplete="off" aria-describedby="c-hint"><button type="submit">Find</button></div>
  <p id="c-hint" class="hint">Up to four districts. The link in your address bar keeps your choices, so you can bookmark or share it.</p>
</form>
<div id="c-results" aria-live="polite"></div>
<h2 id="c-chosen-h">Chosen districts</h2>
<ul id="c-chosen" class="chosen" aria-labelledby="c-chosen-h"></ul>
<div class="page-tools"><button type="button" data-print>Print this comparison</button></div>
<p id="c-status" class="hint" aria-live="polite"></p>
<figure id="c-chart" class="chart" aria-hidden="true" hidden><figcaption>Each row shows the chosen districts on the same scale. The ring marks the national median.</figcaption><div class="chart-body"></div></figure>
<div id="c-wrap" class="table-wrap" role="region" tabindex="0" aria-labelledby="c-caption" hidden>
  <table id="c-table" class="profile compare"><caption id="c-caption">Side-by-side figures</caption><thead></thead><tbody></tbody></table>
</div>
<h2>Words used here</h2>
{explain("per100", "median", "status", "years", "iep", "504", "settings", "leaving", "discipline", "spending", "idea_money", "poverty")}
"""
    return page("Compare districts", body, desc="Compare special education figures for up to four school districts side by side.",
                path=BASE + "compare/", scripts=("atlas.js",), crumbs=[("IDEA Atlas", BASE)])


DETAIL_PREFIX = {"cc": "Child count", "ev": "Learning setting", "ex": "Leaving", "cr": "Civil rights", "fin": "Finance ($000s)", "pov": "Poverty"}

# counts behind each rate: (numerator columns, denominator column); "main:" reads from the district file, others from detail
COUNTS = {
    "id_rate": (["main:idea_count"], "main:enrollment"),
    "pct_504": (["cr|enr_504"], "cr|enr_total"),
    "env_80plus": (["ev|School Age Inside regular class 80% or more of the day"], "ev|School Age All Educational Environments"),
    "env_lt40": (["ev|School Age Inside regular class less than 40% of the day"], "ev|School Age All Educational Environments"),
    "env_separate": (["ev|School Age Separate School", "ev|School Age Residential Facility", "ev|School Age Homebound/Hospital"], "ev|School Age All Educational Environments"),
    "grad_regular": (["ex|All Disabilities Graduated With Regular High School Diploma"], "ex|All Disabilities Total Exiting School"),
    "dropout": (["ex|All Disabilities Dropped Out"], "ex|All Disabilities Total Exiting School"),
    "oos_idea": (["cr|oos_idea"], "cr|enr_idea"), "oos_nodis": (["cr|oos_nodis"], "cr|enr_nodis"), "oos_504": (["cr|oos_504"], "cr|enr_504"),
    "expulsion_idea": (["cr|exp_idea"], "cr|enr_idea"), "restraint_physical_idea": (["cr|rs_phys_idea"], "cr|enr_idea"),
    "restraint_mechanical_idea": (["cr|rs_mech_idea"], "cr|enr_idea"), "seclusion_idea": (["cr|rs_secl_idea"], "cr|enr_idea"),
    "referral_idea": (["cr|ref_idea"], "cr|enr_idea"), "arrest_idea": (["cr|arr_idea"], "cr|enr_idea"),
    "child_poverty": (["pov|children_poor"], "pov|children_5_17"),
}


def add_counts(out: pd.DataFrame, det: pd.DataFrame) -> pd.DataFrame:
    """Add <measure>_count and <measure>_group next to each rate, so figures can be recomputed or pooled.
    Withheld or unreported pieces are left blank, never estimated."""
    det = det.reindex(out.leaid)
    def col(name):
        if name.startswith("main:"):
            return pd.to_numeric(out[name[5:]], errors="coerce").reset_index(drop=True)
        x = pd.to_numeric(det[name], errors="coerce") if name in det.columns else pd.Series(np.nan, index=det.index)
        return x.where(x >= 0).reset_index(drop=True)
    cols = list(out.columns)
    out = out.reset_index(drop=True)
    for k, (nums, den) in COUNTS.items():
        parts = [col(n) for n in nums]
        num_ = parts[0] if len(parts) == 1 else pd.concat(parts, axis=1).sum(axis=1, min_count=len(parts))
        out[k + "_count"] = num_.round().astype("Int64")
        out[k + "_group"] = col(den).round().astype("Int64")
        i = cols.index(k + "_status") + 1
        cols[i:i] = [k + "_count", k + "_group"]
    return out[cols]


def download_page(fname: str, n: int, dname: str = "", ncols: int = 0, tname: str = "") -> str:
    detail = f"""
<h2>Full detail file</h2>
<p>Every count behind the district pages, one row per district: all federal disability categories for early childhood and school age,
every learning setting, every way students left special education, civil rights counts by group, district finances, and the child poverty estimate
({ncols} columns).</p>
<p><a class="button" href="{BASE}download/{dname}" download>Download {E(dname)}</a></p>
{explain("detail_codes")}""" if dname else ""
    body = f"""
<h1>Download the data</h1>
<p class="lede">Everything in IDEA Atlas, ready to open in Excel or any statistics program.</p>

<h2>Main file</h2>
<p>One row per district ({n:,} rows). Each measure has three companions: <code>_status</code> says whether the figure is a real number or why it is not shown;
<code>_count</code> and <code>_group</code> give the number of students counted and the size of the group, so you can recompute a rate or pool districts.</p>
<p><a class="button" href="{BASE}download/{fname}" download>Download {E(fname)}</a></p>
{explain("status")}
{detail}
{f"""<h2>Trends file</h2>
<p>Each district's trend lines, one row per district, measure, and year: students with IEPs per 100 enrolled (1991–92 onward), spending per student in 2024 dollars (fiscal year 1990 onward), child poverty (2003 onward), and out-of-school suspension for students with and without disabilities (2013–14 onward).
See <a href="{BASE}methods/#trends">how the trends are made</a>.</p>
<p><a class="button" href="{BASE}download/{tname}" download>Download {E(tname)}</a></p>""" if tname else ""}

<h2>Using the files</h2>
<p>The <a href="{BASE}methods/#dictionary">data dictionary</a> describes every measure and the group it is counted against, and the
<a href="{BASE}methods/#rules">data rules</a> explain privacy, small groups, and minimums.
Code and processed data are shared under a Creative Commons Attribution 4.0 license. The original federal data are in the public domain.</p>
<p>Please <a href="{BASE}methods/#cite">cite IDEA Atlas</a> with its version number ({VERSION}) so others can find the same figures.</p>
"""
    return page("Download the data", body, desc="Download the full IDEA Atlas data set as CSV files: district measures with counts, and a full detail file.",
                path=BASE + "download/", crumbs=[("IDEA Atlas", BASE)])


def compare_row(label: str, k: str, unit: str, r, st_med, nat_med) -> list[str]:
    v, s = r[k], str(r[k + "_status"])
    sm = st_med[k].get(r.state, np.nan)
    nm = nat_med[k]
    lo, hi = st_med["_q"][k][0].get(r.state, np.nan), st_med["_q"][k][1].get(r.state, np.nan)
    mid = f"{fmt(lo, unit)} to {fmt(hi, unit)}" if pd.notna(lo) and pd.notna(hi) else "—"
    return [label, cell(v, s, unit), fmt(sm, unit) or "—", mid, fmt(nm, unit) or "—"]


def chart(kind: str, caption: str, keys: str = "") -> str:
    """Placeholder for a chart drawn in the browser from this page's chart data. Hidden from screen readers:
    the sentences and tables around it carry the same figures."""
    k = f' data-keys="{keys}"' if keys else ""
    if kind == "trend":       # trend charts can be explored year by year with the arrow keys, so they stay visible to screen readers
        return f'<figure class="chart explorable" data-chart="{kind}"{k}><figcaption>{E(caption)}</figcaption><div class="chart-body"></div></figure>'
    return f'<figure class="chart" data-chart="{kind}"{k} aria-hidden="true"><figcaption>{E(caption)}</figcaption><div class="chart-body"></div></figure>'


def section(title: str, intro: str, rows: list[list[str]], src: list[str], sid: str, unit_note: str, extra: str = "",
            plain: str = "", terms: tuple[str, ...] = (), more: str = "", pic: str = "", pic2: str = "", trend: str = "") -> str:
    """Three layers: plain sentences and explainers; the numbers with medians (one click); full detail (another click)."""
    sources = "; ".join(f"{SOURCES[s][0]}, {SOURCES[s][1]}" for s in src)
    return f"""
<section aria-labelledby="{sid}">
  <h2 id="{sid}">{E(title)}</h2>
  {intro}{plain}
  {pic}{trend}
  {explain(*terms) if terms else ""}
  <details class="numbers"><summary>The numbers: this district, the state, and the nation</summary>
  {detail_table(f"{title}: {unit_note}", ["Measure", "This district", "State median", "Middle half of state districts", "National median"], rows, sid + "-cap", "profile")}
  {explain("middle") if sid == "s-who" else ""}{pic2}{more}
  </details>
  {extra}
  <p class="source">Source: {E(sources)}. <a href="{BASE}methods/#sources">About the sources</a></p>
</section>"""


# ---------------------------------------------------------------- race and ethnicity (2023-24 civil rights counts)

def grp_block(which: str, cd: dict) -> str:
    """A collapsed table, built in the browser from cd["rg"]: each group's rate beside the rate for all other students."""
    if not cd.get("rg"):
        return ""
    summ = "By race and ethnicity: students with IEPs" if which == "iep" else "By race and ethnicity: out-of-school suspensions of students with IEPs"
    return f"""<details class="full grp"><summary>{summ}</summary>
<p class="hint">Groups are the race and ethnicity categories used in federal data. Each group's figure is shown beside the same figure for all other students in the district,
the comparison federal reviews use. A figure is not shown when a group has fewer than 10 students. Figures describe what was reported, not why they differ.
Source: Civil Rights Data Collection, 2023–24.</p>
<div class="jg" data-g="{which}"></div></details>"""


# ---------------------------------------------------------------- full detail

def raw_cell(v) -> str:
    v = "" if v is None else str(v).strip()
    if v == "":
        return "Not reported"
    if v == "-8":
        return "Withheld for privacy"
    if v == "-9":
        return "Flagged for data quality"
    try:
        x = float(v)
    except ValueError:
        return v
    return "Not reported" if x < 0 else f"{x:,.0f}"


def num(v):
    try:
        x = float(v)
        return x if x >= 0 else None
    except (TypeError, ValueError):
        return None


def per100(a, b) -> str:
    a, b = num(a), num(b)
    if a is None or b is None or b == 0:
        return "—"
    if b < 10:
        return "Fewer than 10 students"
    return f"{100 * a / b:,.1f}"


def detail_table(caption: str, head: list[str], rows: list[list[str]], tid: str, cls: str = "profile detail") -> str:
    """Register a table for this page. It is stored as data and built in the browser as a normal, fully labelled table."""
    TABLES.append({"id": tid, "c": caption, "h": head, "r": rows, "k": cls})
    return f'<div class="jt" data-t="{len(TABLES) - 1}"></div>'


def details_block(summary: str, inner: str, note: str = "") -> str:
    n = f'<p class="hint">{E(note)}</p>' if note else ""
    return f'<details class="full"><summary>{E(summary)}</summary>{n}{inner}</details>'


def full_who(dr) -> str:
    if dr is None:
        return ""
    cats = sorted({c.split("|", 1)[1].replace("School Age ", "", 1) for c in dr.index if c.startswith("cc|School Age ") and "All Disabilities" not in c})
    sa_all = dr.get("cc|School Age All Disabilities")
    rows = []
    for c in cats:
        rows.append([c, raw_cell(dr.get(f"cc|Early Childhood {c}")), raw_cell(dr.get(f"cc|School Age {c}")), per100(dr.get(f"cc|School Age {c}"), sa_all)])
    rows.append(["All disabilities", raw_cell(dr.get("cc|Early Childhood All Disabilities")), raw_cell(sa_all), "100.0" if num(sa_all) else "—"])
    rows.append(["Total, ages 3 to 21", "", raw_cell(dr.get("cc|Combined Early Childhood and School Age Total")), ""])
    return details_block("Full detail: students with IEPs by federal disability category",
                         detail_table("Students with IEPs by category, 2024–25", ["Federal category", "Early childhood (ages 3 to 5)", "School age (5 in kindergarten to 21)", "Per 100 school-age students with IEPs"], rows, "fd-who"),
                         "Category names are the federal terms used in the IDEA count.")


PLAIN_ROW = {
    "Inside regular class 80% or more of the day": "In a general class 80% or more of the day",
    "Inside regular class 40% through 79% of the day": "In a general class 40% to 79% of the day",
    "Inside regular class less than 40% of the day": "In a general class less than 40% of the day",
    "Separate School": "Separate school", "Residential Facility": "Residential facility",
    "Homebound/Hospital": "At home or in a hospital", "Correctional Facilities": "Correctional facility",
    "Parentally placed in private schools": "Private school chosen by the family",
    "Services in Regular Early Childhood Program (at least 10 hours)": "Preschool class, 10 or more hours a week, services there",
    "Other Location Regular Early Childhood Program (at least 10 hours)": "Preschool class, 10 or more hours a week, services elsewhere",
    "Services in Regular Early Childhood Program (less than 10 hours)": "Preschool class, under 10 hours a week, services there",
    "Other Location Regular Early Childhood Program (less than 10 hours)": "Preschool class, under 10 hours a week, services elsewhere",
    "Separate Class": "Separate class", "Home": "At home", "Service Provider Location": "At a service provider's location",
    "Died": "Died", "Dropped Out": "Dropped out", "Graduated With an Alternate Diploma": "Alternate diploma",
    "Graduated With Regular High School Diploma": "Regular high school diploma", "Moved, Known to be Continuing": "Moved and continuing school elsewhere",
    "Reached Maximum Age": "Reached the maximum age for services", "Received a Certificate": "Certificate of completion",
    "Transferred to Regular Education": "No longer needs special education", "Total Exiting School": "All who left school",
    "Total Exiting Special Education": "All who left special education",
}


def full_where(dr) -> str:
    if dr is None:
        return ""
    out = []
    for label, pre, allc in (("School age (5 in kindergarten to 21)", "School Age", "School Age All Educational Environments"),
                             ("Early childhood (ages 3 to 5)", "Early Childhood", "Early Childhood All Educational Environments")):
        cols = [c.split("|", 1)[1] for c in dr.index if c.startswith(f"ev|{pre} ") and not c.endswith("All Educational Environments")]
        if not cols:
            continue
        tot = dr.get(f"ev|{allc}")
        rows = [[PLAIN_ROW.get(c.replace(pre + " ", "", 1), c.replace(pre + " ", "", 1)), raw_cell(dr.get(f"ev|{c}")), per100(dr.get(f"ev|{c}"), tot)] for c in cols]
        rows.append(["All settings", raw_cell(tot), "100.0" if num(tot) else "—"])
        tid = "fd-where-" + pre.split()[0].lower()
        out.append(detail_table(f"Where students with IEPs learn, {label}, 2024–25", ["Setting", "Students", "Per 100 students with IEPs"], rows, tid))
    return details_block("Full detail: every learning setting", "".join(out)) if out else ""


def full_leave(dr) -> str:
    if dr is None:
        return ""
    cols = [c.split("|", 1)[1] for c in dr.index if c.startswith("ex|All Disabilities ")]
    if not cols:
        return ""
    tot = dr.get("ex|All Disabilities Total Exiting Special Education")
    rows = [[PLAIN_ROW.get(c.replace("All Disabilities ", "", 1), c.replace("All Disabilities ", "", 1)), raw_cell(dr.get(f"ex|{c}")), per100(dr.get(f"ex|{c}"), tot) if "Total" not in c else ""] for c in cols]
    return details_block("Full detail: every way students left special education",
                         detail_table("How students with IEPs, ages 14 to 21, left special education, 2023–24", ["Reason", "Students", "Per 100 who left special education"], rows, "fd-leave"),
                         "Leaving school counts graduation, other completion, reaching the maximum age, and dropping out. Leaving special education also counts students who moved or returned to general education.")


CR_ROWS = [("Out-of-school suspension (one or more)", "oos_idea", "enr_idea", "oos_nodis", "enr_nodis", "oos_504", "enr_504"),
           ("Expulsion", "exp_idea", "enr_idea", None, None, None, None),
           ("Physical restraint", "rs_phys_idea", "enr_idea", None, None, None, None),
           ("Mechanical restraint", "rs_mech_idea", "enr_idea", None, None, None, None),
           ("Seclusion", "rs_secl_idea", "enr_idea", None, None, None, None),
           ("Referral to law enforcement", "ref_idea", "enr_idea", None, None, None, None),
           ("School-related arrest", "arr_idea", "enr_idea", None, None, None, None)]


def full_disc(dr) -> str:
    if dr is None or "cr|enr_idea" not in dr.index or dr.get("cr|enr_idea", "") == "":
        return ""
    g = lambda k: dr.get(f"cr|{k}") if k else None
    rows = []
    for label, n1, d1, n2, d2, n3, d3 in CR_ROWS:
        rows.append([label, raw_cell(g(n1)), per100(g(n1), g(d1)),
                     raw_cell(g(n2)) if n2 else "Not collected", per100(g(n2), g(d2)) if n2 else "—",
                     raw_cell(g(n3)) if n3 else "Not collected", per100(g(n3), g(d3)) if n3 else "—"])
    rows.append(["Students in the group", raw_cell(g("enr_idea")), "", raw_cell(g("enr_nodis")), "", raw_cell(g("enr_504")), ""])
    return details_block("Full detail: discipline and safety counts",
                         detail_table("Students affected, by group, 2023–24", ["Action", "Students with IEPs", "Per 100", "Students without disabilities", "Per 100", "Students with Section 504 plans", "Per 100"], rows, "fd-disc"),
                         "Counts of students, not incidents. Some actions are reported only for students with IEPs.")


def full_fund(dr) -> str:
    if dr is None or dr.get("fin|V33", "") == "":
        return ""
    k = lambda c: (f"${float(dr.get(c)) * 1000:,.0f}" if num(dr.get(c)) is not None else "Not reported")
    rows = [["Total revenue", k("fin|TOTALREV")], ["Federal revenue", k("fin|TFEDREV")], ["Federal IDEA revenue (through the state)", k("fin|C15")],
            ["Total spending", k("fin|TOTALEXP")], ["Current spending (day-to-day costs)", k("fin|TCURELSC")],
            ["Students enrolled in the fall (finance count)", raw_cell(dr.get("fin|V33"))]]
    return details_block("Full detail: district finances", detail_table("District finances, fiscal year 2024", ["Item", "Amount"], rows, "fd-fund"))


def full_comm(dr) -> str:
    if dr is None or dr.get("pov|children_5_17", "") == "":
        return ""
    rows = [["Children ages 5 to 17 living in the district's area", raw_cell(dr.get("pov|children_5_17"))],
            ["Of those, children living in poverty", raw_cell(dr.get("pov|children_poor"))]]
    return details_block("Full detail: child poverty estimate", detail_table("Child poverty estimate, 2024", ["Item", "Children"], rows, "fd-comm"),
                         "Census estimates for the area the district serves, not only children enrolled.")


TYPE_PLAIN = {
    "Regular public school district that is not a component of a supervisory union": "Public school district",
    "Regular public school district that is a component of a supervisory union": "Public school district (part of a supervisory union)",
    "Independent charter district": "Charter school district",
    "Service agency": "Regional service agency",
    "Specialized public school district": "Specialized public school district",
    "Other local education agency": "Other local education agency",
    "State operated agency": "State-run school agency",
    "Federal operated agency": "Federally run school agency",
}


def district_page(r, st_med, nat_med, kids_of, by_id, dr=None, tr=None) -> str:
    TABLES.clear()
    SHORT_TERMS[0] = True
    name = r.display
    lab = {m[0]: m[2] for m in MEASURES}
    unit = {m[0]: m[4] for m in MEASURES}
    meta = []
    if isinstance(r.city, str) and r.city:
        meta.append(("Location", f"{r.city.title()}, {r.state_name.title()}"))
    if isinstance(r.district_type, str):
        meta.append(("Type", TYPE_PLAIN.get(r.district_type, r.district_type)))
    if isinstance(r.grade_low, str) and isinstance(r.grade_high, str):
        meta.append(("Grades", f"{r.grade_low} to {r.grade_high}"))
    if pd.notna(r.enrollment):
        meta.append(("Students, 2024–25", f"{r.enrollment:,.0f}"))
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
        glance.append(add_everyday(f"In 2024–25, {fmt(r.id_rate, 'per100')} of every 100 students enrolled had an IEP served by the district.", fmt(r.id_rate, 'per100'), r.id_rate))
    if str(r.env_80plus_status) == "ok":
        glance.append(add_everyday(f"{fmt(r.env_80plus, 'per100')} of every 100 students with IEPs spent at least 80% of the day in a general class.", fmt(r.env_80plus, 'per100'), r.env_80plus))
    if str(r.grad_regular_status) == "ok":
        glance.append(add_everyday(f"Of students with IEPs who left school in 2023–24, {fmt(r.grad_regular, 'per100')} of every 100 left with a regular diploma.", fmt(r.grad_regular, 'per100'), r.grad_regular))
    if str(r.oos_idea_status) == "ok" and str(r.oos_nodis_status) == "ok":
        glance.append(f"In 2023–24, {fmt(r.oos_idea, 'per100')} of every 100 students with IEPs received an out-of-school suspension, "
                      f"compared with {fmt(r.oos_nodis, 'per100')} of every 100 students without disabilities.")
    glance_html = ("<section aria-labelledby=\"g-h\" class=\"glance\"><h2 id=\"g-h\">At a glance</h2><ul>"
                   + "".join(f"<li>{figs(x)}</li>" for x in glance) + "</ul>" + explain("iep", "per100") + "</section>") if glance else ""
    howto = ('<p class="howto">Each topic below starts in plain words. Open <strong>The numbers</strong> to see this district beside the state and the nation, '
             'and <strong>Full detail</strong> for every count behind the figures. Questions such as <em>What is a median?</em> open a short explanation.</p>')

    def rows(ks):
        return [compare_row(lab[k], k, unit[k], r, st_med, nat_med) for k in ks]

    st_name = r.state_name.title() if isinstance(r.state_name, str) else "the state"
    def rng(ks):
        return chart("range", f"Where this district sits among {st_name} districts", ",".join(ks))

    def sec(title, intro, ks, src, sid, unit_note, extra, terms, more="", pic=None, pic2="", trend=("", "")):
        return section(title, intro, rows(ks), src, sid, unit_note, extra, plain=plain_lines(r, ks, st_med), terms=terms, more=trend[1] + more,
                       pic=rng(ks) if pic is None else pic, pic2=pic2, trend=trend[0])

    tr = tr or {}
    cd_tr = {}

    def over_time(code, cur, label, unit, yfmt, src, what, comp=None):
        """A plain sentence, a small chart and a table for one measure over time. Returns (visible part, numbers-layer part)."""
        pts = {int(y): v for y, v in (tr.get(code) or {}).items()}
        if cur[1] is not None and pd.notna(cur[1]):
            pts[cur[0]] = round(float(cur[1]), 1) if unit != "usd" else int(round(float(cur[1])))
        if len(pts) < 3:
            return "", ""
        ys = sorted(pts)
        f = (lambda v: f"${v:,.0f}") if unit == "usd" else (lambda v: f"{v:,.1f}")
        a, b = ys[0], ys[-1]
        say = what.format(a=yfmt(a), b=yfmt(b), va=f(pts[a]), vb=f(pts[b]))
        cd_tr[code] = [[y, pts[y]] for y in ys]
        if comp:                                   # a second, quieter line for comparison (same years where available)
            ccode, ccur, csay = comp
            cp = {int(y): v for y, v in (tr.get(ccode) or {}).items()}
            if ccur is not None and pd.notna(ccur):
                cp[cur[0]] = round(float(ccur), 1)
            if len(cp) >= 2:
                cy = sorted(cp)
                cd_tr[code + "c"] = [[y, cp[y]] for y in cy]
                say += " " + csay.format(a=yfmt(cy[0]), b=yfmt(cy[-1]), va=f(cp[cy[0]]), vb=f(cp[cy[-1]]))
        vis = (f'<h3 class="ot-h">Over time</h3><ul class="plain"><li>{figs(say)}</li></ul>'
               + chart("trend", f"{label}, {yfmt(a)} to {yfmt(b)}. Dashed lines join years without a figure.", code))
        # the year-by-year table is built in the browser from the same numbers as the chart
        tbl = (f'<div class="jt-tr" data-k="{code}" data-cap="{E(label)}, by year" data-label="{E(label)}" '
               f'data-y="{"sy" if yfmt is sy else "fy" if yfmt is fy else "y"}"></div>')
        return vis, tbl + f'<p class="source">{E(src)}</p>'

    sy = lambda y: f"{y}–{str(y + 1)[-2:]}"
    fy = lambda y: f"{y - 1}–{str(y)[-2:]}"
    ot_iep = over_time("i", (2024, r.id_rate if str(r.id_rate_status) == "ok" else None), "Students with IEPs per 100 enrolled", "per100", sy,
                       "Earlier years: Common Core of Data, district files 1991–92 to 2017–18 (students with IEPs and enrollment). Years when a state reported in an unusual way are left out.",
                       "About {va} of every 100 students had an IEP in {a}, compared with about {vb} in {b}.")
    ot_sp = over_time("s", (2024, r.spend_per_pupil if str(r.spend_per_pupil_status) == "ok" else None), "Spending per student, in 2024 dollars", "usd", fy,
                      "Earlier years: NCES and Census Bureau school district finance surveys, adjusted for inflation with the Consumer Price Index (Bureau of Labor Statistics).",
                      "Adjusted for inflation, the district spent about {va} per student in {a} and about {vb} in {b}.")
    ot_dc = over_time("d", (2023, r.oos_idea if str(r.oos_idea_status) == "ok" else None), "Out-of-school suspension, students with IEPs, per 100", "per100", sy,
                      "Earlier years: Civil Rights Data Collection, 2013–14, 2015–16, 2017–18, 2020–21, and 2021–22, summed from schools to the district. 2020–21 was a pandemic year with much remote learning.",
                      "About {va} of every 100 students with IEPs received an out-of-school suspension in {a}, compared with about {vb} in {b}.",
                      comp=("n", r.oos_nodis if str(r.oos_nodis_status) == "ok" else None, "For students without disabilities, it was about {va} in {a} and about {vb} in {b}."))
    ot_pv = over_time("p", (2024, r.child_poverty if str(r.child_poverty_status) == "ok" else None), "Children ages 5 to 17 in poverty, per 100", "per100", str,
                      "Earlier years: Census Bureau Small Area Income and Poverty Estimates, 2003 onward.",
                      "About {va} of every 100 children in the district's area lived in poverty in {a}, and about {vb} in {b}.")

    order = sorted(CATEGORIES, key=lambda c: -(r[c[0]] if str(r[c[0] + "_status"]) == "ok" and pd.notna(r[c[0]]) else -1))
    cat_rows = [[label, cell(r[k], str(r[k + "_status"]), "per100")] for k, label in order]
    cats_args = ("Disability categories, largest first, per 100 school-age students with IEPs", ["Federal category", "This district"], cat_rows, "cat-cap", "profile narrow")

    check = ""
    if bool(r.crdc_count_check) if pd.notna(r.crdc_count_check) else False:
        check = ('<p class="note"><strong>Please check with the district.</strong> The number of students with IEPs in the civil rights data '
                 f"({r.crdc_enr_idea:,.0f}) is very different from the IDEA count ({r.idea_count:,.0f}). "
                 "The figures in this section use the civil rights count, so they may not be reliable.</p>")
    partial = ""
    if bool(r.crdc_partial) if pd.notna(r.crdc_partial) else False:
        partial = '<p class="note">Some schools in this district withheld or did not report an item, so the figures in this section are minimums.</p>'

    def q(x):
        return None if x is None or pd.isna(x) else round(float(x), 1)
    cd = {"st": st_name, "m": {}, "id": r.leaid, "s2": r.state}
    if GROUPS_BY.get(r.leaid):
        cd["rg"] = GROUPS_BY[r.leaid]
    for k in [m[0] for m in MEASURES]:
        code = STATUS.get(str(r[k + "_status"]), ("5", ""))[0]
        cd["m"][k] = [q(r[k]) if code in ("0", "1") else None, code,
                      q(st_med["_q"][k][0].get(r.state)), q(st_med[k].get(r.state)), q(st_med["_q"][k][1].get(r.state)), q(nat_med[k])]
    cd["cats"] = [[lbl, q(r[k])] for k, lbl in CATEGORIES if STATUS.get(str(r[k + "_status"]), ("5",))[0] == "0" and pd.notna(r[k])]
    if dr is not None:
        def n(c):
            x = num(dr.get(c))
            return None if x is None else int(x)
        ev = lambda c: n("ev|School Age " + c)
        parts = [ev("Inside regular class 80% or more of the day"), ev("Inside regular class 40% through 79% of the day"),
                 ev("Inside regular class less than 40% of the day")]
        sep = [ev("Separate School"), ev("Residential Facility"), ev("Homebound/Hospital")]
        oth = [ev("Correctional Facilities"), ev("Parentally placed in private schools")]
        if all(x is not None for x in parts + sep):
            cd["set"] = parts + [sum(sep), sum(x or 0 for x in oth)]
        ex = lambda c: n("ex|All Disabilities " + c)
        xs = [ex("Graduated With Regular High School Diploma"), ex("Graduated With an Alternate Diploma"), ex("Received a Certificate"),
              ex("Reached Maximum Age"), ex("Dropped Out"), ex("Died")]
        if all(x is not None for x in xs) and sum(xs) >= 10:
            cd["ex"] = [xs[0], xs[1] + xs[2], xs[3], xs[4], xs[5]]
    det = r.determination_2026 if isinstance(r.determination_2026, str) else "Not available"
    state_note = f'<p class="note">{E(STATE_NOTES[r.state])}</p>' if r.state in STATE_NOTES else ""
    body = f"""
<h1>{E(name)}</h1>
<dl class="facts">{''.join(f'<div><dt>{E(a)}</dt><dd>{E(b)}</dd></div>' for a, b in meta)}</dl>
<div class="page-tools"><button type="button" data-print>Print this page</button>
  <button type="button" data-expand>Show all detail</button>
  <a class="button secondary" href="{BASE}compare/?ids={r.leaid}">Compare with other districts</a></div>
{parent}{kids}
{glance_html}
{howto}
{sec("Who is served", state_note, ["id_rate", "pct_504"], ["idea_cc", "ccd", "crdc"], "s-who", "per 100 students enrolled", full_who(dr) + grp_block("iep", cd), ("typical", "504", "categories"), trend=ot_iep, more=chart("cats", "Students with IEPs by federal category, per 100 school-age students with IEPs") + detail_table(*cats_args))}
{sec("Where students learn", "<p>School-age students with IEPs, 2024–25.</p>", ["env_80plus", "env_lt40", "env_separate"], ["idea_env"], "s-where", "per 100 students with IEPs, ages 5 to 21", full_where(dr), ("settings",), pic=chart("settings", "Time in a general class, school-age students with IEPs"), pic2=rng(["env_80plus", "env_lt40", "env_separate"]))}
{sec("Leaving school", "<p>Students with IEPs, ages 14 to 21, who left school in 2023–24.</p>", ["grad_regular", "dropout"], ["idea_exit"], "s-leave", "per 100 students with IEPs who left school", full_leave(dr), ("leaving",), pic=chart("exit", "How students with IEPs left school, 2023–24"), pic2=rng(["grad_regular", "dropout"]))}
{sec("Discipline and safety", "<p>School year 2023–24.</p>" + check + partial, ["oos_idea", "oos_nodis", "oos_504", "expulsion_idea", "restraint_physical_idea", "restraint_mechanical_idea", "seclusion_idea", "referral_idea", "arrest_idea"], ["crdc"], "s-disc", "per 100 students in each group", full_disc(dr) + grp_block("oos", cd), ("discipline", "504"), trend=ot_dc)}
{sec("Funding", "<p>Fiscal year 2024.</p>", ["spend_per_pupil", "idea_federal_per_student"], ["fin", "idea_cc"], "s-fund", "dollars", full_fund(dr), ("spending", "idea_money"), trend=ot_sp)}
{sec("Community", "<p>2024 estimate.</p>", ["child_poverty"], ["saipe"], "s-comm", "per 100 children ages 5 to 17", full_comm(dr), ("poverty",), trend=ot_pv)}
<section aria-labelledby="s-state">
  <h2 id="s-state">State IDEA rating</h2>
  <p>Each year the U.S. Department of Education rates how each state carries out IDEA. In 2026, {E(r.state_name.title())} was rated <strong>{E(det)}</strong>.
  The rating describes the state, not this district.</p>
  {explain("rating")}
  <p class="source">Source: {E(SOURCES['det'][0])}, {E(SOURCES['det'][1])}.</p>
</section>
<section aria-labelledby="s-like" class="like">
  <h2 id="s-like">Districts like this one</h2>
  <p>Find districts in {E(st_name)} with a similar number of students and a similar level of child poverty, then compare them side by side.</p>
  <button type="button" class="secondary" data-like>Find districts like this one</button>
  <div class="like-out" aria-live="polite"></div>
</section>
<section aria-labelledby="s-rpt" class="rpt-cta">
  <h2 id="s-rpt">Make a printable report</h2>
  <p>Answer a few questions and get a report about this district written for a family, a school leader, or a researcher, with charts, ready to print or save as a PDF.</p>
  <p><a class="button" href="{BASE}report/?id={r.leaid}">Make a report for this district</a></p>
</section>
<section aria-labelledby="s-ask">
  <h2 id="s-ask">Questions you could ask</h2>
  <p>Numbers can start a conversation. If you are a parent or caregiver, these questions may help when you talk with the district or at an IEP meeting.</p>
  <ul class="ask">
    <li>How does the district decide whether a child needs special education, and how long does an evaluation take?</li>
    <li>What supports help students with IEPs learn alongside their classmates in general classes?</li>
    <li>How are families included when an IEP is written and reviewed?</li>
    <li>What can a family do if they disagree with a decision?</li>
    <li>How does the district help students with IEPs plan for life after high school?</li>
    <li>Where can I read the district's own special education reports?</li>
  </ul>
  <p>For free, one-on-one help, every state has at least one federally funded Parent Training and Information Center.
  <a href="https://www.parentcenterhub.org/find-your-center/">Find your state's Parent Center</a>.</p>
</section>
<section aria-labelledby="s-more">
  <h2 id="s-more">Using these figures</h2>
  <p>These figures describe what was reported. They are not grades. See <a href="{BASE}methods/">methods and sources</a> for how each one is made.</p>
  {explain("median", "status", "years")}
  <p>Federal ID for this district: {r.leaid}. This is the National Center for Education Statistics (NCES) number, useful when looking up the district in other federal data.</p>
  <p>Cite this page: Rath, S. (2026). <cite>IDEA Atlas: Special education data for every U.S. school district</cite> (Version {VERSION}). {E(name)}. {ATLAS_ORIGIN}{BASE}district/{r.leaid}/ https://doi.org/{DOI}</p>
</section>
"""
    cd["t"] = [{"id": t_["id"], "k": t_["k"], "c": shared_label(t_["c"]), "h": [shared_label(x) for x in t_["h"]], "r": [[shared_label(c) for c in row] for row in t_["r"]]} for t_ in TABLES]
    if cd_tr:
        cd["tr"] = cd_tr
    LAST_CD.clear()
    LAST_CD.update(cd)
    SHORT_TERMS[0] = False
    chart_json = json.dumps(cd, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    body = f'<script type="application/json" id="chart-data">{chart_json}</script>' + body
    desc = f"Special education data for {name}, {r.state_name.title()}: students with IEPs, settings, graduation, discipline, Section 504, funding, and child poverty."
    return page(f"{name}, {r.state}", body, desc=desc, path=f"{BASE}district/{r.leaid}/", scripts=("atlas.js",), alt=f"{BASE}es/distrito/{r.leaid}/",
                crumbs=[("IDEA Atlas", BASE), (r.state_name.title(), f"{BASE}table/?state={r.state}")])


def methods_page() -> str:
    src_rows = "".join(f"<tr><th scope=\"row\">{E(v[0])}</th><td>{E(v[1])}</td><td>{E(v[2])}</td></tr>" for v in SOURCES.values())
    dict_rows = "".join(f"<tr><th scope=\"row\"><code>{m[0]}</code></th><td>{E(m[2])}</td><td>{E(m[6])}</td></tr>" for m in MEASURES)
    status_rows = "".join(f"<tr><th scope=\"row\"><code>{k}</code></th><td>{E(v[1] or 'A real figure')}</td></tr>" for k, v in STATUS.items())
    body = f"""
<h1>Methods and sources</h1>
<p class="lede">How every figure in IDEA Atlas is made, where it comes from, and what it cannot tell you.</p>
<div class="page-tools"><button type="button" data-print>Print this page</button></div>

<nav aria-label="On this page" class="toc"><ul>
<li><a href="#what">What the tool shows</a></li><li><a href="#sources">Sources</a></li><li><a href="#rules">Data rules</a></li>
<li><a href="#measures">How each measure is calculated</a></li><li><a href="#zip">ZIP code search</a></li>
<li><a href="#det">State ratings</a></li><li><a href="#limits">Known limits</a></li><li><a href="#dictionary">Data dictionary</a></li>
<li><a href="#trends">History and trends</a></li><li><a href="#words">Words explained</a></li><li><a href="#updates">Updates and versions</a></li><li><a href="#cite">How to cite</a></li></ul></nav>

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

<section aria-labelledby="trends"><h2 id="trends">History and trends</h2>
<p>The <a href="{BASE}history/">History page</a> uses the Digest of Education Statistics (National Center for Education Statistics), which gathers the counts states report each year,
tables 204.30, 204.60, 204.70, 219.90, and 203.20, editions 2013 to 2023. Where editions overlap, the newest is used. Years the tables do not report are shown as dashed lines, never filled in.</p>
<p>The <strong>Over time</strong> lines on district pages use:</p>
<ul>
<li><strong>Students with IEPs per 100 enrolled:</strong> Common Core of Data district files, 1991–92 to 2019–20, then the Department of Education's district child count files, 2020–21 to 2024–25.
Before using a year, I check each state: if its districts' combined rate that year is more than 35% away from the state's official share served (Digest of Education Statistics), which usually means the state reported
IEP counts differently that year (for example, at a regional agency), the whole state-year is left out.
A single year that both neighbouring years contradict is also left out.</li>
<li><strong>Spending per student:</strong> NCES school district finance surveys (F-33), fiscal years 1990, 1992, and 1995 to 2018, and the Census Bureau's Annual Survey of School System Finances, fiscal years 2019 to 2024.
Earlier years are adjusted to 2024 dollars with the Consumer Price Index for All Urban Consumers (Bureau of Labor Statistics), averaged over each July to June school year.</li>
<li><strong>Child poverty:</strong> Census Bureau Small Area Income and Poverty Estimates for school districts, 2003 to 2024.</li>
<li><strong>Out-of-school suspension:</strong> Civil Rights Data Collection, 2013–14, 2015–16, 2017–18, 2020–21, 2021–22, and 2023–24, with school counts summed to the district.
Students with IEPs and students without disabilities are each counted per 100 students in that group. 2020–21 was a pandemic year with much remote learning, so suspensions were far lower that year.</li>
</ul>
<p>Districts sometimes merge, split, or change ID numbers. Trend lines follow the district's current federal ID, so a district that changed shape may show a jump. The trend file can be downloaded on the <a href="{BASE}download/">download page</a>.</p></section>

<section aria-labelledby="words"><h2 id="words">Words explained</h2>
<dl class="glossary">{''.join(f'<dt id="term-{k}">{E(v[0])}</dt><dd>{E(v[1])}</dd>' for k, v in TERMS.items())}</dl></section>

<section aria-labelledby="updates"><h2 id="updates">Updates and versions</h2>
<p>A check runs every month. When an agency posts a new file, IDEA Atlas is rebuilt and reviewed before it goes live, and the version number changes.
This is version {VERSION}.</p></section>

<section aria-labelledby="cite"><h2 id="cite">How to cite</h2>
<p>Rath, S. (2026). <cite>IDEA Atlas: Special education data for every U.S. school district</cite> (Version {VERSION}) [Online tool and data set]. https://doi.org/{DOI}</p>
<p>Online tool: <a href="{ATLAS_ORIGIN}{BASE}">{ATLAS_ORIGIN}{BASE}</a>. The data files for each version are kept permanently at <a href="https://doi.org/{DOI}">doi.org/{DOI}</a>.</p>
<p>To report an error, please use the <a href="{SITE}/contact/">contact page</a>.</p></section>
"""
    return page("Methods and sources", body, desc="How IDEA Atlas figures are made: sources, data rules, calculations, limits, and data dictionary.",
                path=BASE + "methods/", scripts=("atlas.js",), crumbs=[("IDEA Atlas", BASE)])


if __name__ == "__main__":
    sys.exit(main())
