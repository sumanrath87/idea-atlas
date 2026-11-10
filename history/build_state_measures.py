"""State measures for the report assistant: selected IDEA Part B SPP/APR indicators (FFY 2022) and dispute resolution counts (2023-24).
Input: the unchanged federal files in RAW. Output: build/history/state_measures.json (one small table per state)."""
import json
import statistics
import sys
from pathlib import Path

import re

import pandas as pd

RAW = Path(sys.argv[1] if len(sys.argv) > 1 else "raw/state")
APR = Path(sys.argv[2] if len(sys.argv) > 2 else "raw/apr")   # each state's FFY 2024 SPP/APR, as text (pdftotext -layout)
Y24 = "2024–25"   # FFY 2024 covers the 2024–25 school year (indicators 8, 11, 12)
APR_IND = [  # key, indicator number, English, Spanish, note label (en, es), note (en, es)
    ("b8", "8", "Parents of children with IEPs who said the school helped them take part in their child's education",
     "Padres de niños con IEP que dijeron que la escuela les ayudó a participar en la educación de su hijo",
     ("Parent involvement", "Participación de los padres",
      "Each state uses its own survey and scoring, and how many parents answer differs a great deal, so this figure is best compared with the same state over time.",
      "Cada estado usa su propia encuesta y puntuación, y la cantidad de padres que responde varía mucho, así que conviene comparar esta cifra con el mismo estado a lo largo del tiempo.")),
    ("b11", "11", "Children evaluated within 60 days of the parent's consent, or within the state's own timeline",
     "Niños evaluados dentro de 60 días después del permiso de los padres, o dentro del plazo del estado", None),
    ("b12", "12", "Children moving from early intervention who had an IEP in place by their third birthday",
     "Niños que pasan de la intervención temprana y tenían un IEP en marcha al cumplir 3 años",
     ("Timely evaluations and services", "Evaluaciones y servicios a tiempo",
      "For these two measures, the federal target is 100%.", "Para estas dos medidas, la meta federal es 100 %.")),
]
# Two tables the reader cannot parse, checked by hand against their counts.
APR_FIXED = {("IA", "8"): 92.0,      # 4,361 of 4,740 respondent parents; no FFY 2023 figure (new baseline)
             ("MS", "12"): 69.04}    # 252 of 365 children


def read_apr():
    """The FFY 2024 figure in each indicator's "FFY 2024 SPP/APR Data" table: the third percentage on the data row (FFY 2023, target, FFY 2024)."""
    pct, out = re.compile(r"(\d{1,3}(?:\.\d+)?)%"), {}
    for f in sorted(APR.glob("apr_*_FFY24.txt")):
        st, L = f.name.split("_")[1], f.read_text(errors="ignore").split("\n")
        for _, ind, *_ in APR_IND:
            v = APR_FIXED.get((st, ind))
            if v is None:
                try:
                    i = next(k for k, l in enumerate(L) if re.match(rf"^\s*{ind} - Indicator Data", l))
                    j = next(k for k in range(i, len(L)) if "FFY 2024 SPP/APR Data" in L[k])
                    v = next(float(p[2]) for k in range(j + 1, min(j + 40, len(L))) if len(p := pct.findall(L[k])) >= 3)
                except StopIteration:
                    continue
            out.setdefault(st, {})[ind] = v
    return out
OUT = Path(__file__).resolve().parent.parent / "build" / "history" / "state_measures.json"
STATES = set("AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split())
Y22 = "2022–23"   # FFY 2022 covers the 2022–23 school year (B7, B13)
Y22_LEFT = "2021–22"   # B14 (FFY 2022): young people who left high school in 2021–22

SPP = [  # key, file, code, English, Spanish, note (en, es)
    ("b7a", "B07", "B07A2CFFY", "Preschool children with IEPs at age expectations in social relationships when they left preschool",
     "Niños de preescolar con IEP al nivel esperado para su edad en relaciones sociales al salir del preescolar", None),
    ("b7b", "B07", "B07B2CFFY", "Preschool children with IEPs at age expectations in early learning, language, and literacy when they left preschool",
     "Niños de preescolar con IEP al nivel esperado para su edad en aprendizaje temprano, lenguaje y lectoescritura al salir del preescolar", None),
    ("b7c", "B07", "B07C2CFFY", "Preschool children with IEPs at age expectations in meeting their own needs when they left preschool",
     "Niños de preescolar con IEP al nivel esperado para su edad en atender sus propias necesidades al salir del preescolar",
     ("Preschool outcomes", "Resultados del preescolar", "States measure preschool outcomes in different ways, so figures are best compared with the same state over time.",
      "Los estados miden los resultados del preescolar de formas distintas, así que conviene comparar las cifras con el mismo estado a lo largo del tiempo.")),
    ("b13", "B13", "B13CFFY", "IEPs of youth 16 and older that include every required part of transition planning",
     "IEP de jóvenes de 16 años o más que incluyen todas las partes requeridas de la planificación de la transición",
     ("Transition planning", "Planificación de la transición", "States check a sample of IEPs through their own monitoring.", "Los estados revisan una muestra de IEP mediante su propio monitoreo.")),
    ("b14a", "B14", "B14ACFFY", "Youth with IEPs enrolled in higher education within a year of leaving high school",
     "Jóvenes con IEP inscritos en educación superior dentro de un año después de salir de la secundaria", None),
    ("b14b", "B14", "B14BCFFY", "Youth with IEPs in higher education or a competitive job within a year of leaving high school",
     "Jóvenes con IEP en educación superior o en un empleo competitivo dentro de un año después de salir de la secundaria", None),
    ("b14c", "B14", "B14CCFFY", "Youth with IEPs in any education, training, or job within a year of leaving high school",
     "Jóvenes con IEP en cualquier educación, capacitación o empleo dentro de un año después de salir de la secundaria",
     ("Life after school", "La vida después de la escuela", "Life-after-school figures come from a survey of young people about a year after they left school; how many respond differs by state.",
      "Las cifras de la vida después de la escuela vienen de una encuesta a los jóvenes un año después de salir; la cantidad de respuestas varía por estado.")),
]
DISPUTE = [("dwsc", 2, "Written complaints filed with the state", "Quejas escritas presentadas ante el estado"),
           ("dmed", 10, "Mediation requests", "Solicitudes de mediación"),
           ("ddpc", 18, "Due process complaints", "Quejas de debido proceso"),
           ("dhear", 21, "Due process hearings held to a decision", "Audiencias de debido proceso que llegaron a una decisión")]


def read_spp(code):
    f = next(RAW.glob(f"spp_{code}_FFY*.xlsx"))
    x = pd.read_excel(f, header=None)
    h = x.index[x[7].astype(str) == "FFY Name"][0]
    d = pd.read_excel(f, header=h)
    return d[d["FFY Name"] == 2022]


def main():
    st, names = {}, {}
    for key, code, abbr, *_ in SPP:
        d = read_spp(code)
        d = d[d.SurveyDataAbbrv == abbr]
        for _, r in d.iterrows():
            ab = str(r["State Postal Code"]).strip()
            names[str(r["State Name"]).strip().lower()] = ab
            v = pd.to_numeric(r["Data"], errors="coerce")
            if ab in STATES and pd.notna(v):
                st.setdefault(ab, {})[key] = [round(float(v) + 1e-9, 1), Y22_LEFT if key.startswith("b14") else Y22]
    apr = read_apr()
    for ab, v in apr.items():
        for key, ind, *_ in APR_IND:
            if ab in STATES and ind in v:
                st.setdefault(ab, {})[key] = [round(v[ind] + 1e-9, 1), Y24]
    dd = pd.read_excel(next(RAW.glob("dispute_*.xlsx")), 0, header=None)
    for i in range(6, len(dd)):
        ab = names.get(str(dd.iloc[i, 1]).strip().lower())
        if ab not in STATES:
            continue
        for key, col, *_ in DISPUTE:
            v = pd.to_numeric(dd.iloc[i, col], errors="coerce")
            if pd.notna(v):
                st.setdefault(ab, {})[key] = [int(v), "2023–24"]
    nat = {}
    for key, *_ in APR_IND + SPP:
        vals = [s[key][0] for s in st.values() if key in s]
        if len(vals) > 20:
            nat[key] = round(statistics.median(vals), 1)
    ind = [{"k": k, "en": en, "es": es, "u": "pct", **({"nl": n[0], "nl_es": n[1], "note": n[2], "note_es": n[3]} if n else {})} for k, _, en, es, n in APR_IND]
    ind += [{"k": k, "en": en, "es": es, "u": "pct", **({"nl": n[0], "nl_es": n[1], "note": n[2], "note_es": n[3]} if n else {})} for k, _, _, en, es, n in SPP]
    ind += [{"k": k, "en": en, "es": es, "u": "n"} for k, _, en, es in DISPUTE]
    ind[-1]["nl"], ind[-1]["nl_es"] = "Disagreements", "Desacuerdos"
    ind[-1]["note"] = "Counts of disagreements for the whole state. They depend on the state's size and its own procedures."
    ind[-1]["note_es"] = "Cantidades de desacuerdos en todo el estado. Dependen del tamaño del estado y de sus propios procedimientos."
    out = {"ind": ind, "st": st, "nat": nat,
           "source": "Sources: U.S. Department of Education, Office of Special Education Programs: each state's IDEA Part B State Performance Plan and Annual Performance Report for federal fiscal year 2024 (indicators 8, 11, and 12; the 2024–25 school year); the federal data files for indicators 7, 13, and 14 (federal fiscal year 2022: the 2022–23 school year, and for indicator 14, young people who left high school in 2021–22); IDEA Part B dispute resolution data for each state, 2023–24.",
           "source_es": "Fuentes: Departamento de Educación de EE. UU., Oficina de Programas de Educación Especial: el Plan de Desempeño Estatal y el Informe Anual de Desempeño de IDEA Parte B de cada estado para el año fiscal federal 2024 (indicadores 8, 11 y 12; año escolar 2024–25); los archivos de datos federales de los indicadores 7, 13 y 14 (año fiscal federal 2022: el año escolar 2022–23 y, para el indicador 14, jóvenes que salieron de la escuela secundaria en 2021–22); datos de resolución de disputas de IDEA Parte B de cada estado, 2023–24."}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(len(st), "states;", OUT.stat().st_size, "bytes; NJ:", st.get("NJ"), "; medians:", nat)


if __name__ == "__main__":
    main()
