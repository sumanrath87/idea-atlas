"""History page for IDEA Atlas: fifty years of special education in U.S. public schools.

Built from build/history/national.json and states.json (made by history/build_national.py from the
Digest of Education Statistics). Charts are drawn here as static SVG, so they print and need no script;
each chart is hidden from screen readers and has a full table one click away.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

E = html.escape
HERE = Path(__file__).resolve().parent / "history"

# validated categorical order (dataviz reference palette, light)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, INK2, MUTED, RULE, PAPER, ACCENT = "#1d2126", "#474d55", "#5b6168", "#e6e1d6", "#fbfaf6", "#8a2b2b"

MILESTONES = [
    (1975, "1975", "Congress passes the Education for All Handicapped Children Act. For the first time, every child with a disability has a right to a free appropriate public education."),
    (1986, "1986", "Amendments extend the law to children ages 3 to 5 and create early intervention for infants and toddlers."),
    (1990, "1990", "The law is renamed the Individuals with Disabilities Education Act (IDEA). Autism and traumatic brain injury become their own categories, and planning for life after school is added."),
    (1997, "1997", "Amendments emphasize learning in the general curriculum and taking part in state tests, and let states use developmental delay up to age 9."),
    (2004, "2004", "The law is reauthorized as the Individuals with Disabilities Education Improvement Act, with changes to how learning disabilities may be identified."),
]

CAT_LABEL = {"learning": "Specific learning disability", "speech": "Speech or language impairment", "otherhealth": "Other health impairment",
             "autism": "Autism", "devdelay": "Developmental delay", "intellectual": "Intellectual disability", "emotional": "Emotional disturbance"}


def sy(y: int) -> str:
    """Fall year to school year: 1976 -> 1976–77."""
    return f"{y}–{str(y + 1)[-2:]}"


def line_chart(series: list[dict], *, ymax: float | None = None, unit: str = "", w: int = 720, h: int = 320,
               xmin: int | None = None, xmax: int | None = None, marks: list[tuple[int, str]] | None = None,
               ticks: list[float] | None = None, gap_years: int = 3) -> str:
    """Static SVG line chart. series: [{label, color, points: {year: value}}]. Lines break across gaps longer than
    gap_years (drawn dashed), so missing years are never hidden. Labels sit at the end of each line."""
    L, R, T, B = 48, 190, 14, 34
    ys = [y for s in series for y in s["points"]]
    x0, x1 = xmin or min(ys), xmax or max(ys)
    vmax = ymax or max(v for s in series for v in s["points"].values()) * 1.1
    X = lambda y: L + (w - L - R) * (y - x0) / max(1, x1 - x0)
    Y = lambda v: T + (h - T - B) * (1 - v / vmax)
    out = [f'<svg viewBox="0 0 {w} {h}" class="hchart" aria-hidden="true" focusable="false">']
    tks = ticks or [vmax * i / 4 for i in range(5)]
    for t in tks:
        out.append(f'<line x1="{L}" x2="{w - R}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" stroke="{RULE}" stroke-width="1"/>')
        lab = f"{t:,.0f}{unit}" if float(t).is_integer() else f"{t:,.1f}{unit}"
        out.append(f'<text x="{L - 8}" y="{Y(t) + 4:.1f}" text-anchor="end" class="ax">{E(lab)}</text>')
    step = 10 if x1 - x0 > 30 else 5
    for yr in range((x0 // step + 1) * step if x0 % step else x0, x1 + 1, step):
        out.append(f'<text x="{X(yr):.1f}" y="{h - 10}" text-anchor="middle" class="ax">{yr}</text>')
    for yr, txt in (marks or []):
        out.append(f'<line x1="{X(yr):.1f}" x2="{X(yr):.1f}" y1="{T}" y2="{h - B}" stroke="{MUTED}" stroke-width="1" stroke-dasharray="2 3"/>')
        out.append(f'<text x="{X(yr) + 4:.1f}" y="{T + 10}" class="mk">{E(txt)}</text>')
    ends = []
    for s in series:
        pts = sorted(s["points"].items())
        segs, cur = [], [pts[0]]
        for a, b in zip(pts, pts[1:]):
            if b[0] - a[0] > gap_years:
                segs.append(cur)
                cur = [b]
            else:
                cur.append(b)
        segs.append(cur)
        for i, seg in enumerate(segs):
            if i:
                a, b = segs[i - 1][-1], seg[0]
                out.append(f'<line x1="{X(a[0]):.1f}" y1="{Y(a[1]):.1f}" x2="{X(b[0]):.1f}" y2="{Y(b[1]):.1f}" stroke="{s["color"]}" stroke-width="1.5" stroke-dasharray="3 4" opacity=".7"/>')
            d = " ".join(f'{"M" if j == 0 else "L"}{X(y):.1f},{Y(v):.1f}' for j, (y, v) in enumerate(seg))
            out.append(f'<path d="{d}" fill="none" stroke="{s["color"]}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>')
        lone = {seg[0][0] for seg in segs if len(seg) == 1} | ({p[0] for p in pts} if len(pts) <= 8 else set())
        for y, v in pts:
            if y in lone:
                out.append(f'<circle cx="{X(y):.1f}" cy="{Y(v):.1f}" r="3" fill="{s["color"]}" stroke="{PAPER}" stroke-width="1.5"><title>{E(s["label"])}, {sy(y)}: {v:,.1f}{unit}</title></circle>')
        ly, lv = pts[-1]
        ends.append([Y(lv), s, lv])
    ends.sort(key=lambda e: e[0])
    for i in range(1, len(ends)):                       # keep end labels from overlapping
        if ends[i][0] - ends[i - 1][0] < 15:
            ends[i][0] = ends[i - 1][0] + 15
    for yy, s, lv in ends:
        val = f"{lv:,.1f}{unit}"
        out.append(f'<text x="{w - R + 8}" y="{yy + 4:.1f}" class="el"><tspan class="ev" fill="{INK}">{E(val)}</tspan>'
                   f'<tspan dx="6" fill="{INK2}">{E(s["label"])}</tspan></text>')
    out.append("</svg>")
    return "".join(out)


def key(series) -> str:
    return '<ul class="chart-key">' + "".join(
        f'<li><span class="k-line" style="background:{s["color"]}"></span>{E(s["label"])}</li>' for s in series) + "</ul>"


def table(caption: str, tid: str, head: list[str], rows: list[list[str]]) -> str:
    th = "".join(f'<th scope="col">{E(x)}</th>' for x in head)
    body = "".join("<tr><th scope=\"row\">" + E(r[0]) + "</th>" + "".join(f"<td>{E(c)}</td>" for c in r[1:]) + "</tr>" for r in rows)
    return (f'<div class="table-wrap" role="region" tabindex="0" aria-labelledby="{tid}"><table class="profile">'
            f'<caption id="{tid}">{E(caption)}</caption><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>')


def numbers(inner: str, label: str = "The numbers, year by year") -> str:
    return f'<details class="numbers"><summary>{E(label)}</summary>{inner}</details>'


def f1(v):
    return "—" if v is None else f"{v:,.1f}"


def render(page, explain, BASE: str, sources_note: str = "") -> str:
    nat = json.loads((HERE / "national.json").read_text())
    states = json.loads((HERE / "states.json").read_text())
    I = lambda d: {int(k): v for k, v in d.items() if v is not None}
    served = I(nat["served_thousands"])
    pct = I(nat["pct_enrollment"])
    first, last = min(pct), max(pct)

    # ---- 1. how many
    s1 = [{"label": "Share of public school students", "color": ACCENT, "points": {y: v for y, v in pct.items()}}]
    c1 = line_chart(s1, ymax=20, unit="", xmin=1975, xmax=last, ticks=[0, 5, 10, 15, 20],
                    marks=[(1975, "1975 law"), (1990, "IDEA"), (2004, "2004")])
    t1 = table("Students ages 3 to 21 served under IDEA", "h1-t", ["School year", "Students served", "Per 100 public school students"],
               [[sy(y), f"{served[y] * 1000:,.0f}", f1(pct.get(y))] for y in sorted(served)])
    sec1 = f"""
<section aria-labelledby="h-many">
  <h2 id="h-many">How many students are served</h2>
  <ul class="plain">
    <li>In {sy(first)}, about <span class="fig">{pct[first]:.1f}</span> of every 100 public school students were served under the law, or about 1 in {round(100 / pct[first])}.</li>
    <li>In {sy(last)}, it was about <span class="fig">{pct[last]:.1f}</span> of every 100, or about 1 in {round(100 / pct[last])}: <span class="fig">{served[last] / 1000:.1f} million</span> students.</li>
  </ul>
  <figure class="chart wide" aria-hidden="true"><figcaption>Students served under the law, per 100 public school students, {sy(first)} to {sy(last)}. Dashed lines join years the federal tables do not report.</figcaption>{c1}</figure>
  {explain("per100", "idea")}
  {numbers(t1)}
  <p class="source">Source: U.S. Department of Education, Digest of Education Statistics, table 204.30 (editions 2013 to 2023). Counts before 1994–95 include children served under a related program (Chapter 1).</p>
</section>"""

    # ---- 2. which disabilities (share of all students served)
    cats = nat["by_category_thousands"]
    years = sorted(int(y) for y in cats if cats[y].get("all"))
    s2 = []
    for i, (k, lab) in enumerate(CAT_LABEL.items()):
        pts = {y: 100 * cats[str(y)][k] / cats[str(y)]["all"] for y in years if cats[str(y)].get(k) is not None}
        if pts:
            s2.append({"label": lab, "color": SERIES[i], "points": pts})
    c2 = line_chart(s2, ymax=50, xmin=1975, xmax=last, ticks=[0, 10, 20, 30, 40, 50])
    rows2 = [[sy(y)] + [f1(100 * cats[str(y)][k] / cats[str(y)]["all"]) if cats[str(y)].get(k) is not None else "—" for k in CAT_LABEL] for y in years]
    t2 = table("Students served, by federal category, per 100 students served", "h2-t", ["School year"] + list(CAT_LABEL.values()), rows2)
    lk = lambda k, y: 100 * cats[str(y)][k] / cats[str(y)]["all"]
    sec2 = f"""
<section aria-labelledby="h-which">
  <h2 id="h-which">Which disabilities</h2>
  <ul class="plain">
    <li>In {sy(first)}, speech or language impairment was the largest category: about <span class="fig">{lk('speech', first):.0f}</span> of every 100 students served.</li>
    <li>Specific learning disability has been the largest since the 1980s. In {sy(last)}, it was about <span class="fig">{lk('learning', last):.0f}</span> of every 100.</li>
    <li>Autism, a separate category since 1990, grew to about <span class="fig">{lk('autism', last):.0f}</span> of every 100 in {sy(last)}.</li>
  </ul>
  <figure class="chart wide" aria-hidden="true"><figcaption>Share of students served in each of the seven largest federal categories, per 100 students served.</figcaption>{key(s2)}{c2}</figure>
  {explain("categories")}
  {numbers(t2)}
  <p class="source">Source: Digest of Education Statistics, table 204.30. Categories and their names changed over time; for example, autism and traumatic brain injury were added in 1990.</p>
</section>"""

    # ---- 3. where students learn
    env = I(nat["environments"])
    e_first, e_last = min(env), max(env)
    s3 = [{"label": "80% or more of the day", "color": "#0d366b", "points": {y: v["80plus"] for y, v in env.items()}},
          {"label": "40% to 79%", "color": "#3987e5", "points": {y: v["40_79"] for y, v in env.items()}},
          {"label": "Less than 40%", "color": "#86b6ef", "points": {y: v["lt40"] for y, v in env.items()}},
          {"label": "Separate school or facility", "color": "#b9b4a8",
           "points": {y: (v["sep_school"] or 0) + (v["residential"] or 0) + (v["homebound"] or 0) for y, v in env.items()}}]
    c3 = line_chart(s3, ymax=80, xmin=1985, xmax=e_last, ticks=[0, 20, 40, 60, 80], marks=[(2019, "Counting change")])
    t3 = table("School-age students with IEPs, time in a general class, per 100", "h3-t",
               ["Fall of", "80% or more", "40% to 79%", "Less than 40%", "Separate school or facility"],
               [[str(y), f1(v["80plus"]), f1(v["40_79"]), f1(v["lt40"]), f1((v["sep_school"] or 0) + (v["residential"] or 0) + (v["homebound"] or 0))] for y, v in sorted(env.items())])
    sec3 = f"""
<section aria-labelledby="h-where">
  <h2 id="h-where">Time in general classes</h2>
  <ul class="plain">
    <li>In {e_first}, about <span class="fig">{env[e_first]['80plus']:.0f}</span> of every 100 school-age students with IEPs spent most of the day (80% or more) in a general class.</li>
    <li>By {e_last}, it was about <span class="fig">{env[e_last]['80plus']:.0f}</span> of every 100, or about {'2 in 3' if 63 <= env[e_last]['80plus'] <= 70 else 'half'}.</li>
  </ul>
  <figure class="chart wide" aria-hidden="true"><figcaption>School-age students with IEPs by time in a general class, per 100, {e_first} to {e_last}. The federal tables skip 1991 to 1993 (dashed). From 2019, 5-year-olds in kindergarten are counted as school age.</figcaption>{key(s3)}{c3}</figure>
  {explain("settings")}
  {numbers(t3)}
  <p class="source">Source: Digest of Education Statistics, table 204.60.</p>
</section>"""

    # ---- 4. leaving school
    ex = I(nat["exits"])
    x_first, x_last = min(ex), max(ex)
    s4 = [{"label": "Regular diploma", "color": SERIES[0], "points": {y: v["regular"] for y, v in ex.items()}},
          {"label": "Alternate diploma or certificate", "color": SERIES[1], "points": {y: v["alt_cert"] for y, v in ex.items()}},
          {"label": "Dropped out", "color": SERIES[3], "points": {y: v["dropout"] for y, v in ex.items()}}]
    c4 = line_chart(s4, ymax=80, xmin=x_first, xmax=x_last, ticks=[0, 20, 40, 60, 80])
    t4 = table("How students with IEPs ages 14 to 21 left school, per 100 who left", "h4-t",
               ["School year", "Regular diploma", "Alternate diploma or certificate", "Reached maximum age", "Dropped out", "Died"],
               [[sy(y), f1(v["regular"]), f1(v["alt_cert"]), f1(v["max_age"]), f1(v["dropout"]), f1(v["died"])] for y, v in sorted(ex.items())])
    sec4 = f"""
<section aria-labelledby="h-leave">
  <h2 id="h-leave">Leaving school</h2>
  <ul class="plain">
    <li>In {sy(x_first)}, about <span class="fig">{ex[x_first]['regular']:.0f}</span> of every 100 students with IEPs who left school left with a regular diploma.</li>
    <li>In {sy(x_last)}, it was about <span class="fig">{ex[x_last]['regular']:.0f}</span> of every 100, or about 3 in 4.</li>
  </ul>
  <figure class="chart wide" aria-hidden="true"><figcaption>Students with IEPs, ages 14 to 21, who left school, per 100 who left, {sy(x_first)} to {sy(x_last)}.</figcaption>{key(s4)}{c4}</figure>
  {explain("leaving")}
  {numbers(t4)}
  <p class="source">Source: Digest of Education Statistics, table 219.90 (editions 2013 to 2023).</p>
</section>"""

    # ---- 5. your state
    names = [s for s in states if s not in ("United States",) and len(s) < 25 and s not in ("Education", "Other jurisdictions")
             and states[s] and any(v.get("pct") for v in states[s].values())]
    stdata = {s: {int(y): v["pct"] for y, v in states[s].items() if v.get("pct")} for s in ["United States"] + names}
    opts = "".join(f'<option value="{E(s)}">{E(s)}</option>' for s in names)
    us = stdata["United States"]
    yrs = sorted({y for d in stdata.values() for y in d})
    rows5 = [[s] + [f1(stdata[s].get(y)) for y in yrs] for s in ["United States"] + names]
    t5 = table("Students served under IDEA, per 100 public school students, by state", "h5-t", ["State"] + [sy(y) for y in yrs], rows5)
    def st_chart(name):
        ser = [{"label": "United States", "color": MUTED, "points": us}]
        if name:
            ser.append({"label": name, "color": ACCENT, "points": stdata[name]})
        return line_chart(ser, ymax=25, xmin=min(yrs), xmax=max(yrs), ticks=[0, 5, 10, 15, 20, 25])

    def st_say(name):
        d = stdata[name]
        a, b = min(d), max(d)
        word = "about the same as" if abs(d[b] - us.get(b, d[b])) < 1 else ("higher than" if d[b] > us.get(b, 0) else "lower than")
        return (f"In {name}, about {d[a]:.1f} of every 100 public school students were served in {sy(a)}, and about {d[b]:.1f} of every 100 in {sy(b)}. "
                f"That is {word} the nation in {sy(b)} ({us.get(b, 0):.1f}).")
    tmpl = "".join(f'<template data-state="{E(n)}" data-say="{E(st_say(n))}">{st_chart(n)}</template>' for n in names)
    sec5 = f"""
<section aria-labelledby="h-state">
  <h2 id="h-state">Your state over time</h2>
  <div class="controls"><div><label for="h-st">Choose a state</label> <select id="h-st"><option value="">United States only</option>{opts}</select></div></div>
  <p id="h-st-say" class="plain-one" aria-live="polite">Nationally, about {us[min(us)]:.1f} of every 100 public school students were served in {sy(min(us))}, and about {us[max(us)]:.1f} in {sy(max(us))}. Choose a state to compare.</p>
  <figure class="chart wide" aria-hidden="true"><figcaption>Students served, per 100 public school students, {sy(min(yrs))} to {sy(max(yrs))}.</figcaption><div id="h-st-chart">{st_chart("")}</div></figure>
  {tmpl}
  {numbers(t5, "Every state, year by year")}
  <p class="source">Source: Digest of Education Statistics, tables 204.70 and 203.20. State shares divide students served by fall public school enrollment.</p>
</section>"""

    tl = "".join(f'<li><span class="tl-y">{E(lab)}</span><span class="tl-t">{E(txt)}</span></li>' for _, lab, txt in MILESTONES)
    body = f"""
<h1>Fifty years of special education</h1>
<p class="lede">How the number of students served, the kinds of disabilities, time in general classes, and graduation have changed since the law was passed in 1975.</p>
<nav aria-label="On this page" class="toc"><ul>
<li><a href="#h-time">A short timeline</a></li><li><a href="#h-many">How many students are served</a></li><li><a href="#h-which">Which disabilities</a></li>
<li><a href="#h-where">Time in general classes</a></li><li><a href="#h-leave">Leaving school</a></li><li><a href="#h-state">Your state over time</a></li></ul></nav>
<div class="page-tools"><button type="button" data-print>Print this page</button><button type="button" data-expand>Show all detail</button></div>
<section aria-labelledby="h-time">
  <h2 id="h-time">A short timeline</h2>
  <ol class="timeline">{tl}</ol>
</section>
{sec1}{sec2}{sec3}{sec4}{sec5}
<section aria-labelledby="h-about">
  <h2 id="h-about">About these figures</h2>
  <p>National and state figures come from the Digest of Education Statistics, which gathers the counts states report each year.
  Rules for counting, category names, and age groups have changed over the decades, and these changes are noted beside each chart.
  For a district's own figures over time, open its page from the <a href="{BASE}">search</a>.</p>
  {explain("years")}
</section>"""
    return page("Fifty years of special education", body,
                desc="How special education in U.S. public schools has changed since 1975: students served, disability categories, time in general classes, graduation, and each state over time.",
                path=BASE + "history/", scripts=("atlas.js",), crumbs=[("IDEA Atlas", BASE)], alt=BASE + "es/historia/")


# ---------------------------------------------------------------- Spanish
MILESTONES_ES = [
    ("1975", "El Congreso aprueba la Ley de Educación para Todos los Niños Impedidos. Por primera vez, todo niño con una discapacidad tiene derecho a una educación pública gratuita y apropiada."),
    ("1986", "Unas enmiendas extienden la ley a los niños de 3 a 5 años y crean la intervención temprana para bebés y niños pequeños."),
    ("1990", "La ley pasa a llamarse Ley de Educación para Personas con Discapacidades (IDEA). El autismo y la lesión cerebral traumática pasan a ser categorías propias, y se agrega la planificación para la vida después de la escuela."),
    ("1997", "Unas enmiendas dan importancia al aprendizaje en el currículo general y a la participación en las pruebas estatales, y permiten a los estados usar el retraso del desarrollo hasta los 9 años."),
    ("2004", "La ley se renueva como Ley de Mejoramiento de la Educación para Personas con Discapacidades, con cambios en la forma de identificar las discapacidades del aprendizaje."),
]
CAT_LABEL_ES = {"learning": "Discapacidad específica del aprendizaje", "speech": "Impedimento del habla o del lenguaje", "otherhealth": "Otro impedimento de salud",
                "autism": "Autismo", "devdelay": "Retraso del desarrollo", "intellectual": "Discapacidad intelectual", "emotional": "Trastorno emocional"}


def render_es(page, explain, BASE: str, state_es: dict) -> str:
    nat = json.loads((HERE / "national.json").read_text())
    states = json.loads((HERE / "states.json").read_text())
    I = lambda d: {int(k): v for k, v in d.items() if v is not None}
    served, pct = I(nat["served_thousands"]), I(nat["pct_enrollment"])
    first, last = min(pct), max(pct)
    c1 = line_chart([{"label": "Estudiantes atendidos", "color": ACCENT, "points": pct}], ymax=20, xmin=1975, xmax=last, ticks=[0, 5, 10, 15, 20],
                    marks=[(1975, "Ley de 1975"), (1990, "IDEA"), (2004, "2004")])
    cats = nat["by_category_thousands"]
    years = sorted(int(y) for y in cats if cats[y].get("all"))
    s2 = []
    for i, (k, lab) in enumerate(CAT_LABEL_ES.items()):
        pts = {y: 100 * cats[str(y)][k] / cats[str(y)]["all"] for y in years if cats[str(y)].get(k) is not None}
        if pts:
            s2.append({"label": lab, "color": SERIES[i], "points": pts})
    c2 = line_chart(s2, ymax=50, xmin=1975, xmax=last, ticks=[0, 10, 20, 30, 40, 50])
    lk = lambda k, y: 100 * cats[str(y)][k] / cats[str(y)]["all"]
    env = I(nat["environments"])
    e_first, e_last = min(env), max(env)
    s3 = [{"label": "80% o más del día", "color": "#0d366b", "points": {y: v["80plus"] for y, v in env.items()}},
          {"label": "40% a 79%", "color": "#3987e5", "points": {y: v["40_79"] for y, v in env.items()}},
          {"label": "Menos del 40%", "color": "#86b6ef", "points": {y: v["lt40"] for y, v in env.items()}},
          {"label": "Escuela o centro separado", "color": "#b9b4a8",
           "points": {y: (v["sep_school"] or 0) + (v["residential"] or 0) + (v["homebound"] or 0) for y, v in env.items()}}]
    c3 = line_chart(s3, ymax=80, xmin=1985, xmax=e_last, ticks=[0, 20, 40, 60, 80], marks=[(2019, "Cambio en el conteo")])
    ex = I(nat["exits"])
    x_first, x_last = min(ex), max(ex)
    s4 = [{"label": "Diploma regular", "color": SERIES[0], "points": {y: v["regular"] for y, v in ex.items()}},
          {"label": "Diploma alternativo o certificado", "color": SERIES[1], "points": {y: v["alt_cert"] for y, v in ex.items()}},
          {"label": "Abandonaron", "color": SERIES[3], "points": {y: v["dropout"] for y, v in ex.items()}}]
    c4 = line_chart(s4, ymax=80, xmin=x_first, xmax=x_last, ticks=[0, 20, 40, 60, 80])
    names = [s for s in states if s != "United States" and len(s) < 25 and s not in ("Education", "Other jurisdictions")
             and states[s] and any(v.get("pct") for v in states[s].values())]
    stdata = {s: {int(y): v["pct"] for y, v in states[s].items() if v.get("pct")} for s in ["United States"] + names}
    us = stdata["United States"]
    yrs = sorted({y for d in stdata.values() for y in d})
    es = lambda n: state_es.get(n, n)

    def st_chart(name):
        ser = [{"label": "Estados Unidos", "color": MUTED, "points": us}]
        if name:
            ser.append({"label": es(name), "color": ACCENT, "points": stdata[name]})
        return line_chart(ser, ymax=25, xmin=min(yrs), xmax=max(yrs), ticks=[0, 5, 10, 15, 20, 25])

    def st_say(name):
        d = stdata[name]
        a, b = min(d), max(d)
        word = "aproximadamente igual que" if abs(d[b] - us.get(b, d[b])) < 1 else ("más alto que" if d[b] > us.get(b, 0) else "más bajo que")
        return (f"En {es(name)}, aproximadamente {d[a]:.1f} de cada 100 estudiantes de escuelas públicas recibían servicios en {sy(a)}, y aproximadamente {d[b]:.1f} de cada 100 en {sy(b)}. "
                f"Eso es {word} el promedio del país en {sy(b)} ({us.get(b, 0):.1f}).")
    opts = "".join(f'<option value="{E(s)}">{E(es(s))}</option>' for s in sorted(names, key=es))
    tmpl = "".join(f'<template data-state="{E(n)}" data-say="{E(st_say(n))}">{st_chart(n)}</template>' for n in names)
    t1 = table("Estudiantes de 3 a 21 años atendidos bajo IDEA", "h1-t", ["Año escolar", "Estudiantes atendidos", "Por cada 100 estudiantes de escuelas públicas"],
               [[sy(y), f"{served[y] * 1000:,.0f}", f1(pct.get(y))] for y in sorted(served)])
    tl = "".join(f'<li><span class="tl-y">{E(a)}</span><span class="tl-t">{E(b)}</span></li>' for a, b in MILESTONES_ES)
    body = f"""
<h1>Cincuenta años de educación especial</h1>
<p class="lede">Cómo han cambiado, desde que se aprobó la ley en 1975, el número de estudiantes atendidos, los tipos de discapacidad, el tiempo en las clases de educación general y la graduación.</p>
<div class="page-tools"><button type="button" data-print>Imprimir esta página</button></div>
<section aria-labelledby="h-time"><h2 id="h-time">Una breve cronología</h2><ol class="timeline">{tl}</ol></section>
<section aria-labelledby="h-many">
  <h2 id="h-many">Cuántos estudiantes reciben servicios</h2>
  <ul class="plain">
    <li>En {sy(first)}, aproximadamente <span class="fig">{pct[first]:.1f}</span> de cada 100 estudiantes de escuelas públicas recibían servicios bajo la ley, o aproximadamente 1 de cada {round(100 / pct[first])}.</li>
    <li>En {sy(last)}, fueron aproximadamente <span class="fig">{pct[last]:.1f}</span> de cada 100, o aproximadamente 1 de cada {round(100 / pct[last])}: <span class="fig">{served[last] / 1000:.1f} millones</span> de estudiantes.</li>
  </ul>
  <figure class="chart wide" aria-hidden="true"><figcaption>Estudiantes atendidos bajo la ley, por cada 100 estudiantes de escuelas públicas, de {sy(first)} a {sy(last)}. Las líneas punteadas unen años que las tablas federales no informan.</figcaption>{c1}</figure>
  {explain("per100", "idea")}
  {numbers(t1, "Las cifras, año por año")}
  <p class="source">Fuente: Departamento de Educación de EE. UU., Digest of Education Statistics, tabla 204.30.</p>
</section>
<section aria-labelledby="h-which">
  <h2 id="h-which">Qué discapacidades</h2>
  <ul class="plain">
    <li>En {sy(first)}, el impedimento del habla o del lenguaje era la categoría más grande: aproximadamente <span class="fig">{lk('speech', first):.0f}</span> de cada 100 estudiantes atendidos.</li>
    <li>La discapacidad específica del aprendizaje ha sido la más grande desde la década de 1980. En {sy(last)}, fue aproximadamente <span class="fig">{lk('learning', last):.0f}</span> de cada 100.</li>
    <li>El autismo, una categoría propia desde 1990, llegó a aproximadamente <span class="fig">{lk('autism', last):.0f}</span> de cada 100 en {sy(last)}.</li>
  </ul>
  <figure class="chart wide" aria-hidden="true"><figcaption>Proporción de estudiantes atendidos en cada una de las siete categorías federales más grandes, por cada 100 estudiantes atendidos.</figcaption>{key(s2)}{c2}</figure>
  {explain("categories")}
</section>
<section aria-labelledby="h-where">
  <h2 id="h-where">Tiempo en las clases de educación general</h2>
  <ul class="plain">
    <li>En {e_first}, aproximadamente <span class="fig">{env[e_first]['80plus']:.0f}</span> de cada 100 estudiantes con IEP en edad escolar pasaban la mayor parte del día (80% o más) en una clase de educación general.</li>
    <li>En {e_last}, fueron aproximadamente <span class="fig">{env[e_last]['80plus']:.0f}</span> de cada 100, o aproximadamente 2 de cada 3.</li>
  </ul>
  <figure class="chart wide" aria-hidden="true"><figcaption>Estudiantes con IEP en edad escolar según el tiempo en una clase de educación general, por cada 100. Las tablas federales no incluyen de 1991 a 1993 (línea punteada). Desde 2019, los niños de 5 años en kínder se cuentan en edad escolar.</figcaption>{key(s3)}{c3}</figure>
  {explain("settings")}
</section>
<section aria-labelledby="h-leave">
  <h2 id="h-leave">Al terminar la escuela</h2>
  <ul class="plain">
    <li>En {sy(x_first)}, aproximadamente <span class="fig">{ex[x_first]['regular']:.0f}</span> de cada 100 estudiantes con IEP que salieron de la escuela lo hicieron con un diploma regular.</li>
    <li>En {sy(x_last)}, fueron aproximadamente <span class="fig">{ex[x_last]['regular']:.0f}</span> de cada 100, o aproximadamente 3 de cada 4.</li>
  </ul>
  <figure class="chart wide" aria-hidden="true"><figcaption>Estudiantes con IEP de 14 a 21 años que salieron de la escuela, por cada 100, de {sy(x_first)} a {sy(x_last)}.</figcaption>{key(s4)}{c4}</figure>
  {explain("leaving")}
</section>
<section aria-labelledby="h-state">
  <h2 id="h-state">Su estado a lo largo del tiempo</h2>
  <div class="controls"><div><label for="h-st">Elija un estado</label> <select id="h-st"><option value="">Solo Estados Unidos</option>{opts}</select></div></div>
  <p id="h-st-say" class="plain-one" aria-live="polite">En todo el país, aproximadamente {us[min(us)]:.1f} de cada 100 estudiantes de escuelas públicas recibían servicios en {sy(min(us))}, y aproximadamente {us[max(us)]:.1f} en {sy(max(us))}. Elija un estado para comparar.</p>
  <figure class="chart wide" aria-hidden="true"><figcaption>Estudiantes atendidos, por cada 100 estudiantes de escuelas públicas, de {sy(min(yrs))} a {sy(max(yrs))}.</figcaption><div id="h-st-chart">{st_chart("")}</div></figure>
  {tmpl}
  <p class="source">Fuente: Digest of Education Statistics, tablas 204.70 y 203.20.</p>
</section>
<section aria-labelledby="h-about">
  <h2 id="h-about">Sobre estas cifras</h2>
  <p>Las cifras nacionales y estatales vienen del Digest of Education Statistics, que reúne los conteos que los estados informan cada año. Las reglas de conteo, los nombres de las categorías
  y los grupos de edad han cambiado con los años, y esos cambios se señalan junto a cada gráfico. Para ver las cifras de un distrito a lo largo del tiempo, búsquelo en la <a href="{BASE}es/">página de búsqueda</a>.
  Las tablas completas están en la <a href="{BASE}history/" hreflang="en">página en inglés</a>.</p>
  {explain("years")}
</section>"""
    return page("Cincuenta años de educación especial", body,
                desc="Cómo ha cambiado la educación especial en las escuelas públicas de EE. UU. desde 1975: estudiantes atendidos, categorías, tiempo en clases generales, graduación y cada estado.",
                path=BASE + "es/historia/", scripts=("atlas.js",), lang="es", alt=BASE + "history/", crumbs=[("IDEA Atlas", BASE + "es/")])
