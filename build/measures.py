"""Measure and source definitions for IDEA Atlas. One place for every label,
so the map, table, district pages, download, and methods page always agree."""

VERSION = "2026.1"
import os
BASE = os.environ.get("ATLAS_BASE", "/tools/idea-atlas/")
SITE = "https://www.sumanrath.org"
ATLAS_ORIGIN = os.environ.get("ATLAS_ORIGIN", SITE)  # where the atlas itself lives, for canonical links and citations

SOURCES = {
    "ccd": ("Common Core of Data, district directory and enrollment", "2024–25", "National Center for Education Statistics"),
    "idea_cc": ("IDEA Part B child count, by district", "2024–25", "U.S. Department of Education, Office of Special Education Programs"),
    "idea_env": ("IDEA Part B educational environments, by district", "2024–25", "U.S. Department of Education, Office of Special Education Programs"),
    "idea_exit": ("IDEA Part B exiting, by district", "2023–24", "U.S. Department of Education, Office of Special Education Programs"),
    "crdc": ("Civil Rights Data Collection", "2023–24", "U.S. Department of Education, Office for Civil Rights"),
    "fin": ("Annual Survey of School System Finances", "FY2024", "U.S. Census Bureau"),
    "saipe": ("Small Area Income and Poverty Estimates, school districts", "2024", "U.S. Census Bureau"),
    "det": ("Determination letters on state implementation of IDEA", "2026", "U.S. Department of Education, Office of Special Education Programs"),
    "edge": ("School district boundaries and ZIP code relationship files", "2024–25", "National Center for Education Statistics, EDGE"),
}

# unit: per100 = per 100 students in the group; usd = dollars
# group order is the order on district pages and in the map menu.
MEASURES = [
    # key, group, label, short label, unit, source, denominator note
    ("id_rate", "Who is served", "Students with IEPs served by the district, per 100 enrolled",
     "Students with IEPs", "per100", "idea_cc", "All students enrolled. The IDEA count also includes some children the district serves who are not enrolled, such as preschoolers and students placed in private schools by their parents."),
    ("pct_504", "Who is served", "Students with Section 504 plans, per 100 enrolled",
     "Section 504 plans", "per100", "crdc", "All students enrolled (civil rights count)."),
    ("env_80plus", "Where students learn", "In a general class 80% or more of the school day",
     "General class 80%+", "per100", "idea_env", "Students with IEPs, ages 5 (in kindergarten) through 21."),
    ("env_lt40", "Where students learn", "In a general class less than 40% of the school day",
     "General class under 40%", "per100", "idea_env", "Students with IEPs, ages 5 (in kindergarten) through 21."),
    ("env_separate", "Where students learn", "In a separate school, residential facility, or homebound or hospital setting",
     "Separate settings", "per100", "idea_env", "Students with IEPs, ages 5 (in kindergarten) through 21."),
    ("grad_regular", "Leaving school", "Left school with a regular high school diploma",
     "Regular diploma", "per100", "idea_exit", "Students with IEPs, ages 14 to 21, who left school during the year."),
    ("dropout", "Leaving school", "Left school by dropping out",
     "Dropped out", "per100", "idea_exit", "Students with IEPs, ages 14 to 21, who left school during the year."),
    ("oos_idea", "Discipline and safety", "Received one or more out-of-school suspensions, students with IEPs",
     "Suspension, IEP", "per100", "crdc", "Students with IEPs (civil rights count)."),
    ("oos_nodis", "Discipline and safety", "Received one or more out-of-school suspensions, students without disabilities",
     "Suspension, no disability", "per100", "crdc", "Students without disabilities."),
    ("oos_504", "Discipline and safety", "Received one or more out-of-school suspensions, students with Section 504 plans",
     "Suspension, 504", "per100", "crdc", "Students with Section 504 plans."),
    ("expulsion_idea", "Discipline and safety", "Expelled, students with IEPs",
     "Expulsion, IEP", "per100", "crdc", "Students with IEPs (civil rights count)."),
    ("restraint_physical_idea", "Discipline and safety", "Physically restrained, students with IEPs",
     "Physical restraint", "per100", "crdc", "Students with IEPs (civil rights count)."),
    ("restraint_mechanical_idea", "Discipline and safety", "Mechanically restrained, students with IEPs",
     "Mechanical restraint", "per100", "crdc", "Students with IEPs (civil rights count)."),
    ("seclusion_idea", "Discipline and safety", "Secluded, students with IEPs",
     "Seclusion", "per100", "crdc", "Students with IEPs (civil rights count)."),
    ("referral_idea", "Discipline and safety", "Referred to law enforcement, students with IEPs",
     "Referral to police", "per100", "crdc", "Students with IEPs (civil rights count)."),
    ("arrest_idea", "Discipline and safety", "School-related arrest, students with IEPs",
     "School-related arrest", "per100", "crdc", "Students with IEPs (civil rights count)."),
    ("spend_per_pupil", "Funding", "Current spending per student",
     "Spending per student", "usd", "fin", "Students enrolled in the fall (finance survey count)."),
    ("idea_federal_per_student", "Funding", "Federal IDEA money per student with an IEP",
     "Federal IDEA per student", "usd", "fin", "Students with IEPs (IDEA count). Federal IDEA money reaches districts through the state."),
    ("child_poverty", "Community", "Children ages 5 to 17 living in poverty, per 100",
     "Child poverty", "per100", "saipe", "Children ages 5 to 17 living in the district's area."),
]

CATEGORIES = [
    ("cat_learning", "Specific learning disability"),
    ("cat_speech", "Speech or language impairment"),
    ("cat_other_health", "Other health impairment"),
    ("cat_autism", "Autism"),
    ("cat_intellectual", "Intellectual disability"),
    ("cat_emotional", "Emotional disturbance"),
    ("cat_developmental_delay", "Developmental delay"),
]

# status word -> (code used in data files, how it reads on the site)
STATUS = {
    "ok": ("0", ""),
    "ok_partial": ("1", "at least"),
    "ok_minimum": ("1", "at least"),
    "hidden": ("2", "Withheld for privacy"),
    "small_group": ("3", "Fewer than 10 students"),
    "quality": ("4", "Flagged for data quality"),
    "not_reported": ("5", "Not reported"),
    "none": ("6", "No students in this group"),
}
STATUS_TEXT = {code: text for code, text in STATUS.values()}

MAP_MEASURES = [m[0] for m in MEASURES if m[0] not in ("oos_504", "restraint_mechanical_idea")]

# Plain notes for states whose reporting differs. Shown on district pages, the table, and the methods page.
STATE_NOTES = {
    "CO": ("In Colorado, IDEA figures are reported by administrative units, not by each district. Many administrative units "
           "serve several districts (for example, a BOCES). Search for the administrative unit that serves this area to see its IDEA figures."),
    "WY": ("Wyoming's 2024–25 district counts of students with IEPs were flagged by the U.S. Department of Education for data quality, "
           "so they are not shown. Other Wyoming figures are shown when available."),
}

# ---------------------------------------------------------------- plain words
# Short explainers, shown as "What is ...?" buttons next to the term. Plain, neutral, and accurate.
TERMS = {
    "idea": ("What is IDEA?",
             "The Individuals with Disabilities Education Act (IDEA) is the federal law that guarantees a free appropriate public education "
             "to children with disabilities, from age 3 through 21. States and districts report data about it every year."),
    "iep": ("What is an IEP?",
            "An Individualized Education Program (IEP) is a written plan for a student who qualifies for special education under IDEA. "
            "The family and school team write it together. It lists the student's goals and the services and supports the school will provide."),
    "504": ("What is a Section 504 plan?",
            "Section 504 of the Rehabilitation Act protects students with disabilities from discrimination. A 504 plan lists supports, "
            "such as extra time or an accessible seat, for a student who needs them to take part fully in school. Students with IEPs are not counted here."),
    "per100": ("Why “per 100”?",
               "Showing figures per 100 students lets you read a small district and a large one the same way. "
               "For example, 15 per 100 means about 15 of every 100 students in that group."),
    "median": ("What is a median?",
               "The median is the middle district: half of districts have a higher figure and half have a lower one. "
               "It gives context. It is not a target or a grade."),
    "middle": ("What is the middle half?",
               "Line up every district in the state from lowest to highest and set aside the lowest quarter and the highest quarter. "
               "The middle half is the range that is left (the 25th to the 75th percentile). A figure outside it is less common in that state, not necessarily better or worse."),
    "typical": ("What does “typical district” mean?",
                "On this site, the typical district is the median: the district in the middle when all districts in the state, or the nation, are lined up from lowest to highest."),
    "categories": ("What are the federal categories?",
                   "IDEA names 13 disability categories, plus developmental delay for young children. A student is counted in one category. "
                   "The names are the federal terms used in the reports, not descriptions of any one child."),
    "settings": ("What do the learning settings mean?",
                 "IDEA asks how much of the school day each student with an IEP spends in a general class with classmates without disabilities. "
                 "Separate settings are separate schools, residential facilities, and homebound or hospital settings."),
    "leaving": ("How is “leaving school” counted?",
                "Each year districts report how students with IEPs, ages 14 to 21, left school: with a regular diploma, with another certificate, "
                "by reaching the maximum age for services, or by dropping out. The figures are per 100 students who left that year."),
    "discipline": ("What do these discipline words mean?",
                   "Out-of-school suspension means a student was removed from school for at least half a day. Physical restraint means holding a student so they cannot move freely; "
                   "mechanical restraint uses a device to do so. Seclusion means keeping a student alone in a room they cannot leave. "
                   "Referral to law enforcement means a school reported a student to police; a school-related arrest happened at school or a school event. "
                   "The figures count students, not incidents."),
    "spending": ("What does spending per student include?",
                 "Current spending is the day-to-day cost of running schools, such as staff, services, and supplies. It leaves out building projects and debt. "
                 "It covers all students, not only students with IEPs."),
    "idea_money": ("What is federal IDEA money?",
                   "Each year Congress sends IDEA funds to states, and states pass most of it to districts. This figure is that federal money divided by the number of students with IEPs. "
                   "States and districts pay most special education costs from their own funds."),
    "poverty": ("How is child poverty estimated?",
                "The Census Bureau estimates how many children ages 5 to 17 live in families below the federal poverty line in each district's area. "
                "It counts children who live there, whether or not they attend the district's schools."),
    "status": ("Why are some figures missing?",
               "Agencies withhold small numbers to protect students' privacy, and a rate is not shown when fewer than 10 students are in the group. "
               "“At least” means part of a figure was withheld, so the true number is the same or higher. Missing figures are never estimated."),
    "detail_codes": ("How are missing values marked in the detail file?",
                     "Values are as reported. A blank cell was not reported. In the IDEA columns, -8 means withheld for privacy and -9 means flagged for data quality. "
                     "Civil rights columns have a matching status column (ok, ok_partial for a minimum, hidden, not_reported). Finance amounts are in thousands of dollars."),
    "rating": ("What are the state IDEA ratings?",
               "Each year the U.S. Department of Education reviews each state and gives one of four ratings: meets requirements, needs assistance, "
               "needs intervention, or needs substantial intervention. The rating is about the state, not any one district."),
    "years": ("Why are the school years different?",
              "Each federal source is released on its own schedule, so the newest available year differs. Every figure shows its own year."),
}

# Plain sentence for each measure. {v} is the formatted figure.
PLAIN = {
    "id_rate": "About {v} of every 100 students enrolled have an IEP served by the district.",
    "pct_504": "About {v} of every 100 students enrolled have a Section 504 plan.",
    "env_80plus": "About {v} of every 100 students with IEPs spend most of the day (80% or more) in a general class.",
    "env_lt40": "About {v} of every 100 students with IEPs spend less than 40% of the day in a general class.",
    "env_separate": "About {v} of every 100 students with IEPs learn in a separate school, residential facility, or homebound or hospital setting.",
    "grad_regular": "Of every 100 students with IEPs who left school, about {v} left with a regular high school diploma.",
    "dropout": "Of every 100 students with IEPs who left school, about {v} left by dropping out.",
    "oos_idea": "About {v} of every 100 students with IEPs received an out-of-school suspension.",
    "oos_nodis": "For students without disabilities, the figure was about {v} of every 100.",
    "oos_504": "For students with Section 504 plans, it was about {v} of every 100.",
    "expulsion_idea": "About {v} of every 100 students with IEPs were expelled.",
    "restraint_physical_idea": "About {v} of every 100 students with IEPs were physically restrained.",
    "restraint_mechanical_idea": "About {v} of every 100 students with IEPs were mechanically restrained.",
    "seclusion_idea": "About {v} of every 100 students with IEPs were secluded.",
    "referral_idea": "About {v} of every 100 students with IEPs were referred to law enforcement.",
    "arrest_idea": "About {v} of every 100 students with IEPs had a school-related arrest.",
    "spend_per_pupil": "The district spent about {v} per student on day-to-day costs.",
    "idea_federal_per_student": "It received about {v} in federal IDEA money for each student with an IEP.",
    "child_poverty": "About {v} of every 100 children ages 5 to 17 in the district's area live in poverty.",
}
