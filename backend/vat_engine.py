import re

# =========================================================
# COUNTRY DETECTION MAP (ADDRESS-BASED)
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
# VAT REGEX PATTERNS
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
# EXTRACT BLOCKS
# =========================================================

def get_block(text, keywords):
    text = text.upper()

    for kw in keywords:
        if kw in text:
            return text.split(kw, 1)[1]

    return text


# =========================================================
# VAT EXTRACTION
# =========================================================

def extract_vat(text):
    text = text.upper()

    for country, pattern in VAT_PATTERNS.items():
        match = re.search(pattern, text)
        if match:
            return match.group(), country

    return None, None


# =========================================================
# COUNTRY DETECTION (FIXED LOGIC)
# =========================================================

def detect_country(text, vat_country=None):
    text = text.upper()

    # 1. VAT-based detection (strong signal)
    if vat_country:
        return vat_country

    # 2. Address-based detection (NEW FIX)
    for name, code in COUNTRY_MAP.items():
        if name in text:
            return code

    return None


# =========================================================
# B2B CLASSIFIER
# =========================================================

def is_b2b(text):
    text = text.upper()

    keywords = [
        "GMBH", "SARL", "SAS", "SA",
        "SP Z OO", "SP. Z O.O",
        "LTD", "LLC", "AG", "BV", "NV"
    ]

    return any(k in text for k in keywords)


# =========================================================
# MAIN ENGINE (FINAL LOGIC)
# =========================================================

def analyze_invoice(text: str):

    text = text.upper()

    # -----------------------------
    # SPLIT SELLER / BUYER
    # -----------------------------
    seller_text = get_block(text, ["SELLER", "SUPPLIER", "SPRZEDAWCA"])
    buyer_text = get_block(text, ["BUYER", "CUSTOMER", "NABYWCA"])

    # -----------------------------
    # VAT EXTRACTION
    # -----------------------------
    supplier_vat, supplier_vat_country = extract_vat(seller_text)
    customer_vat, customer_vat_country = extract_vat(buyer_text)

    # -----------------------------
    # COUNTRY DETECTION (FIXED)
    # -----------------------------
    supplier_country = detect_country(seller_text, supplier_vat_country)
    customer_country = detect_country(buyer_text, customer_vat_country)

    # -----------------------------
    # CUSTOMER TYPE
    # -----------------------------
    customer_type = "B2B" if is_b2b(buyer_text) else "B2C"

    # -----------------------------
    # CROSS BORDER CHECK
    # -----------------------------
    cross_border = (
        supplier_country is not None and
        customer_country is not None and
        supplier_country != customer_country
    )

    # -----------------------------
    # VAT RULE ENGINE (FIXED)
    # -----------------------------
    if customer_type == "B2B" and cross_border:
        reverse_charge = True
        vat_status = "REVERSE CHARGE (0% VAT)"
        compliance = "COMPLIANT"

    elif customer_type == "B2B":
        reverse_charge = False
        vat_status = "VAT CHARGED (LOCAL RATE)"
        compliance = "COMPLIANT"

    else:
        reverse_charge = False
        vat_status = "B2C VAT APPLIES"
        compliance = "COMPLIANT"

    # -----------------------------
    # FINAL OUTPUT
    # -----------------------------
    return {
        "customer_type": customer_type,

        # SELLER
        "supplier_country": supplier_country,
        "supplier_vat": supplier_vat,

        # BUYER (CUSTOMER)
        "customer_country": customer_country,
        "customer_vat": customer_vat,

        # RULES
        "reverse_charge": reverse_charge,
        "vat_status": vat_status,
        "compliance": compliance
    }
