"""State measures for the report assistant: selected IDEA Part B SPP/APR indicators (FFY 2022) and dispute resolution counts (2023-24).
Input: the unchanged federal files in RAW. Output: build/history/state_measures.json (one small table per state)."""
import json
import statistics
import sys
from pathlib import Path

import pandas as pd

RAW = Path(sys.argv[1] if len(sys.argv) > 1 else "/home/claude/hist/raw/state")
OUT = Path(__file__).resolve().parent.parent / "build" / "history" / "state_measures.json"
STATES = set("AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split())
Y22 = "2021–22"

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
                st.setdefault(ab, {})[key] = [round(float(v), 1), Y22]
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
    for key, *_ in SPP:
        vals = [s[key][0] for s in st.values() if key in s]
        if len(vals) > 20:
            nat[key] = round(statistics.median(vals), 1)
    ind = [{"k": k, "en": en, "es": es, "u": "pct", **({"nl": n[0], "nl_es": n[1], "note": n[2], "note_es": n[3]} if n else {})} for k, _, _, en, es, n in SPP]
    ind += [{"k": k, "en": en, "es": es, "u": "n"} for k, _, en, es in DISPUTE]
    ind[-1]["nl"], ind[-1]["nl_es"] = "Disagreements", "Desacuerdos"
    ind[-1]["note"] = "Counts of disagreements for the whole state. They depend on the state's size and its own procedures."
    ind[-1]["note_es"] = "Cantidades de desacuerdos en todo el estado. Dependen del tamaño del estado y de sus propios procedimientos."
    out = {"ind": ind, "st": st, "nat": nat,
           "source": "Sources: U.S. Department of Education, Office of Special Education Programs: IDEA Part B State Performance Plan / Annual Performance Report indicator data files B7, B13, and B14 (FFY 2022, mostly the 2021–22 school year); IDEA Part B Dispute Resolution state data file, 2023–24.",
           "source_es": "Fuentes: Departamento de Educación de EE. UU., Oficina de Programas de Educación Especial: archivos de indicadores del Plan de Desempeño Estatal / Informe Anual de Desempeño de IDEA Parte B, B7, B13 y B14 (año fiscal federal 2022, en su mayoría el año escolar 2021–22); archivo estatal de resolución de disputas de IDEA Parte B, 2023–24."}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(len(st), "states;", OUT.stat().st_size, "bytes; NJ:", st.get("NJ"), "; medians:", nat)


if __name__ == "__main__":
    main()
