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
# STRICT SECTION EXTRACTION
# =========================================================

def extract_section(text, start_keywords):
    text = text.upper()

    for k in start_keywords:
        if k in text:
            section = text.split(k, 1)[1]

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
# VAT EXTRACTION (FIXED - OCR ROBUST)
# =========================================================

def extract_vat(text):
    text = text.upper()

    # 1. Direct VAT patterns (highest priority)
    patterns = [
        r"\bDE[0-9]{9}\b",
        r"\bFR[0-9A-Z]{2}[0-9]{9}\b",
        r"\bIT[0-9]{11}\b",
        r"\bPL[0-9]{10}\b",
        r"\bES[A-Z0-9]{9}\b",
        r"\bSE[0-9]{12}\b",
        r"\bNL[0-9A-Z]{9}B[0-9]{2}\b",
    ]

    for p in patterns:
        m = re.search(p, text)
        if m:
            vat = m.group()
            return vat, vat[:2]

    # 2. Label-based extraction (IMPORTANT FIX)
    label_patterns = [
        r"VAT\s*ID[:\-]?\s*([A-Z]{2}[0-9A-Z]+)",
        r"VAT\s*NUMBER[:\-]?\s*([A-Z]{2}[0-9A-Z]+)",
        r"VAT\s*NO[:\-]?\s*([A-Z]{2}[0-9A-Z]+)",
        r"UID[:\-]?\s*([A-Z]{2}[0-9A-Z]+)",
        r"NIP[:\-]?\s*([A-Z]{2}[0-9A-Z]+)",
    ]

    for p in label_patterns:
        m = re.search(p, text)
        if m:
            vat = m.group(1)
            return vat, vat[:2]

    return None, None

# =========================================================
# COUNTRY NORMALIZATION
# =========================================================

def normalize_country(text, vat_country=None):
    text = text.upper()

    if vat_country:
        return vat_country

    if "NORWAY" in text or "NORG" in text or "NORWEGEN" in text:
        return "NO"

    for name, code in COUNTRY_MAP.items():
        if name in text:
            return code

    return None

# =========================================================
# VAT RATE
# =========================================================

def extract_vat_rate(text):
    match = re.search(r"(\d{1,2}(\.\d+)?)\s*%", text)
    return float(match.group(1)) if match else None

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
    # SECTION EXTRACTION
    # =====================================================
    seller_text = extract_section(text, ["SELLER", "SUPPLIER", "SPRZEDAWCA"])
    buyer_text = extract_section(text, ["BUYER", "CUSTOMER", "NABYWCA", "BILL TO"])

    # =====================================================
    # VAT EXTRACTION (BLOCK + FULL FALLBACK FIX)
    # =====================================================
    supplier_vat, supplier_vat_country = extract_vat(seller_text)
    customer_vat, customer_vat_country = extract_vat(buyer_text)

    # 🔥 FALLBACK (CRITICAL FIX FOR OCR LAYOUT ISSUES)
    if customer_vat is None:
        customer_vat, customer_vat_country = extract_vat(text)

    if supplier_vat is None:
        supplier_vat = "NONE"

    if customer_vat is None:
        customer_vat = "NONE"

    # =====================================================
    # COUNTRY DETECTION
    # =====================================================
    supplier_country = normalize_country(seller_text, supplier_vat_country)
    customer_country = normalize_country(buyer_text, customer_vat_country)

    # fallback safety
    if customer_country is None and customer_vat_country:
        customer_country = customer_vat_country

    # =====================================================
    # VAT RATE
    # =====================================================
    vat_rate = extract_vat_rate(text)

    # =====================================================
    # CUSTOMER TYPE
    # =====================================================
    customer_type = "B2B" if is_b2b(buyer_text, customer_vat) else "B2C"

    # =====================================================
    # CROSS BORDER
    # =====================================================
    cross_border = (
        supplier_country is not None and
        customer_country is not None and
        supplier_country != customer_country
    )

    # =====================================================
    # RULE ENGINE
    # =====================================================

    if vat_rate is not None and vat_rate > 0:

        reverse_charge = False

        if supplier_vat == "NONE":
            vat_status = f"VAT CHARGED ({vat_rate}%) - SELLER VAT MISSING"
            compliance = "NOT COMPLIANT"
        else:
            vat_status = f"VAT CHARGED ({vat_rate}%)"
            compliance = "COMPLIANT"

    elif supplier_country in NON_EU:

        reverse_charge = False

        if supplier_vat == "NONE":
            vat_status = "NON-EU SELLER VAT MISSING"
            compliance = "NOT COMPLIANT"
        else:
            vat_status = "NON-EU SUPPLIER"
            compliance = "REQUIRES REVIEW"

    elif customer_type == "B2B" and cross_border:

        reverse_charge = True

        if supplier_vat == "NONE":
            vat_status = "CROSS BORDER - SELLER VAT MISSING"
            compliance = "NOT COMPLIANT"
        else:
            vat_status = "REVERSE CHARGE (0% VAT)"
            compliance = "COMPLIANT"

    elif customer_type == "B2B" and supplier_country == customer_country:

        reverse_charge = False

        if supplier_vat == "NONE":
            vat_status = "DOMESTIC B2B - SELLER VAT MISSING"
            compliance = "NOT COMPLIANT"
        else:
            vat_status = "VAT CHARGED (DOMESTIC B2B)"
            compliance = "COMPLIANT"

    else:
        reverse_charge = False
        vat_status = "B2C VAT APPLIES"
        compliance = "COMPLIANT"

    # =====================================================
    # OUTPUT
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
