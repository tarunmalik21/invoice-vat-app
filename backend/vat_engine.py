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
# BLOCK EXTRACTION (SELLER / BUYER FIX)
# =========================================================

def get_block(text, keys):
    text = text.upper()
    for k in keys:
        if k in text:
            return text.split(k, 1)[1]
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
# COUNTRY NORMALIZATION (IMPORTANT FIX FOR NORWAY OCR)
# =========================================================

def normalize_country(text, vat_country=None):
    text = text.upper()

    # VAT is strongest signal
    if vat_country:
        return vat_country

    # Norway OCR variations fix
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
        "SRL", "SPA", "LTD", "LIMITED", "LLC",
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

    # -------------------------------------------------
    # SELLER / BUYER BLOCKS
    # -------------------------------------------------
    seller_text = get_block(text, ["SELLER", "SUPPLIER", "SPRZEDAWCA"])
    buyer_text = get_block(text, ["BUYER", "CUSTOMER", "NABYWCA"])

    # -------------------------------------------------
    # VAT EXTRACTION (STRICT SEPARATION)
    # -------------------------------------------------
    supplier_vat, supplier_vat_country = extract_vat(seller_text)
    customer_vat, customer_vat_country = extract_vat(buyer_text)

    # IMPORTANT FIX: if missing → NONE
    if supplier_vat is None:
        supplier_vat = "NONE"

    # -------------------------------------------------
    # COUNTRY DETECTION
    # -------------------------------------------------
    supplier_country = normalize_country(seller_text, supplier_vat_country)
    customer_country = normalize_country(buyer_text, customer_vat_country)

    # -------------------------------------------------
    # VAT RATE (IMPORTANT OVERRIDE SIGNAL)
    # -------------------------------------------------
    vat_rate = extract_vat_rate(text)

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

    # -------------------------------------------------
    # CASE 1: VAT RATE PRESENT → STRONGEST SIGNAL
    # -------------------------------------------------
    if vat_rate is not None and vat_rate > 0:

        reverse_charge = False

        if supplier_vat == "NONE":
            vat_status = f"VAT CHARGED ({vat_rate}%) - SELLER VAT MISSING"
            compliance = "NOT COMPLIANT"
        else:
            vat_status = f"VAT CHARGED ({vat_rate}%)"
            compliance = "COMPLIANT"

    # -------------------------------------------------
    # CASE 2: NON-EU SUPPLIER
    # -------------------------------------------------
    elif supplier_country in NON_EU:

        reverse_charge = False

        if supplier_vat == "NONE":
            vat_status = "MISSING SELLER VAT (NON-EU)"
            compliance = "NOT COMPLIANT"
        else:
            vat_status = "NON-EU SUPPLIER (REVIEW REQUIRED)"
            compliance = "REQUIRES REVIEW"

    # -------------------------------------------------
    # CASE 3: EU CROSS BORDER B2B
    # -------------------------------------------------
    elif customer_type == "B2B" and cross_border:

        reverse_charge = True

        if supplier_vat == "NONE":
            vat_status = "MISSING SELLER VAT (CROSS-BORDER ERROR)"
            compliance = "NOT COMPLIANT"
        else:
            vat_status = "REVERSE CHARGE (0% VAT)"
            compliance = "COMPLIANT"

    # -------------------------------------------------
    # CASE 4: DOMESTIC B2B
    # -------------------------------------------------
    elif customer_type == "B2B" and supplier_country == customer_country:

        reverse_charge = False

        if supplier_vat == "NONE":
            vat_status = "MISSING SELLER VAT (DOMESTIC ERROR)"
            compliance = "NOT COMPLIANT"
        else:
            vat_status = "VAT CHARGED (DOMESTIC B2B)"
            compliance = "COMPLIANT"

    # -------------------------------------------------
    # CASE 5: B2C
    # -------------------------------------------------
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
        "vat_rate": vat_rate,
        "reverse_charge": reverse_charge,
        "vat_status": vat_status,
        "compliance": compliance
    }
