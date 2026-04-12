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
- Implemented vectorized filtering across 20M+ encounter records using pre-compiled regex patterns
- Applied SDOH code extraction (Z55-Z65 range) across all available diagnosis columns
- Optimized performance through vectorized operations and modular architecture

**Population Definitions:**
- **ADRD+SDOH:** Encounters with both dementia diagnosis and documented SDOH (Z55-Z65 codes)
- **Any_ADRD:** All encounters with dementia diagnosis (comparison baseline)
- **Any_SDOH:** All encounters with SDOH documentation (broader context population)

**Output Generation:**
- Z-code distribution analysis (SDOH categories: housing, employment, social environment, etc.)
- Demographics summaries (age, sex, payer, discharge status, encounter type)
- Top diagnosis and procedure codes (ICD-10, CPT, DRG)
- Year-specific and combined (2020-2022) summary tables

**Note:** Analysis uses encounter-level data; patient-level tracking not available in de-identified dataset.

---

## Analysis Workflow

The project evolved through iterative exploratory phases before finalizing the production pipeline architecture.

**Phase 1: Initial Research Question - ADRD and Oral Health Conditions** (`notebooks/adrd_ohc.ipynb`)

Original research question examined prevalence of oral health conditions (ICD K00-K14 codes) in ADRD patients. Quarterly filtering of 2022 ED data revealed insufficient overlap (14-20 encounters per quarter with both ADRD and oral health diagnoses) for meaningful analysis. This prompted pivot to social determinants of health as a more prevalent and clinically relevant intersection.

**Phase 2: Z-Code Distribution Exploration** (`notebooks/dx_codes.ipynb`)

Developed initial Z-code extraction methodology using ADRD+SDOH population from 2020 data. Tested different aggregation approaches including per-column distribution analysis and overall frequency counts. Generated stacked bar charts revealing diagnosis column sparsity pattern (OTHDIAG2 spike for ADRD patients, gradual dropoff in later columns). Established foundation for final pipeline's approach of extracting codes across all available diagnosis columns rather than principal diagnosis only.

**Phase 3: Demographics and Temporal Patterns** (`notebooks/demos.ipynb`)

Built demographic summary tables for ADRD+SDOH population across categorical variables (sex, payer, discharge status). Explored age distributions showing mean age 71.6 years with bimodal ED vs inpatient pattern. Generated admission time heatmaps revealing weekday/hour clustering for inpatient ADRD encounters. Established output structure (long format with ED/Inpatient breakdowns) that informed production pipeline design.

**Phase 4: Production Pipeline Development** (`adrd_sdoh.py`, `mappings.py`)

Scaled exploratory methodology to multi-year, multi-population architecture processing 2020-2022 data. Implemented:

- **Modular configuration architecture** (`mappings.py`): Centralized ICD-10 pattern definitions, column specifications, population metadata, and Z-code category mappings. Pre-compiled regex patterns at module level to eliminate redundant compilation overhead during filtering operations.

- Multi-population filtering with populations dictionary structure enabling extensible cohort definitions

- Performance optimization through vectorized pandas operations (8min → 4min per year)

- Automated summary generation across Z-codes, demographics, and top diagnosis/procedure codes

- Column reduction strategy balancing memory constraints with analytical completeness (95 → 47 columns ED, 193 → 70 columns Inpatient)

**Files:**
- `adrd_sdoh.py` - Main processing pipeline with filtering, extraction, and aggregation logic
- `mappings.py` - Pattern definitions, column specifications, helper functions, and metadata constants

---

## Key Findings

**SDOH documentation in ADRD populations is remarkably low.** Only 1.2% of ADRD encounters (889 of 74,101 in 2020) have documented SDOH, despite this population's known risk factors including housing instability, caregiver burden, and social isolation.

**Housing dominates documented SDOH across all populations.** Z59 (housing/economic circumstances) represents 50-63% of all SDOH codes—substantially more prevalent than employment (5-8.5%), family/household issues (2.8-8.8%), or other social factors.

**SDOH documentation is increasing overall.** The Any_SDOH population grew 44% from 2020 to 2022 (150k → 217k encounters), while ADRD prevalence remained stable, suggesting growing awareness of SDOH capture in clinical practice.

**Age and payer patterns differ markedly across populations.** Any_SDOH patients are younger (mean age 47.8 vs 80.2 for Any_ADRD) with Medicaid as top payer (22.7% vs 56.5% Medicare for ADRD). ADRD+SDOH represents the intersection: older than general SDOH but with similar male overrepresentation (63% vs 66.5%).

**ADRD patients are overwhelmingly inpatient.** 95.4% of ADRD+SDOH encounters occur in inpatient settings compared to 65.8% for Any_SDOH, suggesting different care patterns and potentially different SDOH screening workflows.

---

## Limitations and Future Work

**Current analysis is descriptive.** Findings establish prevalence and patterns but do not establish causal relationships between SDOH documentation and outcomes. Hierarchical modeling accounting for patient and hospital clustering would be needed to test independent effects.

**Encounter-level analysis cannot track patients over time.** The assumption that each encounter is independent limits ability to examine within-patient patterns, readmission risk, or longitudinal SDOH trajectories. Patient-level linkage would enable more sophisticated analyses.

**SDOH documentation may not reflect true prevalence.** Low documentation rates in ADRD populations (1.2%) may indicate screening gaps rather than lower SDOH burden. Age-stratified comparison to non-ADRD populations is planned to investigate potential documentation bias.

**Diagnosis column strategy uses all available fields.** Current implementation extracts codes from all diagnosis columns (PRINDIAG + OTHDIAG1-30) since SDOH codes frequently appear in secondary positions. Future work should examine whether principal diagnosis provides more clinically relevant signal.

**If further investigation is warranted,** we recommend conducting age-matched comparison analysis to determine whether SDOH documentation gaps are ADRD-specific or reflect broader elderly population screening patterns. Additionally, qualitative investigation of clinical workflows could identify barriers to SDOH documentation in dementia care settings.

---

## Graduate Research Context

MS Health Informatics thesis work (University of North Florida, expected December 2026). Faculty advisor: Professor Hanadi Hamadi.

Primary research questions: What social determinants are documented for dementia patients? How do SDOH patterns differ between ADRD and general populations? What temporal trends exist in SDOH capture from 2020-2022?

---

Grace Gillen
MS Health Informatics Candidate, University of North Florida
