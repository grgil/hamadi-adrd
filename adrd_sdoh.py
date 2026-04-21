import pandas as pd
import numpy as np

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
    keep_cols = ed_keep_cols if care_setting == 'ED' else inpt_keep_cols
    
    quarterly_dfs = []
    
    for quarter in range(1, 5):
        filename = f"{year_short}Q{quarter}_{suffix}"
        filepath = f"{source_dir}/{filename}"

        try:
            quarter_df = pd.read_csv(filepath, usecols=keep_cols, low_memory=False)
            if care_setting == 'ED':
                quarter_df = quarter_df[quarter_df['TYPE_SERV'] == 2]
            quarterly_dfs.append(quarter_df)
        
        except FileNotFoundError:
            timestamp_print(f"  WARNING: Missing file skipped — {filename}")
    
    annual_df = pd.concat(quarterly_dfs, ignore_index=True)
    
    return annual_df

def load_encounter_data(year, care_setting, quarterly=True):
    """
    Load encounter data for specified year and care setting.
    """
    
    care_setting = care_setting.upper()
    
    if quarterly:
        df = aggregate_quarterly_data(year, care_setting)
    else:
        keep_cols = ed_keep_cols if care_setting == 'ED' else inpt_keep_cols
        filepath = f"{source_dir}/ED_{year}.csv" if care_setting == 'ED' else f"{source_dir}/INPATIENT_{year}.csv"
        df = pd.read_csv(filepath, usecols=keep_cols, low_memory=False)
        if care_setting == 'ED':
            df = df[df['TYPE_SERV'] == 2]
    
    timestamp_print(f"  Loaded {care_setting} data - shape: {df.shape}")
    
    # Unknown (999) and 100+ (888) handling
    df['AGE'] = df['AGE'].replace({888: 100, 999: np.nan})
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
    
    sdoh_mask = has_code_pattern(adrd_df, diag_cols, z_code_pattern)
    
    filtered = adrd_df[sdoh_mask].copy()
    filtered['YEAR'] = year
    
    return filtered

def extract_z_codes(df, diag_cols):
    """
    Extract all Z55-Z65 codes from diagnosis columns in an encounter.
    """
    long = (df[diag_cols]
            .melt(ignore_index=False, value_name='dx')
            .dropna(subset=['dx']))
    
    matches = long['dx'].str.findall(z_code_pattern.pattern)
    matches = matches.explode().str[:3].dropna()
    
    return matches.groupby(level=0).apply(list).reindex(df.index, fill_value=[])


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
            'ED_Code_Occurance': ed_count,
            'Inpatient_Code_Occurance': inpt_count
        })
    
    summary = pd.DataFrame(summary_data)
    
    # Calculate percentages
    ed_total = summary['ED_Code_Occurance'].sum()
    inpt_total = summary['Inpatient_Code_Occurance'].sum()
    
    summary['ED_Percent'] = (summary['ED_Code_Occurance'] / ed_total * 100).round(1) if ed_total > 0 else 0
    summary['Inpatient_Percent'] = (summary['Inpatient_Code_Occurance'] / inpt_total * 100).round(1) if inpt_total > 0 else 0
    summary['Total_Count'] = summary['ED_Code_Occurance'] + summary['Inpatient_Code_Occurance']
    summary['Total_Percent'] = (summary['Total_Count'] / summary['Total_Count'].sum() * 100).round(1)
    
    return summary

def create_demographics_table(ed_filtered, inpt_filtered, population_label):
    """
    Create demographics summary table for a population.

    """ 
    
    combined = pd.concat([ed_filtered, inpt_filtered], ignore_index=True)
    combined_clean_age = combined[combined['AGE'] != 999]
    
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

    icd_pairs = []

    # ED diagnosis codes
    for col in ed_diag_cols:
        mask = ed_filtered[col].str.strip() != ''  # Filter out empty/whitespace
        pairs = list(zip(ed_filtered.loc[mask, 'SYS_RECID'], ed_filtered.loc[mask, col]))
        icd_pairs.extend(pairs)

    # Inpatient diagnosis codes
    for col in inpt_diag_cols:
        mask = inpt_filtered[col].str.strip() != ''
        pairs = list(zip(inpt_filtered.loc[mask, 'SYS_RECID'], inpt_filtered.loc[mask, col]))
        icd_pairs.extend(pairs)

    # Convert to dataframe, drop duplicate pairs
    if icd_pairs:
        icd_pairs_df = pd.DataFrame(icd_pairs, columns=['SYS_RECID', 'code'])
        icd_pairs_df = icd_pairs_df.drop_duplicates()
        icd_counts = icd_pairs_df['code'].value_counts().head(top_n)
        
        if len(icd_counts) == 10:
            all_total = icd_counts.sum()
            bottom5_total = icd_counts.iloc[5:].sum()
            if bottom5_total / all_total < 0.10:  # If bottom 5 are <10% of all 10
                icd_counts = icd_counts.head(5)  # Return only top 5
    
        for rank, (code, count) in enumerate(icd_counts.items(), 1):
            rows.append({
                'Population': population_label,
                'Code_Type': 'ICD-10',
                'Code': code,
                'Rank': rank,
                'Count': int(count),
                'Percent': round(count / total_encounters * 100, 1)})
    
    # === TOP CPT PROCEDURE CODES ===

    cpt_pairs = []

    # ED CPT codes
    for col in ed_cpt_cols:
        mask = ed_filtered[col].str.strip() != '' 
        pairs = list(zip(ed_filtered.loc[mask, 'SYS_RECID'], ed_filtered.loc[mask, col]))
        cpt_pairs.extend(pairs)

    # Inpatient CPT codes
    for col in inpt_cpt_cols:
        mask = inpt_filtered[col].str.strip() != ''
        pairs = list(zip(inpt_filtered.loc[mask, 'SYS_RECID'], inpt_filtered.loc[mask, col]))
        cpt_pairs.extend(pairs)

    # Convert to dataframe, drop duplicate pairs
    if cpt_pairs:
        cpt_pairs_df = pd.DataFrame(cpt_pairs, columns=['SYS_RECID', 'code'])
        cpt_pairs_df = cpt_pairs_df.drop_duplicates()
        cpt_counts = cpt_pairs_df['code'].value_counts().head(top_n)
        
        if len(cpt_counts) == 10:
            all_total = cpt_counts.sum()
            bottom5_total = cpt_counts.iloc[5:].sum()
            if bottom5_total / all_total < 0.10:  # If bottom 5 are <10% of all 10
                cpt_counts = cpt_counts.head(5)  # Return only top 5
    
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

def create_age_match(year, adrd_sdoh_inpt, any_adrd_inpt, any_sdoh_inpt, total_inpt_by_age):
    """
    Compare SDOH documentation rates between ADRD and non-ADRD inpatients,
    stratified by age group.
    """
    
    # Filter to age 50+ for all populations
    adrd_sdoh_50plus = adrd_sdoh_inpt[adrd_sdoh_inpt['AGE'] >= 50].copy()
    any_adrd_50plus = any_adrd_inpt[any_adrd_inpt['AGE'] >= 50].copy()
    any_sdoh_50plus = any_sdoh_inpt[any_sdoh_inpt['AGE'] >= 50].copy()
    
    # Create age groups
    adrd_sdoh_50plus['AGE_GROUP'] = pd.cut(adrd_sdoh_50plus['AGE'], bins=AGE_BINS, labels=AGE_LABELS, right=False)
    any_adrd_50plus['AGE_GROUP'] = pd.cut(any_adrd_50plus['AGE'], bins=AGE_BINS, labels=AGE_LABELS, right=False)
    any_sdoh_50plus['AGE_GROUP'] = pd.cut(any_sdoh_50plus['AGE'], bins=AGE_BINS, labels=AGE_LABELS, right=False)
    
    rows = []
    
    for age_group in AGE_LABELS:
        # ADRD group
        adrd_sdoh_count = len(adrd_sdoh_50plus[adrd_sdoh_50plus['AGE_GROUP'] == age_group])
        adrd_total_count = len(any_adrd_50plus[any_adrd_50plus['AGE_GROUP'] == age_group])
        adrd_rate = (adrd_sdoh_count / adrd_total_count * 100) if adrd_total_count > 0 else 0
        
        rows.append({
            'Year': year,
            'Age_Group': age_group,
            'ADRD_Status': 'ADRD',
            'SDOH_Documented': adrd_sdoh_count,
            'Total_Encounters': adrd_total_count,
            'SDOH_Rate': round(adrd_rate, 2)
        })
        
        # Non-ADRD group
        # Numerator: Any_SDOH in this age group minus ADRD+SDOH overlap
        sdoh_in_age = len(any_sdoh_50plus[any_sdoh_50plus['AGE_GROUP'] == age_group])
        non_adrd_sdoh_count = sdoh_in_age - adrd_sdoh_count
        
        # Denominator: Total inpatients in this age group minus ADRD
        total_in_age = total_inpt_by_age.get(age_group, 0)
        non_adrd_total_count = total_in_age - adrd_total_count
        
        non_adrd_rate = (non_adrd_sdoh_count / non_adrd_total_count * 100) if non_adrd_total_count > 0 else 0
        
        rows.append({
            'Year': year,
            'Age_Group': age_group,
            'ADRD_Status': 'Non-ADRD',
            'SDOH_Documented': non_adrd_sdoh_count,
            'Total_Encounters': non_adrd_total_count,
            'SDOH_Rate': round(non_adrd_rate, 2)
        })
    
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
            
            ed_z = extract_z_codes(pop_data['ed'], ed_diag_cols)
            inpt_z = extract_z_codes(pop_data['inpt'], inpt_diag_cols)
            
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
    
    # Store age-matched comparison rows
    age_comparison_rows = []
    
    for year in years:
        timestamp_print(f"Processing {year}...")
        
        # Load
        ed_df = load_encounter_data(year, 'ED', quarterly=quarterly)
        inpt_df = load_encounter_data(year, 'Inpatient', quarterly=quarterly)
        
        inpt_50plus = inpt_df[(inpt_df['AGE'] >= 50)].copy()
        inpt_50plus['AGE_GROUP'] = pd.cut(inpt_50plus['AGE'], bins=AGE_BINS, labels=AGE_LABELS, right=False)
        total_inpt_by_age = inpt_50plus['AGE_GROUP'].value_counts().to_dict()
        
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
        
        # Create age-matched comparison for this year
        year_comparison = create_age_match(
            year=year,
            adrd_sdoh_inpt=populations['ADRD+SDOH']['inpt'],
            any_adrd_inpt=populations['Any_ADRD']['inpt'],
            any_sdoh_inpt=populations['Any_SDOH']['inpt'],
            total_inpt_by_age=total_inpt_by_age
        )
        age_comparison_rows.append(year_comparison)
        
        timestamp_print(f"  Exported summaries for {year}")

        del ed_df, inpt_df, populations
    
    # Export age-matched comparison (all years in single file)
    all_comparisons = pd.concat(age_comparison_rows, ignore_index=True)
    all_comparisons.to_csv(f"{output_dir}/age_matched_sdoh_comparison.csv", index=False)  # CHANGED: hardcoded path → output_dir variable
    timestamp_print("  Exported age-matched comparison")
    
    timestamp_print("All summaries exported to output directory.")

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    
    years = [2020, 2021, 2022]
    process_multiple_years(years, quarterly=True)
