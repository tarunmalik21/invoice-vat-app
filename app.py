import streamlit as st
import fitz
import re
import json
from openai import OpenAI

client = OpenAI()

# =========================
# PDF extraction
# =========================
def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text


# =========================
# amount parser (kept for future use)
# =========================
def parse_amount(value):
    if value is None:
        return 0.0

    value = str(value).strip()
    value = re.sub(r"[^\d,.\-]", "", value)

    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "")
            value = value.replace(",", ".")
        else:
            value = value.replace(",", "")

    elif "," in value:
        value = value.replace(",", ".")

    try:
        return float(value)
    except:
        return 0.0


# =========================
# OpenAI extraction
# =========================
def extract_invoice_data(text):
    prompt = f"""
Extract invoice data and return ONLY valid JSON.

Fields:
supplier_name, supplier_country, supplier_vat_id,
customer_name, customer_country, customer_vat_id,
invoice_number, invoice_date, currency,
net_amount, tax_amount, gross_amount,
items

IMPORTANT:
- Fix OCR mistakes where possible (e.g. SPRZEDAWCA = VAT ID)
- Do not hallucinate VAT numbers

Invoice:
{text}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    raw = response.choices[0].message.content
    raw = raw.replace("```json", "").replace("```", "").strip()

    return json.loads(raw)


# =========================
# COUNTRY NORMALIZER
# =========================
def normalize_country(c):
    if not c:
        return ""

    c = c.strip().lower()

    mapping = {
        "germany": "de", "de": "de",
        "france": "fr", "fr": "fr",
        "italy": "it", "it": "it",
        "spain": "es", "es": "es",
        "belgium": "be", "be": "be",
        "netherlands": "nl", "nl": "nl",
        "austria": "at", "at": "at",
        "poland": "pl", "pl": "pl",
        "portugal": "pt", "pt": "pt",
        "czech republic": "cz", "cz": "cz"
    }

    return mapping.get(c, c)


# =========================
# CUSTOMER CLASSIFIER
# =========================
def classify_customer(inv):
    vat_id = (inv.get("customer_vat_id") or "").strip()
    name = (inv.get("customer_name") or "").lower()

    keywords = ["gmbh", "ltd", "kg", "ag", "inc", "llc", "sa", "bv", "sprl"]

    if vat_id:
        return "B2B"

    if any(k in name for k in keywords):
        return "B2B"

    return "B2C"


# =========================
# EU COUNTRIES
# =========================
EU_COUNTRIES = {
    "de", "fr", "it", "es", "be",
    "nl", "at", "pl", "pt", "cz"
}


# =========================
# REGION LOGIC
# =========================
def get_region(supplier, customer):

    supplier = normalize_country(supplier)
    customer = normalize_country(customer)

    if supplier == customer:
        return "Domestic"

    if supplier in EU_COUNTRIES and customer in EU_COUNTRIES:
        return "Non-Domestic-EU"

    return "Non-EU"


# =========================
# REVERSE CHARGE
# =========================
def is_reverse_charge(region):
    return region == "Non-Domestic-EU"


# =========================
# VAT VALIDATION (SIMPLIFIED)
# =========================
def validate_vat_presence(supplier_vat, customer_vat):
    return bool(supplier_vat and customer_vat)


# =========================
# ENGINE
# =========================
def run_engine(inv):

    customer_type = classify_customer(inv)
    region = get_region(inv.get("supplier_country"), inv.get("customer_country"))

    supplier_vat = (inv.get("supplier_vat_id") or "").strip()
    customer_vat = (inv.get("customer_vat_id") or "").strip()

    reverse_charge = is_reverse_charge(region)
    vat_correct = validate_vat_presence(supplier_vat, customer_vat)

    return {
        "customer_type": customer_type,
        "region": region,
        "reverse_charge": reverse_charge,
        "vat_correct": vat_correct
    }


# =========================
# STREAMLIT UI
# =========================
st.set_page_config(page_title="EU VAT Invoice Checker", layout="centered")

st.title("📄 EU VAT Invoice Checker")

uploaded_file = st.file_uploader("Upload Invoice PDF", type="pdf")

if uploaded_file:

    st.info("Reading PDF...")
    text = extract_text_from_pdf(uploaded_file)

    st.success("Extracting invoice data...")

    try:
        inv = extract_invoice_data(text)

        result = run_engine(inv)

        st.subheader("📊 VAT Decision Result")

        st.write(f"👤 Customer Type: **{result['customer_type']}**")
        st.write(f"🌍 Region: **{result['region']}**")
        st.write(f"🔁 Reverse Charge: **{'YES' if result['reverse_charge'] else 'NO'}**")
        st.write(f"💰 VAT Correct: **{'YES' if result['vat_correct'] else 'NO'}**")

        if result["vat_correct"]:
            st.success("✅ Invoice OK (VAT IDs present)")
        else:
            st.warning("⚠️ Missing VAT information")

    except Exception as e:
        st.error(f"Error: {e}")
