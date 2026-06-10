import re

# =========================================================
# 1. SECTION EXTRACTION (SELLER / BUYER)
# =========================================================

def get_block(text, start_keywords, end_keywords=None):
    """
    Extracts seller/buyer section from invoice text.
    """
    text = text.upper()

    start_pos = -1

    for kw in start_keywords:
        if kw in text:
            start_pos = text.find(kw)
            break

    if start_pos == -1:
        return text

    if not end_keywords:
        return text[start_pos:]

    end_pos = len(text)

    for kw in end_keywords:
        if kw in text[start_pos:]:
            end_pos = text.find(kw, start_pos)
            break

    return text[start_pos:end_pos]


# =========================================================
# 2. COUNTRY DETECTION (VAT + TEXT)
# =========================================================

VAT_PREFIXES = ["DE", "FR", "IT", "ES", "PL", "NL", "BE", "AT"]

def detect_country(text: str):
    text = text.upper()

    # Detect VAT prefix
    for code in VAT_PREFIXES:
        if re.search(rf"\b{code}[0-9A-Z]", text):
            return code

    # Detect country names
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
        if name in text:
            return code

    return None


# =========================================================
# 3. VAT EXTRACTION
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


def extract_vat(text: str):
    text = text.upper()

    for country, pattern in VAT_PATTERNS.items():
        match = re.search(pattern, text)
        if match:
            return match.group(), country

    return None, None


# =========================================================
# 4. B2B CLASSIFICATION
# =========================================================

B2B_KEYWORDS = [
    "GMBH", "AG", "UG", "KG", "OHG",
    "SARL", "SAS", "SA", "EURL",
    "SRL", "SPA", "S.L", "SL",
    "BV", "NV",
    "SP. Z O.O", "S.A",
    "LTD", "LIMITED", "LLC", "PLC"
]


def classify_customer(text: str):
    text = text.upper()

    for k in B2B_KEYWORDS:
        if k in text:
            return "B2B"

    return "B2C"


# =========================================================
# 5. MAIN ENGINE (FIXED EU VAT LOGIC)
# =========================================================

def analyze_invoice(text: str):

    text = text.upper()

    # -----------------------------
    # SPLIT SELLER / BUYER (FIXED)
    # -----------------------------
    seller_text = get_block(
        text,
        ["SELLER", "SUPPLIER", "SPRZEDAWCA"]
    )

    buyer_text = get_block(
        text,
        ["BUYER", "CUSTOMER", "NABYWCA"]
    )

    # -----------------------------
    # SELLER DATA
    # -----------------------------
    supplier_country = detect_country(seller_text)
    supplier_vat, _ = extract_vat(seller_text)

    # -----------------------------
    # BUYER DATA
    # -----------------------------
    customer_country = detect_country(buyer_text)
    customer_vat, _ = extract_vat(buyer_text)

    # -----------------------------
    # CUSTOMER TYPE
    # -----------------------------
    customer_type = classify_customer(buyer_text)

    # -----------------------------
    # DEFAULT OUTPUT
    # -----------------------------
    reverse_charge = False
    vat_status = "OK"
    compliance = "COMPLIANT"

    # -----------------------------
    # CROSS BORDER CHECK
    # -----------------------------
    cross_border = (
        supplier_country is not None and
        customer_country is not None and
        supplier_country != customer_country
    )

    # =====================================================
    # EU VAT RULE ENGINE
    # =====================================================

    if customer_type == "B2B":

        # CROSS BORDER EU → REVERSE CHARGE
        if cross_border:
            reverse_charge = True
            vat_status = "REVERSE CHARGE"

            # If VAT missing → NOT COMPLIANT
            if not supplier_vat or not customer_vat:
                compliance = "NOT COMPLIANT"

        # DOMESTIC B2B
        else:
            reverse_charge = False

            if not supplier_vat or not customer_vat:
                vat_status = "MISSING VAT"
                compliance = "NOT COMPLIANT"

    else:
        vat_status = "B2C TRANSACTION"
        reverse_charge = False

    # -----------------------------
    # FINAL OUTPUT
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
