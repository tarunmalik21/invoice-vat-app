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
    "SWEDEN": "SE",
    "FINLAND": "FI",
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
    "ES": r"ES[A-Z0-9]{9}",
    "PL": r"PL[0-9]{10}",
    "SE": r"SE[0-9]{12}",
}

# =========================================================
# HELPERS
# =========================================================

def get_block(text, keys):
    text = text.upper()
    for k in keys:
        if k in text:
            return text.split(k, 1)[1]
    return text


def extract_vat(text):
    text = text.upper()
    for country, pattern in VAT_PATTERNS.items():
        m = re.search(pattern, text)
        if m:
            return m.group(), country
    return None, None


def extract_vat_rate(text):
    """
    Extract VAT like:
    VAT 25%
    VAT RATE: 19%
    """
    match = re.search(r"(\d{1,2}(\.\d+)?)\s*%", text)
    if match:
        return float(match.group(1))
    return None


def detect_country(text, vat_country=None):
    if vat_country:
        return vat_country

    text = text.upper()
    for name, code in COUNTRY_MAP.items():
        if name in text:
            return code
    return None


def is_b2b(text, vat):
    text = text.upper()

    keywords = [
        "GMBH", "SARL", "SAS", "SA", "SP Z OO",
        "SRL", "SPA", "LTD", "LIMITED", "LLC",
        "AS", "AB", "OY", "NV", "BV"
    ]

    if vat:
        return True

    return any(k in text for k in keywords)

# =========================================================
# MAIN ENGINE
# =========================================================

def analyze_invoice(text: str):

    text = text.upper()

    # -------------------------------------------------
    # NORMALIZE LABELS (SELLER / SUPPLIER FIX)
    # -------------------------------------------------
    seller_text = get_block(text, ["SELLER", "SUPPLIER", "SPRZEDAWCA"])
    buyer_text  = get_block(text, ["BUYER", "CUSTOMER", "NABYWCA"])

    # -------------------------------------------------
    # VAT EXTRACTION (STRICTLY SEPARATED)
    # -------------------------------------------------
    supplier_vat, supplier_vat_country = extract_vat(seller_text)
    customer_vat, customer_vat_country = extract_vat(buyer_text)

    # IMPORTANT FIX: DO NOT CROSS-USE VAT
    supplier_vat_missing = supplier_vat is None

    # -------------------------------------------------
    # COUNTRY DETECTION (FIXED)
    # -------------------------------------------------
    supplier_country = detect_country(seller_text, supplier_vat_country)
    customer_country = detect_country(buyer_text, customer_vat_country)

    # -------------------------------------------------
    # VAT RATE (CRITICAL FIX)
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
    # RULE ENGINE (FIXED PRIORITY ORDER)
    # =====================================================

    # -------------------------------------------------
    # CASE 1: VAT RATE PRESENT → OVERRIDES REVERSE CHARGE
    # -------------------------------------------------
    if vat_rate is not None and vat_rate > 0:

        reverse_charge = False

        if supplier_vat_missing:
            vat_status = f"VAT CHARGED ({vat_rate}% - SELLER VAT MISSING ERROR)"
            compliance = "NOT COMPLIANT"
        else:
            vat_status = f"VAT CHARGED ({vat_rate}%)"
            compliance = "COMPLIANT"

    # -------------------------------------------------
    # CASE 2: NON-EU SELLER
    # -------------------------------------------------
    elif supplier_country in NON_EU:

        reverse_charge = False

        if supplier_vat_missing:
            vat_status = "MISSING SELLER VAT (NON-EU)"
            compliance = "NOT COMPLIANT"
        else:
            vat_status = "NON-EU SELLER (REVIEW REQUIRED)"
            compliance = "REQUIRES REVIEW"

    # -------------------------------------------------
    # CASE 3: EU CROSS BORDER B2B
    # -------------------------------------------------
    elif customer_type == "B2B" and cross_border:

        reverse_charge = True

        if supplier_vat_missing:
            vat_status = "MISSING SELLER VAT (CROSS BORDER ERROR)"
            compliance = "NOT COMPLIANT"
        else:
            vat_status = "REVERSE CHARGE (0% VAT)"
            compliance = "COMPLIANT"

    # -------------------------------------------------
    # CASE 4: DOMESTIC B2B
    # -------------------------------------------------
    elif customer_type == "B2B" and supplier_country == customer_country:

        reverse_charge = False

        if supplier_vat_missing:
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
