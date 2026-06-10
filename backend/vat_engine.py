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
# SECTION SPLIT
# =========================================================

def extract_section(text, start_keywords, end_keywords):
    text = text.upper()

    for k in start_keywords:
        if k in text:
            start = text.index(k)
            section = text[start:]

            ends = []
            for e in end_keywords:
                pos = section.find(e)
                if pos != -1:
                    ends.append(pos)

            if ends:
                section = section[:min(ends)]

            return section.strip()

    return ""

# =========================================================
# OCR ONLY: VAT RATE
# =========================================================

def extract_vat_rate(text):
    match = re.search(r"(\d{1,2}(\.\d+)?)\s*%", text)
    return float(match.group(1)) if match else None

# =========================================================
# OCR ONLY: VAT NUMBER
# =========================================================

def extract_vat(text):
    text = text.upper()

    pattern = r"\b([A-Z]{2}[0-9A-Z]{8,12})\b"
    m = re.search(pattern, text)

    if m:
        vat = m.group(1)
        return vat, vat[:2]

    return None, None

# =========================================================
# OCR ONLY: COUNTRY
# =========================================================

def extract_country(text, vat_country=None):
    text = text.upper()

    if vat_country:
        return vat_country

    for name, code in COUNTRY_MAP.items():
        if name in text:
            return code

    return None

# =========================================================
# B2B DETECTION
# =========================================================

def is_b2b(text, vat):
    text = text.upper()

    keywords = [
        "GMBH", "SARL", "SAS", "SA",
        "SRL", "SPA", "LTD", "LIMITED",
        "SP Z OO", "AS", "AB", "BV", "NV"
    ]

    if vat:
        return True

    return any(k in text for k in keywords)

# =========================================================
# MAIN ENGINE
# =========================================================

def analyze_invoice(text):

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
    # 🥇 LAYER 1: OCR ONLY (NO LOGIC)
    # =====================================================

    supplier_vat, supplier_vat_country = extract_vat(seller_text)
    customer_vat, customer_vat_country = extract_vat(buyer_text)

    supplier_country = extract_country(seller_text, supplier_vat_country)
    customer_country = extract_country(buyer_text, customer_vat_country)

    vat_rate = extract_vat_rate(text)

    # FIX NULLS
    supplier_vat = supplier_vat if supplier_vat else "NONE"
    customer_vat = customer_vat if customer_vat else "NONE"

    # =====================================================
    # 🥈 LAYER 2: BUSINESS LOGIC ONLY
    # =====================================================

    customer_type = "B2B" if is_b2b(buyer_text, customer_vat) else "B2C"

    reverse_charge = False

    cross_border = (
        supplier_country is not None and
        customer_country is not None and
        supplier_country != customer_country
    )

    # RULE 1: DOMESTIC
    if customer_type == "B2B" and not cross_border:
        reverse_charge = False
        compliance = "COMPLIANT"

    # RULE 2: CROSS BORDER B2B
    elif customer_type == "B2B" and cross_border:
        reverse_charge = True
        compliance = "COMPLIANT" if supplier_vat != "NONE" else "NOT COMPLIANT"

    # RULE 3: B2C
    else:
        reverse_charge = False
        compliance = "COMPLIANT"

    # =====================================================
    # OUTPUT (STRICT SEPARATION)
    # =====================================================

    return {
        # OCR ONLY
        "supplier_country": supplier_country,
        "customer_country": customer_country,
        "supplier_vat": supplier_vat,
        "customer_vat": customer_vat,
        "vat_rate": vat_rate,

        # LOGIC ONLY
        "customer_type": customer_type,
        "reverse_charge": reverse_charge,
        "compliance": compliance
    }
