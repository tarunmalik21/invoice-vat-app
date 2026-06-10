import re

# ---------------- CLEAN ---------------- #

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

# ---------------- FIX: COUNTRY DETECTION ---------------- #

def detect_country(text):

    text = clean(text)

    if "FRANCE" in text:
        return "FR"
    if "POLAND" in text:
        return "PL"
    if "ITALY" in text:
        return "IT"
    if "NORWAY" in text:
        return "NO"
    if "SPAIN" in text:
        return "ES"

    return None

# ---------------- FIX: SELLER / BUYER EXTRACTION ---------------- #

def extract_seller_buyer(text):

    text = clean(text)

    seller = ""
    buyer = ""

    # Try structured OCR first
    if "SELLER" in text or "SPRZEDAWCA" in text:
        seller = text.split("SPRZEDAWCA")[-1]

    if "BUYER" in text or "NABYWCA" in text:
        buyer = text.split("NABYWCA")[-1]

    # fallback if OCR messy
    if not seller:
        seller = text
    if not buyer:
        buyer = text

    return seller, buyer

# ---------------- VAT RATE (ONLY OCR) ---------------- #

def extract_vat_rate(text):
    text = clean(text)
    match = re.search(r"(\d{1,2}(\.\d+)?)\s*%", text)
    return float(match.group(1)) if match else None

# ---------------- MAIN ENGINE ---------------- #

def analyze_invoice(text):

    text = clean(text)

    seller_text, buyer_text = extract_seller_buyer(text)

    # COUNTRY
    supplier_country = detect_country(seller_text)
    customer_country = detect_country(buyer_text)

    # VAT IDS (FIX: must read PL123 etc)
    supplier_vat, _ = extract_vat(seller_text)
    customer_vat, _ = extract_vat(buyer_text)

    vat_rate = extract_vat_rate(text)

    # B2B LOGIC (simple heuristic)
    customer_type = "B2B" if any(x in text for x in ["GMBH", "SARL", "SRL", "LTD"]) else "B2C"

    # ---------------- REVERSE CHARGE (IMPORTANT FIX) ---------------- #
    reverse_charge = (
        supplier_country is not None and
        customer_country is not None and
        supplier_country != customer_country
    )

    # ---------------- VAT STATUS (OCR ONLY) ---------------- #
    vat_status = f"VAT CHARGED ({vat_rate}%)" if vat_rate else "VAT NOT FOUND"

    # ---------------- COMPLIANCE ---------------- #
    if reverse_charge and vat_rate:
        compliance = "NOT COMPLIANT (Reverse Charge should apply)"
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
