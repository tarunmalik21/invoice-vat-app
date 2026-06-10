import re

# ---------------- CLEAN TEXT ---------------- #

def clean(text):
    return text.upper() if text else ""

# ---------------- VAT EXTRACTION ---------------- #

def extract_vat(text):
    text = clean(text)
    match = re.search(r"\b([A-Z]{2}[0-9A-Z]{6,15})\b", text)
    if match:
        vat = match.group(1)
        return vat, vat[:2]
    return None, None

# ---------------- COUNTRY DETECTION ---------------- #

def extract_country(text):

    text = clean(text)

    # Seller / Supplier OCR mapping
    if "NORWAY" in text:
        return "NO"
    if "POLAND" in text:
        return "PL"
    if "FRANCE" in text:
        return "FR"
    if "ITALY" in text:
        return "IT"
    if "SPAIN" in text:
        return "ES"

    return None

# ---------------- VAT RATE OCR ---------------- #

def extract_vat_rate(text):
    text = clean(text)
    match = re.search(r"(\d{1,2}(\.\d+)?)\s*%", text)
    return float(match.group(1)) if match else None

# ---------------- B2B CHECK ---------------- #

def is_b2b(text):
    text = clean(text)
    keywords = ["GMBH", "SARL", "SRL", "LTD", "LIMITED", "SP Z OO", "AS"]
    return any(k in text for k in keywords)

# ---------------- MAIN ENGINE ---------------- #

def analyze_invoice(text):

    text = clean(text)

    # Extract data
    supplier_country = extract_country(text)
    customer_country = extract_country(text)

    supplier_vat, _ = extract_vat(text)
    customer_vat, _ = extract_vat(text)

    vat_rate = extract_vat_rate(text)

    # Logic
    customer_type = "B2B" if is_b2b(text) else "B2C"

    reverse_charge = (
        supplier_country is not None and
        customer_country is not None and
        supplier_country != customer_country
    )

    vat_status = f"VAT CHARGED ({vat_rate}%)" if vat_rate else "NO VAT DETECTED"

    # Compliance logic
    if reverse_charge and vat_rate:
        compliance = "NOT COMPLIANT (Reverse charge ignored)"
    else:
        compliance = "COMPLIANT"

    return {
        "customer_type": customer_type,
        "supplier_country": supplier_country,
        "customer_country": customer_country,
        "supplier_vat": supplier_vat or "NONE",
        "customer_vat": customer_vat or "NONE",
        "reverse_charge": "YES" if reverse_charge else "NO",
        "vat_status": vat_status,
        "compliance": compliance
    }
