"""Build the test corpus for the "Ask a question" box: about 20,000 questions in English and Spanish, each with the kind of
answer it should get. Run after a local build (ATLAS_FAST=1 python build/site.py), then run ops/ask_eval.py.

    python ops/ask_corpus.py            # writes ops/ask_corpus.json.gz

Districts, ZIP codes, states and figures come from the built site's data, so the corpus always matches the atlas.
Family situations come from ops/ask_situations.json (written by hand, mapped to the guides that answer them).
"""
import gzip, json, random, re, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "site" / "tools" / "idea-atlas" / "data"
R = random.Random(20261117)

GENERIC = set(("school schools district districts dist public isd sd usd cusd ccsd esd hsd psd ps msd rsd csd cisd cud ud sch schs cons consol ind "
               "indep unified consolidated independent city county central union elementary elem high local community comm area regional township "
               "twp boro borough board education of the joint r no co inc cs charter academy and for").split())


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


def core(name: str) -> list[str]:
    toks = re.sub(r"\b\d+\b", " ", norm(name)).split()
    return [w for w in toks if w and w not in GENERIC and len(w) > 1 and not re.search(r"\d", w)]


V = json.loads((DATA / "values.json").read_text())
IDS, NAMES, ENR = V["ids"], V["names"], V["enrollment"]
STATES = {}
for line in (ROOT / "build" / "assets" / "atlas.js").read_text().splitlines():
    if line.strip().startswith("var STATES = "):
        STATES = json.loads(line.split("=", 1)[1].strip().rstrip(";"))
        break
ABBR = {v[0]: v[1] for v in STATES.values()}
ST_ES = {"New Jersey": "Nueva Jersey", "New York": "Nueva York", "New Mexico": "Nuevo México", "New Hampshire": "Nuevo Hampshire",
         "North Carolina": "Carolina del Norte", "South Carolina": "Carolina del Sur", "North Dakota": "Dakota del Norte",
         "South Dakota": "Dakota del Sur", "West Virginia": "Virginia Occidental", "Pennsylvania": "Pensilvania", "Hawaii": "Hawái",
         "Louisiana": "Luisiana", "Michigan": "Míchigan", "Oregon": "Oregón", "Tennessee": "Tennessee", "Kansas": "Kansas"}
MAIN_STATES = [c for c in ABBR if c not in ("AS", "GU", "MP", "VI")]

# ---------------------------------------------------------------- districts that can be named unambiguously
by_state_core = {}
for i, n in enumerate(NAMES):
    c = tuple(core(n[0]))
    if c:
        by_state_core.setdefault((n[1], c), []).append(i)
by_core = {}
for (st, c), ii in by_state_core.items():
    by_core.setdefault(c, []).extend(ii)

big = sorted([i for i in range(len(IDS)) if ENR[i]], key=lambda i: -ENR[i])
pool = big[:250] + R.sample(big[250:6000], 450)
DIST = []
STATE_WORDS = set(w for v in STATES.values() for w in norm(v[1]).split()) | set(w for n in ST_ES.values() for w in norm(n).split())
for i in pool:
    c = tuple(core(NAMES[i][0]))
    if not c or len(" ".join(c)) < 4 or set(c) & STATE_WORDS or "geographic" in norm(NAMES[i][0]):
        continue
    same_state = by_state_core[(NAMES[i][1], c)]
    ok_ids = same_state  # any district with this core name in this state is an acceptable answer
    unique_us = len(by_core[c]) == 1
    DIST.append({"i": i, "id": IDS[i], "st": NAMES[i][1], "core": " ".join(c), "full": NAMES[i][0], "ok": [IDS[j] for j in ok_ids], "unique": unique_us})
print(len(DIST), "districts in the pool,", sum(d["unique"] for d in DIST), "with a unique name nationally", file=sys.stderr)

zips = json.loads((ROOT / "clean" / "output" / "zip_lookup.json").read_text())
ZIP1 = [(z, v[0][0] if isinstance(v[0], list) else v[0]) for z, v in zips.items() if isinstance(v, list) and len(v) == 1]
ZIP1 = [(z, lid) for z, lid in ZIP1 if lid in set(IDS)]
R.shuffle(ZIP1)

# ---------------------------------------------------------------- topics, as people say them
TOP = {
 "en": {
  "id_rate": ["IEPs", "students with IEPs", "special education", "special ed", "sped", "kids in special ed", "students with disabilities", "how many kids have IEPs",
              "percent of students in special education", "special education rate", "share of students with disabilities", "disability rate", "students getting services"],
  "pct_504": ["504 plans", "section 504", "504s", "students on 504 plans", "how many kids have a 504"],
  "env_80plus": ["inclusion", "general education classes", "time in general ed", "regular classes", "mainstreaming", "least restrictive environment", "LRE", "gen ed inclusion",
                 "how inclusive", "kids with IEPs in regular classrooms"],
  "env_lt40": ["self-contained classes", "separate classes", "resource room", "kids pulled out most of the day"],
  "env_separate": ["separate schools", "out of district placements", "special schools", "residential placements", "homebound"],
  "grad_regular": ["graduation rate", "graduation", "diplomas", "how many graduate", "graduation for students with IEPs", "regular diploma"],
  "dropout": ["dropout rate", "dropouts", "how many drop out", "students who quit school"],
  "oos_idea": ["suspensions", "suspension rate", "out of school suspensions", "how often kids with IEPs get suspended", "suspended students"],
  "expulsion_idea": ["expulsions", "expelled students"],
  "restraint_physical_idea": ["restraint", "physical restraint", "kids being restrained"],
  "seclusion_idea": ["seclusion", "seclusion rooms", "isolation rooms"],
  "referral_idea": ["police referrals", "referrals to law enforcement", "school police"],
  "arrest_idea": ["school arrests", "arrests of students with disabilities"],
  "spend_per_pupil": ["spending per student", "per pupil spending", "how much money they spend", "school budget per student", "funding"],
  "idea_federal_per_student": ["federal IDEA money", "IDEA funding", "federal special education funding"],
  "child_poverty": ["child poverty", "poverty rate", "low income kids"],
  "_enroll": ["enrollment", "how many students", "how big is it", "total students"],
  "_group_discipline": ["discipline", "discipline data", "behavior and discipline"],
  "_group_settings": ["where students learn", "placements", "classroom settings"],
  "_overview": ["", "overview", "summary", "data", "special education data", "tell me about"],
 },
 "es": {
  "id_rate": ["IEP", "estudiantes con IEP", "educación especial", "educacion especial", "estudiantes con discapacidad", "cuántos niños tienen IEP",
              "porcentaje de estudiantes en educación especial", "niños con discapacidades", "reciben servicios"],
  "pct_504": ["planes 504", "plan 504", "sección 504", "cuántos tienen 504"],
  "env_80plus": ["inclusión", "clase general", "clases generales", "aula regular", "ambiente menos restrictivo", "educación general"],
  "env_lt40": ["clases separadas", "aula separada", "salón separado"],
  "env_separate": ["escuelas separadas", "escuela especial", "lugares separados"],
  "grad_regular": ["graduación", "tasa de graduación", "diploma", "cuántos se gradúan", "se graduan"],
  "dropout": ["abandono escolar", "deserción", "cuántos dejan la escuela", "abandonan la escuela"],
  "oos_idea": ["suspensiones", "suspensión", "cuántos suspenden", "estudiantes suspendidos"],
  "expulsion_idea": ["expulsiones", "expulsados"],
  "restraint_physical_idea": ["sujeción", "restricción física", "inmovilización"],
  "seclusion_idea": ["aislamiento", "cuarto de aislamiento"],
  "referral_idea": ["remisiones a la policía", "policía escolar"],
  "arrest_idea": ["arrestos", "estudiantes arrestados"],
  "spend_per_pupil": ["gasto por estudiante", "cuánto dinero gastan", "presupuesto por estudiante", "fondos"],
  "idea_federal_per_student": ["fondos federales de IDEA", "dinero federal de IDEA"],
  "child_poverty": ["pobreza infantil", "pobreza", "niños de bajos ingresos"],
  "_enroll": ["matrícula", "cuántos estudiantes", "qué tan grande es", "número de estudiantes"],
  "_group_discipline": ["disciplina", "datos de disciplina", "conducta y disciplina"],
  "_group_settings": ["dónde aprenden", "ambientes", "ubicaciones"],
  "_overview": ["", "resumen", "datos", "datos de educación especial", "información"],
 }}

T_DIST = {
 "en": ["{t} in {p}", "{p} {t}", "what is the {t} in {p}?", "{t} for {p}", "show me {t} in {p}", "tell me about {t} in {p}", "{p}: {t}",
        "how does {p} do on {t}", "{t} {p} please", "I live in {p}, what about {t}?", "whats the {t} like in {p}", "can you give me {t} for {p}",
        "{t} at {p}", "how is {p} on {t}", "{p} - {t}", "looking for {t} data for {p}", "{T} in {p}?", "my kids go to {p}. {t}?", "{t} {p}"],
 "es": ["{t} en {p}", "{p} {t}", "¿cuál es la {t} en {p}?", "{t} de {p}", "muéstreme {t} en {p}", "datos de {t} en {p}", "{p}: {t}",
        "¿cómo está {p} en {t}?", "{t} {p} por favor", "vivo en {p}, ¿y la {t}?", "quiero saber {t} en {p}", "{T} en {p}?", "mis hijos van a {p}, {t}"],
}
T_CMP = {
 "en": ["compare {a} and {b}", "{a} vs {b} {t}", "{t} in {a} versus {b}", "how does {a} compare to {b} on {t}", "compare {t} in {a} and {b}",
        "{a} or {b}, which has better {t}", "{a} and {b} {t}", "{t}: {a} vs {b}", "compare {a}, {b} and {c}", "{t} {a} {b} {c}",
        "side by side {a} and {b}", "{a} compared with {b} for {t}"],
 "es": ["comparar {a} y {b}", "{a} vs {b} {t}", "{t} en {a} y {b}", "¿cómo se compara {a} con {b} en {t}?", "comparar {t} en {a} y {b}",
        "{a} o {b}, ¿cuál tiene mejor {t}?", "comparar {a}, {b} y {c}", "{t}: {a} contra {b}", "{a} comparado con {b}"],
}
T_STATE = {
 "en": ["{t} in {s}", "{s} {t}", "what is the {t} in {s}", "how does {s} do on {t}", "typical district in {s} {t}", "{t} statewide in {s}",
        "{T} for the state of {s}", "{s} special education {t}"],
 "es": ["{t} en {s}", "{s} {t}", "¿cuál es la {t} en {s}?", "¿cómo está {s} en {t}?", "distrito típico de {s} {t}", "{t} en el estado de {s}"],
}
T_STATES = {"en": ["compare {s1} and {s2} {t}", "{t} in {s1} vs {s2}", "{s1} or {s2} for {t}", "{t}: {s1}, {s2} and {s3}"],
            "es": ["comparar {s1} y {s2} {t}", "{t} en {s1} y {s2}", "{t}: {s1}, {s2} y {s3}"]}
T_NATION = {"en": ["{t} nationally", "national {t}", "{t} across the US", "{t} in the united states", "what is the national {t}",
                   "{T} nationwide", "{t} in america", "average {t} across the country"],
            "es": ["{t} en todo el país", "{t} a nivel nacional", "{t} en estados unidos", "¿cuál es la {t} nacional?", "{T} en el país"]}

TYPO_KEYS = "qwertyuiopasdfghjklzxcvbnm"


def typo(w: str) -> str:
    if len(w) < 6:
        return w
    k = R.randrange(1, len(w) - 2)
    op = R.choice("swap drop dup")
    if op == "swap":
        return w[:k] + w[k + 1] + w[k] + w[k + 2:]
    if op == "drop":
        return w[:k] + w[k + 1:]
    return w[:k] + w[k] + w[k:]


def style(q: str) -> str:
    r = R.random()
    if r < .30:
        q = q.lower()
    elif r < .35:
        q = q.upper()
    if R.random() < .3:
        q = q.rstrip("?.")
    return q


def place_forms(d, lang):
    st = d["st"]; sname = ABBR[st]; sname_l = ST_ES.get(sname, sname) if lang == "es" else sname
    cap = " ".join(w.capitalize() for w in d["core"].split())
    forms = [f"{cap}, {st}", f"{cap} {sname_l}", f"{d['full']}", f"{d['full']}, {st}", f"{cap} in {sname_l}" if lang == "en" else f"{cap} en {sname_l}"]
    if d["unique"]:
        forms += [cap, cap, d["core"]]
    return forms


Q = {"en": [], "es": []}


def add(lang, q, exp, **kw):
    Q[lang].append(dict(q=style(q) if kw.pop("styled", True) else q, x=exp, **kw))


# ---------------------------------------------------------------- 1. one district, by name
for lang, n in (("en", 6200), ("es", 3800)):
    keys = list(TOP[lang])
    for _ in range(n):
        d = R.choice(DIST); k = R.choice(keys); t = R.choice(TOP[lang][k])
        p = R.choice(place_forms(d, lang))
        amb_ok = not d["unique"] and not re.search(r"(,\s*[A-Z]{2}\b|\b(" + "|".join(re.escape(x) for x in (ABBR[d["st"]], ST_ES.get(ABBR[d["st"]], "")) if x) + r")\b)", p, re.I)
        if R.random() < .12:  # misspell the district name
            ws = p.split(); j = max(range(len(ws)), key=lambda x: len(ws[x])); ws[j] = typo(ws[j]); p = " ".join(ws)
        tpl = R.choice(T_DIST[lang]) if t else "{p}"
        q = tpl.format(t=t, T=t[:1].upper() + t[1:], p=p).replace("  ", " ").strip(" :-")
        add(lang, q, "district", ok=d["ok"], topic=k, amb_ok=bool(amb_ok))

# ---------------------------------------------------------------- 2. one district, by ZIP code
for lang, n in (("en", 700), ("es", 400)):
    for z, lid in ZIP1[:n]:
        k = R.choice(list(TOP[lang])); t = R.choice(TOP[lang][k])
        tpl = R.choice(T_DIST[lang]) if t else "{p}"
        add(lang, tpl.format(t=t, T=t[:1].upper() + t[1:], p=z), "district", ok=[lid], topic=k)

# ---------------------------------------------------------------- 3. compare districts
for lang, n in (("en", 1500), ("es", 900)):
    for _ in range(n):
        st = R.choice([d["st"] for d in DIST])
        same = [d for d in DIST if d["st"] == st]
        picks = R.sample(same, min(3, len(same))) if len(same) >= 2 and R.random() < .6 else R.sample(DIST, 3)
        k = R.choice([x for x in TOP[lang] if x != "_overview"]); t = R.choice(TOP[lang][k])
        def nm(d):
            cap = " ".join(w.capitalize() for w in d["core"].split())
            return cap + (", " + d["st"] if not d["unique"] or R.random() < .5 else "")
        tpl = R.choice(T_CMP[lang])
        q = tpl.format(a=nm(picks[0]), b=nm(picks[1]), c=nm(picks[2]) if len(picks) > 2 else nm(picks[0]), t=t)
        want = 3 if "{c}" in tpl else 2
        add(lang, q, "compare", oks=[d["ok"] for d in picks[:want]], topic=k)

# ---------------------------------------------------------------- 4. states, several states, the nation
for lang, n in (("en", 1100), ("es", 700)):
    for _ in range(n):
        st = R.choice(MAIN_STATES); sname = ABBR[st]; sl = ST_ES.get(sname, sname) if lang == "es" else sname
        k = R.choice([x for x in TOP[lang] if not x.startswith("_")]); t = R.choice(TOP[lang][k])
        s = R.choice([sl, sl, sl.lower(), st]) if lang == "en" else R.choice([sl, sl.lower()])
        add(lang, R.choice(T_STATE[lang]).format(t=t, T=t[:1].upper() + t[1:], s=s), "state", st=st, topic=k)
for lang, n in (("en", 450), ("es", 300)):
    for _ in range(n):
        ss = R.sample(MAIN_STATES, 3); nm = [ST_ES.get(ABBR[x], ABBR[x]) if lang == "es" else ABBR[x] for x in ss]
        k = R.choice([x for x in TOP[lang] if not x.startswith("_")]); t = R.choice(TOP[lang][k])
        tpl = R.choice(T_STATES[lang])
        add(lang, tpl.format(s1=nm[0], s2=nm[1], s3=nm[2], t=t), "states", sts=ss[:3 if "{s3}" in tpl else 2], topic=k)
for lang, n in (("en", 500), ("es", 350)):
    for _ in range(n):
        k = R.choice([x for x in TOP[lang] if not x.startswith("_")]); t = R.choice(TOP[lang][k])
        add(lang, R.choice(T_NATION[lang]).format(t=t, T=t[:1].upper() + t[1:]), "nation", topic=k)

# ---------------------------------------------------------------- 5. words and definitions (answered from the glossary)
TERMS = {
 "en": {"iep": ["IEP", "an IEP", "individualized education program"], "504": ["a 504 plan", "504", "section 504"], "idea": ["IDEA", "the IDEA law", "individuals with disabilities education act"],
        "fape": ["FAPE", "free appropriate public education"], "lre": ["LRE", "least restrictive environment"], "iee": ["an IEE", "independent educational evaluation"],
        "pwn": ["prior written notice", "PWN"], "ps": ["procedural safeguards"], "md": ["a manifestation determination", "manifestation determination review", "MDR"],
        "cf": ["child find"], "rs": ["related services"], "sas": ["supplementary aids and services"], "ts": ["transition services", "a transition plan"],
        "cop": ["continuum of placements"], "sc": ["a state complaint"], "med": ["mediation"], "dp": ["due process", "a due process complaint"],
        "rm": ["a resolution meeting", "resolution session"], "team": ["the IEP team"], "pti": ["a parent training and information center", "PTI"],
        "crdc": ["CRDC", "the civil rights data collection"], "cc": ["child count"], "restr": ["restraint", "physical restraint"], "secl": ["seclusion"],
        "per100": ["per 100"], "median": ["the median", "typical district"], "sig": ["significant disproportionality"], "det": ["a state determination", "meets requirements"],
        "spp": ["SPP/APR", "the state performance plan"], "osep": ["OSEP"], "eval": ["an evaluation", "a special education evaluation"],
        "esy": ["ESY", "extended school year", "summer services"], "fba": ["an FBA", "functional behavioral assessment", "a behavior assessment"],
        "bip": ["a BIP", "a behavior plan", "behavioral intervention plan"], "iaes": ["an interim alternative educational setting", "IAES"],
        "stay": ["stay put", "the stay put rule"], "acc": ["accommodations", "an accommodation"], "mod": ["modifications", "a modified curriculum"],
        "at": ["assistive technology", "assistive tech"], "sdi": ["specially designed instruction", "SDI"], "ifsp": ["an IFSP", "individualized family service plan"],
        "lea": ["LEA", "the LEA representative"], "para": ["a paraprofessional", "a para"], "ohi": ["OHI", "other health impairment"], "pl": ["present levels", "PLAAFP"]},
 "es": {"iep": ["IEP", "un IEP", "programa de educación individualizado"], "504": ["un plan 504", "504", "la sección 504"], "idea": ["IDEA", "la ley IDEA"],
        "fape": ["FAPE", "educación pública gratuita y apropiada"], "lre": ["LRE", "ambiente menos restrictivo"], "iee": ["una evaluación educativa independiente", "IEE"],
        "pwn": ["aviso previo por escrito"], "ps": ["garantías procesales"], "md": ["determinación de manifestación"], "cf": ["búsqueda de niños", "child find"],
        "rs": ["servicios relacionados"], "ts": ["servicios de transición"], "sc": ["una queja estatal"], "med": ["mediación"], "dp": ["debido proceso", "una queja de debido proceso"],
        "rm": ["una reunión de resolución"], "pti": ["centro de información y capacitación para padres"], "crdc": ["CRDC"], "restr": ["inmovilización física", "sujeción"],
        "secl": ["aislamiento"], "per100": ["por cada 100"], "median": ["la mediana", "distrito típico"], "sig": ["desproporcionalidad significativa"], "osep": ["OSEP"],
        "eval": ["una evaluación"], "esy": ["ESY", "año escolar extendido", "servicios de verano"], "fba": ["una FBA", "evaluación funcional de la conducta"],
        "bip": ["un BIP", "un plan de conducta"], "acc": ["adaptaciones", "acomodaciones"], "mod": ["modificaciones"], "at": ["tecnología de asistencia", "tecnología asistiva"],
        "ifsp": ["un IFSP"], "para": ["un paraprofesional"], "ohi": ["otro impedimento de salud"], "pl": ["niveles actuales"], "stay": ["stay put"]}}
T_DEF = {"en": ["what is {x}", "what is {x}?", "what's {x}", "whats {x}", "what does {x} mean", "define {x}", "{x} meaning", "explain {x}", "{x} definition",
                "can you explain {x}", "what does {x} stand for", "i dont understand {x}", "meaning of {x}", "what exactly is {x}"],
         "es": ["¿qué es {x}?", "que es {x}", "¿qué significa {x}?", "que significa {x}", "definición de {x}", "explíqueme {x}", "no entiendo {x}", "significado de {x}"]}
for lang, n in (("en", 1600), ("es", 1000)):
    for _ in range(n):
        key = R.choice(list(TERMS[lang])); x = R.choice(TERMS[lang][key])
        add(lang, R.choice(T_DEF[lang]).format(x=x), "definition", term=key)
for q in ["difference between iep and 504", "iep vs 504", "504 or iep which is better", "is a 504 the same as an iep", "504 plan vs IEP difference"]:
    add("en", q, "definition", term="504")
for q in ["diferencia entre IEP y 504", "iep o 504", "¿es lo mismo un 504 que un IEP?"]:
    add("es", q, "definition", term="504")

# ---------------------------------------------------------------- 6. the site itself (meta questions)
META = {
 "en": {"about": ["where does the data come from", "where is this data from", "is this data accurate", "how often is it updated", "data sources", "how reliable is this", "what are your sources"],
        "years": ["what year is this data", "how old is the data", "is this data current", "what school year"],
        "download": ["can i download the data", "download csv", "is there an excel file", "raw data download", "is there an api"],
        "report": ["make a report for my district", "printable report", "can i print this", "make a pdf"],
        "history": ["history of special education", "special education since 1975", "how has special education changed over the decades"],
        "embed": ["can i embed this on my website", "widget for my site"],
        "contact": ["how do i contact you", "who can i talk to", "email the author"],
        "who": ["who made this", "who built this site", "who is behind idea atlas"],
        "help": ["help", "what can i ask", "how does this work", "what can you do", "examples", "how do i use this"],
        "greet": ["hi", "hello", "hey there", "good morning"],
        "thanks": ["thanks", "thank you!", "thx", "ok", "great"],
        "error": ["this number is wrong", "the data for my district is incorrect", "i found a mistake"],
        "missing": ["why is the data missing", "why is it blank", "why no data for my district", "what does withheld mean"],
        "spanish": ["in spanish please", "spanish version", "español"],
        "rank": ["which district is the best", "best school district in texas for special ed", "rank districts in new jersey", "what is the worst district"]},
 "es": {"about": ["de donde vienen los datos", "¿son confiables estos datos?", "¿con qué frecuencia se actualiza?", "fuentes de los datos"],
        "years": ["¿de qué año son los datos?", "que tan recientes son los datos"],
        "download": ["¿puedo descargar los datos?", "descargar en excel", "datos en bruto"],
        "report": ["hacer un informe de mi distrito", "informe para imprimir", "imprimir"],
        "history": ["historia de la educación especial", "desde 1975"],
        "embed": ["insertar en mi sitio web"],
        "contact": ["¿cómo me comunico con usted?", "contacto"],
        "who": ["¿quién hizo esto?", "quien creo idea atlas"],
        "help": ["ayuda", "¿qué puedo preguntar?", "¿cómo funciona?", "ejemplos"],
        "greet": ["hola", "buenos días", "buenas tardes"],
        "thanks": ["gracias", "muchas gracias", "perfecto"],
        "error": ["este dato está equivocado", "hay un error en mi distrito"],
        "missing": ["¿por qué faltan datos?", "¿por qué está en blanco?", "no hay datos para mi distrito"],
        "spanish": ["en inglés", "english version"],
        "rank": ["¿cuál es el mejor distrito?", "el peor distrito de california", "ranking de distritos"]}}
for lang in META:
    for k, qs in META[lang].items():
        for q in qs:
            for _ in range(4):
                add(lang, q, "info", intent=k)

# ---------------------------------------------------------------- 7. data the atlas does not have
UNS = {"en": ["test scores", "reading scores", "teacher ratio", "class size", "bus transportation", "bullying", "attendance", "chronic absenteeism", "teacher salaries",
              "private school tuition", "vouchers", "school ratings", "covid", "lunch menu", "graduation date", "school start time", "how many teachers"],
       "es": ["calificaciones de exámenes", "tamaño de la clase", "transporte escolar", "acoso escolar", "asistencia", "salario de maestros", "escuela privada", "menú del almuerzo"]}
for lang, n in (("en", 500), ("es", 250)):
    for _ in range(n):
        u = R.choice(UNS[lang]); d = R.choice(DIST) if R.random() < .6 else None
        p = (R.choice(place_forms(d, lang)) if d else "")
        q = (f"{u} in {p}" if lang == "en" else f"{u} en {p}") if p else u
        add(lang, q, "unsupported")

# ---------------------------------------------------------------- 8. off topic and nonsense: a friendly prompt, never a district's figures
OFF = {"en": ["what's the weather in boston", "who won the super bowl", "best pizza near me", "tell me a joke", "what is the capital of france", "stock price of apple",
              "how do i cook rice", "asdfghjkl", "???", "lol", "test", "123", "what time is it", "how old are you", "are you a robot", "write me a poem",
              "who is the president", "my cat is sick", "recommend a movie", "translate hello to french", "ksjdhf ksjdhf", "zzzz", "bananas", "the quick brown fox",
              "how tall is mount everest", "play music", "open netflix", "sports scores tonight", "hotels in miami", "flights to denver"],
       "es": ["¿qué tiempo hace en miami?", "cuéntame un chiste", "receta de arroz", "quién ganó el partido", "asdf", "jaja", "hola que tal estas tu", "precio del dólar",
              "¿cuál es la capital de francia?", "pon música", "hoteles en orlando", "vuelos a chicago", "mi perro está enfermo", "escríbeme un poema"]}
for lang in OFF:
    for q in OFF[lang]:
        for _ in range(6):
            add(lang, q, "offtopic")

# ---------------------------------------------------------------- 9. family situations (hand-written; optionally with a place)
sit = ROOT / "ops" / "ask_situations.json"
if sit.exists():
    S = json.loads(sit.read_text())
    WHO = {"en": ["", "", "in {p}", "we are in {p}.", "({p})"], "es": ["", "", "en {p}", "estamos en {p}."]}
    for lang in ("en", "es"):
        for it in S[lang]:
            add(lang, it["q"], "situation", rels=it["rels"], styled=False)
            for _ in range(2):
                d = R.choice(DIST); w = R.choice(WHO[lang])
                q = it["q"]
                if w:
                    q = q.rstrip(" .?!") + ". " + w.format(p=R.choice(place_forms(d, lang)))
                add(lang, q, "situation", rels=it["rels"])

for lang in Q:
    seen, out = set(), []
    for it in Q[lang]:
        if it["q"].lower() in seen:
            continue
        seen.add(it["q"].lower()); out.append(it)
    Q[lang] = out
tot = sum(len(v) for v in Q.values())
print({lang: len(v) for lang, v in Q.items()}, "total", tot, file=sys.stderr)
from collections import Counter
for lang in Q:
    print(lang, dict(Counter(it["x"] for it in Q[lang])), file=sys.stderr)
with gzip.open(ROOT / "ops" / "ask_corpus.json.gz", "wt") as f:
    json.dump(Q, f, ensure_ascii=False)
