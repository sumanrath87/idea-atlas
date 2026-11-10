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
