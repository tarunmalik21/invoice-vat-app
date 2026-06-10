import re

# =========================
# VAT VALIDATION ENGINE (EU WIDE)
# =========================

VAT_PATTERNS = {
    # Germany
    "de": r"^DE[0-9]{9}$",

    # France (FR + 2 chars + 9 digits)
    "fr": r"^FR[A-Z0-9]{2}[0-9]{9}$",

    # Italy
    "it": r"^IT[0-9]{11}$",

    # Spain (IMPORTANT: flexible formats)
    "es": r"^ES([A-Z][0-9]{7}[A-Z]|[0-9]{8}|[A-Z0-9][0-9]{7}[A-Z0-9])$",

    # Netherlands
    "nl": r"^NL[0-9]{9}B[0-9]{2}$",

    # Austria
    "at": r"^ATU[0-9]{8}$",

    # Belgium
    "be": r"^BE0[0-9]{9}$",

    # Poland
    "pl": r"^PL[0-9]{10}$",

    # Portugal
    "pt": r"^PT[0-9]{9}$",

    # Czech Republic
    "cz": r"^CZ[0-9]{8,10}$",

    # UK (still used in invoices)
    "uk": r"^GB[0-9]{9}$",

    # USA (non-EU fallback)
    "us": r"^[0-9]{2}-[0-9]{7}$"
}


# =========================
# NORMALIZE VAT
# =========================
def normalize_vat(vat: str):
    if not vat:
        return ""

    return vat.replace(" ", "").upper()


# =========================
# DETECT COUNTRY FROM VAT
# =========================
def detect_vat_country(vat: str):
    vat = normalize_vat(vat)

    if len(vat) < 2:
        return None

    prefix = vat[:2].lower()
    return prefix


# =========================
# VALIDATE VAT
# =========================
def is_valid_vat(vat: str):
    vat = normalize_vat(vat)

    country = detect_vat_country(vat)

    if not country:
        return False

    pattern = VAT_PATTERNS.get(country)

    if not pattern:
        return False

    return bool(re.match(pattern, vat))


# =========================
# CLASSIFY VAT (IMPORTANT FIX)
# =========================
def classify_vat(vat: str):
    vat = normalize_vat(vat)

    if not vat:
        return {
            "valid": False,
            "country": None,
            "type": "MISSING"
        }

    country = detect_vat_country(vat)

    valid = is_valid_vat(vat)

    return {
        "valid": valid,
        "country": country,
        "type": "VALID" if valid else "INVALID"
    }


# =========================
# TEST EXAMPLES
# =========================
test_vats = [
    "ATU12345678",   # Austria
    "NL123456789B01", # Netherlands
    "ESX1234567X",   # Spain (your case)
    "DE123456789",   # Germany
    "FRXX123456789", # France
]

for v in test_vats:
    print(v, "->", classify_vat(v))
