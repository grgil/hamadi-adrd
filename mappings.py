import re
from datetime import datetime

# ============================================================================
# REGEX PATTERNS
# ============================================================================

# ICD-10 codes (October 2015 onwards)
# ADRD: All Alzheimer's and related dementias (F01, F02, F03, G30, G31.0, G31.83)
adrd_icd10_pattern = re.compile(r'^(?:F0[123]\.|G30\.|G31\.(?:0|83)).*')

# Z-codes introduced in ICD-10, no ICD-9 equivalent
# SDOH: Z55-Z65 (education, employment, housing, economic, social environment, legal)
z_code_pattern = re.compile(r'Z(?:5[5-9]|6[0-5])(?:\.\d+)?')

# ICD-9 patterns (before October 2015) - TODO: Add ADRD pattern for earlier years if needed
adrd_icd9_pattern = None

# ============================================================================
# COLUMN DEFINITIONS
# ============================================================================

# ED analysis cols
ed_diag_cols = ['REASON_CDE', 'PRINDIAG'] + [f'OTHDIAG{i}' for i in range(1,10)] #OTHDIAG1 - OTHDIAG9
ed_cpt_cols = [f'OTHCPT{i}' for i in range(1,31)]
ed_demog_cols = ["SEX", "AGE", "LOSDAYS", "PT_STATUS", "PAYER", "TCHGS"]
ed_keep_cols = ed_diag_cols + ed_cpt_cols + ed_demog_cols + ["SYS_RECID"]

# Inpatient analysis cols
inpt_diag_cols = ['ADMITDIAG', 'PRINDIAG'] + [f'OTHDIAG{i}' for i in range(1,31)] #OTHDIAG1 - OTHDIAG30
inpt_cpt_cols = ['PRINPROC'] + [f'OTHPROC{i}' for i in range(1,31)]
inpt_demog_cols = ["SEX", "AGE", "LOSDAYS", "DISCHSTAT", "PAYER", "MSDRG", "TCHGS"]
inpt_keep_cols = inpt_diag_cols + inpt_cpt_cols + inpt_demog_cols + ["SYS_RECID"]

# Define population groups
POP_NAMES = ['ADRD+SDOH', 'Any_ADRD', 'Any_SDOH']
SDOH_POP= ['ADRD+SDOH', 'Any_SDOH']

# Define age-comparison bins
AGE_BINS   = [50, 65, 75, 85, 100, 120]
AGE_LABELS = ['50-64', '65-74', '75-84', '85-99', '100+']

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
    