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
}

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
# HELPERS
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


def detect_country(text, vat_country=None):
    text = text.upper()

    if vat_country:
        return vat_country

    for name, code in COUNTRY_MAP.items():
        if name in text:
            return code

    return None


# =========================================================
# B2B DETECTION (FIXED + EU SAFE LOGIC)
# =========================================================

def is_b2b(text, vat_number=None):
    text = text.upper()

    # -----------------------------
    # 1. LEGAL ENTITY SUFFIXES
    # -----------------------------
    keywords = [
        # Germany / Austria
        "GMBH", "AG", "KG", "UG",

        # France
        "SARL", "SAS", "SA", "SNC", "EURL",

        # Italy
        "SRL", "S.R.L", "SPA", "S.P.A",

        # Spain
        "SL", "S.L", "SA",

        # Netherlands / Belgium
        "BV", "NV", "VOF",

        # Poland
        "SP Z OO", "SP. Z O.O",

        # UK / generic
        "LTD", "LIMITED", "PLC", "LLC",

        # Nordic / others
        "AB", "OY", "AS"
    ]

    if any(k in text for k in keywords):
        return True

    # -----------------------------
    # 2. VAT NUMBER (VERY STRONG SIGNAL)
    # -----------------------------
    if vat_number:
        return True

    # -----------------------------
    # 3. BUSINESS KEYWORDS
    # -----------------------------
    business_words = [
        "COMPANY", "CORP", "GROUP", "ENTERPRISE",
        "CONSULTING", "SERVICES", "TECH",
        "SOFTWARE", "INDUSTRIES", "TRADING"
    ]

    if any(w in text for w in business_words):
        return True

    return False


# =========================================================
# MAIN ENGINE
# =========================================================

def analyze_invoice(text: str):

    text = text.upper()

    # -----------------------------
    # SPLIT SECTIONS
    # -----------------------------
    seller_text = get_block(text, ["SELLER", "SUPPLIER", "SPRZEDAWCA"])
    buyer_text = get_block(text, ["BUYER", "CUSTOMER", "NABYWCA"])

    # -----------------------------
    # VAT EXTRACTION
    # -----------------------------
    supplier_vat, supplier_vat_country = extract_vat(seller_text)
    customer_vat, customer_vat_country = extract_vat(buyer_text)

    # -----------------------------
    # COUNTRY DETECTION
    # -----------------------------
    supplier_country = detect_country(seller_text, supplier_vat_country)
    customer_country = detect_country(buyer_text, customer_vat_country)

    # -----------------------------
    # CUSTOMER TYPE (FIXED)
    # -----------------------------
    customer_type = "B2B" if is_b2b(buyer_text, customer_vat) else "B2C"

    # -----------------------------
    # CROSS BORDER CHECK
    # -----------------------------
    cross_border = (
        supplier_country is not None and
        customer_country is not None and
        supplier_country != customer_country
    )

    # -----------------------------
    # VAT DETECTION
    # -----------------------------
    vat_rate_detected = bool(re.search(r"\b23%\b|VAT RATE: 23", text))

    # =====================================================
    # COMPLIANCE ENGINE
    # =====================================================

    if customer_type == "B2B" and cross_border:

        # ❌ WRONG: VAT charged instead of reverse charge
        if vat_rate_detected:
            reverse_charge = False
            vat_status = "VAT CHARGED (INCORRECT FOR CROSS-BORDER B2B)"
            compliance = "NOT COMPLIANT"

        else:
            reverse_charge = True
            vat_status = "REVERSE CHARGE (0% VAT)"
            compliance = "COMPLIANT"

    elif customer_type == "B2B":

        reverse_charge = False

        if vat_rate_detected:
            vat_status = "VAT CHARGED (DOMESTIC B2B)"
            compliance = "COMPLIANT"
        else:
            vat_status = "MISSING VAT (DOMESTIC B2B ERROR)"
            compliance = "NOT COMPLIANT"

    else:

        reverse_charge = False
        vat_status = "B2C VAT APPLIES"
        compliance = "COMPLIANT"

    # -----------------------------
    # RETURN RESULT
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
