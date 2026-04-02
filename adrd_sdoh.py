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
    if quarterly:
        return aggregate_quarterly_data(year, care_setting)
    
    else:
        care_setting = care_setting.upper()
        
        if care_setting == 'ED':
            filepath = f"{source_dir}/ED_{year}.csv"
        else:
            filepath = f"{source_dir}/INPATIENT_{year}.csv"
        
        df = pd.read_csv(filepath, low_memory=False)
        return df


# ============================================================================
# FILTERING FUNCTIONS
# ============================================================================

def has_code_pattern(df, diag_cols, pattern):
    """
    Check if any diagnosis column contains code matching pattern.
    
    """
    return df[diag_cols].apply(
        lambda x: x.astype(str).str.contains(pattern, na=False, regex=True)
    ).any(axis=1)


def filter_adrd_only(df, diag_cols, year):
    """
    Filter to encounters with ADRD codes.
    
    """
    adrd_pattern = get_adrd_pattern(year)
    adrd_mask = has_code_pattern(df, diag_cols, adrd_pattern)
    
    filtered = df[adrd_mask].copy()
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
            # Match full codes including subcodes (Z59.0, Z59.1)
            matches = re.findall(r'Z5[5-9](?:\.\d+)?|Z6[0-5](?:\.\d+)?', str(row[col]))
            # Strip to category level (Z59.0 -> Z59)
            matches = [m[:3] for m in matches]
            z_codes.extend(matches)
    
    return z_codes


# ============================================================================
# ANALYSIS FUNCTIONS
# ============================================================================

def create_z_code_summary(ed_z, inpt_z):
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


def create_year_summary(year, ed_adrd_sdoh, inpt_adrd_sdoh, ed_adrd_all, inpt_adrd_all):
    """
    Create comprehensive summary for a single year or combined period.
    Exports Z-codes and demographics for ADRD+SDOH, All ADRD, and All Encounters.

    """
    
    # === Z-CODE SUMMARY (ADRD+SDOH only) ===
    
    ed_z = ed_adrd_sdoh.apply(lambda row: extract_all_z_codes(row, ed_diag_cols), axis=1)
    inpt_z = inpt_adrd_sdoh.apply(lambda row: extract_all_z_codes(row, inpt_diag_cols), axis=1)
    
    z_summary = create_z_code_summary(ed_z, inpt_z)
    z_summary.to_csv(f"{output_dir}/z_code_summary_{year}.csv", index=False)
    
    # === DEMOGRAPHICS SUMMARIES ===
    
    # Population 1: ADRD+SDOH
    demog_adrd_sdoh = create_demographics_table(
        ed_adrd_sdoh, inpt_adrd_sdoh, 
        population_label="ADRD+SDOH"
    )
    
    # Population 2: All ADRD (regardless of SDOH)
    demog_adrd_all = create_demographics_table(
        ed_adrd_all, inpt_adrd_all,
        population_label="All_ADRD"
    )
    
    # Combine all demographics into one file
    combined_demog = pd.concat([demog_adrd_sdoh, demog_adrd_all], ignore_index=True)
    combined_demog.to_csv(f"{output_dir}/demographics_summary_{year}.csv", index=False)


# ============================================================================
# MULTI-YEAR PROCESSING
# ============================================================================

def process_multiple_years(years, quarterly=True):
    
    all_ed_adrd_sdoh = []
    all_inpt_adrd_sdoh = []
    all_ed_adrd_all = []
    all_inpt_adrd_all = []
    
    for year in years:
        print(f"\nProcessing {year}...")
        
        # Load
        ed_df = load_encounter_data(year, 'ED', quarterly=quarterly)
        inpt_df = load_encounter_data(year, 'Inpatient', quarterly=quarterly)
        
        # Filter ADRD+SDOH
        ed_adrd_sdoh = filter_adrd_with_sdoh(ed_df, ed_diag_cols, year)
        inpt_adrd_sdoh = filter_adrd_with_sdoh(inpt_df, inpt_diag_cols, year)
        
        # Filter ALL ADRD
        ed_adrd_all = filter_adrd_only(ed_df, ed_diag_cols, year)
        inpt_adrd_all = filter_adrd_only(inpt_df, inpt_diag_cols, year)
        
        # Create year summary
        create_year_summary(year, ed_adrd_sdoh, inpt_adrd_sdoh, ed_adrd_all, inpt_adrd_all)
        print(f"  Exported summaries for {year}")
        
        # Store for combined
        all_ed_adrd_sdoh.append(ed_adrd_sdoh)
        all_inpt_adrd_sdoh.append(inpt_adrd_sdoh)
        all_ed_adrd_all.append(ed_adrd_all)
        all_inpt_adrd_all.append(inpt_adrd_all)
        
        del ed_df, inpt_df
    
    # Combined
    combined_ed_sdoh = pd.concat(all_ed_adrd_sdoh, ignore_index=True)
    combined_inpt_sdoh = pd.concat(all_inpt_adrd_sdoh, ignore_index=True)
    combined_ed_adrd_all = pd.concat(all_ed_adrd_all, ignore_index=True)
    combined_inpt_adrd_all = pd.concat(all_inpt_adrd_all, ignore_index=True)
    
    year_range = f"{min(years)}-{max(years)}"
    create_year_summary(year_range, combined_ed_sdoh, combined_inpt_sdoh, combined_ed_adrd_all, combined_inpt_adrd_all)
    
    print("\nAll summaries exported to output directory.")


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    
    years = [2020, 2021, 2022]
    process_multiple_years(years, quarterly=True)