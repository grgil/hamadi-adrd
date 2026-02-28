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

def load_encounter_data(year, care_setting, chunksize=None):
    """
    Load encounter data for specified year and care setting.
    
    """
    care_setting = care_setting.upper()
    
    if care_setting == 'ED':
        filepath = f"{source_dir}/ED_{year}.csv"
    elif care_setting == 'INPATIENT':
        filepath = f"{source_dir}/INPATIENT_{year}.csv"
    else:
        raise ValueError(f"Invalid care_setting: {care_setting}. Must be 'ED' or 'Inpatient'")
    
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
    
    filename = f"{care_setting.lower()}_{filter_type}_{year}.parquet"
    filepath = f"{output_dir}/{filename}"
    
    df_slim.to_parquet(filepath, compression='snappy')
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


# ============================================================================
# ENTRY POINT
# ============================================================================

