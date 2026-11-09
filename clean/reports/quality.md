# Quality report

- District directory: 19,630 districts listed; 0 duplicate IDs; status counts: Open 19,281, Closed 114, New 101, Inactive 59, Future 57, Changed Boundary/Agency 15, Reopened 2, Added 1
- Enrollment file total types: Category Set A - By Race/Ethnicity; Sex; Grade (3,271,718); Derived - Subtotal by Race/Ethnicity and Sex minus Adult Education Count (278,220); Subtotal 4 - By Grade (235,426); Derived - Education Unit Total minus Adult Education Count (18,548); Education Unit Total (18,548)
- Combined record: New York City Public Schools (3620580) adds up 32 component districts for enrollment and IDEA counts; other sources report it as one district.
- IDEA child count 2024-25: 18,497 district rows; 0 duplicate IDs; total hidden: 242; national sum of reported totals (combined records not double-counted): 8,157,664
- Educational environments 2024-25: 18,497 rows. Separate settings combine: School Age Separate School; School Age Residential Facility; School Age Homebound/Hospital
- Civil rights data 2023-24: 17,591 districts from 97,094 schools. A count of -9 (skipped because the school reported none) is read as zero. Districts where at least one school withheld or did not report an item (figure shown as a minimum): 24
- Finance FY2024: 14,077 districts; federal IDEA revenue total $13.65 billion
- Child poverty 2024: 12,897 districts from 51 state files
- ZIP lookup: 33,789 ZIP code areas; 20,724 cover more than one district (the site will list all of them, largest share first)
- Map shapes 2024-25: 13,368 districts with a boundary; 13,224 of 19,631 listed districts have one (charter and specialty districts usually do not)

## Match rates (open districts)
Open or active districts: 19,401
- IDEA child count: ok 17,235, not_reported 1,865, hidden 242, quality 59
- Environments: ok 13,758, hidden 2,767, not_reported 1,956, small_group 493, none 420, quality 7
- Exiting: not_reported 5,559, ok 5,246, small_group 3,475, hidden 3,207, none 1,542, quality 372
- Civil rights: ok 16,408, not_reported 1,883, small_group 689, none 419, hidden 2
- Finance: ok 13,135, not_reported 5,387, small_group 879
- Child poverty: ok 12,777, not_reported 6,557, small_group 64, none 3

## Unusual values to look at
- Identification rate above 50 per 100 (often schools for the deaf or blind, or online schools): 159 (e.g. Arizona Department of Corrections (8336), AZ; Maricopa County Sheriffs Office (79540), AZ; Arizona State Schools for the Deaf and the Blind (6393), AZ; Edkey Inc. - Sequoia School for the Deaf and Hard (81050), AZ; Arizona Autism Charter Schools Inc. (91958), AZ)
- Suspension rate for students with IEPs above 100 (students counted in two suspension types): 6 (e.g. ELEVATE ACADEMY INC., ID; Adam/Brwn/Cass/Morgn/Pik/Sctt ROE, IL; Aurora Waasakone Community of Learn, MN; Mount Auburn Preparatory Academy, OH; GRAHAM-DUSTIN, OK)
- Civil rights IEP count differs from IDEA count by more than half (different school years or reporting): 515 (e.g. Hoover City, AL; Bullock County, AL; Cullman County, AL; Eufaula City, AL; Lawrence County, AL)
- Spending per pupil above $60,000: 104 (e.g. Aleutian Region School District, AK; Bristol Bay Borough School District, AK; Lake and Peninsula Borough School District, AK; Yukon Flats School District, AK; Northern Arizona Vocational Institute of Technolog (78786), AZ)
- Graduation share of 100 with 30 or more leavers: 125 (e.g. Mountain Brook City, AL; Cave Creek Unified District (4244), AZ; PINE BLUFF SCHOOL DISTRICT, AR; CONWAY SCHOOL DISTRICT, AR; NETTLETON SCHOOL DISTRICT, AR)

## Columns used from each source
`Combined Early Childhood and School Age Total`, `School Age All Disabilities`, `School Age Autism`, `School Age Emotional disturbance`, `School Age Intellectual disability`, `School Age Specific learning disability`, `School Age Speech or language impairment`, `School Age Other health impairment`, `School Age Developmental delay`, `School Age All Educational Environments`, `School Age Inside regular class 80% or more of the day`, `School Age Inside regular class less than 40% of the day`, `School Age Separate School`, `School Age Residential Facility`, `School Age Homebound/Hospital`, `All Disabilities Total Exiting School`, `All Disabilities Graduated With Regular High School Diploma`, `All Disabilities Dropped Out`, `TOT_ENR_M`, `TOT_ENR_F`, `TOT_ENR_X`, `TOT_IDEAENR_M`, `TOT_IDEAENR_F`, `TOT_IDEAENR_X`, `TOT_504ENR_M`, `TOT_504ENR_F`, `TOT_504ENR_X`, `TOT_DISCWDIS_SINGOOS_IDEA_M`, `TOT_DISCWDIS_SINGOOS_IDEA_F`, `TOT_DISCWDIS_SINGOOS_IDEA_X`, `TOT_DISCWDIS_MULTOOS_IDEA_M`, `TOT_DISCWDIS_MULTOOS_IDEA_F`, `TOT_DISCWDIS_MULTOOS_IDEA_X`, `TOT_DISCWODIS_SINGOOS_M`, `TOT_DISCWODIS_SINGOOS_F`, `TOT_DISCWODIS_SINGOOS_X`, `TOT_DISCWODIS_MULTOOS_M`, `TOT_DISCWODIS_MULTOOS_F`, `TOT_DISCWODIS_MULTOOS_X`, `SCH_DISCWDIS_SINGOOS_504_M`, `SCH_DISCWDIS_SINGOOS_504_F`, `SCH_DISCWDIS_SINGOOS_504_X`, `SCH_DISCWDIS_MULTOOS_504_M`, `SCH_DISCWDIS_MULTOOS_504_F`, `SCH_DISCWDIS_MULTOOS_504_X`, `TOT_DISCWDIS_EXPWE_IDEA_M`, `TOT_DISCWDIS_EXPWE_IDEA_F`, `TOT_DISCWDIS_EXPWE_IDEA_X`, `TOT_DISCWDIS_EXPWOE_IDEA_M`, `TOT_DISCWDIS_EXPWOE_IDEA_F`, `TOT_DISCWDIS_EXPWOE_IDEA_X`, `TOT_RS_IDEA_PHYS_M`, `TOT_RS_IDEA_PHYS_F`, `TOT_RS_IDEA_PHYS_X`, `TOT_RS_IDEA_MECH_M`, `TOT_RS_IDEA_MECH_F`, `TOT_RS_IDEA_MECH_X`, `TOT_RS_IDEA_SECL_M`, `TOT_RS_IDEA_SECL_F`, `TOT_RS_IDEA_SECL_X`, `TOT_DISCWDIS_REF_IDEA_M`, `TOT_DISCWDIS_REF_IDEA_F`, `TOT_DISCWDIS_REF_IDEA_X`, `TOT_DISCWDIS_ARR_IDEA_M`, `TOT_DISCWDIS_ARR_IDEA_F`, `TOT_DISCWDIS_ARR_IDEA_X`, `NCESID`, `V33 (fall enrollment)`, `TCURELSC (current spending, $000)`, `C15 (federal IDEA revenue through state, $000)`
