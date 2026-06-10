import re

# =========================
# COUNTRY MAP
# =========================

COUNTRY_MAP = {
    "GERMANY": "DE",
    "FRANCE": "FR",
    "ITALY": "IT",
    "SPAIN": "ES",
    "POLAND": "PL",
    "NORWAY": "NO",
    "COLOMBIA": "CO",
    "SWEDEN": "SE",
    "FINLAND": "FI",
    "BELGIUM": "BE",
    "AUSTRIA": "AT",
    "NETHERLANDS": "NL",
}

# EU set (for future logic expansion)
EU = {"DE","FR","IT","ES","PL","SE","FI","BE","AT","NL"}

# =========================
# HELPERS
# =========================

def up(text):
    return text.upper() if text else ""


def extract_party(text, keys):
    text = up(text)
    for k in keys:
        if k in text:
            return text.split(k, 1)[1]
    return text


def extract_vat(text):
    text = up(text)
    m = re.search(r"\b([A-Z]{2}[0-9A-Z]{6,15})\b", text)
    if m:
        vat = m.group(1)
        return vat, vat[:2]
    return None, None


def extract_country(text, vat_country=None):
    if vat_country:
        return vat_country

    text = up(text)
    for name, code in COUNTRY_MAP.items():
        if name in text:
            return code
    return None


def extract_vat_rate(text):
    m = re.search(r"(\d{1,2}(\.\d+)?)\s*%", up(text))
    return float(m.group(1)) if m else None


def is_b2b(text, vat):
    text = up(text)
    keywords = ["GMBH","SARL","SAS","SA","LTD","LIMITED","SRL","SP Z OO","BV","NV"]
    return bool(vat) or any(k in text for k in keywords)

# =========================
# MAIN ENGINE
# =========================

def analyze_invoice(text):
    text = up(text)

    # -------------------------
    # SELLER / BUYER SPLIT
    # -------------------------
    seller = extract_party(text, ["SELLER","SUPPLIER","SPRZEDAWCA"])
    buyer = extract_party(text, ["BUYER","CUSTOMER","NABYWCA"])

    # -------------------------
    # OCR LAYER
    # -------------------------
    sup_vat, sup_ct = extract_vat(seller)
    cus_vat, cus_ct = extract_vat(buyer)

    supplier_country = extract_country(seller, sup_ct)
    customer_country = extract_country(buyer, cus_ct)

    vat_rate = extract_vat_rate(text)

    supplier_vat = sup_vat or "NONE"
    customer_vat = cus_vat or "NONE"

    vat_status = f"VAT CHARGED ({vat_rate}%)" if vat_rate else "NO VAT DETECTED"

    # -------------------------
    # LOGIC LAYER
    # -------------------------
    customer_type = "B2B" if is_b2b(buyer, customer_vat) else "B2C"

    cross_border = (
        supplier_country is not None and
        customer_country is not None and
        supplier_country != customer_country
    )

    reverse_charge = customer_type == "B2B" and cross_border

    # compliance rule
    if reverse_charge and vat_rate:
        compliance = "NOT COMPLIANT (VAT wrongly charged)"
    else:
        compliance = "COMPLIANT"

    # -------------------------
    # OUTPUT
    # -------------------------
    return {
        "supplier_country": supplier_country,
        "customer_country": customer_country,
        "supplier_vat": supplier_vat,
        "customer_vat": customer_vat,
        "vat_rate": vat_rate,
        "vat_status": vat_status,
        "customer_type": customer_type,
        "reverse_charge": reverse_charge,
        "compliance": compliance
    }
