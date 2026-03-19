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
    
    suffix = 'ED.csv' if care_setting == 'ED' else 'IP.csv'
    year_short = str(year)[-2:]
    
    quarterly_dfs = []
    
    for quarter in range(1, 5):
        filename = f"{year_short}Q{quarter}_{suffix}"
        filepath = f"{source_dir}/{filename}"
        
        print(f"  Loading {filename}...")
        quarter_df = pd.read_csv(filepath, low_memory=False)
        quarterly_dfs.append(quarter_df)
        print(f"    {len(quarter_df)} rows")
    
    annual_df = pd.concat(quarterly_dfs, ignore_index=True)
    print(f"Combined {year} {care_setting}: {len(annual_df)} total rows")
    
    return annual_df

def load_encounter_data(year, care_setting, quarterly=True, chunksize=None):
    """
    Load encounter data for specified year and care setting.
    
    """
    if quarterly:
        return aggregate_quarterly_data(year, care_setting)
    
    else:
        care_setting = care_setting.upper()
        
        if care_setting == 'ED':
            filepath = f"{source_dir}/ED_{year}.csv"
        else:  # INPATIENT
            filepath = f"{source_dir}/INPATIENT_{year}.csv"
        
        print(f"Loading {care_setting} data from {filepath}...")
        
        if chunksize:
            return pd.read_csv(filepath, chunksize=chunksize, low_memory=False)
        else:
            df = pd.read_csv(filepath, low_memory=False)
            print(f"  Loaded {len(df)} rows")
            return df

def save_filtered_data(df, year, care_setting, filter_type):
    """Save filtered encounters with only analysis columns."""
    
    if care_setting == 'ED':
        cols = [c for c in ed_keep_cols if c in df.columns]
    else:
        cols = [c for c in inpt_keep_cols if c in df.columns]
    
    df_slim = df[cols].copy()
    
    filename = f"{care_setting.lower()}_{filter_type}_{year}.csv"
    filepath = f"{output_dir}/{filename}"
    
    df_slim.to_csv(filepath)
    print(f"Saved {len(df_slim)} rows to {filepath}")

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
    print(f"  Found {len(filtered)} encounters with ADRD")
    
    return filtered

def filter_adrd_with_sdoh(df, diag_cols, year):
    """
    Filter to encounters with ADRD AND SDOH codes.
    """
    adrd_df = filter_adrd_only(df, diag_cols, year)
    
    # Add SDOH requirement
    sdoh_pattern = get_sdoh_pattern(year)
    sdoh_mask = has_code_pattern(adrd_df, diag_cols, sdoh_pattern)
    
    filtered = adrd_df[sdoh_mask].copy()
    print(f"  Found {len(filtered)} encounters with ADRD + SDOH")
    
    return filtered

def extract_all_z_codes(row, diag_cols):

    z_codes = []
    
    for col in diag_cols:
        if pd.notna(row[col]):
            matches = re.findall(r'Z5[5-9](?:\.\d+)?|Z6[0-5](?:\.\d+)?', str(row[col]))
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
    ed_counts = pd.Series([code for codes in ed_z for code in codes]).value_counts()
    inpt_counts = pd.Series([code for codes in inpt_z for code in codes]).value_counts()
    
    # ALL UNIQUE CODES
    all_codes = sorted(set(ed_counts.index.tolist() + inpt_counts.index.tolist()))
    
    summary_data = []
    
    # Z CODE COUNT PER ROW
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
    
    ed_total = summary['ED_Count'].sum()
    inpt_total = summary['Inpatient_Count'].sum()
    
    summary['ED_Percent'] = (summary['ED_Count'] / ed_total * 100).round(1)
    summary['Inpatient_Percent'] = (summary['Inpatient_Count'] / inpt_total * 100).round(1)
    summary['Total_Count'] = summary['ED_Count'] + summary['Inpatient_Count']
    summary['Total_Percent'] = (summary['Total_Count'] / summary['Total_Count'].sum() * 100).round(1)
    
    return summary

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    
    print("="*60)
    print("TESTING Z-CODE EXTRACTION (2020 ANNUAL FILES)")
    print("="*60)
    
    # Load data
    print("\nLoading ED data...")
    ed_df = load_encounter_data(2020, 'ED', quarterly=False)
    
    print("\nLoading Inpatient data...")
    inpt_df = load_encounter_data(2020, 'Inpatient', quarterly=False)
    
    # Filter to ADRD+SDOH
    print("\nFiltering ED to ADRD+SDOH...")
    ed_filtered = filter_adrd_with_sdoh(ed_df, ed_diag_cols, 2020)
    
    print("\nFiltering Inpatient to ADRD+SDOH...")
    inpt_filtered = filter_adrd_with_sdoh(inpt_df, inpt_diag_cols, 2020)
    
    # Extract Z-codes
    print("\nExtracting Z-codes...")
    ed_z = ed_filtered.apply(lambda row: extract_all_z_codes(row, ed_diag_cols), axis=1)
    inpt_z = inpt_filtered.apply(lambda row: extract_all_z_codes(row, inpt_diag_cols), axis=1)
    
    # Create summary table
    print("\nCreating Z-code summary table...")
    z_summary = create_z_code_summary(ed_z, inpt_z)
    
    # Display
    print("\n" + "="*60)
    print("Z-CODE SUMMARY")
    print("="*60)
    print(z_summary.to_string(index=False))
    
    # Save
    output_file = f"{output_dir}/z_code_summary_2020.csv"
    z_summary.to_csv(output_file, index=False)
    print(f"\nSaved summary to {output_file}")