import re

def clean(text):
    return text.upper() if text else ""

def extract_vat(text):
    text = clean(text)
    match = re.search(r"\b([A-Z]{2}[0-9A-Z]{6,15})\b", text)
    if match:
        vat = match.group(1)
        return vat, vat[:2]
    return None, None

def extract_country(text):
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

def extract_vat_rate(text):
    m = re.search(r"(\d{1,2}(\.\d+)?)\s*%", clean(text))
    return float(m.group(1)) if m else None

def is_b2b(text):
    text = clean(text)
    keywords = ["GMBH","SARL","SP Z OO","SRL","LTD","LIMITED","BV"]
    return any(k in text for k in keywords)

def analyze_invoice(text):

    text = clean(text)

    supplier_country = extract_country(text)
    customer_country = extract_country(text)

    supplier_vat, _ = extract_vat(text)
    customer_vat, _ = extract_vat(text)

    vat_rate = extract_vat_rate(text)

    customer_type = "B2B" if is_b2b(text) else "B2C"

    reverse_charge = supplier_country != customer_country

    vat_status = f"VAT CHARGED ({vat_rate}%)" if vat_rate else "NO VAT DETECTED"

    if reverse_charge and vat_rate:
        compliance = "NOT COMPLIANT (VAT wrongly charged)"
    else:
        compliance = "COMPLIANT"

    return {
        "supplier_country": supplier_country,
        "customer_country": customer_country,
        "supplier_vat": supplier_vat or "NONE",
        "customer_vat": customer_vat or "NONE",
        "vat_rate": vat_rate,
        "customer_type": customer_type,
        "reverse_charge": reverse_charge,
        "vat_status": vat_status,
        "compliance": compliance
    }
