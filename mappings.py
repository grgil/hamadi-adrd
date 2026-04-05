import re
from datetime import datetime

# ============================================================================
# REGEX PATTERNS
# ============================================================================

# ICD-10 codes (October 2015 onwards)
# ADRD: F01.50, F01.51, F02.80, F02.81 (vascular dementia, dementia in other diseases)
adrd_icd10_pattern = re.compile(r'^F0[12]\.(?:5[01]|8[01]).*')

# SDOH: Z55-Z65 (education, employment, housing, economic, social environment, legal)
sdoh_icd10_pattern = re.compile(r"^Z(?:5[5-9]|6[0-5])(?:\.\d+)?$")

# ICD-9 codes (before October 2015) - TODO: Add patterns in future sprint
adrd_icd9_pattern = None
sdoh_icd9_pattern = None

# Compile SDOH regex patterns once at module level
z_code_pattern = re.compile(r'Z5[5-9](?:\.\d+)?|Z6[0-5](?:\.\d+)?')

# ============================================================================
# COLUMN DEFINITIONS
# ============================================================================

# ED analysis cols
ed_diag_cols = ['REASON_CDE', 'PRINDIAG'] + [f'OTHDIAG{i}' for i in range(1,10)] #OTHDIAG1 - OTHDIAG9
ed_cpt_cols = [f'OTHCPT{i}' for i in range(1,31)]
ed_demog_cols = ["SEX", "AGE", "LOSDAYS", "PT_STATUS", "PAYER", "TCHGS"]
ed_keep_cols = ed_diag_cols + ed_cpt_cols + ed_demog_cols

# Inpatient analysis cols
inpt_diag_cols = ['ADMITDIAG', 'PRINDIAG'] + [f'OTHDIAG{i}' for i in range(1,31)] #OTHDIAG1 - OTHDIAG30
inpt_cpt_cols = ['PRINPROC'] + [f'OTHPROC{i}' for i in range(1,31)]
inpt_demog_cols = ["SEX", "AGE", "LOSDAYS", "DISCHSTAT", "PAYER", "MSDRG", "TCHGS"]
inpt_keep_cols = inpt_diag_cols + inpt_cpt_cols + inpt_demog_cols 

# Define population groups
POP_NAMES = ['ADRD+SDOH', 'Any_ADRD', 'Any_SDOH']
SDOH_POP= ['ADRD+SDOH', 'Any_SDOH']

# ============================================================================
# Z-CODE CATEGORY MAPPINGS
# ============================================================================

z_code_categories = [
    'Education/Literacy',           # Z55
    'Employment',                   # Z56
    'Occupational Exposure',        # Z57
    'Physical Environment',         # Z58
    'Housing/Economic',             # Z59
    'Social Environment',           # Z60
    'Upbringing',                   # Z61
    'Family/Household',             # Z62
    'Other Psychosocial'            # Z63-Z65
    ]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_adrd_pattern(year):
    """
    Return correct ADRD diagnosis code pattern for year.
    Uses ICD-9 before October 2015, ICD-10 after.
    """
    if year < 2015:
        return adrd_icd9_pattern
    else: 
        return adrd_icd10_pattern
    
def get_sdoh_pattern(year):
    """
    Return correct SDOH diagnosis code pattern for year.
    Uses ICD-9 before October 2015, ICD-10 after.
    """
    if year < 2015:
        return sdoh_icd9_pattern
    else:
        return sdoh_icd10_pattern
    
def categorize_z_code(code):
    """
    Map Z-code to category based on numeric portion.
    """
    code_num = int(code[1:3])
    
    if code_num <= 62:
        return z_code_categories[code_num - 55]
    else:
        return z_code_categories[8]          

def timestamp_print(message):
    """Print message with timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")     
    