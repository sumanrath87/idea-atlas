"""Spanish family edition of IDEA Atlas (Phase 2).

Families first: every district page keeps the plain-language layer, the charts, the explanations, the over-time
lines, and the questions to ask, in Spanish. The full research tables stay on the English page, one link away.
Written in plain, respectful Spanish (usted) for families in the United States; reviewed wording should be
checked by a native-speaking educator before launch.
"""
from __future__ import annotations

import html
import json
import re

E = html.escape

TERMS_ES = {
    "idea": ("¿Qué es IDEA?",
             "La Ley de Educación para Personas con Discapacidades (IDEA, por sus siglas en inglés) es la ley federal que garantiza una educación pública gratuita y apropiada "
             "a los niños con discapacidades, desde los 3 hasta los 21 años. Cada año, los estados y los distritos informan datos sobre ella."),
    "iep": ("¿Qué es un IEP?",
            "Un Programa de Educación Individualizado (IEP, por sus siglas en inglés) es un plan escrito para un estudiante que califica para recibir educación especial bajo IDEA. "
            "La familia y el equipo escolar lo preparan juntos. Incluye las metas del estudiante y los servicios y apoyos que la escuela dará."),
    "504": ("¿Qué es un plan de la Sección 504?",
            "La Sección 504 de la Ley de Rehabilitación protege a los estudiantes con discapacidades contra la discriminación. Un plan 504 indica los apoyos, "
            "como tiempo adicional o un asiento accesible, que un estudiante necesita para participar plenamente en la escuela. Aquí no se cuentan los estudiantes con IEP."),
    "per100": ("¿Por qué «de cada 100»?",
               "Mostrar las cifras por cada 100 estudiantes permite leer igual un distrito pequeño y uno grande. "
               "Por ejemplo, 15 de cada 100 quiere decir que unos 15 de cada 100 estudiantes de ese grupo."),
    "median": ("¿Qué es la mediana?",
               "La mediana es el distrito del medio: la mitad de los distritos tiene una cifra más alta y la otra mitad una más baja. "
               "Sirve como punto de referencia. No es una meta ni una calificación."),
    "typical": ("¿Qué quiere decir «distrito típico»?",
                "En este sitio, el distrito típico es la mediana: el distrito que queda en el medio cuando todos los distritos del estado, o del país, se ordenan de la cifra más baja a la más alta."),
    "middle": ("¿Qué es la mitad central?",
               "Si se ordenan todos los distritos del estado de menor a mayor y se dejan de lado la cuarta parte más baja y la cuarta parte más alta, lo que queda es la mitad central. "
               "Una cifra fuera de ese rango es menos común en el estado, pero no necesariamente mejor ni peor."),
    "categories": ("¿Qué son las categorías federales?",
                   "IDEA nombra 13 categorías de discapacidad, además del retraso del desarrollo para niños pequeños. Cada estudiante se cuenta en una sola categoría. "
                   "Los nombres son los términos federales de los informes, no descripciones de un niño en particular."),
    "settings": ("¿Qué significan los lugares de aprendizaje?",
                 "IDEA pregunta qué parte del día escolar pasa cada estudiante con IEP en una clase de educación general junto a compañeros sin discapacidades. "
                 "Los lugares separados son escuelas separadas, centros residenciales, y la enseñanza en el hogar o en un hospital."),
    "leaving": ("¿Cómo se cuenta «al terminar la escuela»?",
                "Cada año, los distritos informan cómo salieron de la escuela los estudiantes con IEP de 14 a 21 años: con un diploma regular, con otro certificado, "
                "al llegar a la edad máxima para recibir servicios, o al abandonar la escuela. Las cifras son por cada 100 estudiantes que salieron ese año."),
    "discipline": ("¿Qué significan estas palabras sobre disciplina?",
                   "Suspensión fuera de la escuela quiere decir que el estudiante fue retirado de la escuela por al menos medio día. La restricción física es sujetar a un estudiante para que no se mueva libremente; "
                   "la restricción mecánica usa un aparato para hacerlo. El aislamiento es dejar a un estudiante solo en un cuarto del que no puede salir. "
                   "Remitir a la policía quiere decir que la escuela informó del estudiante a las autoridades; un arresto relacionado con la escuela ocurrió en la escuela o en una actividad escolar. "
                   "Las cifras cuentan estudiantes, no incidentes."),
    "spending": ("¿Qué incluye el gasto por estudiante?",
                 "El gasto corriente es el costo diario de operar las escuelas, como personal, servicios y materiales. No incluye construcciones ni deudas. "
                 "Cubre a todos los estudiantes, no solo a los que tienen IEP."),
    "idea_money": ("¿Qué son los fondos federales de IDEA?",
                   "Cada año, el Congreso envía fondos de IDEA a los estados, y los estados pasan la mayor parte a los distritos. Esta cifra es ese dinero federal dividido entre el número de estudiantes con IEP. "
                   "Los estados y los distritos pagan la mayor parte de los costos de educación especial con sus propios fondos."),
    "poverty": ("¿Cómo se calcula la pobreza infantil?",
                "La Oficina del Censo calcula cuántos niños de 5 a 17 años viven en familias por debajo del nivel federal de pobreza en la zona de cada distrito. "
                "Cuenta a los niños que viven allí, vayan o no a las escuelas del distrito."),
    "status": ("¿Por qué faltan algunas cifras?",
               "Las agencias retienen números pequeños para proteger la privacidad de los estudiantes, y no se muestra una cifra cuando el grupo tiene menos de 10 estudiantes. "
               "«Al menos» quiere decir que parte de la cifra fue retenida, así que el número real es igual o mayor. Las cifras que faltan nunca se estiman."),
    "rating": ("¿Qué son las calificaciones estatales de IDEA?",
               "Cada año, el Departamento de Educación de EE. UU. revisa a cada estado y le da una de cuatro calificaciones: cumple los requisitos, necesita ayuda, "
               "necesita intervención o necesita intervención sustancial. La calificación es sobre el estado, no sobre un distrito en particular."),
    "years": ("¿Por qué los años escolares son distintos?",
              "Cada fuente federal se publica en su propio calendario, por eso el año más reciente no es igual para todas. Cada cifra indica su propio año."),
}

PLAIN_ES = {
    "id_rate": "Aproximadamente {v} de cada 100 estudiantes inscritos tienen un IEP con servicios del distrito.",
    "pct_504": "Aproximadamente {v} de cada 100 estudiantes inscritos tienen un plan de la Sección 504.",
    "env_80plus": "Aproximadamente {v} de cada 100 estudiantes con IEP pasan la mayor parte del día (80% o más) en una clase de educación general.",
    "env_lt40": "Aproximadamente {v} de cada 100 estudiantes con IEP pasan menos del 40% del día en una clase de educación general.",
    "env_separate": "Aproximadamente {v} de cada 100 estudiantes con IEP aprenden en una escuela separada, un centro residencial, en el hogar o en un hospital.",
    "grad_regular": "De cada 100 estudiantes con IEP que salieron de la escuela, aproximadamente {v} salieron con un diploma regular de escuela secundaria.",
    "dropout": "De cada 100 estudiantes con IEP que salieron de la escuela, aproximadamente {v} abandonaron los estudios.",
    "oos_idea": "Aproximadamente {v} de cada 100 estudiantes con IEP recibieron una suspensión fuera de la escuela.",
    "oos_nodis": "Para los estudiantes sin discapacidades, la cifra fue de aproximadamente {v} de cada 100.",
    "oos_504": "Para los estudiantes con planes de la Sección 504, fue de aproximadamente {v} de cada 100.",
    "expulsion_idea": "Aproximadamente {v} de cada 100 estudiantes con IEP fueron expulsados.",
    "restraint_physical_idea": "Aproximadamente {v} de cada 100 estudiantes con IEP recibieron restricción física.",
    "restraint_mechanical_idea": "Aproximadamente {v} de cada 100 estudiantes con IEP recibieron restricción mecánica.",
    "seclusion_idea": "Aproximadamente {v} de cada 100 estudiantes con IEP fueron puestos en aislamiento.",
    "referral_idea": "Aproximadamente {v} de cada 100 estudiantes con IEP fueron remitidos a la policía.",
    "arrest_idea": "Aproximadamente {v} de cada 100 estudiantes con IEP fueron arrestados en relación con la escuela.",
    "spend_per_pupil": "El distrito gastó aproximadamente {v} por estudiante en costos diarios.",
    "idea_federal_per_student": "Recibió aproximadamente {v} en fondos federales de IDEA por cada estudiante con IEP.",
    "child_poverty": "Aproximadamente {v} de cada 100 niños de 5 a 17 años en la zona del distrito viven en la pobreza.",
}
SHORT_ES = {
    "id_rate": "Estudiantes con IEP", "pct_504": "Planes 504", "env_80plus": "Clase general 80%+", "env_lt40": "Clase general menos del 40%",
    "env_separate": "Lugares separados", "grad_regular": "Diploma regular", "dropout": "Abandonaron", "oos_idea": "Suspensión, IEP",
    "oos_nodis": "Suspensión, sin discapacidad", "oos_504": "Suspensión, 504", "expulsion_idea": "Expulsión, IEP", "restraint_physical_idea": "Restricción física",
    "restraint_mechanical_idea": "Restricción mecánica", "seclusion_idea": "Aislamiento", "referral_idea": "Remisión a la policía", "arrest_idea": "Arresto escolar",
    "spend_per_pupil": "Gasto por estudiante", "idea_federal_per_student": "Fondos IDEA por estudiante", "child_poverty": "Pobreza infantil",
}
ZERO_VERB_ES = {"expulsion_idea": "expulsado", "restraint_physical_idea": "sujetado físicamente", "restraint_mechanical_idea": "sujetado con medios mecánicos",
                "seclusion_idea": "puesto en aislamiento", "referral_idea": "remitido a la policía", "arrest_idea": "arrestado en la escuela"}
ZERO_TEXT_ES = {"oos_nodis": "Ningún estudiante sin discapacidades recibió una suspensión fuera de la escuela.",
                "oos_504": "Ningún estudiante con plan de la Sección 504 recibió una suspensión fuera de la escuela.",
                "oos_idea": "Ningún estudiante con IEP recibió una suspensión fuera de la escuela."}
CAT_ES = {"Specific learning disability": "Discapacidad específica del aprendizaje", "Speech or language impairment": "Impedimento del habla o del lenguaje",
          "Other health impairment": "Otro impedimento de salud", "Autism": "Autismo", "Intellectual disability": "Discapacidad intelectual",
          "Emotional disturbance": "Trastorno emocional", "Developmental delay": "Retraso del desarrollo"}
STATUS_ES = {"at least": "al menos", "Withheld for privacy": "retenido por privacidad", "Fewer than 10 students": "menos de 10 estudiantes",
             "Flagged for data quality": "marcado por la calidad de los datos", "Not reported": "no se informó", "No students in this group": "no hay estudiantes en este grupo"}
TYPE_ES = {"Regular public school district that is not a component of a supervisory union": "Distrito escolar público",
           "Regular public school district that is a component of a supervisory union": "Distrito escolar público (parte de una unión supervisora)",
           "Independent charter district": "Distrito de escuelas chárter", "Service agency": "Agencia regional de servicios",
           "Specialized public school district": "Distrito escolar público especializado", "Other local education agency": "Otra agencia educativa local",
           "State operated agency": "Agencia escolar del estado", "Federal operated agency": "Agencia escolar federal",
           "Combined record of 32 districts": "Registro combinado de 32 distritos"}
DET_ES = {"Meets requirements": "Cumple los requisitos", "Needs assistance": "Necesita ayuda", "Needs intervention": "Necesita intervención",
          "Needs substantial intervention": "Necesita intervención sustancial", "Not available": "No disponible"}
STATE_ES = {"New Jersey": "Nueva Jersey", "New York": "Nueva York", "New Mexico": "Nuevo México", "New Hampshire": "Nuevo Hampshire",
            "North Carolina": "Carolina del Norte", "South Carolina": "Carolina del Sur", "North Dakota": "Dakota del Norte", "South Dakota": "Dakota del Sur",
            "Pennsylvania": "Pensilvania", "Louisiana": "Luisiana", "Missouri": "Misuri", "Mississippi": "Misisipi", "West Virginia": "Virginia Occidental",
            "Hawaii": "Hawái", "District Of Columbia": "Distrito de Columbia", "District of Columbia": "Distrito de Columbia", "Michigan": "Míchigan",
            "Oregon": "Oregón", "Tennessee": "Tennessee", "Kansas": "Kansas", "Puerto Rico": "Puerto Rico", "United States": "Estados Unidos"}
STATE_NOTES_ES = {
    "CO": "En Colorado, las cifras de IDEA se informan por unidades administrativas, no por cada distrito. Muchas unidades administrativas atienden a varios distritos "
          "(por ejemplo, un BOCES). Busque la unidad administrativa que atiende esta zona para ver sus cifras de IDEA.",
    "WY": "El Departamento de Educación de EE. UU. marcó por la calidad de los datos los conteos de estudiantes con IEP de 2024–25 en los distritos de Wyoming, por eso no se muestran. "
          "Las demás cifras de Wyoming se muestran cuando están disponibles.",
}


def st_es(name: str) -> str:
    import states
    n = states.display(name) if isinstance(name, str) else ""
    return STATE_ES.get(n, states.ES_EXTRA.get(n, n))


GUIDES_P = [""]   # set by site.py once guides are published
STATE_PATHS: dict = {}   # set by site.py: state code -> Spanish state page


def grado(code):
    """Códigos de grado de NCES en palabras; N (no aplica) y M (falta) se omiten."""
    if not isinstance(code, str) or code in ("N", "M", ""):
        return None
    return {"PK": "Prekínder", "KG": "Kínder", "UG": "Sin grado", "AE": "Educación de adultos"}.get(code, code.lstrip("0") or code)


def explain_es(BASE: str, *keys: str, full: bool = False) -> str:
    if full:
        items = "".join(f'<details class="explain"><summary>{E(TERMS_ES[k][0])}</summary><p>{E(TERMS_ES[k][1])}</p></details>' for k in keys)
    else:
        return (f'<div class="explainers" data-terms="{" ".join(keys)}">'
                f'<p class="terms-fallback"><a href="{BASE}es/#words-h">Qué significan estas palabras</a></p></div>')
    return f'<div class="explainers">{items}</div>'


def everyday_es(v) -> str:
    if v is None or v != v or v <= 0:
        return ""
    if v < 1:
        return "menos de 1 de cada 100"
    if v >= 95:
        return "casi todos"
    if 45 <= v <= 55:
        return "aproximadamente la mitad"
    if v <= 34:
        return f"aproximadamente 1 de cada {round(100 / v)}"
    best = min(((k, d) for d in (3, 4, 5, 10) for k in range(1, d)), key=lambda kd: (abs(kd[0] / kd[1] - v / 100), kd[1]))
    return f"aproximadamente {best[0]} de cada {best[1]}"


def figs_es(text: str) -> str:
    h = E(text)
    h = re.sub(r"(?<!\()(\$[\d,]+|\b\d[\d,]*\.\d\b)", r'<span class="fig">\1</span>', h)
    h = re.sub(r", o ((?:aproximadamente|casi|menos de) [^.]*)\.", r', o <span class="ev">\1</span>.', h)
    return re.sub(r"\((\$?[\d,]+(?:\.\d)?)\)", r'<span class="med">(\1)</span>', h)


def plain_es(r, keys, st_med, fmt, STATUS, pd) -> str:
    unit = {"spend_per_pupil": "usd", "idea_federal_per_student": "usd"}
    state = st_es(r.state_name)
    out, zeros = [], []
    for k in keys:
        u = unit.get(k, "per100")
        v, st = r[k], str(r[k + "_status"])
        code, text = STATUS.get(st, ("5", "Not reported"))
        if code in ("0", "1") and pd.notna(v):
            if code == "0" and v == 0 and k in ZERO_VERB_ES:
                zeros.append(ZERO_VERB_ES[k])
                continue
            fv = fmt(v, u)
            sent = ZERO_TEXT_ES[k] if (code == "0" and v == 0 and k in ZERO_TEXT_ES) else PLAIN_ES[k].format(v=fv)
            if code == "1":
                sent = sent.replace("Aproximadamente " + fv, "Al menos " + fv).replace("aproximadamente " + fv, "al menos " + fv)
            if u == "per100" and not (code == "0" and v == 0):
                w = everyday_es(v)
                if w and sent.endswith("."):
                    sent = sent[:-1] + f", o {w}."
            sm = st_med[k].get(r.state, float("nan"))
            if code == "0" and pd.notna(sm):
                if sm == 0:
                    sent += f" En el distrito típico de {state}, fue 0." if v else f" Lo mismo ocurre en el distrito típico de {state}."
                else:
                    tol = max(0.1 * abs(sm), 0.5 if u == "per100" else 50)
                    word = "aproximadamente igual que" if abs(v - sm) <= tol else ("más alto que" if v > sm else "más bajo que")
                    sent += f" Eso es {word} en el distrito típico de {state} ({fmt(sm, u)})."
            out.append(sent)
        else:
            out.append(f"{SHORT_ES[k]}: {STATUS_ES.get(text, 'no se informó')}.")
    if zeros:
        lst = zeros[0] if len(zeros) == 1 else ", ".join(zeros[:-1]) + " o " + zeros[-1]
        out.append(f"Ningún estudiante con IEP fue {lst}.")
    return '<ul class="plain">' + "".join(f"<li>{figs_es(x)}</li>" for x in out) + "</ul>"


def chart_es(kind: str, caption: str, keys: str = "") -> str:
    k = f' data-keys="{keys}"' if keys else ""
    if kind == "trend":
        return f'<figure class="chart explorable" data-chart="{kind}"{k}><figcaption>{E(caption)}</figcaption><div class="chart-body"></div></figure>'
    return f'<figure class="chart" data-chart="{kind}"{k} aria-hidden="true"><figcaption>{E(caption)}</figcaption><div class="chart-body"></div></figure>'


ASK_ES = [
    "¿Cómo decide el distrito si un niño necesita educación especial, y cuánto tiempo toma una evaluación?",
    "¿Qué apoyos ayudan a los estudiantes con IEP a aprender junto a sus compañeros en las clases de educación general?",
    "¿Cómo participan las familias cuando se escribe y se revisa un IEP?",
    "¿Qué puede hacer una familia si no está de acuerdo con una decisión?",
    "¿Cómo ayuda el distrito a los estudiantes con IEP a planear su vida después de la escuela secundaria?",
    "¿Dónde puedo leer los informes de educación especial del propio distrito?",
    "¿Puedo recibir los documentos del IEP y un intérprete en español?",
]


def district_es(r, cd: dict, st_med, *, BASE, page, fmt, STATUS, pd, VERSION, ATLAS_ORIGIN, nice_kids: str = "", parent_note: str = "") -> str:
    name = r.display
    state = st_es(r.state_name)
    facts = []
    import abbrev
    fullname = abbrev.full_name(name, r.state)
    if fullname:
        facts.append(("Nombre completo", fullname))
    if isinstance(r.city, str) and r.city:
        facts.append(("Ubicación", f"{r.city.title()}, {state}"))
    if isinstance(r.district_type, str):
        facts.append(("Tipo", TYPE_ES.get(r.district_type, r.district_type)))
    gl, gh = grado(r.grade_low), grado(r.grade_high)
    if gl and gh:
        facts.append(("Grados", gl if gl == gh else f"{gl} a {gh}"))
    if pd.notna(r.enrollment):
        facts.append(("Estudiantes, 2024–25", f"{r.enrollment:,.0f}"))
    glance = []
    if str(r.id_rate_status) == "ok":
        glance.append(f"En 2024–25, {fmt(r.id_rate, 'per100')} de cada 100 estudiantes inscritos tenían un IEP con servicios del distrito, o {everyday_es(r.id_rate)}.")
    if str(r.env_80plus_status) == "ok":
        glance.append(f"{fmt(r.env_80plus, 'per100')} de cada 100 estudiantes con IEP pasaron al menos el 80% del día en una clase de educación general, o {everyday_es(r.env_80plus)}.")
    if str(r.grad_regular_status) == "ok":
        glance.append(f"De los estudiantes con IEP que salieron de la escuela en 2023–24, {fmt(r.grad_regular, 'per100')} de cada 100 salieron con un diploma regular, o {everyday_es(r.grad_regular)}.")
    if str(r.oos_idea_status) == "ok" and str(r.oos_nodis_status) == "ok":
        glance.append(f"En 2023–24, {fmt(r.oos_idea, 'per100')} de cada 100 estudiantes con IEP recibieron una suspensión fuera de la escuela, "
                      f"comparado con {fmt(r.oos_nodis, 'per100')} de cada 100 estudiantes sin discapacidades.")
    glance = [g.replace(", o .", ".") for g in glance]
    g_html = ('<section aria-labelledby="g-h" class="glance"><h2 id="g-h">De un vistazo</h2><ul>' + "".join(f"<li>{figs_es(x)}</li>" for x in glance)
              + "</ul>" + explain_es(BASE, "iep", "per100") + "</section>") if glance else ""
    rng = lambda ks: chart_es("range", f"Dónde se ubica este distrito entre los distritos de {state}", ",".join(ks))

    def ot(code, label, what, yfmt):
        pts = (cd.get("tr") or {}).get(code)
        if not pts or len(pts) < 3:
            return ""
        a, b = pts[0], pts[-1]
        f = (lambda v: f"${v:,.0f}") if code == "s" else (lambda v: f"{v:,.1f}")
        say = what.format(a=yfmt(a[0]), b=yfmt(b[0]), va=f(a[1]), vb=f(b[1]))
        return (f'<h3 class="ot-h">A lo largo del tiempo</h3><ul class="plain"><li>{figs_es(say)}</li></ul>'
                + chart_es("trend", f"{label}, de {yfmt(a[0])} a {yfmt(b[0])}. Las líneas punteadas unen años sin cifra.", code))

    sy = lambda y: f"{y}–{str(y + 1)[-2:]}"
    fy = lambda y: f"{y - 1}–{str(y)[-2:]}"

    def sec(title, sid, intro, ks, terms, pic="", extra="", src=""):
        return f"""
<section aria-labelledby="{sid}">
  <h2 id="{sid}">{E(title)}</h2>
  {intro}{plain_es(r, ks, st_med, fmt, STATUS, pd)}
  {pic if pic else rng(ks)}{extra}
  {explain_es(BASE, *terms)}
  <p class="source">Fuente: {E(src)}.</p>
</section>"""

    state_note = f'<p class="note">{E(STATE_NOTES_ES[r.state])}</p>' if r.state in STATE_NOTES_ES else ""
    det = DET_ES.get(r.determination_2026.strip().capitalize() if isinstance(r.determination_2026, str) else "Not available", "No disponible")
    en = f"{BASE}district/{r.leaid}/"
    asks = "".join(f"<li>{E(q)}</li>" for q in ASK_ES)
    body = f"""
<h1>{E(name)}</h1>
<dl class="facts">{''.join(f'<div><dt>{E(a)}</dt><dd>{E(b)}</dd></div>' for a, b in facts)}</dl>
<div class="page-tools"><button type="button" data-print>Imprimir esta página</button>
  <a class="button secondary" href="{en}" hreflang="en">Ver todas las cifras y tablas (en inglés)</a></div>
{parent_note}{nice_kids}
{g_html}
<p class="howto">Cada tema comienza con palabras sencillas y un gráfico. Las preguntas como <em>¿Qué es la mediana?</em> abren una explicación breve.
Todas las cifras y tablas detalladas están en la <a href="{en}" hreflang="en">página en inglés</a>.</p>
{sec("Quiénes reciben servicios", "s-who", state_note, ["id_rate", "pct_504"], ("typical", "504", "categories"),
     extra=ot("i", "Estudiantes con IEP por cada 100 inscritos", "Aproximadamente {va} de cada 100 estudiantes tenían un IEP en {a}, comparado con aproximadamente {vb} en {b}.", sy),
     src="conteo de niños de IDEA Parte B por distrito, 2024–25; Common Core of Data, 2024–25; Civil Rights Data Collection, 2023–24")}
{sec("Dónde aprenden", "s-where", "<p>Estudiantes con IEP en edad escolar, 2024–25.</p>", ["env_80plus", "env_lt40", "env_separate"], ("settings",),
     pic=chart_es("settings", "Tiempo en una clase de educación general, estudiantes con IEP en edad escolar"), src="ambientes educativos de IDEA Parte B por distrito, 2024–25")}
{sec("Al terminar la escuela", "s-leave", "<p>Estudiantes con IEP de 14 a 21 años que salieron de la escuela en 2023–24.</p>", ["grad_regular", "dropout"], ("leaving",),
     pic=chart_es("exit", "Cómo salieron de la escuela los estudiantes con IEP, 2023–24"), src="salidas de IDEA Parte B por distrito, 2023–24")}
{sec("Disciplina y seguridad", "s-disc", "<p>Año escolar 2023–24.</p>", ["oos_idea", "oos_nodis", "oos_504", "expulsion_idea", "restraint_physical_idea", "restraint_mechanical_idea", "seclusion_idea", "referral_idea", "arrest_idea"],
     ("discipline", "504"), extra=ot("d", "Suspensión fuera de la escuela, estudiantes con IEP, por cada 100",
     "Aproximadamente {va} de cada 100 estudiantes con IEP recibieron una suspensión fuera de la escuela en {a}, comparado con aproximadamente {vb} en {b}.", sy),
     src="Civil Rights Data Collection (Oficina de Derechos Civiles), 2023–24; años anteriores desde 2013–14")}
{sec("Fondos", "s-fund", "<p>Año fiscal 2024.</p>", ["spend_per_pupil", "idea_federal_per_student"], ("spending", "idea_money"),
     extra=ot("s", "Gasto por estudiante, en dólares de 2024", "Ajustado por la inflación, el distrito gastó aproximadamente {va} por estudiante en {a} y aproximadamente {vb} en {b}.", fy),
     src="Encuesta Anual de Finanzas de los Sistemas Escolares (Oficina del Censo), año fiscal 2024")}
{sec("Comunidad", "s-comm", "<p>Cálculo de 2024.</p>", ["child_poverty"], ("poverty",),
     extra=ot("p", "Niños de 5 a 17 años en la pobreza, por cada 100", "Aproximadamente {va} de cada 100 niños en la zona del distrito vivían en la pobreza en {a}, y aproximadamente {vb} en {b}.", str),
     src="Cálculos de Ingresos y Pobreza para Áreas Pequeñas (Oficina del Censo), 2024")}
<section aria-labelledby="s-state">
  <h2 id="s-state">Calificación estatal de IDEA</h2>
  <p>Cada año, el Departamento de Educación de EE. UU. califica cómo cada estado cumple con IDEA. En 2026, {E(state)} recibió la calificación <strong>{E(det)}</strong>.
  La calificación describe al estado, no a este distrito.</p>
  {explain_es(BASE, "rating")}
</section>
<section aria-labelledby="s-like" class="like">
  <h2 id="s-like">Distritos parecidos a este</h2>
  <p>Busque distritos de {E(state)} con un número parecido de estudiantes y un nivel parecido de pobreza infantil, y compárelos uno al lado del otro.</p>
  <button type="button" class="secondary" data-like>Buscar distritos parecidos</button>
  <div class="like-out" aria-live="polite"></div>
</section>
<section aria-labelledby="s-rpt" class="rpt-cta">
  <h2 id="s-rpt">Crear un informe para imprimir</h2>
  <p>Responda unas preguntas y reciba un informe sobre este distrito escrito para una familia, un líder escolar o un investigador, con gráficos, listo para imprimir o guardar como PDF.</p>
  <p><a class="button" href="{BASE}es/informe/?id={r.leaid}">Crear un informe de este distrito</a></p>
</section>
<section aria-labelledby="s-ask">
  <h2 id="s-ask">Preguntas que puede hacer</h2>
  <div data-shared="ask"></div>
</section>
<section aria-labelledby="s-more">
  <h2 id="s-more">Sobre estas cifras</h2>
  <p>Estas cifras describen lo que se informó. No son calificaciones. Algunas cifras son de años escolares distintos.</p>
  {explain_es(BASE, "median", "status", "years")}
  {__import__("extra_pages").embed_snippet("es", leaid=r.leaid, name=name, ATLAS_ORIGIN=ATLAS_ORIGIN, BASE=BASE)}
  <p>Cómo citar esta página: Rath, S. (2026). <cite>IDEA Atlas: Special education data for every U.S. school district</cite> (Versión {VERSION}). {E(name)}. {ATLAS_ORIGIN}{BASE}es/distrito/{r.leaid}/</p>
</section>"""
    es_cd = dict(cd)
    es_cd.pop("t", None)
    es_cd.pop("rg", None)
    es_cd["st"] = state
    es_cd["cats"] = [[CAT_ES.get(a, a), b] for a, b in cd.get("cats", [])]
    data = json.dumps(es_cd, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    body = f'<script type="application/json" id="chart-data">{data}</script>' + body
    return page(f"{name}, {state}", body,
                desc=f"Datos de educación especial de {name}, {state}, en palabras sencillas: estudiantes con IEP, lugares de aprendizaje, graduación, disciplina, fondos y pobreza infantil.",
                path=f"{BASE}es/distrito/{r.leaid}/", scripts=("atlas.js",), lang="es", alt=en,
                crumbs=[("IDEA Atlas", f"{BASE}es/"), (state, STATE_PATHS.get(r.state, f"{BASE}es/estados/"))])


def home_es(*, BASE, page, n: int) -> str:
    gloss = "".join(f'<dt id="term-{k}">{E(v[0])}</dt><dd>{E(v[1])}</dd>' for k, v in TERMS_ES.items())
    body = f"""
<h1>IDEA Atlas en español</h1>
<p class="lede">Busque cualquier distrito escolar público de EE. UU. y vea, en palabras sencillas, cómo atiende a los estudiantes con discapacidades.
Todas las cifras vienen de datos federales públicos.</p>
<p class="hint">Las cifras son los datos federales más recientes, en su mayoría de los años escolares 2024–25 y 2023–24. Cada cifra indica su propio año.
Vea las <a href="{BASE}es/acerca-de-los-datos/#sources">fuentes y los años</a>.</p>
{explain_es(BASE, "idea", "iep", "504", full=True)}
<section aria-labelledby="find-h" class="panel">
  <h2 id="find-h">Buscar un distrito</h2>
  <form id="search-form" role="search" novalidate>
    <label for="q">Código postal o nombre del distrito</label>
    <div class="row">
      <input id="q" name="q" type="search" autocomplete="off" spellcheck="false" aria-describedby="q-hint">
      <button type="submit">Buscar</button>
    </div>
    <p id="q-hint" class="hint">Por ejemplo, 07042 o Montclair.</p>
  </form>
  <div id="results" aria-live="polite"></div>
</section>

<section aria-labelledby="qa-title" class="panel qa">
  <h2 id="qa-title">Haga una pregunta</h2>
  <p class="hint">Pregunte con sus propias palabras, en español o en inglés. Las respuestas vienen solo de las cifras y las guías de este atlas, nunca de suposiciones. Lo que escribe no se guarda ni se envía a ningún lugar, salvo que usted elija enviarlo para ayudar al atlas a aprender.</p>
  <form id="qa-form" role="search" aria-label="Haga una pregunta" novalidate>
    <label for="qa-q">Su pregunta</label>
    <div class="row">
      <input id="qa-q" name="ask" type="search" autocomplete="off" spellcheck="true" aria-describedby="qa-examples-h">
      <button type="submit">Preguntar</button>
    </div>
  </form>
  <p class="hint" id="qa-examples-h">Pruebe una de estas:</p>
  <ul class="qa-examples">
    <li><button type="button" class="link-btn" data-qa-example>¿Cuántos estudiantes tienen IEP en 07042?</button></li>
    <li><button type="button" class="link-btn" data-qa-example>Comparar suspensiones en Newark y Paterson, NJ</button></li>
    <li><button type="button" class="link-btn" data-qa-example>Graduación en Nueva Jersey</button></li>
    <li><button type="button" class="link-btn" data-qa-example>La escuela manda a mi hijo a casa temprano</button></li>
    <li><button type="button" class="link-btn" data-qa-example>¿Qué es un plan 504?</button></li>
  </ul>
  <p id="qa-live" class="visually-hidden" aria-live="polite"></p>
  <div id="qa-out"></div>
</section>
<section aria-labelledby="what-h">
  <h2 id="what-h">Qué muestra esta herramienta</h2>
  <p>IDEA Atlas cubre {n:,} distritos escolares públicos, incluidos los distritos de escuelas chárter. Cada página de distrito empieza con unas pocas oraciones sencillas
  sobre quiénes reciben servicios de educación especial, dónde aprenden, cómo terminan la escuela, la disciplina, los fondos y la pobreza infantil, con gráficos y explicaciones.
  Las cifras describen lo que los distritos y los estados informaron. No son calificaciones y no pueden mostrar la calidad de los servicios de un distrito.
  La experiencia de su familia y los informes del propio distrito agregan lo que los números no pueden.</p>
  <p class="more-path"><a href="{BASE}es/informe/">Cree un informe</a> para imprimir sobre cualquier distrito, escrito para una familia, un líder escolar o un investigador.</p>
  <p class="more-path">Vea la página de <a href="{BASE}es/estados/">su estado</a>: cómo se comparan sus distritos, sus resultados en los indicadores federales y todos sus distritos.</p>
  {GUIDES_P[0]}
  <p class="more-path">Vea también <a href="{BASE}es/historia/">cincuenta años de educación especial</a>, desde 1975 hasta hoy, para el país y cada estado.</p>
</section>
<section aria-labelledby="words-h">
  <h2 id="words-h">Palabras explicadas</h2>
  <dl class="glossary">{gloss}</dl>
</section>"""
    return page("Datos de educación especial por distrito escolar", body,
                desc="Busque cualquier distrito escolar de EE. UU. por código postal y vea, en palabras sencillas, datos federales de educación especial: estudiantes con IEP, lugares de aprendizaje, graduación, disciplina y fondos.",
                path=BASE + "es/", scripts=("atlas.js",), lang="es", alt=BASE)


def report_es(*, BASE, page) -> str:
    import extra_pages
    from measures import SITE
    STORY = extra_pages.story("es", SITE)
    body = f"""
<div class="rpt-intro">
  <h1>Crear un informe</h1>
  <p class="lede">Responda cinco preguntas cortas y reciba un informe completo sobre cualquier distrito escolar, con gráficos y títulos claros, listo para imprimir o guardar como PDF.</p>
  <ul class="rpt-kinds">
    <li><strong>Para una familia:</strong> palabras sencillas, dibujos, cada término explicado y las preguntas que quiere llevar a una reunión.</li>
    <li><strong>Para un líder escolar:</strong> una página de resumen, el distrito junto a su estado, el país y los distritos que elija, y las tendencias.</li>
    <li><strong>Para un investigador:</strong> cada cifra con su estado, las tablas detalladas y de tendencias, el diccionario de datos y la cita.</li>
  </ul>
</div>
<div id="rpt-app" class="rpt-app"><noscript><p>El asistente necesita JavaScript. Cada <a href="{BASE}es/">página de distrito</a> tiene la misma información.</p></noscript></div>
<div id="rpt-out" hidden></div>
{STORY}"""
    return page("Crear un informe", body, desc="Cree un informe para imprimir sobre la educación especial en cualquier distrito escolar de EE. UU., para una familia, un líder escolar o un investigador.",
                path=BASE + "es/informe/", scripts=("atlas.js", "report.js"), crumbs=[("IDEA Atlas", BASE + "es/")], lang="es", alt=BASE + "report/")
