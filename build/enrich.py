"""Extra, crawlable context for district pages, and county pages.

- County: from the district's office ZIP code (Census ZIP-to-county table bundled in the `zipcodes` package).
- Links: other districts based in the same county, and districts in the same state with a similar
  enrollment and child poverty level, as plain links that search engines can follow.
- Common questions: four or five questions answered from the district's own reported figures,
  with FAQPage structured data. A question is asked only when its figure was fully reported.
- Structured data: Dataset and BreadcrumbList for each district page.
- Byline: who made the page, when it was last rebuilt, and where the figures come from.
- County pages: every county with at least two districts based in it, in English and Spanish.
"""
from __future__ import annotations

import datetime as _dt
import html
import json
import math

E = html.escape
C: dict = {}            # context set by setup()
COUNTY: dict = {}       # leaid -> (state code, county name)
MEMBERS: dict = {}      # (state, county) -> [leaid, ...] sorted by enrollment, largest first
SIMILAR: dict = {}      # leaid -> [leaid, ...]
MIN_COUNTY = 2          # a county page needs at least this many districts

MONTHS_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _nan(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


def _code(r, key) -> str:
    st = r.get(key + "_status") if hasattr(r, "get") else None
    return C["STATUS"].get(str(st), ("5", ""))[0]


def _ok(r, key) -> bool:
    return key in r and _code(r, key) == "0" and not _nan(r[key])


def _n(v) -> str:
    return C["fmt"](v, "per100")


def _kind(t) -> str:
    t = str(t or "").lower()
    return "charter" if "charter" in t else "regular" if "regular" in t else "other"


def setup(d, *, BASE, ATLAS_ORIGIN, SITE, STATE_NAMES, fmt, STATUS, pd, VERSION, DOI, states_mod, es_state):
    """d: the districts table (with 'display'). es_state: maps an English state name to its Spanish name."""
    C.update(BASE=BASE, ORIGIN=ATLAS_ORIGIN, SITE=SITE, SN=STATE_NAMES, fmt=fmt, STATUS=STATUS, pd=pd, VERSION=VERSION, DOI=DOI,
             slug=states_mod.slug, es_state=es_state, today=_dt.date.today())
    C["by"] = d.set_index("leaid")
    try:
        import zipcodes
    except ImportError:          # no county pages or county links without the ZIP table
        zipcodes = None
    COUNTY.clear(); MEMBERS.clear(); SIMILAR.clear()
    if zipcodes is not None:
        for lid, z, st in zip(d.leaid, d.zip.fillna(""), d.state):
            m = zipcodes.matching(str(z)[:5]) if len(str(z)) >= 5 else []
            if m and m[0].get("state") == st and m[0].get("county"):
                COUNTY[lid] = (st, m[0]["county"])
    enr = {lid: (float(e) if s == "ok" and not _nan(e) else 0.0) for lid, e, s in zip(d.leaid, d.enrollment, d.enrollment_status)}
    C["enr"] = enr
    for lid, key in COUNTY.items():
        MEMBERS.setdefault(key, []).append(lid)
    for key in MEMBERS:
        MEMBERS[key].sort(key=lambda x: (-enr[x], C["by"].at[x, "display"]))
    # Similar districts: same state and kind, closest enrollment (log scale) and child poverty.
    import numpy as np
    for st, g in d.groupby("state"):
        g = g[(g.enrollment_status == "ok") & (g.enrollment > 0)]
        if len(g) < 3:
            continue
        le = np.log(g.enrollment.astype(float).values)
        pv = np.where(g.child_poverty_status.values == "ok", g.child_poverty.astype(float).values, np.nan)
        kinds = np.array([_kind(t) for t in g.district_type])
        ids = g.leaid.values
        for i in range(len(g)):
            dp = np.abs(pv - pv[i]) / 15.0
            dp = np.where(np.isnan(dp), 0.5, dp)
            score = np.abs(le - le[i]) + dp + np.where(kinds == kinds[i], 0, 3)
            score[i] = np.inf
            SIMILAR[ids[i]] = [ids[j] for j in np.argsort(score)[:5] if np.isfinite(score[j])]


# ---------- paths and names ----------

def state_name(code: str, lang: str) -> str:
    sn = C["SN"][0]
    return (sn.es if lang == "es" else sn.en).get(code, code)


def county_path(key, lang: str) -> str:
    st, cty = key
    if lang == "es":
        return f"es/condado/{C['slug'](state_name(st, 'es'))}/{C['slug'](cty)}/"
    return f"county/{C['slug'](state_name(st, 'en'))}/{C['slug'](cty)}/"


def has_county_page(key) -> bool:
    return len(MEMBERS.get(key, [])) >= MIN_COUNTY


def district_path(lid: str, lang: str) -> str:
    return f"{C['BASE']}{'es/distrito' if lang == 'es' else 'district'}/{lid}/"


def _city(lid: str) -> str:
    c = C["by"].at[lid, "city"]
    return c.title() if isinstance(c, str) else ""


# ---------- district page parts ----------

def links_html(r, lang: str) -> str:
    """Plain links to nearby and similar districts (inside the 'Districts like this one' section)."""
    by, enr = C["by"], C["enr"]
    stu = "estudiantes" if lang == "es" else "students"

    def li(lid):
        n = enr.get(lid, 0)
        meta = " · ".join(x for x in (_city(lid), f"{n:,.0f} {stu}" if n else "") if x)
        return f'<li><a href="{district_path(lid, lang)}">{E(by.at[lid, "display"])}</a><span class="near-meta">{E(meta)}</span></li>'

    blocks = []
    key = COUNTY.get(r.leaid)
    if key:
        others = [x for x in MEMBERS[key] if x != r.leaid]
        if others:
            cty = key[1]
            head = f"También con sede en {cty}" if lang == "es" else f"Also based in {cty}"
            more = ""
            if has_county_page(key):
                lab = (f"Los {len(MEMBERS[key])} distritos de {cty}" if lang == "es" else f"All {len(MEMBERS[key])} districts in {cty}")
                more = f'<p class="near-more"><a href="{C["BASE"]}{county_path(key, lang)}">{E(lab)}</a></p>'
            blocks.append(f'<div class="near-col"><h3>{E(head)}</h3><ul class="near-list">{"".join(li(x) for x in others[:6])}</ul>{more}</div>')
    sim = SIMILAR.get(r.leaid, [])
    if sim:
        stn = state_name(r.state, lang)
        head = f"De tamaño y pobreza infantil parecidos en {stn}" if lang == "es" else f"Similar in size and child poverty in {stn}"
        blocks.append(f'<div class="near-col"><h3>{E(head)}</h3><ul class="near-list">{"".join(li(x) for x in sim)}</ul></div>')
    return f'<div class="near">{"".join(blocks)}</div>' if blocks else ""


def faq_items(r, name: str, state: str, lang: str, st_med) -> list[tuple[str, str]]:
    """(question, answer) pairs, each built only from fully reported figures."""
    q = []
    med = lambda k: st_med[k].get(r.state, float("nan")) if k in st_med else float("nan")
    es = lang == "es"
    if _ok(r, "id_rate"):
        cnt = f"{r['idea_count']:,.0f}" if _ok(r, "idea_count") else None
        m = med("id_rate")
        if es:
            a = (f"En 2024–25, {name} atendió a {cnt} estudiantes con un IEP, o {_n(r.id_rate)} de cada 100 estudiantes inscritos." if cnt
                 else f"En 2024–25, {name} atendió a {_n(r.id_rate)} estudiantes con un IEP por cada 100 inscritos.")
            if not _nan(m):
                a += f" En el distrito típico de {state}, la cifra es {_n(m)} de cada 100."
            q.append((f"¿Cuántos estudiantes de {name} tienen un IEP?", a))
        else:
            a = (f"In 2024–25, {name} served {cnt} students with an IEP, or {_n(r.id_rate)} of every 100 students enrolled." if cnt
                 else f"In 2024–25, {name} served {_n(r.id_rate)} students with an IEP for every 100 enrolled.")
            if not _nan(m):
                a += f" In the typical {state} district, the figure is {_n(m)} of every 100."
            q.append((f"How many students in {name} have an IEP?", a))
    if _ok(r, "env_80plus"):
        m = med("env_80plus")
        if es:
            a = f"{_n(r.env_80plus)} de cada 100 estudiantes con IEP pasan el 80 % o más del día escolar en una clase de educación general."
            if not _nan(m):
                a += f" En el distrito típico de {state}, son {_n(m)} de cada 100."
            q.append((f"¿Cuánto tiempo pasan en clases generales los estudiantes con IEP de {name}?", a))
        else:
            a = f"{_n(r.env_80plus)} of every 100 students with IEPs spend 80% or more of the school day in a general education class."
            if not _nan(m):
                a += f" In the typical {state} district, it is {_n(m)} of every 100."
            q.append((f"How much of the day do students with IEPs in {name} spend in general classes?", a))
    if _ok(r, "grad_regular"):
        m = med("grad_regular")
        if es:
            a = f"De los estudiantes con IEP que dejaron la escuela en 2023–24, {_n(r.grad_regular)} de cada 100 obtuvieron un diploma regular."
            if not _nan(m):
                a += f" En el distrito típico de {state}, son {_n(m)} de cada 100."
            q.append((f"¿Cuántos estudiantes con IEP de {name} obtienen un diploma regular?", a))
        else:
            a = f"Of students with IEPs who left school in 2023–24, {_n(r.grad_regular)} of every 100 left with a regular high school diploma."
            if not _nan(m):
                a += f" In the typical {state} district, it is {_n(m)} of every 100."
            q.append((f"How many students with IEPs in {name} earn a regular diploma?", a))
    if _ok(r, "oos_idea") and _ok(r, "oos_nodis"):
        a_, b_ = float(r.oos_idea), float(r.oos_nodis)
        if es:
            a = (f"En 2023–24, {_n(a_)} de cada 100 estudiantes con IEP recibieron al menos una suspensión fuera de la escuela, "
                 f"comparado con {_n(b_)} de cada 100 estudiantes sin discapacidades.")
            if b_ > 0 and a_ / b_ >= 1.5:
                a += f" Es decir, unas {a_ / b_:.1f} veces más a menudo."
            q.append((f"¿Se suspende más a los estudiantes con discapacidades en {name}?", a))
        else:
            a = (f"In 2023–24, {_n(a_)} of every 100 students with IEPs received at least one out-of-school suspension, "
                 f"compared with {_n(b_)} of every 100 students without disabilities.")
            if b_ > 0 and a_ / b_ >= 1.5:
                a += f" That is about {a_ / b_:.1f} times as often."
            q.append((f"Are students with disabilities suspended more often in {name}?", a))
    if _ok(r, "spend_per_pupil"):
        f = C["fmt"]
        extra = ""
        if _ok(r, "idea_federal_per_student"):
            extra = (f" Además, recibió {f(r.idea_federal_per_student, 'usd')} de fondos federales de IDEA por cada estudiante con un IEP." if es
                     else f" It also received {f(r.idea_federal_per_student, 'usd')} in federal IDEA money for each student with an IEP.")
        if es:
            q.append((f"¿Cuánto gasta {name} por estudiante?",
                      f"En el año fiscal 2024, {name} gastó {f(r.spend_per_pupil, 'usd')} por estudiante en gastos corrientes.{extra}"))
        else:
            q.append((f"How much does {name} spend per student?",
                      f"In fiscal year 2024, {name} spent {f(r.spend_per_pupil, 'usd')} per student in current spending.{extra}"))
    return q


def faq_html(items, lang: str) -> str:
    if len(items) < 2:
        return ""
    head = "Preguntas frecuentes" if lang == "es" else "Common questions"
    note = ("Respuestas basadas en lo que el distrito informó al gobierno federal." if lang == "es"
            else "Answers come from what the district reported to the federal government.")
    qa = "".join(f'<details class="faq-q"><summary>{E(q)}</summary><p>{E(a)}</p></details>' for q, a in items)
    return (f'<section aria-labelledby="s-faq" class="faq"><h2 id="s-faq">{head}</h2>'
            f'<p class="faq-note">{note}</p>{qa}</section>')


def _ld(obj) -> str:
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + "</script>"


def district_ld(r, name: str, state: str, lang: str, desc: str, faq) -> str:
    o, B = C["ORIGIN"], C["BASE"]
    url = o + district_path(r.leaid, lang)
    home = f"{o}{B}{'es/' if lang == 'es' else ''}"
    st_url = o + B + C["SN"][0].path(r.state, es=(lang == "es"))
    es = lang == "es"
    ds = {"@context": "https://schema.org", "@type": "Dataset",
          "name": (f"Datos de educación especial de {name}, {state}" if es else f"Special education data for {name}, {state}"),
          "description": desc if len(desc) >= 50 else (desc + " " + ("Datos federales en palabras sencillas." if es else "Federal data in plain language.")),
          "url": url, "inLanguage": lang, "isAccessibleForFree": True,
          "license": "https://creativecommons.org/licenses/by/4.0/",
          "dateModified": C["today"].isoformat(), "temporalCoverage": "2023/2025",
          "spatialCoverage": {"@type": "Place", "name": f"{name}, {state}"},
          "identifier": f"NCES LEAID {r.leaid}",
          "isPartOf": {"@type": "Dataset", "name": "IDEA Atlas", "url": f"{o}{B}", "identifier": f"https://doi.org/{C['DOI']}"},
          "creator": {"@type": "Person", "name": "Suman Rath", "url": C["SITE"] + "/", "sameAs": "https://orcid.org/0000-0002-7497-6335",
                      "affiliation": {"@type": "Organization", "name": "Montclair State University"}},
          "variableMeasured": (["Estudiantes con IEP por cada 100 inscritos", "Estudiantes con IEP en clases generales el 80 % o más del día",
                                "Diploma regular", "Suspensión fuera de la escuela", "Gasto por estudiante", "Pobreza infantil"] if es else
                               ["Students with IEPs per 100 enrolled", "Students with IEPs in general classes 80% or more of the day",
                                "Regular diploma", "Out-of-school suspension", "Spending per student", "Child poverty"]),
          "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{o}{B}download/"}]}
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "IDEA Atlas", "item": home},
        {"@type": "ListItem", "position": 2, "name": state, "item": st_url}]}
    key = COUNTY.get(r.leaid)
    if key and has_county_page(key):
        crumbs["itemListElement"].append({"@type": "ListItem", "position": 3, "name": key[1], "item": o + B + county_path(key, lang)})
    crumbs["itemListElement"].append({"@type": "ListItem", "position": len(crumbs["itemListElement"]) + 1, "name": name, "item": url})
    out = _ld(ds) + _ld(crumbs)
    if len(faq) >= 2:
        out += _ld({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]})
    return out


def byline_html(lang: str) -> str:
    t, B, S = C["today"], C["BASE"], C["SITE"]
    if lang == "es":
        when = f"{t.day} de {MONTHS_ES[t.month - 1]} de {t.year}"
        return (f'<p class="byline">Por <a href="{S}/" hreflang="en">el Dr. Suman Rath</a>, Universidad Estatal de Montclair · '
                f'Página actualizada el <time datetime="{t.isoformat()}">{when}</time> · '
                f'Fuentes: <a href="{B}es/acerca-de-los-datos/">Departamento de Educación de EE. UU. y otros datos federales</a></p>')
    when = f"{t:%B} {t.day}, {t.year}"
    return (f'<p class="byline">By <a href="{S}/">Dr. Suman Rath</a>, Montclair State University · '
            f'Page updated <time datetime="{t.isoformat()}">{when}</time> · '
            f'Sources: <a href="{B}methods/#sources">U.S. Department of Education and other federal data</a></p>')


# ---------- share images ----------

OG_LABELS = {
    "en": {"id_rate": "of every 100 students have an IEP", "env_80plus": "of 100 with IEPs in general classes 80%+ of the day",
           "grad_regular": "of 100 with IEPs who left school earned a regular diploma", "oos_idea": "of 100 with IEPs suspended out of school"},
    "es": {"id_rate": "de cada 100 estudiantes tienen un IEP", "env_80plus": "de cada 100 con IEP en clases generales el 80 % o más del día",
           "grad_regular": "de cada 100 con IEP que dejaron la escuela obtuvieron un diploma regular",
           "oos_idea": "de cada 100 con IEP fueron suspendidos fuera de la escuela"},
}


def og_job(r, name: str, state: str, lang: str):
    """The inputs for a district's share image, or None when fewer than two figures were fully reported."""
    figs = [(_n(r[k]), OG_LABELS[lang][k]) for k in ("id_rate", "env_80plus", "grad_regular", "oos_idea") if _ok(r, k)]
    if len(figs) < 2:
        return None
    n = C["enr"].get(r.leaid, 0)
    city = _city(r.leaid)
    stu = f"{n:,.0f} {'estudiantes' if lang == 'es' else 'students'}" if n else ""
    place = " · ".join(x for x in (f"{city}, {state}" if city else state, stu) if x)
    return {"name": name, "place": place, "figures": figs,
            "footer": "Datos de educación especial en palabras sencillas" if lang == "es" else "Special education data in plain words",
            "brand_note": "Datos federales de educación especial" if lang == "es" else "Federal special education data"}


def og_rel(lid: str, lang: str) -> str:
    return f"assets/og/d/{lid}{'-es' if lang == 'es' else ''}.png"


# ---------- county pages ----------

def _cell(r, key) -> str:
    code = _code(r, key)
    if code == "0" and not _nan(r[key]):
        return _n(r[key])
    if code == "1" and not _nan(r[key]):
        return f'<span class="least">≥</span>{_n(r[key])}'
    return '<span class="na" aria-label="not available">—</span>'


def county_page(key, lang: str, *, page) -> str:
    by, B = C["by"], C["BASE"]
    st, cty = key
    es = lang == "es"
    stn = state_name(st, lang)
    ids = MEMBERS[key]
    rows = [by.loc[x] for x in ids]
    both = [x for x in rows if _ok(x, "idea_count") and _ok(x, "enrollment") and x.enrollment > 0]
    kids, enr = sum(float(x.idea_count) for x in both), sum(float(x.enrollment) for x in both)
    n = len(ids)
    if es:
        lede = f"{n} distritos escolares y otras agencias educativas locales tienen su oficina principal en {cty}, {stn}."
        if both and enr:
            lede += (f" {'En conjunto, ' if len(both) == n else f'Los {len(both)} que informaron sus cifras '}"
                     f"atendieron a {kids:,.0f} estudiantes con un IEP en 2024–25, unos {_n(100 * kids / enr)} de cada 100 estudiantes inscritos.")
    else:
        lede = f"{n} school districts and other local education agencies have their main office in {cty}, {stn}."
        if both and enr:
            lede += (f" {'Together they' if len(both) == n else f'The {len(both)} that reported'} served {kids:,.0f} students with an IEP in 2024–25, "
                     f"about {_n(100 * kids / enr)} of every 100 students enrolled.")
    hd = (["Distrito", "Ciudad", "Inscritos", "Con IEP, por cada 100", "Clase general 80%+, por cada 100", "Diploma regular, por cada 100", "Suspensión fuera de la escuela, por cada 100"] if es else
          ["District", "City", "Enrolled", "With IEPs, per 100", "General class 80%+, per 100", "Regular diploma, per 100", "Out-of-school suspension, per 100"])
    trs = []
    for x, lid in zip(rows, ids):
        e = C["enr"].get(lid, 0)
        trs.append(f'<tr><th scope="row"><a href="{district_path(lid, lang)}">{E(x.display)}</a></th><td class="tl">{E(_city(lid))}</td>'
                   f'<td>{f"{e:,.0f}" if e else "—"}</td>' + "".join(f"<td>{_cell(x, k)}</td>" for k in ("id_rate", "env_80plus", "grad_regular", "oos_idea")) + "</tr>")
    cap = (f"Distritos con sede en {cty}: cifras clave. Inscripción e IEP 2024–25; diploma y suspensión 2023–24." if es
           else f"Districts based in {cty}: key figures. Enrollment and IEPs 2024–25; diplomas and suspensions 2023–24.")
    others = sorted(k for k in MEMBERS if k[0] == st and k != key and has_county_page(k))
    other_html = ""
    if others:
        oh = f"Otros condados de {stn}" if es else f"Other counties in {stn}"
        other_html = (f'<section aria-labelledby="s-oc"><h2 id="s-oc">{E(oh)}</h2><ul class="cty-list">'
                      + "".join(f'<li><a href="{B}{county_path(k, lang)}">{E(k[1])}</a></li>' for k in others) + "</ul></section>")
    if es:
        note = ("Estas cifras describen lo que informó cada distrito. No son calificaciones. Los distritos aparecen según dónde está su oficina principal; "
                "un distrito puede atender a estudiantes de más de un condado. ≥ significa «al menos»; — significa que la cifra no está disponible.")
        more = f'<p>Vea <a href="{B}{C["SN"][0].path(st, es=True)}">la página de {E(stn)}</a> para todos los distritos del estado, o <a href="{B}es/acerca-de-los-datos/">cómo se calculan las cifras</a>.</p>'
        h_t = "Distritos y cifras clave"
    else:
        note = ("These figures describe what each district reported. They are not grades. Districts are listed by where their main office is; "
                "a district can serve students in more than one county. ≥ means “at least”; — means the figure is not available.")
        more = f'<p>See <a href="{B}{C["SN"][0].path(st)}">the {E(stn)} page</a> for every district in the state, or <a href="{B}methods/">how the figures are made</a>.</p>'
        h_t = "Districts and key figures"
    body = f"""<main id="main" class="wrap">
<h1>{E(f"Educación especial en {cty}, {stn}" if es else f"Special education in {cty}, {stn}")}</h1>
<p class="lede">{E(lede)}</p>
{byline_html(lang)}
<section aria-labelledby="s-cd">
  <h2 id="s-cd">{h_t}</h2>
  <div class="table-wrap" role="region" tabindex="0" aria-labelledby="cd-cap"><table class="profile districts county-t"><caption id="cd-cap">{E(cap)}</caption>
  <thead><tr>{"".join(f'<th scope="col">{E(h)}</th>' for h in hd)}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>
  <p class="brief-note">{E(note)}</p>
  {more}
</section>
{other_html}
</main>"""
    title = f"{cty}, {stn}"
    desc = (f"Datos de educación especial de los {n} distritos escolares con sede en {cty}, {stn}: estudiantes con IEP, tiempo en clases generales, diplomas y suspensiones, distrito por distrito." if es
            else f"Special education data for the {n} school districts based in {cty}, {stn}: students with IEPs, time in general classes, diplomas and suspensions, district by district.")
    home = f"{B}es/" if es else B
    st_path = B + C["SN"][0].path(st, es=es)
    o = C["ORIGIN"]
    crumbs_ld = _ld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "IDEA Atlas", "item": o + home},
        {"@type": "ListItem", "position": 2, "name": stn, "item": o + st_path},
        {"@type": "ListItem", "position": 3, "name": cty, "item": o + B + county_path(key, lang)}]})
    og = (f"assets/og/{'estado' if es else 'state'}-{C['slug'](stn)}.png")
    return page(title, body, seo_title=(f"Educación especial en {cty}, {stn}: datos por distrito" if es else f"Special Education in {cty}, {stn}: District Data"),
                desc=desc, path=B + county_path(key, lang), lang=lang, alt=B + county_path(key, "en" if es else "es"),
                extra_head=crumbs_ld, og_image=og, crumbs=[("IDEA Atlas", home), (stn, st_path)])


def state_counties_html(st: str, lang: str) -> str:
    keys = sorted(k for k in MEMBERS if k[0] == st and has_county_page(k))
    if len(keys) < 2:
        return ""
    B = C["BASE"]
    if lang == "es":
        h, p = "Distritos por condado", "Cada página de condado reúne los distritos con sede allí y sus cifras clave."
    else:
        h, p = "Districts by county", "Each county page brings together the districts based there, with their key figures."
    items = "".join(f'<li><a href="{B}{county_path(k, lang)}">{E(k[1])}</a> <span class="near-meta">{len(MEMBERS[k])}</span></li>' for k in keys)
    return f'\n<section aria-labelledby="s-cty"><h2 id="s-cty">{h}</h2><p>{p}</p><ul class="cty-list">{items}</ul></section>'


def county_keys() -> list:
    return sorted(k for k in MEMBERS if has_county_page(k))
