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
# safe JSON parser
# =========================
def safe_json_load(raw):
    try:
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception:
        return None


# =========================
# amount parser
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
You are a strict invoice parser.

Return ONLY valid JSON:

supplier_name, supplier_country, supplier_vat_id,
customer_name, customer_country, customer_vat_id,
invoice_number, invoice_date, currency,
net_amount, tax_amount, gross_amount,
items (array with category field if possible)

Invoice:
{text}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    raw = response.choices[0].message.content
    data = safe_json_load(raw)

    if not data:
        raise ValueError("Failed to parse invoice JSON")

    return data


# =========================
# B2B / B2C classifier
# =========================
def classify_customer(inv):
    vat_id = (inv.get("customer_vat_id") or "").strip()
    name = (inv.get("customer_name") or "").lower()

    if vat_id:
        return "B2B"

    company_keywords = ["gmbh", "ltd", "kg", "ag", "inc", "llc"]
    if any(k in name for k in company_keywords):
        return "B2B"

    return "B2C"


# =========================
# EU reverse charge logic
# =========================
EU_COUNTRIES = {
    "germany", "france", "italy", "spain", "netherlands",
    "austria", "belgium", "poland", "portugal", "czech republic"
}

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
# VAT rate engine (Germany)
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
def validate_vat(net, tax, expected_rate):
    expected_tax = round(net * expected_rate, 2)

    return {
        "expected_tax": expected_tax,
        "actual_tax": tax,
        "is_correct": abs(expected_tax - tax) < 0.02
    }


# =========================
# FULL ENGINE
# =========================
def run_vat_engine(inv):

    customer_type = classify_customer(inv)
    reverse_charge = is_reverse_charge(inv, customer_type)

    net = parse_amount(inv.get("net_amount"))
    tax = parse_amount(inv.get("tax_amount"))

    # category (fallback safe)
    category = "standard"
    if isinstance(inv.get("items"), list) and inv["items"]:
        category = inv["items"][0].get("category", "standard")

    vat_rate = 0.0 if reverse_charge else get_vat_rate(category)

    validation = validate_vat(net, tax, vat_rate)

    warnings = []

    if not validation["is_correct"]:
        warnings.append("VAT mismatch detected")

    if reverse_charge and tax > 0:
        warnings.append("Reverse charge expected but VAT charged")

    return {
        "customer_type": customer_type,
        "reverse_charge": reverse_charge,
        "vat_rate": vat_rate,
        "net": net,
        "tax": tax,
        "validation": validation,
        "warnings": warnings,
        "status": "OK" if validation["is_correct"] else "ERROR"
    }


# =========================
# STREAMLIT UI
# =========================
st.set_page_config(page_title="VAT Checker", layout="wide")

st.title("📄 Germany VAT Invoice Checker (Upgraded)")

uploaded_file = st.file_uploader("Upload Invoice PDF", type="pdf")

if uploaded_file:

    st.info("Reading PDF...")
    text = extract_text_from_pdf(uploaded_file)

    st.success("Extracting invoice data...")

    try:
        inv = extract_invoice_data(text)
        st.subheader("📦 Extracted Invoice")
        st.json(inv)

        st.subheader("🧠 VAT Analysis")

        result = run_vat_engine(inv)
        st.json(result)

        if result["warnings"]:
            st.warning(result["warnings"])
        else:
            st.success("No issues detected")

        st.success("Done")

    except Exception as e:
        st.error(f"Error: {e}")
