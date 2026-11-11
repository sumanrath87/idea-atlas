"""Pages and pieces added in November 2026: For reporters, the accessibility statement (English and Spanish),
the "share your story" prompt, the privacy note, and share images (Open Graph) for each state page.
"""
from __future__ import annotations

import html
import io
from pathlib import Path

E = html.escape
HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
REVIEWED_EN = "November 10, 2026"
REVIEWED_ES = "10 de noviembre de 2026"


# ---------------------------------------------------------------- small pieces

def story(lang: str, SITE: str) -> str:
    """An invitation to say how the atlas was used. Answers go to the existing feedback survey."""
    if lang == "es":
        return (f'<aside class="story" aria-labelledby="story-h"><h2 id="story-h">¿Le ayudó el atlas?</h2>'
                f'<p>Cuénteme cómo lo usó: en una reunión del IEP, en una clase, en la planificación de un distrito o en un reportaje. '
                f'La encuesta toma unos cinco minutos. Las respuestas ayudan a mejorar el atlas y pueden usarse en investigaciones publicadas.</p>'
                f'<p><a href="{SITE}/tools/idea-atlas/#encuesta">Contar cómo usé el atlas</a></p></aside>')
    return (f'<aside class="story" aria-labelledby="story-h"><h2 id="story-h">Did the atlas help you?</h2>'
            f'<p>Tell me how you used it: at an IEP meeting, in a class, in district planning, or in a story. '
            f'The survey takes about five minutes. Answers help improve the atlas and may be used in published research.</p>'
            f'<p><a href="{SITE}/tools/idea-atlas/#feedback">Tell me how you used the atlas</a></p></aside>')


def privacy_section(counter_on: bool) -> str:
    if counter_on:
        txt = ("IDEA Atlas has no advertising, no sign-in, and no cookies. To know how many people use it, it counts page views with "
               "<a href=\"https://www.goatcounter.com/\">GoatCounter</a>, a privacy-friendly counter that does not use cookies and does not collect "
               "personal information. Only totals are kept: which pages were viewed, which sites linked to them, and general information such as "
               "country, screen size, and browser.")
    else:
        txt = "IDEA Atlas has no advertising, no sign-in, no cookies, and no tracking."
    return f'<section aria-labelledby="privacy"><h2 id="privacy">Privacy</h2><p>{txt}</p></section>'


# ---------------------------------------------------------------- For reporters

def reporters_page(*, page, BASE, ATLAS_ORIGIN, SITE, VERSION, DOI, n_districts: int) -> str:
    cite = (f'Rath, S. (2026). <cite>IDEA Atlas: Special education data for every U.S. school district</cite> (Version {VERSION}) '
            f'[Online tool and data set]. <a href="https://doi.org/{DOI}">https://doi.org/{DOI}</a>')
    body = f"""
<h1>For reporters</h1>
<p class="lede">IDEA Atlas puts public federal data on special education for {n_districts:,} U.S. school districts in one place, in plain words.
It is free to use, quote, and link to.</p>

<section aria-labelledby="r-find"><h2 id="r-find">What you can find</h2>
<ul>
<li><a href="{BASE}">District pages</a>: who is served, where students with IEPs learn, how they leave school, discipline and safety, Section 504 plans, funding, and child poverty, each with its school year and source.</li>
<li><a href="{BASE}states/">State pages</a>: how a state's districts compare, the state's results on the federal indicators, dispute resolution counts, and its federal IDEA rating.</li>
<li><a href="{BASE}history/">History</a>: national and state trends in special education since 1975.</li>
<li><a href="{BASE}guides/">Guides</a>: plain-language explanations of the law and the numbers, such as <a href="{BASE}guides/discipline/">discipline</a> and <a href="{BASE}guides/disproportionality/">significant disproportionality</a>.</li>
<li><a href="{BASE}report/">Printable reports</a> for any district, and every page in <a href="{BASE}es/">Spanish</a>.</li>
</ul></section>

<section aria-labelledby="r-data"><h2 id="r-data">Get the data</h2>
<p>The full data set is on the <a href="{BASE}download/">download page</a> as CSV files. Each version is kept permanently, with its own record, at
<a href="https://doi.org/{DOI}">doi.org/{DOI}</a>. The <a href="{BASE}methods/">methods page</a> explains every source, calculation, and column.
The data are shared under a <a href="https://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0</a> license: you may reuse them with credit.</p>
</section>

<section aria-labelledby="r-care"><h2 id="r-care">Reporting with care</h2>
<ul>
<li>The figures describe what districts and states reported. They are not a measure of the quality of a district's services.</li>
<li>Sources cover different school years. Each figure on the site shows its year.</li>
<li>Small numbers swing widely. Some figures are withheld by the source to protect students' privacy, and the site marks them.</li>
<li>Comparing a district with the typical district in its state is usually fairer than ranking districts.</li>
<li>State ratings are the U.S. Department of Education's annual IDEA determinations, not the atlas's judgment.</li>
</ul></section>

<section aria-labelledby="r-angles"><h2 id="r-angles">Questions the data can help answer</h2>
<ul>
<li>How much of the school day do students with IEPs spend in general classes in your area, and how wide is the range within the state?</li>
<li>How do suspension rates for students with IEPs compare with rates for students without disabilities?</li>
<li>How often are students restrained, secluded, or referred to police, and which districts report zero?</li>
<li>How have state complaints, mediation requests, and due process complaints changed over time?</li>
<li>How much federal IDEA money reaches each district per student with an IEP, next to overall spending?</li>
</ul></section>

<section aria-labelledby="r-cite"><h2 id="r-cite">How to cite</h2>
<p>{cite}</p>
<p>When you write about a single district, please link to its page so readers can see the figures and their sources.</p></section>

<section aria-labelledby="r-contact"><h2 id="r-contact">Talk with the creator</h2>
<p>Dr. Suman Rath built IDEA Atlas. He is an assistant professor of special education leadership in the Department of Educational Leadership at
Montclair State University and studies how special education policy is put into practice. He can explain what the numbers show and what they leave out.</p>
<p>To arrange an interview, write through the <a href="{SITE}/contact/">contact page on sumanrath.org</a>.</p></section>
"""
    return page("For reporters", body, desc="Using IDEA Atlas in reporting: what the atlas covers, how to get the data, how to cite it, and how to reach its creator.",
                path=BASE + "for-reporters/", scripts=("atlas.js",), crumbs=[("IDEA Atlas", BASE)])


# ---------------------------------------------------------------- Accessibility statement

def accessibility_page(lang: str, *, page, BASE, SITE) -> str:
    if lang == "es":
        body = f"""
<h1>Accesibilidad</h1>
<p class="lede">IDEA Atlas es para familias, educadores e investigadores, incluidas las personas con discapacidades. Quiero que todas puedan usarlo.</p>
<section aria-labelledby="a-goal"><h2 id="a-goal">Meta</h2>
<p>El atlas busca cumplir las Pautas de Accesibilidad para el Contenido Web (WCAG) 2.2, nivel AA.</p></section>
<section aria-labelledby="a-how"><h2 id="a-how">Cómo está hecho</h2>
<ul>
<li>Cada página tiene títulos ordenados, regiones con nombre y un enlace para saltar al contenido principal.</li>
<li>Cada gráfico viene con una tabla que tiene las mismas cifras. Los gráficos de tendencias se pueden recorrer año por año con las flechas del teclado.</li>
<li>El mapa se puede mover con el teclado, y la búsqueda de distritos y la <a href="{BASE}table/">tabla de distritos</a> (en inglés) dan la misma información sin el mapa.</li>
<li>El color nunca es la única manera de mostrar algo; las cifras siempre aparecen también en palabras.</li>
<li>El texto usa palabras sencillas y explica cada término, en inglés y en español.</li>
<li>Las páginas se adaptan a pantallas pequeñas y se pueden imprimir.</li>
</ul></section>
<section aria-labelledby="a-check"><h2 id="a-check">Cómo se revisa</h2>
<p>Antes de cada versión, cada tipo de página se revisa con el motor de pruebas automáticas axe. Las pruebas automáticas no encuentran todos los problemas, así que sus comentarios importan.</p></section>
<section aria-labelledby="a-limits"><h2 id="a-limits">Límites conocidos</h2>
<ul>
<li>El mapa es visual. Use la búsqueda o la tabla para obtener la misma información.</li>
<li>Los archivos de datos para descargar son tablas en bruto, pensadas para programas de hojas de cálculo.</li>
<li>Los enlaces a documentos externos, como los informes de los estados, pueden no cumplir el mismo nivel.</li>
</ul></section>
<section aria-labelledby="a-tell"><h2 id="a-tell">Avíseme</h2>
<p>Si algo en el atlas le resulta difícil de usar, escriba por la <a href="{SITE}/contact/">página de contacto</a>. Diga qué página, qué intentaba hacer y,
si quiere, qué tecnología de apoyo usa. Arreglar estos problemas es una prioridad.</p>
<p class="hint">Revisado el {REVIEWED_ES}.</p></section>
"""
        return page("Accesibilidad", body, desc="Cómo está hecho IDEA Atlas para que todas las personas puedan usarlo, cómo se revisa y cómo informar un problema.",
                    path=BASE + "es/accesibilidad/", scripts=("atlas.js",), crumbs=[("IDEA Atlas", BASE + "es/")], lang="es", alt=BASE + "accessibility/")
    body = f"""
<h1>Accessibility</h1>
<p class="lede">IDEA Atlas is for families, educators, and researchers, including people with disabilities. I want everyone to be able to use it.</p>
<section aria-labelledby="a-goal"><h2 id="a-goal">Goal</h2>
<p>The atlas aims to meet the Web Content Accessibility Guidelines (WCAG) 2.2 at Level AA.</p></section>
<section aria-labelledby="a-how"><h2 id="a-how">How it is built</h2>
<ul>
<li>Every page has ordered headings, named regions, and a link to skip to the main content.</li>
<li>Every chart comes with a table of the same figures. Trend charts can be explored year by year with the arrow keys.</li>
<li>The map can be moved with the keyboard, and district search and the <a href="{BASE}table/">table of districts</a> give the same information without the map.</li>
<li>Color is never the only way something is shown; figures are always given in words as well.</li>
<li>The writing uses plain words and explains every term, in English and Spanish.</li>
<li>Pages adjust to small screens and can be printed.</li>
</ul></section>
<section aria-labelledby="a-check"><h2 id="a-check">How it is checked</h2>
<p>Before each release, every type of page is checked with the axe automated testing engine. Automated tests do not catch every problem, so your feedback matters.</p></section>
<section aria-labelledby="a-limits"><h2 id="a-limits">Known limits</h2>
<ul>
<li>The map is visual. Use search or the table for the same information.</li>
<li>The data files for download are raw tables, meant for spreadsheet programs.</li>
<li>Links to outside documents, such as state reports, may not meet the same standard.</li>
</ul></section>
<section aria-labelledby="a-tell"><h2 id="a-tell">Tell me</h2>
<p>If anything in the atlas is hard to use, please write through the <a href="{SITE}/contact/">contact page</a>. Say which page, what you were trying to do,
and, if you like, what assistive technology you use. Fixing these problems is a priority.</p>
<p class="hint">Last reviewed {REVIEWED_EN}.</p></section>
"""
    return page("Accessibility", body, desc="How IDEA Atlas is built so everyone can use it, how it is checked, and how to report a problem.",
                path=BASE + "accessibility/", scripts=("atlas.js",), crumbs=[("IDEA Atlas", BASE)], alt=BASE + "es/accesibilidad/")


# ---------------------------------------------------------------- share images

_FONTS: dict = {}


def _font(name: str, size: int, weight: int):
    """Load a bundled web font (woff2) as a TrueType font Pillow can draw with."""
    from PIL import ImageFont
    key = (name, size, weight)
    if key in _FONTS:
        return _FONTS[key]
    from fontTools.ttLib import TTFont
    src = ASSETS / f"{name}-latin-wght-normal.woff2"
    buf = _FONTS.get(("ttf", name))
    if buf is None:
        f = TTFont(str(src))
        f.flavor = None
        b = io.BytesIO()
        f.save(b)
        buf = b.getvalue()
        _FONTS[("ttf", name)] = buf
    ft = ImageFont.truetype(io.BytesIO(buf), size)
    try:
        ft.set_variation_by_axes([weight])
    except Exception:
        pass
    _FONTS[key] = ft
    return ft


def _wrap(draw, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def og_state(out: Path, *, title: str, line1: str, line2: str, rate: float | None, footer: str) -> None:
    """A 1200 x 630 share image in the style of the main one: brand, title, one key figure, and 100 dots with the rate shaded."""
    from PIL import Image, ImageDraw
    W, H = 1200, 630
    bg, maroon, ink, muted, blue, grey = "#fbf9f5", "#8a2a2b", "#20232a", "#5c6370", "#2a5ea8", "#dcd8cf"
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 18, H], fill=maroon)
    d.text((90, 88), "IDEA Atlas", font=_font("vollkorn", 58, 600), fill=maroon)
    tf = _font("vollkorn", 50, 600)
    y = 190
    for ln in _wrap(d, title, tf, 680)[:3]:
        d.text((90, y), ln, font=tf, fill=ink)
        y += 66
    y += 18
    bf = _font("manrope", 27, 600)
    for ln in _wrap(d, line1, bf, 640)[:2]:
        d.text((90, y), ln, font=bf, fill=ink)
        y += 38
    sf = _font("manrope", 24, 400)
    for ln in _wrap(d, line2, sf, 640)[:2]:
        d.text((90, y + 4), ln, font=sf, fill=muted)
        y += 34
    d.text((90, 555), "atlas.sumanrath.org", font=_font("manrope", 24, 700), fill=ink)
    d.text((370, 555), footer, font=_font("manrope", 24, 400), fill=muted)
    shaded = int(round(rate)) if rate is not None else 0
    for i in range(100):
        r_, c_ = divmod(i, 10)
        cx, cy = 820 + c_ * 32, 150 + r_ * 32
        d.ellipse([cx, cy, cx + 22, cy + 22], fill=blue if i < shaded else grey)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "PNG", optimize=True)


def og_guide(out: Path, *, title: str, line: str, kind: str, footer: str) -> None:
    """A 1200 x 630 share image for a guide: brand, the guide's title and one line about it."""
    from PIL import Image, ImageDraw
    from typeset import typeset
    title, line = typeset(title), typeset(line)
    W, H = 1200, 630
    bg, maroon, ink, muted, rule = "#fbf9f5", "#8a2a2b", "#20232a", "#5c6370", "#e2dfd6"
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    lnum = {"features": ["lnum"]}
    d.rectangle([0, 0, 18, H], fill=maroon)
    d.text((90, 80), "IDEA Atlas", font=_font("vollkorn", 52, 600), fill=maroon)
    d.text((90, 150), kind, font=_font("manrope", 26, 600), fill=muted)
    size = 62
    while True:
        tf = _font("vollkorn", size, 600)
        lines = _wrap(d, title, tf, 1000)
        if len(lines) <= 3 or size <= 46:
            break
        size -= 4
    y = 205
    for ln in lines[:3]:
        d.text((90, y), ln, font=tf, fill=ink, **lnum)
        y += int(size * 1.22)
    y += 16
    sf = _font("manrope", 27, 400)
    room = max(0, (512 - y) // 38)
    desc = _wrap(d, line, sf, 960)
    if len(desc) > room:
        desc = desc[:room]
        if desc:
            last = desc[-1]
            while last and d.textlength(last + "\u2026", font=sf) > 960:
                last = last.rsplit(" ", 1)[0]
            desc[-1] = last.rstrip(" ,;:") + "\u2026"
    for ln in desc:
        d.text((90, y), ln, font=sf, fill=muted)
        y += 38
    d.line([(90, 532), (1110, 532)], fill=rule, width=2)
    d.text((90, 555), "atlas.sumanrath.org", font=_font("manrope", 24, 700), fill=ink)
    d.text((370, 555), footer, font=_font("manrope", 24, 400), fill=muted)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "PNG", optimize=True)


# ---------------------------------------------------------------- Spanish: compare and about the data

def compare_es(*, page, BASE, explain_es) -> str:
    body = f"""
<h1>Comparar distritos</h1>
<p class="lede">Elija de dos a cuatro distritos para ver sus cifras lado a lado, con la mediana nacional como referencia.</p>
<form id="c-form" role="search" novalidate>
  <label for="c-q">Agregue un distrito por nombre o código postal</label>
  <div class="row"><input id="c-q" type="search" autocomplete="off" aria-describedby="c-hint"><button type="submit">Buscar</button></div>
  <p id="c-hint" class="hint">Hasta cuatro distritos. El enlace en la barra de direcciones guarda su elección, así que puede guardarlo o compartirlo.</p>
</form>
<div id="c-results" aria-live="polite"></div>
<h2 id="c-chosen-h">Distritos elegidos</h2>
<ul id="c-chosen" class="chosen" aria-labelledby="c-chosen-h"></ul>
<div class="page-tools"><button type="button" data-print>Imprimir esta comparación</button></div>
<p id="c-status" class="hint" aria-live="polite"></p>
<figure id="c-chart" class="chart" aria-hidden="true" hidden><figcaption>Cada fila muestra los distritos elegidos en la misma escala. El círculo marca la mediana nacional.</figcaption><div class="chart-body"></div></figure>
<div id="c-wrap" class="table-wrap" role="region" tabindex="0" aria-labelledby="c-caption" hidden>
  <table id="c-table" class="profile compare"><caption id="c-caption">Cifras lado a lado</caption><thead></thead><tbody></tbody></table>
</div>
<h2>Palabras que se usan aquí</h2>
{explain_es(BASE, "per100", "median", "status", "years", "iep", "504", "settings", "leaving", "discipline", "spending", "idea_money", "poverty", full=True)}
"""
    return page("Comparar distritos", body, desc="Compare las cifras de educación especial de hasta cuatro distritos escolares, lado a lado.",
                path=BASE + "es/comparar/", scripts=("atlas.js",), crumbs=[("IDEA Atlas", BASE + "es/")], lang="es", alt=BASE + "compare/")


def about_es(*, page, BASE, SITE, ATLAS_ORIGIN, VERSION, DOI, SOURCES, MEASURES, es_site, counter_on: bool) -> str:
    src_rows = "".join(f'<tr><th scope="row">{E(v[0])}</th><td>{E(v[1])}</td><td>{E(v[2])}</td></tr>' for v in SOURCES.values())
    dict_rows = "".join(f'<tr><th scope="row"><code>{m[0]}</code></th><td>{E(es_site.SHORT_ES.get(m[0], m[3]))}</td></tr>' for m in MEASURES)
    status_rows = "".join(f'<tr><th scope="row">{E(k)}</th><td>{E(v.capitalize())}</td></tr>' for k, v in es_site.STATUS_ES.items())
    notes = "".join(f"<li>{E(v)}</li>" for v in es_site.STATE_NOTES_ES.values())
    terms = "".join(f'<dt>{E(q)}</dt><dd>{E(a)}</dd>' for q, a in es_site.TERMS_ES.values())
    priv = ("IDEA Atlas no tiene publicidad, no pide iniciar sesión y no usa cookies. Para saber cuántas personas lo usan, cuenta las visitas con "
            "<a href=\"https://www.goatcounter.com/\">GoatCounter</a>, un contador que respeta la privacidad: no usa cookies ni reúne información personal. "
            "Solo se guardan totales: qué páginas se vieron, qué sitios enlazaron a ellas e información general como el país, el tamaño de la pantalla y el navegador."
            if counter_on else "IDEA Atlas no tiene publicidad, no pide iniciar sesión, no usa cookies y no rastrea a nadie.")
    body = f"""
<h1>Acerca de los datos</h1>
<p class="lede">Cómo se hace cada cifra de IDEA Atlas, de dónde viene y lo que no puede decirle.</p>
<div class="page-tools"><button type="button" data-print>Imprimir esta página</button></div>

<section aria-labelledby="what"><h2 id="what">Qué muestra la herramienta</h2>
<p>Creé IDEA Atlas para que las familias, los educadores y los investigadores puedan ver, en un solo lugar, lo que dicen los datos federales públicos sobre la
educación especial en cada distrito escolar. Muestra a quiénes se atiende, dónde aprenden los estudiantes, cómo salen de la escuela, la disciplina y la seguridad,
los planes de la Sección 504, los fondos y la pobreza infantil. No clasifica ni califica a los distritos. Las cifras describen lo que se informó.</p></section>

<section aria-labelledby="sources"><h2 id="sources">Fuentes</h2>
<p>Cada cifra viene de una fuente federal pública. Cada archivo se descarga sin cambios, con su fecha, se revisa y se guarda una copia. Los nombres de las fuentes están en inglés, como las publica cada agencia.</p>
<div class="table-wrap" role="region" tabindex="0" aria-labelledby="src-cap"><table><caption id="src-cap">Fuentes y años escolares</caption>
<thead><tr><th scope="col">Fuente</th><th scope="col">Año</th><th scope="col">Agencia</th></tr></thead><tbody>{src_rows}</tbody></table></div></section>

<section aria-labelledby="rules"><h2 id="rules">Reglas de los datos</h2>
<ul>
<li><strong>Tasas por cada 100.</strong> La mayoría de las cifras se muestran por cada 100 estudiantes de un grupo, para que distritos de distinto tamaño se lean igual.</li>
<li><strong>Grupo mínimo de 10.</strong> No se muestra una tasa cuando el grupo que describe tiene menos de 10 estudiantes.</li>
<li><strong>Retenido por privacidad.</strong> Las agencias retienen las cifras pequeñas para proteger a los estudiantes. Estas cifras nunca se estiman.</li>
<li><strong>Al menos.</strong> Cuando se retiene una parte pequeña de una cifra, el resto se muestra como un mínimo ("al menos").</li>
<li><strong>Registros combinados.</strong> La ciudad de Nueva York se informa como un solo distrito en algunos archivos y como 32 distritos geográficos en otros. IDEA Atlas muestra un registro combinado de la ciudad y mantiene los 32 distritos como registros enlazados.</li>
<li><strong>Revisión de conteos.</strong> Cuando el conteo de estudiantes con IEP de los datos de derechos civiles de un distrito es muy distinto de su conteo de IDEA, sus cifras de disciplina llevan una nota.</li>
</ul>
<div class="table-wrap" role="region" tabindex="0" aria-labelledby="st-cap"><table><caption id="st-cap">Palabras de estado que se usan en los datos</caption>
<thead><tr><th scope="col">En los archivos (en inglés)</th><th scope="col">Qué significa en el sitio</th></tr></thead><tbody>{status_rows}</tbody></table></div></section>

<section aria-labelledby="measures"><h2 id="measures">Cómo se calcula cada medida</h2>
<p>Cada tasa es el número de estudiantes de una categoría dividido entre el número de estudiantes del grupo, multiplicado por 100. Las tasas de disciplina cuentan estudiantes, no incidentes.
El gasto por estudiante es el gasto corriente dividido entre la inscripción de otoño. Los fondos federales de IDEA por estudiante son los ingresos federales de IDEA que el distrito recibió a través del estado, divididos entre su conteo de IDEA.</p>
<p>El mapa agrupa los distritos en cinco tonos, de claro a oscuro, cada uno con más o menos el mismo número de distritos. Los tonos muestran más o menos de algo; no significan mejor o peor.</p></section>

<section aria-labelledby="det"><h2 id="det">Calificaciones estatales</h2>
<p>Cada año, el Departamento de Educación de EE. UU. revisa cómo cada estado aplica IDEA y le da una de cuatro calificaciones: cumple los requisitos, necesita ayuda,
necesita intervención o necesita intervención sustancial. Las calificaciones de 2026 se basan en datos del año fiscal federal 2024. Una calificación describe al estado, no a un distrito.</p></section>

<section aria-labelledby="limits"><h2 id="limits">Límites conocidos</h2>
<ul>
<li>Las fuentes cubren años escolares distintos. Cada cifra muestra su propio año.</li>
<li>Los archivos federales reflejan lo que informaron los estados y los distritos. Los errores de informe se mantienen, y las agencias a veces corrigen los archivos.</li>
<li>El conteo de IDEA puede incluir a niños que el distrito atiende pero que no están inscritos, como niños de preescolar y estudiantes que sus padres pusieron en escuelas privadas. Esto sube la tasa por cada 100 inscritos en algunos lugares.</li>
<li>Los distritos pequeños suelen tener cifras retenidas.</li>
{notes}
<li>Las zonas de código postal son aproximaciones de las rutas del correo.</li>
<li>Las cifras describen lo que se informó, no la calidad de los servicios de un distrito.</li>
<li>Es información general, no asesoría legal.</li>
</ul></section>

<section aria-labelledby="dictionary"><h2 id="dictionary">Diccionario de datos</h2>
<p>Los archivos para descargar están en inglés. Esta tabla da el nombre de cada columna y su medida. El <a href="{BASE}methods/#dictionary">diccionario completo</a> (en inglés) indica el grupo de cada medida.</p>
<div class="table-wrap" role="region" tabindex="0" aria-labelledby="dd-cap"><table><caption id="dd-cap">Medidas del archivo para descargar</caption>
<thead><tr><th scope="col">Columna</th><th scope="col">Medida</th></tr></thead><tbody>{dict_rows}</tbody></table></div>
<p><a href="{BASE}download/">Descargar los datos</a> (página en inglés).</p></section>

<section aria-labelledby="words"><h2 id="words">Palabras explicadas</h2>
<dl class="glossary">{terms}</dl></section>

<section aria-labelledby="updates"><h2 id="updates">Actualizaciones y versiones</h2>
<p>Cada mes se revisa si las agencias publicaron archivos nuevos. Cuando hay uno, IDEA Atlas se vuelve a construir y se revisa antes de publicarse, y cambia el número de versión. Esta es la versión {VERSION}.</p></section>

<section aria-labelledby="privacy"><h2 id="privacy">Privacidad</h2><p>{priv}</p></section>

<section aria-labelledby="cite"><h2 id="cite">Cómo citar</h2>
<p>Rath, S. (2026). <cite>IDEA Atlas: Special education data for every U.S. school district</cite> (Versión {VERSION}) [Herramienta en línea y conjunto de datos]. https://doi.org/{DOI}</p>
<p>Herramienta en línea: <a href="{ATLAS_ORIGIN}{BASE}">{ATLAS_ORIGIN}{BASE}</a>. Los archivos de cada versión se guardan de forma permanente en <a href="https://doi.org/{DOI}">doi.org/{DOI}</a>.</p>
<p>Para informar un error, use la <a href="{SITE}/contact/">página de contacto</a>.</p></section>
"""
    return page("Acerca de los datos", body, desc="Cómo se hacen las cifras de IDEA Atlas: fuentes, reglas de los datos, cálculos, límites y diccionario de datos.",
                path=BASE + "es/acerca-de-los-datos/", scripts=("atlas.js",), crumbs=[("IDEA Atlas", BASE + "es/")], lang="es", alt=BASE + "methods/")


# ---------------------------------------------------------------- embeddable district card

EMBED_KEYS = [("id_rate", "Students with IEPs, per 100 students enrolled", "Estudiantes con IEP, por cada 100 estudiantes inscritos"),
              ("env_80plus", "In a general class 80% or more of the day, per 100 students with IEPs", "En una clase general el 80% o más del día, por cada 100 estudiantes con IEP"),
              ("grad_regular", "Left school with a regular diploma, per 100 students with IEPs who left", "Salieron con un diploma regular, por cada 100 estudiantes con IEP que salieron"),
              ("oos_idea", "Out-of-school suspension, per 100 students with IEPs", "Suspensión fuera de la escuela, por cada 100 estudiantes con IEP")]


def embed_data(OUT: Path, SOURCES, MEASURES, state_names_en: dict, state_names_es: dict) -> None:
    """Small files for the embeddable card: one per two-digit state code, plus labels and national medians."""
    import json
    v = json.loads((OUT / "data" / "values.json").read_text())
    keys = [k for k, _, _ in EMBED_KEYS]
    pos = [next(i for i, m in enumerate(v["measures"]) if m["key"] == k) for k in keys]
    src = {m[0]: m[5] for m in MEASURES}
    meta = {"v": v.get("version"), "m": [{"k": k, "en": en, "es": es, "u": v["measures"][p]["unit"], "nat": v["measures"][p].get("national_median"),
                                          "y": SOURCES[src[k]][1]} for (k, en, es), p in zip(EMBED_KEYS, pos)],
            "status": v["status"], "st_en": state_names_en, "st_es": state_names_es}
    shards: dict = {}
    for i, lid in enumerate(v["ids"]):
        n = v["names"][i]
        shards.setdefault(lid[:2], {})[lid] = [n[0], n[1], [v["values"][i][p] for p in pos], "".join(v["codes"][i][p] for p in pos)]
    d = OUT / "data" / "embed"
    d.mkdir(parents=True, exist_ok=True)
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, separators=(",", ":")))
    for k, rows in shards.items():
        (d / f"{k}.json").write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")))


def embed_page(*, BASE: str, ATLAS_ORIGIN: str) -> str:
    """One page, /embed/?id=<district ID>&lang=en|es, made to sit inside an iframe on another site."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>IDEA Atlas district card</title>
<style>
:root {{ --ink:#20232a; --muted:#5c6370; --rule:#e2ddd2; --accent:#8a2a2b; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font: 15px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; color: var(--ink); background: #fbf9f5; }}
.card {{ border: 1px solid var(--rule); border-top: 4px solid var(--accent); border-radius: 6px; padding: 14px 16px; background: #fff; }}
.brand {{ font: 600 13px/1 Georgia, serif; color: var(--accent); margin: 0 0 6px; letter-spacing: .01em; }}
h1 {{ font: 600 19px/1.25 Georgia, serif; margin: 0; }}
.place {{ color: var(--muted); margin: 2px 0 10px; font-size: 14px; }}
dl {{ margin: 0; display: grid; gap: 8px; }}
dl div {{ border-top: 1px solid var(--rule); padding-top: 7px; }}
dt {{ font-size: 13.5px; color: var(--muted); }}
dd {{ margin: 1px 0 0; font-size: 14px; }}
dd b {{ font-size: 18px; color: var(--ink); }}
.foot {{ margin: 10px 0 0; font-size: 13px; color: var(--muted); }}
a {{ color: var(--accent); }}
a:focus-visible {{ outline: 3px solid #2a5ea8; outline-offset: 2px; }}
</style>
</head>
<body>
<main class="card" id="card" aria-live="polite"><p class="brand">IDEA Atlas</p><p>Loading…</p></main>
<script>
(function () {{
  var BASE = "{BASE}", ORIGIN = "{ATLAS_ORIGIN}";
  var q = new URLSearchParams(location.search), id = (q.get("id") || "").replace(/[^0-9A-Za-z]/g, ""), es = q.get("lang") === "es";
  if (es) document.documentElement.lang = "es";
  var T = es ? {{nat: "Mediana nacional", see: "Ver todas las cifras", none: "No se encontró este distrito.", at: "al menos ", rep: "No se informó", title: "Datos de educación especial", src: "Datos federales públicos."}}
             : {{nat: "National median", see: "See all the figures", none: "This district was not found.", at: "at least ", rep: "Not reported", title: "Special education data", src: "Public federal data."}};
  var ST_ES = {{"Withheld for privacy": "Retenido por privacidad", "Fewer than 10 students": "Menos de 10 estudiantes", "Flagged for data quality": "Marcado por la calidad de los datos",
               "Not reported": "No se informó", "No students in this group": "No hay estudiantes en este grupo"}};
  function esc(s) {{ return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {{ return {{"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}}[c]; }}); }}
  function f(v, u) {{ return u === "usd" ? "$" + Math.round(v).toLocaleString("en-US") : Number(v).toLocaleString("en-US", {{minimumFractionDigits: 1, maximumFractionDigits: 1}}); }}
  var card = document.getElementById("card");
  function fail() {{ card.innerHTML = '<p class="brand">IDEA Atlas</p><p>' + T.none + '</p><p class="foot"><a href="' + ORIGIN + BASE + '" target="_blank" rel="noopener">atlas.sumanrath.org</a></p>'; }}
  if (!id) return fail();
  Promise.all([fetch(BASE + "data/embed/meta.json").then(function (r) {{ return r.json(); }}),
               fetch(BASE + "data/embed/" + id.slice(0, 2) + ".json").then(function (r) {{ return r.ok ? r.json() : {{}}; }})]).then(function (x) {{
    var meta = x[0], row = x[1][id]; if (!row) return fail();
    var st = (es ? meta.st_es : meta.st_en)[row[1]] || row[1];
    document.title = row[0] + " | IDEA Atlas";
    var items = meta.m.map(function (m, j) {{
      var c = row[3].charAt(j), v = row[2][j], val;
      if (c === "0" && v != null) val = "<b>" + f(v, m.u) + "</b>";
      else if (c === "1" && v != null) val = T.at + "<b>" + f(v, m.u) + "</b>";
      else {{ var s = meta.status[c] || "Not reported"; val = es ? (ST_ES[s] || s) : s; }}
      var nat = m.nat != null ? " · " + T.nat + " " + f(m.nat, m.u) : "";
      return "<div><dt>" + esc(es ? m.es : m.en) + " (" + esc(m.y) + ")</dt><dd>" + val + nat + "</dd></div>";
    }}).join("");
    var link = ORIGIN + BASE + (es ? "es/distrito/" : "district/") + id + "/";
    card.innerHTML = '<p class="brand">IDEA Atlas · ' + T.title + '</p><h1>' + esc(row[0]) + '</h1><p class="place">' + esc(st) + '</p><dl>' + items + '</dl>' +
      '<p class="foot">' + T.src + ' <a href="' + link + '" target="_blank" rel="noopener">' + T.see + '<span style="position:absolute;left:-9999px"> (' + (es ? "se abre en una pestaña nueva" : "opens in a new tab") + ')</span></a></p>';
  }}).catch(fail);
}})();
</script>
</body>
</html>
"""


def embed_snippet(lang: str, *, leaid: str, name: str, ATLAS_ORIGIN: str, BASE: str) -> str:
    """A small placeholder; atlas.js builds the 'embed this district' box from it, so the same text is not repeated on 38,000 pages."""
    return f'<div data-embed="{leaid}" data-name="{E(name)}"></div>'


# ---------------------------------------------------------------- Teaching with IDEA Atlas

def teaching_page(*, page, BASE, SITE, VERSION, DOI) -> str:
    g = lambda rel, t: f'<a href="{BASE}guides/{rel}/">{t}</a>'
    body = f"""
<h1>Teaching with IDEA Atlas</h1>
<p class="lede">Four ready-to-use class activities for courses in special education, teacher preparation, school leadership, and education policy.
Each one uses real public data for a district or state your students care about, and each ends with questions the numbers alone cannot answer.</p>

<section aria-labelledby="t-notes"><h2 id="t-notes">Before you start</h2>
<ul>
<li>The atlas is free, needs no account, and works with screen readers and keyboards. Every page is also in Spanish.</li>
<li>Students can choose a district they know: where they grew up, work, or do field placements. Search by name or ZIP code from the <a href="{BASE}">home page</a>.</li>
<li>The figures describe what districts reported. They are not grades. The guide {g("how-to-read-district-data", "How to read your district's special education data")} is a good first reading for any activity.</li>
<li>Times are suggestions for a single class session. Each activity also works as a short assignment.</li>
</ul></section>

<section aria-labelledby="t-1"><h2 id="t-1">Activity 1: Read a district before an IEP meeting</h2>
<p><strong>Fits:</strong> introduction to special education, family partnerships, teacher preparation. <strong>Time:</strong> about 45 minutes.</p>
<ol>
<li>Each student opens a district page and reads the plain-language sentences at the top of each section.</li>
<li>Using <a href="{BASE}report/">Make a report</a>, students create a family report for an imagined child getting ready for an annual IEP meeting.</li>
<li>Students write three questions a family could bring to the meeting, each tied to a figure in the report. The guide {g("iep-meeting-questions", "the guide to questions for an IEP meeting")} offers models.</li>
</ol>
<p><strong>Discuss:</strong> Which figures would reassure a family, and which would worry them? What would a family need to know that no federal figure can show?</p></section>

<section aria-labelledby="t-2"><h2 id="t-2">Activity 2: Where do students learn across one state?</h2>
<p><strong>Fits:</strong> inclusive education, teacher preparation, school leadership. <strong>Time:</strong> about 60 minutes.</p>
<ol>
<li>Students open a <a href="{BASE}states/">state page</a> and find how much of the school day the typical district's students with IEPs spend in general classes.</li>
<li>In <a href="{BASE}compare/">Compare districts</a>, they choose three districts in that state with very different figures.</li>
<li>Students read {g("least-restrictive-environment", "the least restrictive environment guide")} and list reasons the figures might differ, such as regional programs, definitions, or how services are organized.</li>
</ol>
<p><strong>Discuss:</strong> The law sets the general class as the starting point for each child. What would it take for a district at the low end to change, and who would need to be part of that change?</p></section>

<section aria-labelledby="t-3"><h2 id="t-3">Activity 3: Discipline data and fair comparisons</h2>
<p><strong>Fits:</strong> school leadership, school psychology, behavior and classroom management. <strong>Time:</strong> about 60 minutes.</p>
<ol>
<li>Students find the out-of-school suspension rates for students with IEPs and students without disabilities on a district page, and the figures by race and ethnicity.</li>
<li>Using the worked example in {g("disproportionality", "the significant disproportionality guide")}, they calculate a simple risk ratio from the district's figures.</li>
<li>Students note every figure that is withheld or based on small numbers, and explain why that matters before drawing a conclusion.</li>
</ol>
<p><strong>Discuss:</strong> Read the "Beyond compliance" section of {g("discipline", "the discipline guide")}. If this district were cited for discipline disparities, what would a review that changes practice, rather than paperwork, look like?</p></section>

<section aria-labelledby="t-4"><h2 id="t-4">Activity 4: Compliance and results in a state's federal report</h2>
<p><strong>Fits:</strong> education policy, leadership doctoral seminars, special education administration. <strong>Time:</strong> about 75 minutes, or a short written memo.</p>
<ol>
<li>Students read {g("indicators", "the federal indicators explained")} and note which indicators measure results and which measure compliance.</li>
<li>On a state page, they compare the state's results on indicators 8 (parent involvement), 11 (timely evaluation), and 13 (transition planning) with the national figures.</li>
<li>Students read the essay {g("beyond-compliance", "Beyond compliance: what the indicators miss")} and write a one-page memo to a state director: what the state does well on paper, and one question its data cannot answer.</li>
</ol>
<p><strong>Discuss:</strong> Can a state meet every compliance target and still fall short for students? What evidence would show the difference?</p></section>

<section aria-labelledby="t-cite"><h2 id="t-cite">Citing the atlas in student work</h2>
<p>Rath, S. (2026). <cite>IDEA Atlas: Special education data for every U.S. school district</cite> (Version {VERSION}) [Online tool and data set].
<a href="https://doi.org/{DOI}">https://doi.org/{DOI}</a></p>
<p>Each district page has its own citation line at the bottom.</p></section>

<section aria-labelledby="t-tell"><h2 id="t-tell">Using the atlas in your course?</h2>
<p>I would love to hear how it went, what worked, and what your students found confusing. A <a href="{SITE}/tools/idea-atlas/#feedback">five-minute survey</a> asks how you used it,
or you can write through the <a href="{SITE}/contact/">contact page</a>. Your feedback shapes what comes next.</p></section>
"""
    return page("Teaching with IDEA Atlas", body,
                desc="Four ready-to-use class activities that use IDEA Atlas data for courses in special education, teacher preparation, school leadership, and education policy.",
                path=BASE + "teaching/", scripts=("atlas.js",), crumbs=[("IDEA Atlas", BASE)])


# ---------------------------------------------------------------- text shared by every district page

SHARED_ASK_EN = '<p>Numbers can start a conversation. If you are a parent or caregiver, these questions may help when you talk with the district or at an IEP meeting.</p> <ul class="ask"> <li>How does the district decide whether a child needs special education, and how long does an evaluation take?</li> <li>What supports help students with IEPs learn alongside their classmates in general classes?</li> <li>How are families included when an IEP is written and reviewed?</li> <li>What can a family do if they disagree with a decision?</li> <li>How does the district help students with IEPs plan for life after high school?</li> <li>Where can I read the district\'s own special education reports?</li> </ul> <p>For free, one-on-one help, every state has at least one federally funded Parent Training and Information Center. <a href="https://www.parentcenterhub.org/find-your-center/">Find your state\'s Parent Center</a>.</p>'
SHARED_ASK_ES = '<p>Las cifras pueden abrir una conversación. Si usted es madre, padre o cuidador, estas preguntas pueden ayudarle al hablar con el distrito o en una reunión del IEP.</p> <ul class="ask">{asks}</ul> <p>Para recibir ayuda gratuita y personal, cada estado tiene al menos un Centro de Capacitación e Información para Padres con fondos federales, y muchos atienden en español. <a href="https://www.parentcenterhub.org/find-your-center/" hreflang="en">Busque el Centro de Padres de su estado</a> (sitio en inglés).</p>'


def shared_blocks(OUT: Path, es_site) -> None:
    """Text that is the same on all 19,400 district pages, stored once and filled in by atlas.js."""
    import json
    asks = "".join(f"<li>{E(q)}</li>" for q in es_site.ASK_ES)
    (OUT / "data").mkdir(parents=True, exist_ok=True)
    (OUT / "data" / "shared_en.json").write_text(json.dumps({"ask": __import__("typeset").typeset(SHARED_ASK_EN)}, ensure_ascii=False))
    (OUT / "data" / "shared_es.json").write_text(json.dumps({"ask": __import__("typeset").typeset(SHARED_ASK_ES.replace("{asks}", asks))}, ensure_ascii=False))


# ---------------------------------------------------------------- page not found (GitHub Pages serves /404.html)

def not_found_page(*, page, BASE) -> str:
    body = f"""
<h1>We could not find that page</h1>
<p class="lede">The address may be mistyped, or the page may have moved. You can search for a district below, or start from one of these pages.</p>
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
<section aria-labelledby="go-h">
  <h2 id="go-h">Other places to start</h2>
  <ul>
    <li><a href="{BASE}">The atlas home page and map</a></li>
    <li><a href="{BASE}states/">Every state</a></li>
    <li><a href="{BASE}guides/">Guides in plain words</a></li>
    <li><a href="{BASE}report/">Make a report</a></li>
  </ul>
</section>
<section aria-labelledby="es-h" lang="es">
  <h2 id="es-h">¿Busca la versión en español?</h2>
  <p>No encontramos esa página. Puede <a href="{BASE}es/">buscar un distrito en español</a>, ver <a href="{BASE}es/estados/">todos los estados</a> o leer las <a href="{BASE}es/guias/">guías</a>.</p>
</section>
"""
    return page("Page not found", body, desc="This page could not be found. Search for a district or start from the IDEA Atlas home page.",
                path=BASE + "404.html", scripts=("atlas.js",), extra_head='<meta name="robots" content="noindex">')
