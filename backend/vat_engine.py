import re

# =========================================================
# COUNTRY MAP
# =========================================================

COUNTRY_MAP = {
    "GERMANY": "DE",
    "FRANCE": "FR",
    "ITALY": "IT",
    "SPAIN": "ES",
    "POLAND": "PL",
    "NETHERLANDS": "NL",
    "BELGIUM": "BE",
    "AUSTRIA": "AT",
    "NORWAY": "NO",
    "SWITZERLAND": "CH",
    "UNITED KINGDOM": "GB",
}

NON_EU_COUNTRIES = {"NO", "CH", "GB", "US", "IN", "CN", "AE"}

# =========================================================
# VAT PATTERNS
# =========================================================

VAT_PATTERNS = {
    "DE": r"DE[0-9]{9}",
    "FR": r"FR[0-9A-Z]{2}[0-9]{9}",
    "IT": r"IT[0-9]{11}",
    "ES": r"ES[A-Z0-9]{9}",
    "PL": r"PL[0-9]{10}",
    "NL": r"NL[0-9A-Z]{9}B[0-9]{2}",
    "BE": r"BE[0-9]{10}",
    "AT": r"ATU[0-9]{8}",
}

# =========================================================
# TEXT BLOCK DETECTION (FIXED)
# =========================================================

def get_block(text, keywords):
    text = text.upper()
    for kw in keywords:
        if kw in text:
            return text.split(kw, 1)[1]
    return text

def extract_vat(text):
    text = text.upper()
    for country, pattern in VAT_PATTERNS.items():
        match = re.search(pattern, text)
        if match:
            return match.group(), country
    return None, None

# =========================================================
# FIXED COUNTRY DETECTION (PRIORITY BASED)
# =========================================================

def detect_country(text, vat_country=None):
    text = text.upper()

    # 1. VAT country is strongest signal
    if vat_country:
        return vat_country

    # 2. Explicit country keywords
    for name, code in COUNTRY_MAP.items():
        if name in text:
            return code

    return None

# =========================================================
# B2B DETECTION (IMPROVED)
# =========================================================

def is_b2b(text, vat_number=None):
    text = text.upper()

    keywords = [
        "GMBH", "AG", "KG", "UG",
        "SARL", "SAS", "SA", "SNC", "EURL",
        "SRL", "SPA", "S.P.A",
        "SL", "S.L",
        "BV", "NV", "VOF",
        "SP Z OO", "SP. Z O.O",
        "LTD", "LIMITED", "LLC",
        "AB", "OY", "AS"
    ]

    if any(k in text for k in keywords):
        return True

    if vat_number:
        return True

    return False

# =========================================================
# MAIN ENGINE
# =========================================================

def analyze_invoice(text: str):

    text = text.upper()

    # -------------------------------------------------
    # SELLER / SUPPLIER FIX (IMPORTANT)
    # -------------------------------------------------
    seller_text = get_block(text, ["SELLER", "SUPPLIER", "SPRZEDAWCA"])
    buyer_text  = get_block(text, ["BUYER", "CUSTOMER", "NABYWCA"])

    # -------------------------------------------------
    # VAT EXTRACTION
    # -------------------------------------------------
    supplier_vat, supplier_vat_country = extract_vat(seller_text)
    customer_vat, customer_vat_country = extract_vat(buyer_text)

    supplier_vat_missing = supplier_vat is None

    # -------------------------------------------------
    # COUNTRY DETECTION (FIXED LOGIC)
    # -------------------------------------------------
    supplier_country = detect_country(seller_text, supplier_vat_country)
    customer_country = detect_country(buyer_text, customer_vat_country)

    # -------------------------------------------------
    # CUSTOMER TYPE
    # -------------------------------------------------
    customer_type = "B2B" if is_b2b(buyer_text, customer_vat) else "B2C"

    # -------------------------------------------------
    # CROSS BORDER
    # -------------------------------------------------
    cross_border = (
        supplier_country is not None and
        customer_country is not None and
        supplier_country != customer_country
    )

    # =====================================================
    # RULE ENGINE
    # =====================================================

    # CASE 1: NON-EU SUPPLIER (IMPORTANT FIX FOR NORWAY)
    if supplier_country and supplier_country in NON_EU_COUNTRIES:

        reverse_charge = False

        if supplier_vat_missing:
            vat_status = "MISSING SUPPLIER VAT (SELLER NON-EU)"
            compliance = "NOT COMPLIANT"
        else:
            vat_status = "NON-EU SELLER (MANUAL REVIEW)"
            compliance = "REQUIRES REVIEW"

    # CASE 2: EU CROSS BORDER B2B
    elif customer_type == "B2B" and cross_border:

        reverse_charge = True

        if supplier_vat_missing:
            vat_status = "MISSING VAT (SELLER CROSS-BORDER ERROR)"
            compliance = "NOT COMPLIANT"
        else:
            vat_status = "REVERSE CHARGE (0% VAT)"
            compliance = "COMPLIANT"

    # CASE 3: DOMESTIC B2B
    elif customer_type == "B2B" and supplier_country == customer_country:

        reverse_charge = False

        if supplier_vat_missing:
            vat_status = "MISSING VAT (SELLER DOMESTIC ERROR)"
            compliance = "NOT COMPLIANT"
        else:
            vat_status = "VAT CHARGED (DOMESTIC B2B)"
            compliance = "COMPLIANT"

    # CASE 4: B2C
    else:
        reverse_charge = False
        vat_status = "B2C VAT APPLIES"
        compliance = "COMPLIANT"

    # -------------------------------------------------
    # OUTPUT
    # -------------------------------------------------
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
