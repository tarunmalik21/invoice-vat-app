import re

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

EU = {"DE","FR","IT","ES","PL","SE","FI","BE","AT","NL"}


def safe_upper(t):
    return t.upper() if t else ""


def extract_party(text, keys):
    text = safe_upper(text)
    for k in keys:
        if k in text:
            return text.split(k, 1)[1]
    return text


def extract_vat(text):
    text = safe_upper(text)
    m = re.search(r"\b([A-Z]{2}[0-9A-Z]{6,15})\b", text)
    if m:
        vat = m.group(1)
        return vat, vat[:2]
    return None, None


def extract_country(text, vat_country=None):
    if vat_country:
        return vat_country

    text = safe_upper(text)
    for name, code in COUNTRY_MAP.items():
        if name in text:
            return code
    return None


def extract_vat_rate(text):
    m = re.search(r"(\d{1,2}(\.\d+)?)\s*%", text)
    return float(m.group(1)) if m else None


def is_b2b(text, vat):
    text = safe_upper(text)
    keywords = ["GMBH","SARL","SAS","SA","LTD","SP Z OO","SRL","BV","NV"]
    return bool(vat) or any(k in text for k in keywords)


def analyze_invoice(text):
    text = safe_upper(text)

    seller = extract_party(text, ["SELLER","SUPPLIER","SPRZEDAWCA"])
    buyer = extract_party(text, ["BUYER","CUSTOMER","NABYWCA"])

    sup_vat, sup_ct = extract_vat(seller)
    cus_vat, cus_ct = extract_vat(buyer)

    sup_country = extract_country(seller, sup_ct)
    cus_country = extract_country(buyer, cus_ct)

    vat_rate = extract_vat_rate(text)

    sup_vat = sup_vat or "NONE"
    cus_vat = cus_vat or "NONE"

    customer_type = "B2B" if is_b2b(buyer, cus_vat) else "B2C"

    cross_border = sup_country and cus_country and sup_country != cus_country

    reverse_charge = customer_type == "B2B" and cross_border

    if reverse_charge and vat_rate:
        compliance = "NOT COMPLIANT (VAT wrongly charged)"
    else:
        compliance = "COMPLIANT"

    return {
        "supplier_country": sup_country,
        "customer_country": cus_country,
        "supplier_vat": sup_vat,
        "customer_vat": cus_vat,
        "vat_rate": vat_rate,
        "customer_type": customer_type,
        "reverse_charge": reverse_charge,
        "compliance": compliance
    }
