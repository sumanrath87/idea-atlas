"""State pages for IDEA Atlas: /states/ and /state/<slug>/, with Spanish versions at /es/estados/ and /es/estado/<slug>/.

Each page sums up one state from figures the atlas already has:
  - students served under IDEA over time (Digest of Education Statistics, by state), beside the nation
  - how the state's districts compare: the typical district, the middle half, and the typical district nationwide
  - the state's results on federal indicators (State Performance Plan / Annual Performance Report) and dispute resolution counts
  - the state's 2026 IDEA rating
  - every district in the state, with a filter box
Nothing here ranks or grades states. Sentences say what was reported.
"""
from __future__ import annotations

import html
import json
import math
import re
import unicodedata

E = html.escape

FIX = {"District Of Columbia": "District of Columbia", "Bureau Of Indian Education": "Bureau of Indian Education",
       "U.S. Virgin Islands": "U.S. Virgin Islands", "Northern Marianas": "Northern Mariana Islands"}
ES_EXTRA = {"Bureau of Indian Education": "Oficina de Educación Indígena", "U.S. Virgin Islands": "Islas Vírgenes de EE. UU.",
            "Northern Mariana Islands": "Islas Marianas del Norte", "American Samoa": "Samoa Estadounidense"}
# The Digest's state tables name a few places differently.
HIST_NAME = {"Northern Mariana Islands": "Northern Marianas", "Bureau of Indian Education": "Education"}
TERRITORIES = {"AS", "GU", "MP", "PR", "VI", "BI"}
DET_ES = {"Meets requirements": "cumple los requisitos", "Needs assistance": "necesita ayuda", "Needs intervention": "necesita intervención",
          "Needs substantial intervention": "necesita intervención sustancial"}


def display(raw: str) -> str:
    t = raw.title() if isinstance(raw, str) else ""
    t = t.replace("U.S. Virgin Islands".title(), "U.S. Virgin Islands")
    return FIX.get(t, t)


def slug(name: str) -> str:
    a = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", a.lower()).strip("-")


class StateNames:
    """Code -> English name, Spanish name, and both slugs."""
    def __init__(self, d, state_es: dict):
        self.en, self.es = {}, {}
        for code, raw in d.groupby("state").state_name.first().items():
            n = display(raw)
            self.en[code] = n
            self.es[code] = state_es.get(n, ES_EXTRA.get(n, n))

    def path(self, code: str, es: bool = False) -> str:
        return f"es/estado/{slug(self.es[code])}/" if es else f"state/{slug(self.en[code])}/"


def _isnum(v) -> bool:
    return v is not None and not (isinstance(v, float) and math.isnan(v))


def build(d, st_med, nat_med, *, BASE, ATLAS_ORIGIN, page, write, fmt, figs, everyday, MEASURES, SOURCES, STATE_NOTES,
          es_site, hist: dict, sm: dict | None, names: StateNames, explain, guide_links: dict | None = None, og=None) -> list[str]:
    """Write every state page and both hubs. Returns the paths written, for the sitemap."""
    units = {m[0]: m[4] for m in MEASURES}
    short = {m[0]: m[3] for m in MEASURES}
    q = st_med["_q"]
    nat = {k: nat_med[k] for k in units}
    paths = []
    hub_en, hub_es = [], []
    us = hist.get("United States", {})

    def ok(r, k):
        return str(r[k + "_status"]) in ("ok", "ok_partial", "ok_minimum") and _isnum(r[k])

    for code, g in d.groupby("state"):
        en, es = names.en[code], names.es[code]
        p_en, p_es = names.path(code), names.path(code, es=True)
        n = len(g)
        enr = g.enrollment.where(g.enrollment > 0).sum()
        has_iep = g.idea_count.notna() & g.id_rate_status.astype(str).isin(["ok", "ok_partial", "ok_minimum"]) & g.enrollment.notna()
        iep_sum = g.loc[has_iep, "idea_count"].sum()
        iep_rate = 100 * iep_sum / g.loc[has_iep, "enrollment"].sum() if has_iep.any() and g.loc[has_iep, "enrollment"].sum() > 0 else None
        det_raw = g.determination_2026.dropna().iloc[0] if g.determination_2026.notna().any() else None
        det = det_raw.strip().capitalize() if isinstance(det_raw, str) else None
        med = {k: st_med[k].get(code) for k in units}
        lo = {k: q[k][0].get(code) for k in units}
        hi = {k: q[k][1].get(code) for k in units}

        # ---- trend from the Digest (state share of public school students served under IDEA)
        h = hist.get(HIST_NAME.get(en, en), {})
        pts = sorted((int(y), round(v["pct"], 1)) for y, v in h.items() if isinstance(v, dict) and _isnum(v.get("pct")))
        upts = sorted((int(y), round(v["pct"], 1)) for y, v in us.items() if isinstance(v, dict) and _isnum(v.get("pct")))
        cd = {"st": en, "state": 1, "m": {k: [None, "5", lo[k], med[k], hi[k], nat[k]] for k in units}}
        cd_es = {"st": es, "state": 1, "m": cd["m"]}
        if len(pts) >= 3:
            cd["tr"] = {"i": [list(p) for p in pts], "ic": [list(p) for p in upts]}
            cd_es["tr"] = cd["tr"]

        # ---- federal indicators and dispute resolution
        ind_rows_en, ind_rows_es, disp = [], [], {}
        if sm:
            stv = sm["st"].get(code, {})
            for i in sm["ind"]:
                k = i["k"]
                if k.startswith("d"):
                    if k in stv:
                        disp[k] = stv[k]
                    continue
                v = stv.get(k)
                nv = sm["nat"].get(k)
                if v is None:
                    continue
                ind_rows_en.append((i["en"], v[0], nv, v[1], i.get("nl"), i.get("note")))
                ind_rows_es.append((i["es"], v[0], nv, v[1], i.get("nl_es"), i.get("note_es")))

        # ---- every district in the state
        drows_en, drows_es = [], []
        for _, r in g.sort_values("display").iterrows():
            city = r.city.title() if isinstance(r.city, str) else ""
            e = f"{int(r.enrollment):,}" if _isnum(r.enrollment) else "—"
            a = fmt(r.id_rate, "per100") if ok(r, "id_rate") else "—"
            b = fmt(r.env_80plus, "per100") if ok(r, "env_80plus") else "—"
            drows_en.append(f'<tr><th scope="row"><a href="{BASE}district/{r.leaid}/">{E(r.display)}</a></th><td>{E(city)}</td><td>{e}</td><td>{a}</td><td>{b}</td></tr>')
            drows_es.append(f'<tr><th scope="row"><a href="{BASE}es/distrito/{r.leaid}/">{E(r.display)}</a></th><td>{E(city)}</td><td>{e}</td><td>{a}</td><td>{b}</td></tr>')

        args = dict(code=code, n=n, enr=enr, iep_sum=iep_sum, iep_rate=iep_rate, det=det, med=med, lo=lo, hi=hi, nat=nat,
                    pts=pts, upts=upts, disp=disp, units=units, short=short)
        pg_en, pg_es = page, page
        if og:
            import functools
            img_en, img_es = og(code, en, es, n, iep_sum, iep_rate)
            pg_en, pg_es = functools.partial(page, og_image=img_en), functools.partial(page, og_image=img_es)
        write(p_en + "index.html", _page_en(en, p_en, p_es, cd, ind_rows_en, drows_en, sm, BASE=BASE, page=pg_en, fmt=fmt, figs=figs,
                                            everyday=everyday, SOURCES=SOURCES, note=STATE_NOTES.get(code), explain=explain, guides=guide_links, **args))
        write(p_es + "index.html", _page_es(es, p_es, p_en, cd_es, ind_rows_es, drows_es, sm, BASE=BASE, page=pg_es, fmt=fmt, es_site=es_site,
                                            note=es_site.STATE_NOTES_ES.get(code), **args))
        paths += [p_en, p_es]
        sub_en = []
        if iep_rate is not None:
            sub_en.append(f"{fmt(iep_rate, 'per100')} per 100 students have IEPs")
        sub_es = [f"{fmt(iep_rate, 'per100')} de cada 100 estudiantes tienen IEP"] if iep_rate is not None else []
        sub_en.append(f"{n:,} {'district' if n == 1 else 'districts'}")
        sub_es.append(f"{n:,} {'distrito' if n == 1 else 'distritos'}")
        hub_en.append((code, en, p_en, " · ".join(sub_en), det))
        hub_es.append((code, es, p_es, " · ".join(sub_es), det))

    write("states/index.html", _hub_en(hub_en, BASE=BASE, page=page))
    write("es/estados/index.html", _hub_es(hub_es, BASE=BASE, page=page))
    return ["states/", "es/estados/"] + paths


# ---------------------------------------------------------------- English

def _figure(kind, caption, keys="", extra=""):
    k = f' data-keys="{keys}"' if keys else ""
    hidden = "" if kind == "trend" else ' aria-hidden="true"'
    cls = "chart explorable" if kind == "trend" else "chart"
    return f'<figure class="{cls}" data-chart="{kind}"{k}{extra}{hidden}><figcaption>{E(caption)}</figcaption><div class="chart-body"></div></figure>'


GROUPS = [("Who is served", ["id_rate", "pct_504"]), ("Where students learn", ["env_80plus", "env_lt40", "env_separate"]),
          ("Leaving school", ["grad_regular", "dropout"]),
          ("Discipline and safety", ["oos_idea", "oos_nodis", "expulsion_idea", "restraint_physical_idea", "seclusion_idea", "referral_idea", "arrest_idea"]),
          ("Funding and community", ["spend_per_pupil", "idea_federal_per_student", "child_poverty"])]
GROUPS_ES = ["Quiénes reciben servicios", "Dónde aprenden los estudiantes", "Al salir de la escuela", "Disciplina y seguridad", "Fondos y comunidad"]
UNIT_EN = {"per100": "per 100", "usd": "dollars"}


def _cmp_word(a, b, en=True):
    """'higher than', 'lower than', or 'about the same as' — within a tenth (relative) counts as about the same."""
    if not (_isnum(a) and _isnum(b)) or b == 0:
        return None
    if abs(a - b) <= max(0.1 * abs(b), 0.5):
        return "about the same as" if en else "parecido a"
    return ("higher than" if a > b else "lower than") if en else ("más alto que" if a > b else "más bajo que")


def _page_en(name, path, alt, cd, ind_rows, drows, sm, *, BASE, page, fmt, figs, everyday, SOURCES, note, explain, guides,
             code, n, enr, iep_sum, iep_rate, det, med, lo, hi, nat, pts, upts, disp, units, short):
    g = guides or {}
    lines = []
    if iep_rate is not None and iep_sum:
        ev = everyday(iep_rate)
        lines.append(f"In 2024–25, districts in {name} served {int(iep_sum):,} students with IEPs, about {iep_rate:.1f} of every 100 students enrolled"
                     + (f", or {ev}." if ev else "."))
    if _isnum(med["env_80plus"]):
        lines.append(f"In the typical {name} district, {med['env_80plus']:.1f} of every 100 students with IEPs spent 80% or more of the school day in a general class. "
                     f"The typical district nationwide reported ({nat['env_80plus']:.1f}).")
    if _isnum(med["grad_regular"]):
        lines.append(f"In the typical district, {med['grad_regular']:.1f} of every 100 students with IEPs who left school in 2023–24 left with a regular high school diploma. "
                     f"The typical district nationwide reported ({nat['grad_regular']:.1f}).")
    if _isnum(med["oos_idea"]) and _isnum(med["oos_nodis"]):
        lines.append(f"In 2023–24, the typical district suspended {med['oos_idea']:.1f} of every 100 students with IEPs out of school at least once, "
                     f"compared with {med['oos_nodis']:.1f} of every 100 students without disabilities.")
    if det:
        lines.append(f"In 2026, the U.S. Department of Education rated {name}'s work under IDEA as “{det.lower()}.”")
    glance = "".join(f"<li>{figs(s)}</li>" for s in lines)

    facts = [("Districts and agencies", f"{n:,}")]
    if enr and enr > 0:
        facts.append(("Students enrolled, 2024–25", f"{int(enr):,}"))
    if iep_sum:
        facts.append(("Students with IEPs, 2024–25", f"{int(iep_sum):,}"))
    if det:
        facts.append(("State IDEA rating, 2026", det))
    facts_html = "".join(f"<div><dt>{E(a)}</dt><dd>{E(b)}</dd></div>" for a, b in facts)

    # over time
    trend = ""
    if len(pts) >= 3:
        f0, f1 = pts[0], pts[-1]
        u_last = dict(upts).get(f1[0])
        s = (f"In {f0[0]}–{str(f0[0] + 1)[-2:]}, about {f0[1]:.1f} of every 100 public school students in {name} were served under IDEA. "
             f"In {f1[0]}–{str(f1[0] + 1)[-2:]}, about {f1[1]:.1f} were" + (f", compared with {u_last:.1f} nationwide." if u_last else "."))
        trend = f"""
<section aria-labelledby="s-time">
  <h2 id="s-time">Over time</h2>
  <ul class="plain"><li>{figs(s)}</li></ul>
  {_figure("trend", f"Students served under IDEA, ages 3 to 21, per 100 public school students: {name} and the nation, {f0[0]} to {f1[0]}.", "i", ' data-labels="' + E(name) + '|United States" data-years="sy"')}
  <p class="source">Source: U.S. Department of Education, Digest of Education Statistics, tables 204.70 (children ages 3 to 21 served under IDEA, Part B) and 203.20 (public school enrollment), several editions.</p>
</section>"""

    # how districts compare
    blocks = []
    for gi, (title, keys) in enumerate(GROUPS):
        keys = [k for k in keys if _isnum(med.get(k))]
        if not keys:
            continue
        body_rows = "".join(
            f'<tr><th scope="row">{E(short[k])}</th><td>{fmt(med[k], units[k])}</td>'
            f'<td>{(fmt(lo[k], units[k]) + " to " + fmt(hi[k], units[k])) if _isnum(lo[k]) and _isnum(hi[k]) else "—"}</td>'
            f'<td>{fmt(nat[k], units[k]) if _isnum(nat[k]) else "—"}</td></tr>' for k in keys)
        tid = f"cmp-{gi}"
        blocks.append(f"""<h3>{E(title)}</h3>
  {_figure("range", f"{title}: where {name} districts sit", ",".join(keys))}
  <div class="table-wrap" role="region" tabindex="0" aria-labelledby="{tid}"><table class="profile narrow-ish"><caption id="{tid}">{E(title)}: typical district in {E(name)} and nationwide</caption>
  <thead><tr><th scope="col">Measure</th><th scope="col">Typical {E(name)} district</th><th scope="col">Middle half of {E(name)} districts</th><th scope="col">Typical district nationwide</th></tr></thead>
  <tbody>{body_rows}</tbody></table></div>""")
    compare = f"""
<section aria-labelledby="s-cmp">
  <h2 id="s-cmp">How {E(name)} districts compare</h2>
  <p>The typical district is the one in the middle when all {E(name)} districts are lined up from lowest to highest. The middle half shows the range where most districts fall.
  Rates are per 100 students in each group; money is per student.</p>
  {explain("typical", "middle")}
  {"".join(blocks)}
  <p class="source">Sources: IDEA Part B child count, educational environments, and exiting data (2023–24 and 2024–25); Civil Rights Data Collection (2023–24); Census Bureau school finance survey (fiscal 2024); Small Area Income and Poverty Estimates (2024). <a href="{BASE}methods/#sources">About the sources</a></p>
</section>""" if blocks else ""

    # federal indicators
    ind = ""
    if ind_rows:
        trs = "".join(f'<tr><th scope="row">{E(lbl)}</th><td>{v:.1f}%</td><td>{(f"{nv:.1f}%" if _isnum(nv) else "—")}</td><td>{E(y)}</td></tr>'
                      for lbl, v, nv, y, _nl, _note in ind_rows)
        notes = "".join(f"<li>{E(nl)}: {E(nt)}</li>" for _l, _v, _nv, _y, nl, nt in ind_rows if nl and nt)
        g_ind = f' <a href="{g["indicators"]}">How to read the state indicators</a>.' if g.get("indicators") else ""
        ind = f"""
<section aria-labelledby="s-ind">
  <h2 id="s-ind">Results on federal indicators</h2>
  <p>Every state reports its results on a set of federal indicators each year, in its State Performance Plan and Annual Performance Report. These are statewide figures.{g_ind}</p>
  <div class="table-wrap" role="region" tabindex="0" aria-labelledby="ind-cap"><table class="profile"><caption id="ind-cap">{E(name)} results on federal indicators, with the national figure</caption>
  <thead><tr><th scope="col">Indicator</th><th scope="col">{E(name)}</th><th scope="col">Nation</th><th scope="col">Year</th></tr></thead><tbody>{trs}</tbody></table></div>
  {f'<ul class="notes">{notes}</ul>' if notes else ""}
  <p class="source">{E(sm["source"])}</p>
</section>"""

    # dispute resolution
    dsp = ""
    if disp:
        y = next(iter(disp.values()))[1]
        parts = []
        if "dwsc" in disp: parts.append(f"{disp['dwsc'][0]:,} signed written state complaints")
        if "dmed" in disp: parts.append(f"{disp['dmed'][0]:,} mediation requests")
        if "ddpc" in disp: parts.append(f"{disp['ddpc'][0]:,} due process complaints")
        s = f"In {y}, {name} received " + (", ".join(parts[:-1]) + (", and " if len(parts) > 2 else " and ") + parts[-1] if len(parts) > 1 else parts[0]) + "."
        if "dhear" in disp:
            s += f" {disp['dhear'][0]:,} due process {'hearing was' if disp['dhear'][0] == 1 else 'hearings were'} fully held."
        g_d = f' <a href="{g["disputes"]}">What these numbers mean</a>.' if g.get("disputes") else ""
        dsp = f"""
<section aria-labelledby="s-disp">
  <h2 id="s-disp">Complaints, mediation, and hearings</h2>
  <p>When a family and a school disagree, IDEA offers several ways to resolve it. These counts are for the whole state.{g_d}</p>
  <ul class="plain"><li>{figs(s)}</li></ul>
  <p class="source">Source: U.S. Department of Education, IDEA Part B Dispute Resolution data, {E(y)}.</p>
</section>"""

    rating = f"""
<section aria-labelledby="s-rate">
  <h2 id="s-rate">State IDEA rating</h2>
  <p>Each year the U.S. Department of Education reviews how each state carries out IDEA and gives one of four ratings. In 2026, {E(name)} was rated <strong>{E(det.lower())}</strong>.</p>
  {explain("rating")}
  <p class="source">Source: {E(SOURCES['det'][0])}, {E(SOURCES['det'][1])}.</p>
</section>""" if det else ""

    note_html = f'<p class="note">{E(note)}</p>' if note else ""
    dl = f"""
<section aria-labelledby="s-all">
  <h2 id="s-all">Every district in {E(name)}</h2>
  <p>{n:,} districts and other local education agencies, in alphabetical order. Open a district for its full page, or <a href="{BASE}table/?state={code}">sort and filter them in the table</a>.</p>
  <div class="filter" data-filter-for="dl-{code}"><label for="f-{code}">Filter by district or city</label>
    <input id="f-{code}" type="search" autocomplete="off"><output aria-live="polite"></output></div>
  <div class="table-wrap" role="region" tabindex="0" aria-labelledby="dl-cap"><table class="profile districts" id="dl-{code}"><caption id="dl-cap">Districts in {E(name)}: students enrolled, students with IEPs per 100 enrolled, and students with IEPs in a general class 80% or more of the day, per 100 (2024–25)</caption>
  <thead><tr><th scope="col">District</th><th scope="col">City</th><th scope="col">Enrolled</th><th scope="col">With IEPs, per 100</th><th scope="col">General class 80%+, per 100</th></tr></thead>
  <tbody>{"".join(drows)}</tbody></table></div>
</section>"""

    guide_box = ""
    if g.get("hub"):
        items = "".join(f'<li><a href="{u}">{E(t)}</a></li>' for t, u in g.get("featured", []))
        guide_box = f"""
<section aria-labelledby="s-guides">
  <h2 id="s-guides">Guides</h2>
  <p>Plain-language guides to reading these figures and asking good questions about them.</p>
  <ul class="guide-list">{items}</ul>
  <p><a href="{g['hub']}">All guides</a></p>
</section>"""

    report = f"""
<section aria-labelledby="s-rpt" class="rpt-cta">
  <h2 id="s-rpt">Make a report for a district</h2>
  <p>Choose any {E(name)} district and get a printable report written for a family, a school leader, or a researcher.</p>
  <p><a class="button" href="{BASE}report/">Make a report</a></p>
</section>"""

    body = f"""
<h1>Special education in {E(name)}</h1>
<p class="lede">How {E(name)}'s school districts serve students with disabilities, in plain words, from public federal data.</p>
<dl class="facts">{facts_html}</dl>
{note_html}
<section aria-labelledby="g-h" class="glance">
  <h2 id="g-h">At a glance</h2>
  <ul>{glance}</ul>
  {explain("iep", "per100")}
</section>
{trend}{compare}{ind}{dsp}{rating}{guide_box}{dl}{report}
<p class="hint">These figures describe what was reported. They are not grades. See <a href="{BASE}methods/">about the data</a> for how each one is made.</p>"""
    cdj = json.dumps(cd, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    body = f'<script type="application/json" id="chart-data">{cdj}</script>' + body
    desc = (f"Special education in {name}: students with IEPs, where they learn, graduation, discipline, federal indicator results, "
            f"and every school district, from public federal data.")
    return page(f"Special education in {name}", body, desc=desc[:300], path=BASE + path, scripts=("atlas.js",),
                crumbs=[("IDEA Atlas", BASE), ("States", BASE + "states/")], alt=BASE + alt)


def _hub_en(items, *, BASE, page):
    def li(it):
        code, name, p, sub, det = it
        return f'<li><a href="{BASE}{p}">{E(name)}</a><span class="sub">{E(sub)}</span></li>'
    main = [i for i in items if i[0] not in TERRITORIES]
    other = [i for i in items if i[0] in TERRITORIES]
    main.sort(key=lambda i: i[1]); other.sort(key=lambda i: i[1])
    body = f"""
<h1>Special education by state</h1>
<p class="lede">Each state page sums up how its districts serve students with disabilities, how the state did on federal indicators, and links to every district.</p>
<section aria-labelledby="st-h">
  <h2 id="st-h">States and the District of Columbia</h2>
  <ul class="state-grid">{"".join(li(i) for i in main)}</ul>
</section>
<section aria-labelledby="ot-h">
  <h2 id="ot-h">Territories and the Bureau of Indian Education</h2>
  <ul class="state-grid">{"".join(li(i) for i in other)}</ul>
</section>
<p class="hint">Students with IEPs per 100 enrolled are for 2024–25, from district counts. They are not grades.</p>"""
    return page("Special education by state", body,
                desc="Special education data for every U.S. state: students with IEPs, where they learn, graduation, discipline, federal indicators, and every district.",
                path=BASE + "states/", scripts=("atlas.js",), crumbs=[("IDEA Atlas", BASE)], alt=BASE + "es/estados/")


# ---------------------------------------------------------------- Spanish

def _page_es(name, path, alt, cd, ind_rows, drows, sm, *, BASE, page, fmt, es_site, note,
             code, n, enr, iep_sum, iep_rate, det, med, lo, hi, nat, pts, upts, disp, units, short):
    figs, everyday = es_site.figs_es, es_site.everyday_es
    ex = lambda *k: es_site.explain_es(BASE, *k, full=True)
    sh = es_site.SHORT_ES
    lines = []
    if iep_rate is not None and iep_sum:
        ev = everyday(iep_rate)
        lines.append(f"En 2024–25, los distritos de {name} atendieron a {int(iep_sum):,} estudiantes con IEP, aproximadamente {iep_rate:.1f} de cada 100 estudiantes inscritos"
                     + (f", o {ev}." if ev else "."))
    if _isnum(med["env_80plus"]):
        lines.append(f"En el distrito típico de {name}, {med['env_80plus']:.1f} de cada 100 estudiantes con IEP pasaron el 80% o más del día escolar en una clase general. "
                     f"El distrito típico del país informó ({nat['env_80plus']:.1f}).")
    if _isnum(med["grad_regular"]):
        lines.append(f"En el distrito típico, {med['grad_regular']:.1f} de cada 100 estudiantes con IEP que salieron de la escuela en 2023–24 lo hicieron con un diploma regular. "
                     f"El distrito típico del país informó ({nat['grad_regular']:.1f}).")
    if _isnum(med["oos_idea"]) and _isnum(med["oos_nodis"]):
        lines.append(f"En 2023–24, el distrito típico suspendió fuera de la escuela al menos una vez a {med['oos_idea']:.1f} de cada 100 estudiantes con IEP, "
                     f"frente a {med['oos_nodis']:.1f} de cada 100 estudiantes sin discapacidades.")
    det_es = DET_ES.get(det) if det else None
    if det_es:
        lines.append(f"En 2026, el Departamento de Educación de EE. UU. calificó el trabajo de {name} bajo IDEA como «{det_es}».")
    glance = "".join(f"<li>{figs(s)}</li>" for s in lines)
    facts = [("Distritos y agencias", f"{n:,}")]
    if enr and enr > 0:
        facts.append(("Estudiantes inscritos, 2024–25", f"{int(enr):,}"))
    if iep_sum:
        facts.append(("Estudiantes con IEP, 2024–25", f"{int(iep_sum):,}"))
    if det_es:
        facts.append(("Calificación estatal de IDEA, 2026", det_es[0].upper() + det_es[1:]))
    facts_html = "".join(f"<div><dt>{E(a)}</dt><dd>{E(b)}</dd></div>" for a, b in facts)
    us_name = "Estados Unidos"

    trend = ""
    if len(pts) >= 3:
        f0, f1 = pts[0], pts[-1]
        u_last = dict(upts).get(f1[0])
        s = (f"En {f0[0]}–{str(f0[0] + 1)[-2:]}, aproximadamente {f0[1]:.1f} de cada 100 estudiantes de escuelas públicas de {name} recibían servicios bajo IDEA. "
             f"En {f1[0]}–{str(f1[0] + 1)[-2:]}, aproximadamente {f1[1]:.1f}" + (f", frente a {u_last:.1f} en todo el país." if u_last else "."))
        trend = f"""
<section aria-labelledby="s-time">
  <h2 id="s-time">A lo largo del tiempo</h2>
  <ul class="plain"><li>{figs(s)}</li></ul>
  {_figure("trend", f"Estudiantes de 3 a 21 años con servicios bajo IDEA, por cada 100 estudiantes de escuelas públicas: {name} y el país, {f0[0]} a {f1[0]}.", "i", ' data-labels="' + E(name) + '|' + us_name + '" data-years="sy"')}
  <p class="source">Fuente: Departamento de Educación de EE. UU., Digest of Education Statistics, tablas 204.70 (niños de 3 a 21 años con servicios bajo IDEA, Parte B) y 203.20 (inscripción en escuelas públicas), varias ediciones.</p>
</section>"""

    blocks = []
    for gi, ((title, keys), t_es) in enumerate(zip(GROUPS, GROUPS_ES)):
        keys = [k for k in keys if _isnum(med.get(k))]
        if not keys:
            continue
        body_rows = "".join(
            f'<tr><th scope="row">{E(sh[k])}</th><td>{fmt(med[k], units[k])}</td>'
            f'<td>{(fmt(lo[k], units[k]) + " a " + fmt(hi[k], units[k])) if _isnum(lo[k]) and _isnum(hi[k]) else "—"}</td>'
            f'<td>{fmt(nat[k], units[k]) if _isnum(nat[k]) else "—"}</td></tr>' for k in keys)
        tid = f"cmp-{gi}"
        blocks.append(f"""<h3>{E(t_es)}</h3>
  {_figure("range", f"{t_es}: dónde se ubican los distritos de {name}", ",".join(keys))}
  <div class="table-wrap" role="region" tabindex="0" aria-labelledby="{tid}"><table class="profile"><caption id="{tid}">{E(t_es)}: distrito típico de {E(name)} y del país</caption>
  <thead><tr><th scope="col">Medida</th><th scope="col">Distrito típico de {E(name)}</th><th scope="col">Mitad central de los distritos de {E(name)}</th><th scope="col">Distrito típico del país</th></tr></thead>
  <tbody>{body_rows}</tbody></table></div>""")
    compare = f"""
<section aria-labelledby="s-cmp">
  <h2 id="s-cmp">Cómo se comparan los distritos de {E(name)}</h2>
  <p>El distrito típico es el que queda en el medio cuando se ordenan todos los distritos de {E(name)} de menor a mayor. La mitad central muestra el rango donde está la mayoría.</p>
  {ex("typical", "middle")}
  {"".join(blocks)}
</section>""" if blocks else ""

    ind = ""
    if ind_rows:
        trs = "".join(f'<tr><th scope="row">{E(lbl)}</th><td>{v:.1f} %</td><td>{(f"{nv:.1f} %" if _isnum(nv) else "—")}</td><td>{E(y)}</td></tr>'
                      for lbl, v, nv, y, _nl, _note in ind_rows)
        notes = "".join(f"<li>{E(nl)}: {E(nt)}</li>" for _l, _v, _nv, _y, nl, nt in ind_rows if nl and nt)
        ind = f"""
<section aria-labelledby="s-ind">
  <h2 id="s-ind">Resultados en los indicadores federales</h2>
  <p>Cada estado informa cada año sus resultados en un conjunto de indicadores federales, en su Plan de Desempeño Estatal e Informe Anual de Desempeño. Son cifras de todo el estado.</p>
  <div class="table-wrap" role="region" tabindex="0" aria-labelledby="ind-cap"><table class="profile"><caption id="ind-cap">Resultados de {E(name)} en los indicadores federales, con la cifra nacional</caption>
  <thead><tr><th scope="col">Indicador</th><th scope="col">{E(name)}</th><th scope="col">País</th><th scope="col">Año</th></tr></thead><tbody>{trs}</tbody></table></div>
  {f'<ul class="notes">{notes}</ul>' if notes else ""}
  <p class="source">{E(sm["source_es"])}</p>
</section>"""

    dsp = ""
    if disp:
        y = next(iter(disp.values()))[1]
        parts = []
        if "dwsc" in disp: parts.append(f"{disp['dwsc'][0]:,} quejas escritas firmadas ante el estado")
        if "dmed" in disp: parts.append(f"{disp['dmed'][0]:,} solicitudes de mediación")
        if "ddpc" in disp: parts.append(f"{disp['ddpc'][0]:,} demandas de debido proceso")
        s = f"En {y}, {name} recibió " + (", ".join(parts[:-1]) + " y " + parts[-1] if len(parts) > 1 else parts[0]) + "."
        if "dhear" in disp:
            s += f" Se celebraron completas {disp['dhear'][0]:,} {'audiencia' if disp['dhear'][0] == 1 else 'audiencias'} de debido proceso."
        dsp = f"""
<section aria-labelledby="s-disp">
  <h2 id="s-disp">Quejas, mediación y audiencias</h2>
  <p>Cuando una familia y una escuela no están de acuerdo, IDEA ofrece varias maneras de resolverlo. Estas cifras son de todo el estado.</p>
  <ul class="plain"><li>{figs(s)}</li></ul>
  <p class="source">Fuente: Departamento de Educación de EE. UU., datos de resolución de disputas de IDEA, Parte B, {E(y)}.</p>
</section>"""

    rating = f"""
<section aria-labelledby="s-rate">
  <h2 id="s-rate">Calificación estatal de IDEA</h2>
  <p>Cada año el Departamento de Educación de EE. UU. revisa cómo cada estado cumple con IDEA y le da una de cuatro calificaciones. En 2026, {E(name)} recibió la calificación <strong>{E(det_es)}</strong>.</p>
  {ex("rating")}
</section>""" if det_es else ""

    note_html = f'<p class="note">{E(note)}</p>' if note else ""
    dl = f"""
<section aria-labelledby="s-all">
  <h2 id="s-all">Todos los distritos de {E(name)}</h2>
  <p>{n:,} distritos y otras agencias educativas locales, en orden alfabético.</p>
  <div class="filter" data-filter-for="dl-{code}"><label for="f-{code}">Filtrar por distrito o ciudad</label>
    <input id="f-{code}" type="search" autocomplete="off"><output aria-live="polite"></output></div>
  <div class="table-wrap" role="region" tabindex="0" aria-labelledby="dl-cap"><table class="profile districts" id="dl-{code}"><caption id="dl-cap">Distritos de {E(name)}: estudiantes inscritos, estudiantes con IEP por cada 100 inscritos y estudiantes con IEP en una clase general el 80% o más del día, por cada 100 (2024–25)</caption>
  <thead><tr><th scope="col">Distrito</th><th scope="col">Ciudad</th><th scope="col">Inscritos</th><th scope="col">Con IEP, por cada 100</th><th scope="col">Clase general 80%+, por cada 100</th></tr></thead>
  <tbody>{"".join(drows)}</tbody></table></div>
</section>"""
    report = f"""
<section aria-labelledby="s-rpt" class="rpt-cta">
  <h2 id="s-rpt">Crear un informe sobre un distrito</h2>
  <p>Elija cualquier distrito de {E(name)} y obtenga un informe para imprimir, escrito para una familia, un líder escolar o un investigador.</p>
  <p><a class="button" href="{BASE}es/informe/">Crear un informe</a></p>
</section>"""
    body = f"""
<h1>Educación especial en {E(name)}</h1>
<p class="lede">Cómo los distritos escolares de {E(name)} atienden a los estudiantes con discapacidades, en palabras sencillas, con datos federales públicos.</p>
<dl class="facts">{facts_html}</dl>
{note_html}
<section aria-labelledby="g-h" class="glance">
  <h2 id="g-h">De un vistazo</h2>
  <ul>{glance}</ul>
  {ex("iep", "per100")}
</section>
{trend}{compare}{ind}{dsp}{rating}{dl}{report}
<p class="hint">Estas cifras describen lo que se informó. No son calificaciones.</p>"""
    cdj = json.dumps(cd, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    body = f'<script type="application/json" id="chart-data">{cdj}</script>' + body
    desc = f"Educación especial en {name}: estudiantes con IEP, dónde aprenden, graduación, disciplina, indicadores federales y todos los distritos escolares."
    return page(f"Educación especial en {name}", body, desc=desc[:300], path=BASE + path, scripts=("atlas.js",),
                crumbs=[("IDEA Atlas", BASE + "es/"), ("Estados", BASE + "es/estados/")], lang="es", alt=BASE + alt)


def _hub_es(items, *, BASE, page):
    def li(it):
        code, name, p, sub, det = it
        return f'<li><a href="{BASE}{p}">{E(name)}</a><span class="sub">{E(sub)}</span></li>'
    main = sorted([i for i in items if i[0] not in TERRITORIES], key=lambda i: unicodedata.normalize("NFKD", i[1]))
    other = sorted([i for i in items if i[0] in TERRITORIES], key=lambda i: unicodedata.normalize("NFKD", i[1]))
    body = f"""
<h1>Educación especial por estado</h1>
<p class="lede">Cada página estatal resume cómo sus distritos atienden a los estudiantes con discapacidades, los resultados del estado en los indicadores federales y enlaces a todos sus distritos.</p>
<section aria-labelledby="st-h">
  <h2 id="st-h">Estados y el Distrito de Columbia</h2>
  <ul class="state-grid">{"".join(li(i) for i in main)}</ul>
</section>
<section aria-labelledby="ot-h">
  <h2 id="ot-h">Territorios y la Oficina de Educación Indígena</h2>
  <ul class="state-grid">{"".join(li(i) for i in other)}</ul>
</section>
<p class="hint">Los estudiantes con IEP por cada 100 inscritos son de 2024–25, según los conteos de los distritos. No son calificaciones.</p>"""
    return page("Educación especial por estado", body,
                desc="Datos de educación especial de cada estado de EE. UU.: estudiantes con IEP, dónde aprenden, graduación, disciplina, indicadores federales y todos los distritos.",
                path=BASE + "es/estados/", scripts=("atlas.js",), crumbs=[("IDEA Atlas", BASE + "es/")], lang="es", alt=BASE + "states/")
