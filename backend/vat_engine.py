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
# SECTION SPLITTER (SELLER / BUYER SAFE)
# =========================================================

def extract_section(text, start_keywords, end_keywords):
    text = text.upper()

    for k in start_keywords:
        if k in text:
            start_index = text.index(k)
            section = text[start_index:]

            cut_positions = []
            for end in end_keywords:
                pos = section.find(end)
                if pos != -1:
                    cut_positions.append(pos)

            if cut_positions:
                section = section[:min(cut_positions)]

            return section.strip()

    return ""

# =========================================================
# VAT EXTRACTION
# =========================================================

def extract_vat(text):
    text = text.upper()

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

    label_patterns = [
        r"VAT\s*ID[:\-]?\s*([A-Z]{2}[0-9A-Z]+)",
        r"VAT\s*NUMBER[:\-]?\s*([A-Z]{2}[0-9A-Z]+)",
        r"VAT\s*NO[:\-]?\s*([A-Z]{2}[0-9A-Z]+)",
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

    for name, code in COUNTRY_MAP.items():
        if name in text:
            return code

    return None

# =========================================================
# VAT RATE EXTRACTION (OCR PRIORITY)
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
        "SP Z OO", "AS", "AB", "BV", "NV", "OY"
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
    # SELLER / BUYER SPLIT
    # =====================================================

    seller_text = extract_section(
        text,
        ["SELLER", "SUPPLIER", "SPRZEDAWCA"],
        ["BUYER", "CUSTOMER", "NABYWCA"]
    )

    buyer_text = extract_section(
        text,
        ["BUYER", "CUSTOMER", "NABYWCA"],
        ["SELLER", "SUPPLIER", "SPRZEDAWCA"]
    )

    # =====================================================
    # VAT EXTRACTION
    # =====================================================

    supplier_vat, supplier_vat_country = extract_vat(seller_text)
    customer_vat, customer_vat_country = extract_vat(buyer_text)

    supplier_vat = supplier_vat if supplier_vat else "NONE"
    customer_vat = customer_vat if customer_vat else "NONE"

    # =====================================================
    # COUNTRY DETECTION
    # =====================================================

    supplier_country = normalize_country(seller_text, supplier_vat_country)
    customer_country = normalize_country(buyer_text, customer_vat_country)

    # =====================================================
    # VAT RATE (OCR PRIORITY FIELD)
    # =====================================================

    vat_rate = extract_vat_rate(text)

    # =====================================================
    # CUSTOMER TYPE
    # =====================================================

    customer_type = "B2B" if is_b2b(buyer_text, customer_vat) else "B2C"

    # =====================================================
    # CROSS BORDER CHECK
    # =====================================================

    cross_border = (
        customer_type == "B2B"
        and supplier_country is not None
        and customer_country is not None
        and supplier_country != customer_country
    )

    # =====================================================
    # RULE ENGINE (FINAL PRIORITY LOGIC)
    # =====================================================

    reverse_charge = False

    # 🥇 PRIORITY 1: OCR VAT EXISTS (OVERRIDES EVERYTHING)
    if vat_rate is not None:

        reverse_charge = False
        vat_status = f"VAT CHARGED ({vat_rate}%)"

        if supplier_vat == "NONE":
            compliance = "NOT COMPLIANT"
        else:
            compliance = "COMPLIANT"

    # 🥈 PRIORITY 2: CROSS BORDER B2B (ONLY IF NO VAT FOUND)
    elif cross_border:

        reverse_charge = True

        if supplier_vat == "NONE":
            vat_status = "REVERSE CHARGE (0% VAT) - SELLER VAT MISSING"
            compliance = "NOT COMPLIANT"
        else:
            vat_status = "REVERSE CHARGE (0% VAT)"
            compliance = "COMPLIANT"

    # 🥉 PRIORITY 3: DOMESTIC B2B
    elif customer_type == "B2B" and supplier_country == customer_country:

        reverse_charge = False

        if supplier_vat == "NONE":
            vat_status = "VAT CHARGED (DOMESTIC B2B - MISSING SELLER VAT)"
            compliance = "NOT COMPLIANT"
        else:
            vat_status = "VAT CHARGED (DOMESTIC B2B)"
            compliance = "COMPLIANT"

    # NON-EU SUPPLIER
    elif supplier_country in NON_EU:

        reverse_charge = False
        vat_status = "NON-EU SUPPLIER"
        compliance = "REQUIRES REVIEW"

    # B2C DEFAULT
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
