import re

# ----------------------------
# 1. B2B COMPANY DETECTION
# ----------------------------

B2B_KEYWORDS = [
    # Germany / Austria / Switzerland
    "GMBH", "AG", "UG", "KG", "OHG",

    # France
    "SARL", "SAS", "SA", "EURL",

    # Italy
    "SRL", "SPA", "SAPA",

    # Spain
    "SL", "SA",

    # Netherlands / Belgium
    "BV", "NV", "CVBA", "SNC",

    # Poland
    "SP. Z O.O", "S.A", "SP.K",

    # UK / international
    "LTD", "LIMITED", "PLC", "LLC"
]


def classify_customer_type(name: str, address: str = ""):
    """
    Detect if customer is B2B or B2C based on entity name + address.
    """
    text = f"{name} {address}".upper()

    for keyword in B2B_KEYWORDS:
        if keyword in text:
            return "B2B"

    return "B2C"


# ----------------------------
# 2. VAT EXTRACTION HELPERS
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
    """
    Extract VAT number if present.
    """
    for country, pattern in VAT_PATTERN.items():
        match = re.search(pattern, text.upper())
        if match:
            return match.group(), country
    return None, None


# ----------------------------
# 3. MAIN VAT ANALYSIS ENGINE
# ----------------------------

def analyze_invoice(invoice_text: str):
    """
    Main EU VAT compliance engine
    """

    # Extract VAT numbers
    supplier_vat, supplier_country = extract_vat(invoice_text)

    # naive extraction for customer VAT (can improve later)
    customer_vat, customer_country = extract_vat(invoice_text)

    # Extract names (very simplified - you already improve via parser later)
    lines = invoice_text.split("\n")
    seller_name = ""
    buyer_name = ""

    for i, line in enumerate(lines):
        if "SELLER" in line.upper() or "VERKÄUFER" in line.upper():
            seller_name = lines[i + 1] if i + 1 < len(lines) else ""
        if "BUYER" in line.upper() or "NABYWCA" in line.upper():
            buyer_name = lines[i + 1] if i + 1 < len(lines) else ""

    # ----------------------------
    # 4. CLASSIFY CUSTOMER
    # ----------------------------
    customer_type = classify_customer_type(buyer_name)

    # ----------------------------
    # 5. EU RULE LOGIC
    # ----------------------------

    compliance = "COMPLIANT"
    reverse_charge = False
    vat_status = "UNKNOWN"

    # If B2B EU transaction
    if customer_type == "B2B":

        # Missing VAT = problem
        if not customer_vat:
            vat_status = "MISSING"
            compliance = "NOT COMPLIANT"

        else:
            vat_status = "VALID FORMAT (NOT VERIFIED)"

        # Cross-border EU logic
        if supplier_country and customer_country and supplier_country != customer_country:
            reverse_charge = True

    else:
        # B2C case
        reverse_charge = False

        # If VAT charged in B2C → likely OK (simplified rule)
        vat_status = "B2C CASE"

    # ----------------------------
    # 6. OUTPUT
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
