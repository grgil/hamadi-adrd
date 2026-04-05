import pandas as pd
import numpy as np
import re

from mappings import *

# ============================================================================
# CONFIGURATION
# ============================================================================

source_dir = './source'
output_dir = './output'


# ============================================================================
# DATA LOADING FUNCTIONS
# ============================================================================

def aggregate_quarterly_data(year, care_setting):
    """
    Load and combine quarterly encounter data for a given year and care setting.

    """
    care_setting = care_setting.upper()
    
    suffix = 'ED.csv' if care_setting == 'ED' else 'INP.csv'
    year_short = str(year)[-2:]
    
    quarterly_dfs = []
    
    for quarter in range(1, 5):
        filename = f"{year_short}Q{quarter}_{suffix}"
        filepath = f"{source_dir}/{filename}"
        
        quarter_df = pd.read_csv(filepath, low_memory=False)
        quarterly_dfs.append(quarter_df)
    
    annual_df = pd.concat(quarterly_dfs, ignore_index=True)
    
    return annual_df

def load_encounter_data(year, care_setting, quarterly=True):
    """
    Load encounter data for specified year and care setting.
    """
    import time
    
    care_setting = care_setting.upper()
    
    # Time the loading
    start_load = time.time()
    
    if quarterly:
        df = aggregate_quarterly_data(year, care_setting)
    else:
        if care_setting == 'ED':
            filepath = f"{source_dir}/ED_{year}.csv"
        else:
            filepath = f"{source_dir}/INPATIENT_{year}.csv"
        
        df = pd.read_csv(filepath, low_memory=False)
    
    load_time = time.time() - start_load
    timestamp_print(f"  Loaded {care_setting} data in {load_time:.1f}s - shape: {df.shape}")
    
    # Time the column filtering
    start_filter = time.time()
    
    if care_setting == 'ED':
        df = df[df.columns.intersection(ed_keep_cols)]
    else:
        df = df[df.columns.intersection(inpt_keep_cols)]
    
    filter_time = time.time() - start_filter
    timestamp_print(f"  Filtered columns in {filter_time:.1f}s - new shape: {df.shape}")
    
    return df


# ============================================================================
# FILTERING FUNCTIONS
# ============================================================================

def has_code_pattern(df, diag_cols, pattern):
    """
    Check if any diagnosis column contains code matching pattern.
    
    """
    # Convert to string outside loop
    df_str = df[diag_cols].astype(str)
    
    matches = df_str.apply(lambda col: col.str.contains(pattern, na=False, regex=True))
    return matches.any(axis=1)

def filter_adrd_only(df, diag_cols, year):
    """
    Filter to encounters with ADRD codes.
    
    """
    adrd_pattern = get_adrd_pattern(year)
    adrd_mask = has_code_pattern(df, diag_cols, adrd_pattern)
    
    filtered = df[adrd_mask].copy()
    filtered['YEAR'] = year
    
    return filtered

def filter_sdoh_only(df, diag_cols, year):
    """
    Filter to encounters with SDOH codes.
    
    """
    sdoh_mask = has_code_pattern(df, diag_cols, z_code_pattern)
    
    filtered = df[sdoh_mask].copy()
    filtered['YEAR'] = year
    
    return filtered

def filter_adrd_with_sdoh(df, diag_cols, year):
    """
    Filter to encounters with ADRD AND SDOH codes.
    
    """
    adrd_df = filter_adrd_only(df, diag_cols, year)
    
    sdoh_pattern = get_sdoh_pattern(year)
    sdoh_mask = has_code_pattern(adrd_df, diag_cols, sdoh_pattern)
    
    filtered = adrd_df[sdoh_mask].copy()
    filtered['YEAR'] = year
    
    return filtered

def extract_all_z_codes(row, diag_cols):
    """
    Extract all Z55-Z65 codes from diagnosis columns in an encounter.

    """
    z_codes = []
    
    for col in diag_cols:
        if pd.notna(row[col]):
            matches = [m[:3] for m in z_code_pattern.findall(str(row[col]))]
            z_codes.extend(matches)
    
    return z_codes


# ============================================================================
# ANALYSIS FUNCTIONS
# ============================================================================

def create_z_code_table(ed_z, inpt_z):
    """
    Create summary table of Z-code counts by category.

    """
    # Flatten and count
    ed_counts = pd.Series([code for codes in ed_z for code in codes]).value_counts()
    inpt_counts = pd.Series([code for codes in inpt_z for code in codes]).value_counts()
    
    # Get all unique Z-codes found
    all_codes = sorted(set(ed_counts.index.tolist() + inpt_counts.index.tolist()))
    
    # Build summary rows
    summary_data = []
    
    for code in all_codes:
        category = categorize_z_code(code)
        ed_count = ed_counts.get(code, 0)
        inpt_count = inpt_counts.get(code, 0)
        
        summary_data.append({
            'Z_Code': code,
            'Category': category,
            'ED_Count': ed_count,
            'Inpatient_Count': inpt_count
        })
    
    summary = pd.DataFrame(summary_data)
    
    # Calculate percentages
    ed_total = summary['ED_Count'].sum()
    inpt_total = summary['Inpatient_Count'].sum()
    
    summary['ED_Percent'] = (summary['ED_Count'] / ed_total * 100).round(1) if ed_total > 0 else 0
    summary['Inpatient_Percent'] = (summary['Inpatient_Count'] / inpt_total * 100).round(1) if inpt_total > 0 else 0
    summary['Total_Count'] = summary['ED_Count'] + summary['Inpatient_Count']
    summary['Total_Percent'] = (summary['Total_Count'] / summary['Total_Count'].sum() * 100).round(1)
    
    return summary

def create_demographics_table(ed_filtered, inpt_filtered, population_label):
    """
    Create demographics summary table for a population.

    """ 
    # Keep only demographics columns
    ed_filtered = ed_filtered[ed_demog_cols]
    inpt_filtered = inpt_filtered[inpt_demog_cols]
    
    combined = pd.concat([ed_filtered, inpt_filtered], ignore_index=True)
    combined_clean_age = combined[combined['AGE'] != 888]
    
    rows = []
    
    # === AGE STATISTICS ===
    
    rows.append({
        'Population': population_label,
        'Category': 'Age',
        'Subcategory': 'Mean',
        'Count': None,
        'Percent': None,
        'Value': round(combined_clean_age['AGE'].mean(), 1)
    })
    
    rows.append({
        'Population': population_label,
        'Category': 'Age',
        'Subcategory': 'Median',
        'Count': None,
        'Percent': None,
        'Value': round(combined_clean_age['AGE'].median(), 1)
    })
    
    rows.append({
        'Population': population_label,
        'Category': 'Age',
        'Subcategory': 'Q1',
        'Count': None,
        'Percent': None,
        'Value': round(combined_clean_age['AGE'].quantile(0.25), 1)
    })
    
    rows.append({
        'Population': population_label,
        'Category': 'Age',
        'Subcategory': 'Q3',
        'Count': None,
        'Percent': None,
        'Value': round(combined_clean_age['AGE'].quantile(0.75), 1)
    })
    
    # === SEX ===
    
    sex_counts = combined['SEX'].value_counts()
    sex_pct = (sex_counts / len(combined) * 100)
    
    for sex, count in sex_counts.items():
        rows.append({
            'Population': population_label,
            'Category': 'Sex',
            'Subcategory': sex,
            'Count': int(count),
            'Percent': round(sex_pct[sex], 1),
            'Value': None
        })
    
    # === PAYER ===
    
    payer_counts = combined['PAYER'].value_counts()
    payer_pct = (payer_counts / len(combined) * 100)
    
    for payer, count in payer_counts.items():
        rows.append({
            'Population': population_label,
            'Category': 'Payer',
            'Subcategory': payer,
            'Count': int(count),
            'Percent': round(payer_pct[payer], 1),
            'Value': None
        })
    
    # === DISCHARGE STATUS ===
    
    all_dc = pd.concat([
        ed_filtered['PT_STATUS'],
        inpt_filtered['DISCHSTAT']
    ])
    
    dc_counts = all_dc.value_counts()
    dc_pct = (dc_counts / len(all_dc) * 100)
    
    for status, count in dc_counts.items():
        rows.append({
            'Population': population_label,
            'Category': 'Discharge_Status',
            'Subcategory': status,
            'Count': int(count),
            'Percent': round(dc_pct[status], 1),
            'Value': None
        })
    
    # === ENCOUNTER TYPE ===
    
    rows.append({
        'Population': population_label,
        'Category': 'Encounter_Type',
        'Subcategory': 'ED',
        'Count': len(ed_filtered),
        'Percent': round(len(ed_filtered) / len(combined) * 100, 1),
        'Value': None
    })
    
    rows.append({
        'Population': population_label,
        'Category': 'Encounter_Type',
        'Subcategory': 'Inpatient',
        'Count': len(inpt_filtered),
        'Percent': round(len(inpt_filtered) / len(combined) * 100, 1),
        'Value': None
    })
    
    return pd.DataFrame(rows)

def create_top_codes_table(ed_filtered, inpt_filtered, population_label, top_n=10):
    """
    Extract top ICD-10, CPT, and DRG codes for a population.
    
    """

    combined = pd.concat([ed_filtered, inpt_filtered], ignore_index=True)
    total_encounters = len(combined)
    
    rows = []
    
    # === TOP ICD-10 DIAGNOSIS CODES ===

    all_icd_codes = []

    # ED diagnosis codes
    for col in ed_diag_cols:
        mask = ed_filtered[col].str.strip() != ''
        valid_codes = ed_filtered[col][mask]
        all_icd_codes.extend(valid_codes.tolist())

    # Inpatient diagnosis codes
    for col in inpt_diag_cols:
        mask = inpt_filtered[col].str.strip() != ''
        valid_codes = inpt_filtered[col][mask]
        all_icd_codes.extend(valid_codes.tolist())

    if all_icd_codes:
        icd_counts = pd.Series(all_icd_codes).value_counts().head(top_n)
    
        if len(icd_counts) == 10:
            all_total = icd_counts.sum()
            bottom5_total = icd_counts.iloc[5:].sum()
            if bottom5_total / all_total < 0.10:  # 10% of all 10
                icd_counts = icd_counts.head(5)
    
        for rank, (code, count) in enumerate(icd_counts.items(), 1):
            rows.append({
                'Population': population_label,
                'Code_Type': 'ICD-10',
                'Code': code,
                'Rank': rank,
                'Count': int(count),
                'Percent': round(count / total_encounters * 100, 1)})
    
    # === TOP CPT PROCEDURE CODES ===

    all_cpt_codes = []

    # ED CPT codes
    for col in ed_cpt_cols:
            mask = ed_filtered[col].str.strip() != ''
            valid_codes = ed_filtered[col][mask]
            all_cpt_codes.extend(valid_codes.tolist())

    # Inpatient CPT codes
    for col in inpt_cpt_cols:
        mask = inpt_filtered[col].str.strip() != ''
        valid_codes = inpt_filtered[col][mask]
        all_cpt_codes.extend(valid_codes.tolist())

    if all_cpt_codes:
        cpt_counts = pd.Series(all_cpt_codes).value_counts().head(top_n)
    
        if len(cpt_counts) == 10:
            all_total = cpt_counts.sum()
            bottom5_total = cpt_counts.iloc[5:].sum()
            if bottom5_total / all_total < 0.10:  # 10% of all 10
                cpt_counts = cpt_counts.head(5)
    
        for rank, (code, count) in enumerate(cpt_counts.items(), 1):
            rows.append({
                'Population': population_label,
                'Code_Type': 'CPT',
                'Code': code,
                'Rank': rank,
                'Count': int(count),
                'Percent': round(count / total_encounters * 100, 1)})

    
    # === TOP DRG CODES ===

    all_drg_codes = []

    valid_drgs = inpt_filtered['MSDRG'].dropna()
    all_drg_codes = valid_drgs.tolist()
    
    if all_drg_codes:
        drg_counts = pd.Series(all_drg_codes).value_counts().head(top_n)
        
        if len(drg_counts) == 10:
            all_total = drg_counts.sum()
            bottom5_total = drg_counts.iloc[5:].sum()
            if bottom5_total / all_total < 0.10:  # 10% of all 10
                drg_counts = drg_counts.head(5)
        
        for rank, (code, count) in enumerate(drg_counts.items(), 1):
            rows.append({
                'Population': population_label,
                'Code_Type': 'DRG',
                'Code': code,
                'Rank': rank,
                'Count': int(count),
                'Percent': round(count / len(inpt_filtered) * 100, 1)})

    return pd.DataFrame(rows)

def create_year_summary(year, populations):
    """
    Create comprehensive summary for a single year or combined period.
    Exports Z-codes and demographics for ADRD+SDOH, All ADRD, and All Encounters.

    """

    if not populations:
        timestamp_print(f"WARNING: No populations provided for {year}. Skipping summary generation.")
        return
    
    for pop_name, pop_data in populations.items():
        if len(pop_data['ed']) == 0 and len(pop_data['inpt']) == 0:
            timestamp_print(f"WARNING: {pop_name} has no encounters for {year}.")

    # === Z-CODE SUMMARY ===
    
    z_summaries = []
    
    for pop_name, pop_data in populations.items():
        if pop_name in SDOH_POP:
            
            ed_z = pop_data['ed'].apply(lambda row: extract_all_z_codes(row, ed_diag_cols), axis=1)
            inpt_z = pop_data['inpt'].apply(lambda row: extract_all_z_codes(row, inpt_diag_cols), axis=1)
            
            z_summary = create_z_code_table(ed_z, inpt_z)
            z_summary.insert(0, 'Population', pop_name)
            z_summaries.append(z_summary)
    
    z_summary_combined = pd.concat(z_summaries, ignore_index=True)
    z_summary_combined.to_csv(f"{output_dir}/z_code_summary_{year}.csv", index=False)
    
    # === DEMOGRAPHICS SUMMARIES ===
    
    demog_summaries = []

    for pop_name, pop_data in populations.items():
        demog = create_demographics_table(
            pop_data['ed'],
            pop_data['inpt'],
            pop_name
        )
        demog_summaries.append(demog)

    combined_demog = pd.concat(demog_summaries, ignore_index=True)
    combined_demog.to_csv(f"{output_dir}/demographics_summary_{year}.csv", index=False)

    # === TOP CODE SUMMARIES ===
    
    code_summaries = []

    for pop_name, pop_data in populations.items():
        top_code = create_top_codes_table(
            pop_data['ed'],
            pop_data['inpt'],
            pop_name
        )
        code_summaries.append(top_code)

    combined_codes = pd.concat(code_summaries, ignore_index=True)
    combined_codes.to_csv(f"{output_dir}/top_codes_summary_{year}.csv", index=False)

# ============================================================================
# MULTI-YEAR PROCESSING
# ============================================================================

def process_multiple_years(years, quarterly=True):
    
    # Store populations
    all_populations = {
        'ADRD+SDOH': {'ed': [], 'inpt': []},
        'Any_ADRD': {'ed': [], 'inpt': []},
        'Any_SDOH': {'ed': [], 'inpt': []}
    }
    
    for year in years:
        timestamp_print(f"Processing {year}...")
        
        # Load
        ed_df = load_encounter_data(year, 'ED', quarterly=quarterly)
        inpt_df = load_encounter_data(year, 'Inpatient', quarterly=quarterly)
        
        timestamp_print(f"  Starting population filtering...")
        
        # Filter all populations
        populations = {
            'ADRD+SDOH': {
                'ed': filter_adrd_with_sdoh(ed_df, ed_diag_cols, year),
                'inpt': filter_adrd_with_sdoh(inpt_df, inpt_diag_cols, year)},
            'Any_ADRD': {
                'ed': filter_adrd_only(ed_df, ed_diag_cols, year),
                'inpt': filter_adrd_only(inpt_df, inpt_diag_cols, year)},
            'Any_SDOH': {
                'ed': filter_sdoh_only(ed_df, ed_diag_cols, year),
                'inpt': filter_sdoh_only(inpt_df, inpt_diag_cols, year)}
        }
        
        timestamp_print(f"  Finished population filtering")
        timestamp_print(f"  Creating year summaries...")
        
        # Create year summary
        create_year_summary(year, populations)
        
        timestamp_print(f"  Exported summaries for {year}")
        
        # Store for combined
        for pop_name in populations:
            all_populations[pop_name]['ed'].append(populations[pop_name]['ed'])
            all_populations[pop_name]['inpt'].append(populations[pop_name]['inpt'])
        
        del ed_df, inpt_df
    
    # === COMBINED SUMMARY (all years) ===
    
    timestamp_print("Creating combined summary...")
    
    combined_populations = {}
    for pop_name in all_populations:
        combined_populations[pop_name] = {
            'ed': pd.concat(all_populations[pop_name]['ed'], ignore_index=True),
            'inpt': pd.concat(all_populations[pop_name]['inpt'], ignore_index=True)
        }
    
    year_range = f"{min(years)}-{max(years)}"
    create_year_summary(year_range, combined_populations)
    
    timestamp_print("All summaries exported to output directory.")


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    
    years = [2020, 2021, 2022]
    process_multiple_years(years, quarterly=True)