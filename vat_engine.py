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

# ---------------- SELLER / BUYER EXTRACTION ---------------- #

def extract_parties(text):

    text = clean(text)

    # SELLER
    seller_block = ""
    buyer_block = ""

    if "SELLER" in text or "SUPPLIER" in text:
        seller_block = text.split("SELLER")[-1].split("BUYER")[0]

    if "BUYER" in text:
        buyer_block = text.split("BUYER")[-1]

    return seller_block, buyer_block

# ---------------- COUNTRY DETECTION ---------------- #

def detect_country(text):

    text = clean(text)

    if "POLAND" in text or "PL" in text:
        return "PL"
    if "FRANCE" in text or "FR" in text:
        return "FR"
    if "ITALY" in text or "IT" in text:
        return "IT"
    if "NORWAY" in text or "NO" in text:
        return "NO"

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

    seller_block, buyer_block = extract_parties(text)

    # fallback if OCR not structured
    seller_block = seller_block or text
    buyer_block = buyer_block or text

    supplier_country = detect_country(seller_block)
    customer_country = detect_country(buyer_block)

    supplier_vat, _ = extract_vat(seller_block)
    customer_vat, _ = extract_vat(buyer_block)

    vat_rate = extract_vat_rate(text)

    customer_type = "B2B" if is_b2b(text) else "B2C"

    # ---------------- REVERSE CHARGE LOGIC ---------------- #
    reverse_charge = (
        supplier_country is not None and
        customer_country is not None and
        supplier_country != customer_country
    )

    # ---------------- VAT STATUS (ONLY OCR) ---------------- #
    vat_status = f"VAT CHARGED ({vat_rate}%)" if vat_rate else "VAT NOT FOUND"

    # ---------------- COMPLIANCE ---------------- #
    if reverse_charge and vat_rate:
        compliance = "NOT COMPLIANT (Reverse charge applicable but VAT charged)"
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
