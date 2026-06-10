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
# safe amount parser
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
items (array with category if possible)

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
# CUSTOMER CLASSIFIER
# =========================
def classify_customer(inv):
    vat_id = (inv.get("customer_vat_id") or "").strip()
    name = (inv.get("customer_name") or "").lower()

    company_keywords = ["gmbh", "ltd", "kg", "ag", "inc", "llc"]

    if vat_id:
        return "B2B"

    if any(k in name for k in company_keywords):
        return "B2B"

    return "B2C"


# =========================
# EU detection
# =========================
EU_COUNTRIES = {
    "germany", "france", "italy", "spain", "netherlands",
    "austria", "belgium", "poland", "portugal", "czech republic"
}


def get_region(supplier, customer):
    supplier = (supplier or "").lower()
    customer = (customer or "").lower()

    if supplier == customer:
        return "Domestic"

    if supplier in EU_COUNTRIES and customer in EU_COUNTRIES:
        return "EU"

    return "Non-EU"


# =========================
# Reverse charge logic
# =========================
def is_reverse_charge(inv, customer_type):
    supplier = (inv.get("supplier_country") or "").lower()
    customer = (inv.get("customer_country") or "").lower()

    return (
        supplier in EU_COUNTRIES and
        customer in EU_COUNTRIES and
        customer_type == "B2B" and
        inv.get("customer_vat_id")
    )


# =========================
# VAT rules (Germany)
# =========================
def get_vat_rate(category="standard"):
    category = (category or "").lower()

    if category in ["book", "journal", "newspaper"]:
        return 0.07

    if category in ["export", "intra_eu"]:
        return 0.00

    return 0.19


# =========================
# VAT validation
# =========================
def validate_vat(net, tax, rate):
    expected = round(net * rate, 2)

    return abs(expected - tax) < 0.02


# =========================
# CLEAN ENGINE
# =========================
def run_engine(inv):

    customer_type = classify_customer(inv)
    region = get_region(inv.get("supplier_country"), inv.get("customer_country"))
    reverse_charge = is_reverse_charge(inv, customer_type)

    net = parse_amount(inv.get("net_amount"))
    tax = parse_amount(inv.get("tax_amount"))

    category = "standard"
    if isinstance(inv.get("items"), list) and inv["items"]:
        category = inv["items"][0].get("category", "standard")

    vat_rate = 0.0 if reverse_charge else get_vat_rate(category)

    vat_correct = validate_vat(net, tax, vat_rate)

    return {
        "customer_type": customer_type,
        "region": region,
        "reverse_charge": reverse_charge,
        "vat_correct": vat_correct
    }


# =========================
# STREAMLIT UI
# =========================
st.set_page_config(page_title="VAT Checker", layout="centered")

st.title("📄 Germany VAT Invoice Checker")

uploaded_file = st.file_uploader("Upload Invoice PDF", type="pdf")

if uploaded_file:

    st.info("Reading PDF...")
    text = extract_text_from_pdf(uploaded_file)

    st.success("Extracting invoice data...")

    try:
        inv = extract_invoice_data(text)

        st.success("Analysis Running...")

        result = run_engine(inv)

        st.subheader("📊 VAT Decision")

        st.write(f"👤 Customer Type: **{result['customer_type']}**")
        st.write(f"🌍 Region: **{result['region']}**")
        st.write(f"🔁 Reverse Charge: **{'YES' if result['reverse_charge'] else 'NO'}**")
        st.write(f"💰 VAT Correct: **{'YES' if result['vat_correct'] else 'NO'}**")

        if result["vat_correct"]:
            st.success("✅ Invoice is compliant")
        else:
            st.warning("⚠️ Invoice needs review")

    except Exception as e:
        st.error(f"Error: {e}")
