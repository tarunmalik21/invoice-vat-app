import re
import streamlit as st

# =========================
# VAT VALIDATION ENGINE (EU WIDE)
# =========================

VAT_PATTERNS = {
    "de": r"^DE[0-9]{9}$",
    "fr": r"^FR[A-Z0-9]{2}[0-9]{9}$",
    "it": r"^IT[0-9]{11}$",
    "es": r"^ES([A-Z][0-9]{7}[A-Z]|[0-9]{8}|[A-Z0-9][0-9]{7}[A-Z0-9])$",
    "nl": r"^NL[0-9]{9}B[0-9]{2}$",
    "at": r"^ATU[0-9]{8}$",
    "be": r"^BE0[0-9]{9}$",
    "pl": r"^PL[0-9]{10}$",
    "pt": r"^PT[0-9]{9}$",
    "cz": r"^CZ[0-9]{8,10}$",
    "uk": r"^GB[0-9]{9}$",
    "us": r"^[0-9]{2}-[0-9]{7}$"
}

# =========================
# FUNCTIONS
# =========================

def normalize_vat(vat: str):
    if not vat:
        return ""
    return vat.replace(" ", "").upper()


def detect_vat_country(vat: str):
    vat = normalize_vat(vat)
    if len(vat) < 2:
        return None
    return vat[:2].lower()


def is_valid_vat(vat: str):
    vat = normalize_vat(vat)
    country = detect_vat_country(vat)

    if not country:
        return False

    pattern = VAT_PATTERNS.get(country)

    if not pattern:
        return False

    return bool(re.match(pattern, vat))


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
# STREAMLIT UI
# =========================

st.set_page_config(page_title="EU VAT Checker", layout="centered")

st.title("🧾 EU VAT Invoice Checker")
st.write("Validate EU VAT numbers instantly (Germany, France, Italy, Spain, etc.)")

# Single input mode
vat_input = st.text_input("Enter VAT Number")

if vat_input:
    result = classify_vat(vat_input)
    st.subheader("Result")
    st.json(result)


st.divider()

# Batch mode
st.subheader("Batch VAT Checker")

vat_list = st.text_area(
    "Enter multiple VAT numbers (one per line)",
    height=150
)

if st.button("Validate Batch"):
    vats = [v.strip() for v in vat_list.split("\n") if v.strip()]

    results = []

    for v in vats:
        r = classify_vat(v)
        results.append({
            "VAT": v,
            "Country": r["country"],
            "Status": r["type"],
            "Valid": r["valid"]
        })

    st.table(results)


# =========================
# TEST SECTION (OPTIONAL)
# =========================

st.divider()
st.subheader("Sample Test Data")

test_vats = [
    "ATU12345678",
    "NL123456789B01",
    "ESX1234567X",
    "DE123456789",
    "FRXX123456789",
]

for v in test_vats:
    st.write(v, classify_vat(v))
