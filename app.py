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
def extract_invoice_data(text):
    prompt = f"""
Extract invoice data and return ONLY valid JSON.

Fields:
supplier_name, supplier_country, supplier_vat_id,
customer_name, customer_country, customer_vat_id,
invoice_number, invoice_date, currency,
net_amount, tax_amount, gross_amount,
reverse_charge_text

Invoice:
{text}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.choices[0].message.content
    raw = raw.replace("```json", "").replace("```", "").strip()

    return json.loads(raw)

# =========================
def classify_customer(inv):
    vat_id = inv.get("customer_vat_id")
    name = (inv.get("customer_name") or "").lower()

    if vat_id:
        return "B2B"

    if any(x in name for x in ["gmbh", "ltd", "kg", "ag"]):
        return "B2B"

    return "B2C"

# =========================
def validate(inv):
    net = parse_amount(inv.get("net_amount"))
    tax = parse_amount(inv.get("tax_amount"))
    gross = parse_amount(inv.get("gross_amount"))

    warnings = []

    if abs((net + tax) - gross) > 0.01:
        warnings.append("Net + Tax != Gross")

    return {
        "net": net,
        "tax": tax,
        "gross": gross,
        "customer_type": classify_customer(inv),
        "warnings": warnings
    }

# =========================
# STREAMLIT UI
# =========================
st.title("📄 Invoice VAT Checker")

uploaded_file = st.file_uploader("Upload Invoice PDF", type="pdf")

if uploaded_file:

    st.info("Reading PDF...")
    text = extract_text_from_pdf(uploaded_file)

    st.success("Extracting invoice data...")

    try:
        inv = extract_invoice_data(text)
        st.json(inv)

        st.write("Validating...")
        result = validate(inv)

        st.json(result)

        st.success("Done")

    except Exception as e:
        st.error(f"Error: {e}")
