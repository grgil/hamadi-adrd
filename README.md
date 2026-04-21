# ADRD-SDOH Documentation Analysis

**Characterizing social determinants of health in encounters with Alzheimer's Disease and Related Dementias**

---

## Research Context

Social determinants of health (SDOH)—factors like housing instability, employment challenges, and social isolation—significantly impact outcomes for individuals with dementia. However, SDOH documentation in clinical encounters remains understudied, and patterns of capture across different populations are poorly understood.

This project analyzes Florida ED snd Inpatient claims data (2020-2022) to characterize SDOH documentation patterns in ADRD populations and compare them to broader healthcare utilization trends. The analysis targets three distinct populations to understand both prevalence and temporal trends in SDOH capture.

---

## Project Description

To analyze SDOH documentation patterns, we developed an automated Python pipeline implementing the following approach:

**Data Processing:**
- Aggregated quarterly encounter data (ED and Inpatient) across 3 years
- Implemented modular architecture and vectorized filtering across 20M+ encounter records using pre-compiled regex patterns
- Applied SDOH code extraction (Z55-Z65 range) across all available diagnosis columns
- ED encounters restricted to hospital-based ED visits (type_serv = 2); ambulatory surgery and cardiac catheterization encounters excluded

**Population Definitions:**
- **ADRD+SDOH:** Encounters with both dementia diagnosis and documented SDOH (Z55-Z65 codes)
- **Any_ADRD:** All encounters with dementia diagnosis (comparison baseline)
- **Any_SDOH:** All encounters with SDOH documentation (broader context population)

**Output Generation:**
- Z-code distribution analysis (SDOH categories: housing, employment, social environment, etc.)
- Demographics summaries (age, sex, payer, discharge status, encounter type)
- Top diagnosis and procedure codes (ICD-10, CPT, DRG)
- Year-specific summary tables (demographics, top codes, Z-code distribution)
- Age-matched SDOH comparison trend (yearly inpatient documentation rates by age group and ADRD status)


**Note:** Analysis uses encounter-level data; patient-level tracking not available in de-identified dataset.

---

## Analysis Workflow

The project evolved through iterative exploratory phases before finalizing the production pipeline architecture.

**Phase 1: Initial Research Question - ADRD and Oral Health Conditions** (`notebooks/adrd_ohc.ipynb`)

Original research question examined prevalence of oral health conditions (ICD K00-K14 codes) in ADRD patients, using a modified Bynum-Standard algorithm (F01.50, F01.51, F02.80, F02.81) to identify ADRD, which was optimized for patient-level identification in a Medicare claims context. Quarterly filtering of 2022 ED data revealed insufficient overlap (14-20 encounters per quarter with both ADRD and oral health diagnoses) for meaningful analysis. This prompted pivot to social determinants of health as a more prevalent and clinically relevant intersection. The encounter-level design of the SDOH analysis also prompted expansion of the ADRD code set beyond Bynum-Standard to capture the full ADRD spectrum; see Phase 4 for validation.

**Phase 2: Z-Code Distribution Exploration** (`notebooks/dx_codes.ipynb`)

Developed initial Z-code extraction methodology using ADRD+SDOH population from 2020 data. Tested different aggregation approaches including per-column distribution analysis and overall frequency counts. Generated stacked bar charts revealing diagnosis column sparsity pattern (OTHDIAG2 spike for ADRD patients, gradual dropoff in later columns). Established foundation for final pipeline's approach of extracting codes across all available diagnosis columns rather than principal diagnosis only.

**Phase 3: Demographics and Temporal Patterns** (`notebooks/demos.ipynb`)

Built demographic summary tables for ADRD+SDOH population across categorical variables (sex, payer, discharge status). Explored age distributions showing mean age 71.6 years with bimodal ED vs inpatient pattern. Generated admission time heatmaps revealing weekday/hour clustering for inpatient ADRD encounters. Established output structure (long format with ED/Inpatient breakdowns) that informed production pipeline design.

**Phase 4: Production Pipeline Development** (`adrd_sdoh.py`, `mappings.py`)

Scaled exploratory methodology to multi-year, multi-population architecture processing 2020-2022 data. Analysis restricted to 2016 forward to ensure full ICD-10 coverage; the ICD-9 to ICD-10 transition occurred October 1, 2015, and Z-codes have no ICD-9 equivalent. Current runs use 2020-2022. Implemented:

- **Modular configuration architecture** (`mappings.py`): Centralized ICD-10 pattern definitions, column specifications, population metadata, and Z-code category mappings. Pre-compiled regex patterns at module level to eliminate redundant compilation overhead during filtering operations. ADRD code set expanded from Bynum-Standard to full ADRD spectrum (F01.x, F02.x, F03.x, G30.x, G31.0, G31.83) appropriate for encounter-level analysis; validated against original codes using 2020 outputs
- ED encounter filtering: ED files contain both emergency department visits (type_serv = 2) and ambulatory surgery/cath encounters (type_serv = 1); pipeline restricts to type_serv = 2 at read time
- Performance optimization through vectorized pandas operations and usecols at read time (~4-5 min per year). Column reduction strategy balances memory constraints with analytical completeness (95 → 47 columns ED, 193 → 70 columns Inpatient)

**Files:**
- `adrd_sdoh.py` - Main processing pipeline with filtering, extraction, and aggregation logic
- `mappings.py` - Pattern definitions, column specifications, helper functions, and metadata constants

**Phase 5: Age-Stratified Comparison Analysis** (`adrd_sdoh.py` - `create_age_match()`)

Investigated whether low SDOH documentation rates in ADRD populations (1.2%, 2020) reflected ADRD-specific screening gaps or broader age-related patterns. Implemented age-matched comparison between ADRD and non-ADRD inpatients across four age groups (50-64, 65-74, 75-84, 85+), controlling for care setting.  2020 analysis revealed SDOH documentation declines sharply with age regardless of ADRD status — dropping approximately 6-fold from 5.8% in ages 50-64 to 0.8% in ages 85-99. Within each age stratum, ADRD and non-ADRD rates were nearly identical, indicating the apparent disparity between inpatient ADRD (1.48% overall) and general inpatient populations (3.75% overall) reflects age composition differences rather than cognitive status.

---

## Key Findings

**SDOH documentation declines sharply with age.** 2020 age-stratified analysis revealed documentation rates drop approximately 6-fold from working-age (5.8% in ages 50-64) to elderly populations (0.8% in ages 85+). Within each age stratum, ADRD and non-ADRD rates are nearly identical, indicating the apparent disparity between ADRD (1.48% overall) and general populations (3.75% overall) reflects age composition differences rather than ADRD-specific screening gaps. This pattern holds consistently across all three years.

**Housing dominates documented SDOH, representing 50-63% of all codes** across populations—substantially more prevalent than employment (5-8.5%), family/household issues (2.8-8.8%), or other social factors. ADRD patients are overwhelmingly inpatient (89.4% (2020) of ADRD+SDOH encounters vs 64.8% for Any_SDOH), suggesting different care patterns and potentially different screening workflows.

**SDOH documentation is increasing temporally across all age groups.** The Any_SDOH population grew 44% from 2020 to 2022 (150k → 217k encounters) while ADRD prevalence remained stable. This temporal trend is visible across both ADRD and non-ADRD populations with proportional increases in all age strata.

**Population demographics reveal distinct age and payer profiles.** Any_SDOH patients are younger (mean age 47.8 vs 81.2 (2020) for Any_ADRD) with Medicaid as top payer (23.4% (2020) vs 56.5% Medicare for ADRD). ADRD+SDOH represents the intersection: older than general SDOH but with similar male overrepresentation (63% Any_SDOH vs 51.2% ADRD+SDOH, 2020).

---

## Limitations and Future Work

**Current analysis is descriptive and uses encounter-level data.** Findings establish prevalence and patterns but do not test causal relationships between SDOH documentation and outcomes. Additionally, the assumption that encounters are independent limits ability to examine within-patient patterns or longitudinal trajectories. Hierarchical modeling accounting for patient and hospital clustering, combined with patient-level linkage, would enable more sophisticated analyses.

**Age-stratified findings assume documentation reflects true prevalence, but both elderly groups may be systematically underdocumented.** The 6-fold decline in documentation from working-age to elderly populations suggests either genuine prevalence differences or measurement issues with Z-codes in elderly care contexts. Z-codes designed for working-age social issues (employment, housing instability) may inadequately capture elderly-specific risks (caregiver burden, aging in place challenges).

**Diagnosis column strategy and temporal scope require validation.** Current implementation extracts codes from all diagnosis columns (PRINDIAG + OTHDIAG1-30) since SDOH codes frequently appear in secondary positions; future work should examine whether principal diagnosis provides more clinically relevant signal. Qualitative investigation of clinical workflows could identify why SDOH screening/documentation declines with patient age and whether Z-codes are fit-for-purpose for elderly populations.

---

## Graduate Research Context

MS Health Informatics thesis work (University of North Florida, expected December 2026). Faculty advisor: Professor Hanadi Hamadi.

Primary research questions: What social determinants are documented for dementia patients? How do SDOH patterns differ between ADRD and general populations? What temporal trends exist in SDOH capture from 2020-2022?

---

Grace Gillen
MS Health Informatics Candidate, University of North Florida
