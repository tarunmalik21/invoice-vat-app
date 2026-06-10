import re

# ----------------------------
# 1. B2B DETECTION
# ----------------------------

B2B_KEYWORDS = [
    "GMBH", "AG", "UG", "KG", "OHG",
    "SARL", "SAS", "SA", "EURL",
    "SRL", "SPA", "SAPA",
    "SL", "BV", "NV",
    "SP. Z O.O", "S.A",
    "LTD", "LIMITED", "LLC", "PLC"
]


def classify_customer_type(text: str):
    text = text.upper()

    for k in B2B_KEYWORDS:
        if k in text:
            return "B2B"

    return "B2C"


# ----------------------------
# 2. COUNTRY DETECTION (FIXED - KEY CHANGE)
# ----------------------------

def detect_country(text: str):
    text = text.upper()

    country_map = {
        "GERMANY": "DE",
        "FRANCE": "FR",
        "ITALY": "IT",
        "SPAIN": "ES",
        "POLAND": "PL",
        "NETHERLANDS": "NL",
        "BELGIUM": "BE",
        "AUSTRIA": "AT",
    }

    for name, code in country_map.items():
        if name in text or code in text:
            return code

    return None


# ----------------------------
# 3. VAT EXTRACTION
# ----------------------------

VAT_PATTERN = {
    "DE": r"DE[0-9]{9}",
    "FR": r"FR[0-9A-Z]{2}[0-9]{9}",
    "IT": r"IT[0-9]{11}",
    "ES": r"ES[A-Z0-9]{9}",
    "NL": r"NL[0-9A-Z]{9}B[0-9]{2}",
    "PL": r"PL[0-9]{10}",
}


def extract_vat(text: str):
    text = text.upper()

    for country, pattern in VAT_PATTERN.items():
        match = re.search(pattern, text)
        if match:
            return match.group(), country

    return None, None


# ----------------------------
# 4. MAIN ENGINE
# ----------------------------

def analyze_invoice(text: str):

    text = text.upper()

    # FIX 1: proper country detection (NOT VAT-based)
    supplier_country = detect_country(text)
    customer_country = detect_country(text)

    # VAT extraction (optional validation)
    supplier_vat, _ = extract_vat(text)
    customer_vat, _ = extract_vat(text)

    # B2B / B2C
    customer_type = classify_customer_type(text)

    # ----------------------------
    # DEFAULT VALUES
    # ----------------------------
    reverse_charge = False
    vat_status = "OK"
    compliance = "COMPLIANT"

    # ----------------------------
    # CROSS BORDER CHECK
    # ----------------------------

    is_cross_border = (
        supplier_country is not None and
        customer_country is not None and
        supplier_country != customer_country
    )

    # ----------------------------
    # B2B RULES (EU CORE LOGIC)
    # ----------------------------
    if customer_type == "B2B":

        if is_cross_border:
            reverse_charge = True
            vat_status = "REVERSE CHARGE APPLIES"

            # if VAT is wrongly charged / missing logic issue
            if not customer_vat:
                vat_status = "MISSING OR INVALID VAT"
                compliance = "NOT COMPLIANT"

        else:
            reverse_charge = False

            if not customer_vat:
                vat_status = "MISSING VAT"
                compliance = "NOT COMPLIANT"

    # ----------------------------
    # B2C RULES
    # ----------------------------
    else:
        reverse_charge = False
        vat_status = "B2C TRANSACTION"

    # ----------------------------
    # OUTPUT
    # ----------------------------
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
