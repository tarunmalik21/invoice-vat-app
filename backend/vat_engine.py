import re

# =========================================================
# 1. COUNTRY DETECTION (VAT + TEXT BASED, MORE RELIABLE)
# =========================================================

VAT_PREFIXES = ["DE", "FR", "IT", "ES", "PL", "NL", "BE", "AT"]


def detect_country(text: str):
    """
    Detect EU country from VAT prefix or text.
    Works even if only VAT number exists.
    """

    text = text.upper()

    # 1. Try VAT prefix detection (BEST METHOD)
    for code in VAT_PREFIXES:
        if re.search(rf"\b{code}[0-9A-Z]", text):
            return code

    # 2. Fallback: country name detection
    country_names = {
        "GERMANY": "DE",
        "FRANCE": "FR",
        "ITALY": "IT",
        "SPAIN": "ES",
        "POLAND": "PL",
        "NETHERLANDS": "NL",
        "BELGIUM": "BE",
        "AUSTRIA": "AT",
    }

    for name, code in country_names.items():
        if name in text:
            return code

    return None


# =========================================================
# 2. B2B / B2C CLASSIFIER
# =========================================================

B2B_KEYWORDS = [
    "GMBH", "AG", "UG", "KG", "OHG",
    "SARL", "SAS", "SA", "EURL",
    "SRL", "SPA", "S.L", "SL",
    "BV", "NV",
    "SP. Z O.O", "S.A",
    "LTD", "LIMITED", "LLC", "PLC"
]


def classify_customer(text: str):
    text = text.upper()

    for k in B2B_KEYWORDS:
        if k in text:
            return "B2B"

    return "B2C"


# =========================================================
# 3. VAT EXTRACTION
# =========================================================

VAT_PATTERN = {
    "DE": r"DE[0-9]{9}",
    "FR": r"FR[0-9A-Z]{2}[0-9]{9}",
    "IT": r"IT[0-9]{11}",
    "ES": r"ES[A-Z0-9]{9}",
    "NL": r"NL[0-9A-Z]{9}B[0-9]{2}",
    "PL": r"PL[0-9]{10}",
    "BE": r"BE[0-9]{10}",
    "AT": r"ATU[0-9]{8}",
}


def extract_vat(text: str):
    text = text.upper()

    for country, pattern in VAT_PATTERN.items():
        match = re.search(pattern, text)
        if match:
            return match.group(), country

    return None, None


# =========================================================
# 4. MAIN ENGINE (EU VAT LOGIC)
# =========================================================

def analyze_invoice(text: str):

    text = text.upper()

    # -----------------------------
    # Extract parties (simplified)
    # -----------------------------
    supplier_country = detect_country(text)
    customer_country = detect_country(text)

    supplier_vat, _ = extract_vat(text)
    customer_vat, _ = extract_vat(text)

    customer_type = classify_customer(text)

    # -----------------------------
    # DEFAULT OUTPUT
    # -----------------------------
    reverse_charge = False
    vat_status = "OK"
    compliance = "COMPLIANT"

    # -----------------------------
    # CROSS BORDER CHECK
    # -----------------------------
    cross_border = (
        supplier_country is not None and
        customer_country is not None and
        supplier_country != customer_country
    )

    # =====================================================
    # RULE ENGINE (EU VAT CORE LOGIC)
    # =====================================================

    if customer_type == "B2B":

        # CASE 1: Cross-border EU B2B → Reverse charge applies
        if cross_border:
            reverse_charge = True
            vat_status = "REVERSE CHARGE"

            # If VAT missing → NOT COMPLIANT
            if not customer_vat or not supplier_vat:
                compliance = "NOT COMPLIANT"

        # CASE 2: Domestic B2B
        else:
            reverse_charge = False

            # Missing VAT = problem
            if not customer_vat or not supplier_vat:
                vat_status = "MISSING VAT"
                compliance = "NOT COMPLIANT"

    else:
        # B2C rules
        reverse_charge = False
        vat_status = "B2C TRANSACTION"

    # -----------------------------
    # FINAL RESULT
    # -----------------------------
    return {
        "customer_type": customer_type,
        "supplier_country": supplier_country,
        "customer_country": customer_country,
        "supplier_vat": supplier_vat,
        "customer_vat": customer_vat,
        "reverse_charge": reverse_charge,
        "vat_status": vat_status,
        "compliance": compliance
    }
