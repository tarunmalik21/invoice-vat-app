import re

# =========================================================
# 1. SECTION SPLIT
# =========================================================

def get_block(text, start_keywords):
    text = text.upper()

    for kw in start_keywords:
        if kw in text:
            return text.split(kw, 1)[1]

    return text


# =========================================================
# 2. VAT + COUNTRY DETECTION (FIXED)
# =========================================================

VAT_PATTERNS = {
    "DE": r"DE[0-9]{9}",
    "FR": r"FR[0-9A-Z]{2}[0-9]{9}",
    "IT": r"IT[0-9]{11}",
    "ES": r"ES[A-Z0-9]{9}",
    "PL": r"PL[0-9]{10}",
    "NL": r"NL[0-9A-Z]{9}B[0-9]{2}",
}


def extract_vat(text):
    text = text.upper()

    for country, pattern in VAT_PATTERNS.items():
        match = re.search(pattern, text)
        if match:
            return match.group(), country

    return None, None


def detect_country_from_vat(vat):
    if not vat:
        return None
    return vat[:2]


# =========================================================
# 3. B2B CLASSIFIER
# =========================================================

def is_b2b(text):
    text = text.upper()
    keywords = ["GMBH", "SARL", "SP Z OO", "LTD", "LLC", "SAS", "SA"]

    return any(k in text for k in keywords)


# =========================================================
# 4. MAIN ENGINE (FIXED LOGIC)
# =========================================================

def analyze_invoice(text: str):

    text = text.upper()

    # -----------------------------
    # SPLIT SELLER / BUYER
    # -----------------------------
    seller_text = get_block(text, ["SELLER", "SPRZEDAWCA", "SUPPLIER"])
    buyer_text = get_block(text, ["BUYER", "NABYWCA", "CUSTOMER"])

    # -----------------------------
    # VAT EXTRACTION (KEY FIX)
    # -----------------------------
    supplier_vat, supplier_country = extract_vat(seller_text)
    customer_vat, customer_country = extract_vat(buyer_text)

    # FIX: fallback from VAT prefix
    if supplier_country is None and supplier_vat:
        supplier_country = detect_country_from_vat(supplier_vat)

    if customer_country is None and customer_vat:
        customer_country = detect_country_from_vat(customer_vat)

    # -----------------------------
    # CUSTOMER TYPE
    # -----------------------------
    customer_type = "B2B" if is_b2b(buyer_text) else "B2C"

    # -----------------------------
    # RULES
    # -----------------------------
    reverse_charge = False

    cross_border = (
        supplier_country is not None and
        customer_country is not None and
        supplier_country != customer_country
    )

    # =====================================================
    # EU VAT LOGIC
    # =====================================================

    if customer_type == "B2B":

        if cross_border:
            reverse_charge = True
            vat_status = "REVERSE CHARGE (0% VAT)"

        else:
            vat_status = "VAT CHARGED (LOCAL RATE)"

    else:
        vat_status = "B2C VAT APPLIES"

    # -----------------------------
    # COMPLIANCE LOGIC
    # -----------------------------
    compliance = "COMPLIANT"

    if customer_type == "B2B" and not supplier_vat:
        compliance = "NOT COMPLIANT"

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
