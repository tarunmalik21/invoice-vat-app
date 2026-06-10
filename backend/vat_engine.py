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
    "SWEDEN": "SE",
    "FINLAND": "FI",
    "NORWAY": "NO",
    "SWITZERLAND": "CH",
    "UNITED KINGDOM": "GB",
}

NON_EU = {"NO", "CH", "GB", "US", "IN", "CN", "AE"}

# =========================================================
# VAT PATTERNS
# =========================================================

VAT_PATTERNS = {
    "DE": r"DE[0-9]{9}",
    "FR": r"FR[0-9A-Z]{2}[0-9]{9}",
    "IT": r"IT[0-9]{11}",
    "PL": r"PL[0-9]{10}",
    "ES": r"ES[A-Z0-9]{9}",
    "SE": r"SE[0-9]{12}",
    "NL": r"NL[0-9A-Z]{9}B[0-9]{2}",
}

# =========================================================
# STRICT SECTION EXTRACTION (CRITICAL FIX)
# =========================================================

def extract_section(text, start_keywords):
    text = text.upper()

    for k in start_keywords:
        if k in text:
            section = text.split(k, 1)[1]

            # Stop at next logical block
            end_markers = [
                "BUYER", "CUSTOMER", "NABYWCA",
                "SELLER", "SUPPLIER", "SPRZEDAWCA",
                "INVOICE", "TOTAL", "AMOUNT"
            ]

            for end in end_markers:
                if end in section:
                    section = section.split(end, 1)[0]

            return section.strip()

    return ""

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
# COUNTRY NORMALIZATION
# =========================================================

def normalize_country(text, vat_country=None):
    text = text.upper()

    if vat_country:
        return vat_country

    # Norway OCR fix
    if "NORWAY" in text or "NORG" in text or "NORWEGEN" in text:
        return "NO"

    for name, code in COUNTRY_MAP.items():
        if name in text:
            return code

    return None

# =========================================================
# VAT RATE EXTRACTION
# =========================================================

def extract_vat_rate(text):
    match = re.search(r"(\d{1,2}(\.\d+)?)\s*%", text)
    if match:
        return float(match.group(1))
    return None

# =========================================================
# B2B DETECTION
# =========================================================

def is_b2b(text, vat):
    text = text.upper()

    keywords = [
        "GMBH", "SARL", "SAS", "SA",
        "SRL", "SPA", "LTD", "LIMITED",
        "SP Z OO", "AS", "AB", "OY", "NV", "BV"
    ]

    if vat and vat != "NONE":
        return True

    return any(k in text for k in keywords)

# =========================================================
# MAIN ENGINE
# =========================================================

def analyze_invoice(text: str):

    text = text.upper()

    # =====================================================
    # STEP 1: STRICT SECTION SPLIT (IMPORTANT FIX)
    # =====================================================
    seller_text = extract_section(text, ["SELLER", "SUPPLIER", "SPRZEDAWCA"])
    buyer_text = extract_section(text, ["BUYER", "CUSTOMER", "NABYWCA"])

    # =====================================================
    # STEP 2: VAT EXTRACTION (ONLY FROM SELLER/BUYER BLOCKS)
    # =====================================================
    supplier_vat, supplier_vat_country = extract_vat(seller_text)
    customer_vat, customer_vat_country = extract_vat(buyer_text)

    # FIX: missing VAT must be NONE
    if supplier_vat is None:
        supplier_vat = "NONE"

    if customer_vat is None:
        customer_vat = "NONE"

    # =====================================================
    # STEP 3: COUNTRY DETECTION (BLOCK ONLY)
    # =====================================================
    supplier_country = normalize_country(seller_text, supplier_vat_country)
    customer_country = normalize_country(buyer_text, customer_vat_country)

    # =====================================================
    # STEP 4: VAT RATE (GLOBAL SIGNAL ONLY)
    # =====================================================
    vat_rate = extract_vat_rate(text)

    # =====================================================
    # STEP 5: CUSTOMER TYPE
    # =====================================================
    customer_type = "B2B" if is_b2b(buyer_text, customer_vat) else "B2C"

    # =====================================================
    # STEP 6: CROSS BORDER CHECK
    # =====================================================
    cross_border = (
        supplier_country is not None and
        customer_country is not None and
        supplier_country != customer_country
    )

    # =====================================================
    # STEP 7: RULE ENGINE
    # =====================================================

    # CASE 1: VAT RATE PRESENT (HIGHEST PRIORITY)
    if vat_rate is not None and vat_rate > 0:

        reverse_charge = False

        if supplier_vat == "NONE":
            vat_status = f"VAT CHARGED ({vat_rate}%) - SELLER VAT MISSING"
            compliance = "NOT COMPLIANT"
        else:
            vat_status = f"VAT CHARGED ({vat_rate}%)"
            compliance = "COMPLIANT"

    # CASE 2: NON-EU SUPPLIER
    elif supplier_country in NON_EU:

        reverse_charge = False

        if supplier_vat == "NONE":
            vat_status = "NON-EU SELLER VAT MISSING"
            compliance = "NOT COMPLIANT"
        else:
            vat_status = "NON-EU SUPPLIER"
            compliance = "REQUIRES REVIEW"

    # CASE 3: EU CROSS BORDER B2B
    elif customer_type == "B2B" and cross_border:

        reverse_charge = True

        if supplier_vat == "NONE":
            vat_status = "CROSS BORDER - SELLER VAT MISSING"
            compliance = "NOT COMPLIANT"
        else:
            vat_status = "REVERSE CHARGE (0% VAT)"
            compliance = "COMPLIANT"

    # CASE 4: DOMESTIC B2B
    elif customer_type == "B2B" and supplier_country == customer_country:

        reverse_charge = False

        if supplier_vat == "NONE":
            vat_status = "DOMESTIC B2B - SELLER VAT MISSING"
            compliance = "NOT COMPLIANT"
        else:
            vat_status = "VAT CHARGED (DOMESTIC B2B)"
            compliance = "COMPLIANT"

    # CASE 5: B2C
    else:
        reverse_charge = False
        vat_status = "B2C VAT APPLIES"
        compliance = "COMPLIANT"

    # =====================================================
    # FINAL OUTPUT
    # =====================================================

    return {
        "customer_type": customer_type,
        "supplier_country": supplier_country,
        "customer_country": customer_country,
        "supplier_vat": supplier_vat,
        "customer_vat": customer_vat,
        "vat_rate": vat_rate,
        "reverse_charge": reverse_charge,
        "vat_status": vat_status,
        "compliance": compliance
    }
