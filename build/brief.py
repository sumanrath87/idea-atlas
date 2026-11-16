"""A short, plain-language reading of a district's data, placed at the top of each district page.

It compares four headline figures with the typical (median) district in the same state, using the same
rule as the rest of the page: within 10% (or half a point) of the state median reads as "about the same".
It never grades: higher and lower are stated without praise or blame. Figures that were withheld,
flagged or not reported are left out rather than estimated.
"""
from __future__ import annotations

import html

E = html.escape

# key, year label, (English label, unit, why it matters), (Spanish label, unit, why it matters)
ITEMS = [
    ("id_rate", "2024–25",
     ("Students with IEPs", "per 100 students enrolled",
      "How many students the district serves under IDEA, the federal special education law."),
     ("Estudiantes con IEP", "de cada 100 estudiantes inscritos",
      "Cuántos estudiantes atiende el distrito bajo IDEA, la ley federal de educación especial.")),
    ("env_80plus", "",
     ("In general classes 80%+ of the day", "per 100 students with IEPs",
      "IDEA expects students with disabilities to learn alongside classmates without disabilities as much as is appropriate."),
     ("En clases generales el 80 % o más del día", "de cada 100 estudiantes con IEP",
      "IDEA espera que los estudiantes con discapacidades aprendan junto a sus compañeros sin discapacidades tanto como sea apropiado.")),
    ("grad_regular", "2023–24",
     ("Regular diploma", "per 100 students with IEPs who left school",
      "A regular diploma keeps the widest set of options open after high school."),
     ("Diploma regular", "de cada 100 estudiantes con IEP que dejaron la escuela",
      "Un diploma regular mantiene abiertas más opciones después de la escuela secundaria.")),
    ("oos_idea", "2023–24",
     ("Out-of-school suspension", "per 100 students with IEPs",
      "Each suspension is time away from class. Federal civil rights data count it for students with and without disabilities."),
     ("Suspensión fuera de la escuela", "de cada 100 estudiantes con IEP",
      "Cada suspensión es tiempo fuera de clase. Los datos federales de derechos civiles la cuentan para estudiantes con y sin discapacidades.")),
]

WORDS = {
    "en": {"same": "About the same", "higher": "Higher", "lower": "Lower",
           "cmp": "as the typical district in {st} ({v})", "cmp_hl": "than the typical district in {st} ({v})",
           "least": "at least"},
    "es": {"same": "Similar", "higher": "Más alto", "lower": "Más bajo",
           "cmp": "al distrito típico de {st} ({v})", "cmp_hl": "que el distrito típico de {st} ({v})",
           "least": "al menos"},
}
ARROW = {"same": "≈", "higher": "↑", "lower": "↓"}
TRENDS: dict = {}   # set by site.py: {leaid: {"i": {fall year: students with IEPs per 100 enrolled}}}


def trend_sentence(r, fmt, pd, lang: str) -> str:
    """How the share of students with IEPs changed over about ten years, from the same series as the page's chart."""
    if str(r.get("id_rate_status")) != "ok" or pd.isna(r.id_rate):
        return ""
    pts = {int(y): v for y, v in ((TRENDS.get(r.leaid) or {}).get("i") or {}).items() if v is not None}
    base = 2014 if 2014 in pts else min((y for y in pts if 2010 <= y <= 2016), default=None)
    if base is None:
        return ""
    a, b = float(pts[base]), float(r.id_rate)
    c = _compare(b, a)
    A, B = _num(fmt(a, "per100")), _num(fmt(b, "per100"))
    if lang == "es":
        if c == "same":
            return f"La proporción de estudiantes con IEP se ha mantenido parecida: {A} de cada 100 en el otoño de {base} y {B} en 2024–25."
        return f"La proporción de estudiantes con IEP {'subió' if c == 'higher' else 'bajó'} de {A} de cada 100 en el otoño de {base} a {B} en 2024–25."
    if c == "same":
        return f"The share of students with IEPs has stayed about the same: {A} of every 100 in fall {base} and {B} in 2024–25."
    return f"The share of students with IEPs {'rose' if c == 'higher' else 'fell'} from {A} of every 100 in fall {base} to {B} in 2024–25."


def _num(s: str) -> str:
    return s


def _compare(v, sm):
    tol = max(0.1 * abs(sm), 0.5)
    if abs(v - sm) <= tol:
        return "same"
    return "higher" if v > sm else "lower"


def brief_html(r, name: str, state: str, st_med, lang: str, fmt, STATUS, pd) -> str:
    w = WORDS[lang]
    cards, cmp = [], {}
    for key, year, en, es in ITEMS:
        label, unit, why = en if lang == "en" else es
        if key not in r or (key + "_status") not in r:
            continue
        v, code = r[key], STATUS.get(str(r[key + "_status"]), ("5", ""))[0]
        if code not in ("0", "1") or pd.isna(v):
            continue
        shown = _num(fmt(v, "per100"))
        line = ""
        sm = st_med[key].get(r.state, float("nan")) if key in st_med else float("nan")
        if code == "0" and pd.notna(sm):
            c = _compare(v, sm)
            cmp[key] = (c, v, sm)
            tail = (w["cmp"] if c == "same" else w["cmp_hl"]).format(st=E(state), v=_num(fmt(sm, "per100")))
            line = (f'<p class="brief-cmp"><span class="brief-pill brief-{c}"><span aria-hidden="true">{ARROW[c]}</span> '
                    f'{w[c]}</span> {tail}</p>')
        num = (f'<span class="brief-least">{w["least"]}</span> ' if code == "1" else "") + f'<span class="num">{shown}</span>'
        yr = f' <span class="brief-yr">{year}</span>' if year else ""
        cards.append(f'<div class="brief-item"><p class="brief-k">{E(label)}{yr}</p>'
                     f'<p class="brief-v">{num}<span class="unit">{E(unit)}</span></p>{line}'
                     f'<p class="brief-why">{E(why)}</p></div>')
    if len(cards) < 2:
        return ""

    # Two or three plain sentences built from the comparisons above.
    s = []
    if lang == "en":
        if "id_rate" in cmp:
            c = cmp["id_rate"][0]
            s.append(f"{E(name)} serves students with IEPs at "
                     + {"same": "about the same rate as", "higher": "a higher rate than", "lower": "a lower rate than"}[c]
                     + f" the typical district in {E(state)}.")
        t_ = trend_sentence(r, fmt, pd, "en")
        if t_:
            s.append(E(t_))
        if "env_80plus" in cmp:
            c, v, sm = cmp["env_80plus"]
            s.append({"same": "About as many", "higher": "More", "lower": "Fewer"}[c]
                     + f" of its students with IEPs spend 80% or more of the day in general classes ({_num(fmt(v, 'per100'))} of every 100, "
                     + f"against {_num(fmt(sm, 'per100'))} in the typical {E(state)} district).")
        if "grad_regular" in cmp and len(s) < 3:
            c, v, sm = cmp["grad_regular"]
            s.append(f"{_num(fmt(v, 'per100'))} of every 100 students with IEPs who left school earned a regular diploma, "
                     + {"same": "close to", "higher": "above", "lower": "below"}[c] + f" the typical {E(state)} district.")
        a, b = r.get("oos_idea"), r.get("oos_nodis")
        if ("oos_idea" in cmp and str(r.get("oos_nodis_status")) == "ok" and pd.notna(a) and pd.notna(b) and b > 0):
            ratio = a / b
            if ratio >= 1.5:
                s.append(f"Students with IEPs were suspended out of school about {ratio:.1f} times as often as students without disabilities.")
            elif ratio <= 1.2:
                s.append("Students with IEPs were suspended out of school at about the same rate as students without disabilities, or less often.")
        note = ("These figures describe what was reported to the U.S. Department of Education. They are not grades: "
                "differences can reflect who a district serves, how it identifies students and how it reports.")
        head = f"What the data show for {E(name)}"
    else:
        if "id_rate" in cmp:
            c = cmp["id_rate"][0]
            s.append(f"{E(name)} atiende a estudiantes con IEP en una proporción "
                     + {"same": "similar a la", "higher": "más alta que la", "lower": "más baja que la"}[c]
                     + f" del distrito típico de {E(state)}.")
        t_ = trend_sentence(r, fmt, pd, "es")
        if t_:
            s.append(E(t_))
        if "env_80plus" in cmp:
            c, v, sm = cmp["env_80plus"]
            s.append({"same": "Una proporción similar", "higher": "Una proporción mayor", "lower": "Una proporción menor"}[c]
                     + f" de sus estudiantes con IEP pasa el 80 % o más del día en clases generales ({_num(fmt(v, 'per100'))} de cada 100, "
                     + f"frente a {_num(fmt(sm, 'per100'))} en el distrito típico de {E(state)}).")
        if "grad_regular" in cmp and len(s) < 3:
            c, v, sm = cmp["grad_regular"]
            s.append(f"{_num(fmt(v, 'per100'))} de cada 100 estudiantes con IEP que dejaron la escuela obtuvieron un diploma regular, "
                     + {"same": "cerca del", "higher": "por encima del", "lower": "por debajo del"}[c] + f" distrito típico de {E(state)}.")
        a, b = r.get("oos_idea"), r.get("oos_nodis")
        if ("oos_idea" in cmp and str(r.get("oos_nodis_status")) == "ok" and pd.notna(a) and pd.notna(b) and b > 0):
            ratio = a / b
            if ratio >= 1.5:
                s.append("Los estudiantes con IEP fueron suspendidos fuera de la escuela con una frecuencia unas "
                         + f"{ratio:.1f}" + " veces mayor que la de los estudiantes sin discapacidades.")
            elif ratio <= 1.2:
                s.append("Los estudiantes con IEP fueron suspendidos fuera de la escuela en una proporción similar o menor que los estudiantes sin discapacidades.")
        note = ("Estas cifras describen lo que se informó al Departamento de Educación de EE. UU. No son calificaciones: "
                "las diferencias pueden reflejar a quién atiende un distrito, cómo identifica a los estudiantes y cómo informa.")
        head = f"Qué muestran los datos de {E(name)}"
    import re
    lede_txt = re.sub(r"\b(\d+(?:[.,]\d)?)( of every| de cada| times| veces| in 2024| en 2024)", r'<span class="fig">\1</span>\2', " ".join(s[:4]))
    lede = f'<p class="brief-lede">{lede_txt}</p>' if s else ""
    return (f'<section aria-labelledby="b-h" class="brief"><h2 id="b-h">{head}</h2>{lede}'
            f'<div class="brief-grid">{"".join(cards)}</div><p class="brief-note">{note}</p></section>')
