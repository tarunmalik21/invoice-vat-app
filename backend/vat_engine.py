import re
print("🔥 VAT ENGINE ACTIVE - NEW CODE LOADED")
# ----------------------------
# 1. B2B COMPANY DETECTION
# ----------------------------

B2B_KEYWORDS = [
    "GMBH", "AG", "UG", "KG", "OHG",
    "SARL", "SAS", "SA", "EURL",
    "SRL", "SPA", "SAPA",
    "SL", "BV", "NV",
    "SP. Z O.O", "S.A",
    "LTD", "LIMITED", "LLC", "PLC"
]


def classify_customer_type(text: str):
    text = text.upper()

    for k in B2B_KEYWORDS:
        if k in text:
            return "B2B"

    return "B2C"


# ----------------------------
# 2. VAT EXTRACTION
# ----------------------------

VAT_PATTERN = {
    "DE": r"DE[0-9]{9}",
    "FR": r"FR[0-9A-Z]{2}[0-9]{9}",
    "IT": r"IT[0-9]{11}",
    "ES": r"ES[A-Z0-9]{9}",
    "NL": r"NL[0-9A-Z]{9}B[0-9]{2}",
    "PL": r"PL[0-9]{10}",
}


def extract_vat(text: str):
    text = text.upper()

    for country, pattern in VAT_PATTERN.items():
        match = re.search(pattern, text)
        if match:
            return match.group(), country

    return None, None


# ----------------------------
# 3. SECTION EXTRACTION (simple but stable)
# ----------------------------

def extract_section(text, keyword):
    lines = text.split("\n")
    capture = False
    buffer = []

    for line in lines:
        if keyword.upper() in line.upper():
            capture = True
            continue

        if capture and any(x in line.upper() for x in ["SELLER", "BUYER", "SUPPLIER", "CUSTOMER"]):
            if keyword.upper() not in line.upper():
                break

        if capture:
            buffer.append(line)

    return "\n".join(buffer)


def extract_party_vat(text, role):
    section = extract_section(text, role)
    return extract_vat(section)


# ----------------------------
# 4. MAIN ENGINE
# ----------------------------

def analyze_invoice(text: str):

    # Extract supplier & customer separately
    supplier_vat, supplier_country = extract_party_vat(text, "SELLER")
    customer_vat, customer_country = extract_party_vat(text, "BUYER")

    # fallback if structure unclear
    if not supplier_vat:
        supplier_vat, supplier_country = extract_vat(text)

    if not customer_vat:
        customer_vat, customer_country = extract_vat(text)

    # ----------------------------
    # CUSTOMER TYPE
    # ----------------------------
    customer_type = classify_customer_type(text)

    # ----------------------------
    # DEFAULT VALUES
    # ----------------------------
    reverse_charge = False
    vat_status = "OK"
    compliance = "COMPLIANT"

    # ----------------------------
    # EU LOGIC CORE
    # ----------------------------

    is_cross_border = (
        supplier_country is not None and
        customer_country is not None and
        supplier_country != customer_country
    )

    # ----------------------------
    # B2B RULES
    # ----------------------------
    if customer_type == "B2B":

        # Case 1: cross-border EU service
        if is_cross_border:
            reverse_charge = True
            vat_status = "REVERSE CHARGE APPLIES"

            # VAT missing = critical error
            if not customer_vat:
                compliance = "NOT COMPLIANT"
                vat_status = "MISSING CUSTOMER VAT"

        # Case 2: same country B2B
        else:
            reverse_charge = False

            if not customer_vat:
                vat_status = "MISSING CUSTOMER VAT"
                compliance = "NOT COMPLIANT"

    # ----------------------------
    # B2C RULES
    # ----------------------------
    else:
        reverse_charge = False

        # If VAT wrongly applied in B2C, still basic check
        vat_status = "B2C TRANSACTION"

    # ----------------------------
    # FINAL OUTPUT
    # ----------------------------
    return {
        "customer_type": customer_type,
        "supplier_vat": supplier_vat,
        "customer_vat": customer_vat,
        "supplier_country": supplier_country,
        "customer_country": customer_country,
        "reverse_charge": reverse_charge,
        "vat_status": vat_status,
        "compliance": compliance
    }
