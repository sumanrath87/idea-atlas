"""Measure and source definitions for IDEA Atlas. One place for every label,
so the map, table, district pages, download, and methods page always agree."""

VERSION = "2026.1"
import os
BASE = os.environ.get("ATLAS_BASE", "/tools/idea-atlas/")
SITE = "https://www.sumanrath.org"

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
