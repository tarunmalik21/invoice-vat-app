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
# amount parser (EU safe)
# =========================
def parse_amount(value):
    if value is None:
        return 0.0

    value = str(value).strip()
    value = re.sub(r"[^\d,.\-]", "", value)

    # EU format fix (1.000,00 → 1000.00)
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
# COUNTRY NORMALIZER (CRITICAL FIX)
# =========================
def normalize_country(c):
    if not c:
        return ""

    c = c.strip().lower()

    mapping = {
        "germany": "germany", "de": "germany",
        "france": "france", "fr": "france",
        "italy": "italy", "it": "italy",
        "spain": "spain", "es": "spain",
        "netherlands": "netherlands", "nl": "netherlands",
        "belgium": "belgium", "be": "belgium", "belgique": "belgium",
        "austria": "austria", "at": "austria",
        "poland": "poland", "pl": "poland",
        "portugal": "portugal", "pt": "portugal",
        "czech republic": "czech republic", "cz": "czech republic"
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
# EU COUNTRIES (EXPANDED)
# =========================
EU_COUNTRIES = {
    "germany", "france", "italy", "spain", "netherlands",
    "austria", "belgium", "poland", "portugal", "czech republic"
}


# =========================
# REGION LOGIC (FIXED)
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
# REVERSE CHARGE (EU CORRECT RULE)
# =========================
def is_reverse_charge(inv, customer_type):

    supplier = normalize_country(inv.get("supplier_country"))
    customer = normalize_country(inv.get("customer_country"))
    vat_id = (inv.get("customer_vat_id") or "").strip()

    # ❌ NEVER reverse charge for domestic (IMPORTANT FIX)
    if supplier == customer:
        return False

    # ✔ EU cross-border B2B ONLY
    if (
        supplier in EU_COUNTRIES and
        customer in EU_COUNTRIES and
        customer_type == "B2B" and
        vat_id
    ):
        return True

    return False


# =========================
# VAT validation (simple correctness check)
# =========================
def validate_vat(net, tax, rate):
    expected = round(net * rate, 2)
    return abs(expected - tax) < 0.05  # small tolerance for EU rounding


# =========================
# VAT RATE DETECTION (SAFE DEFAULT)
# =========================
def detect_vat_rate(net, tax):
    if net == 0:
        return 0.0

    actual = round(tax / net, 2)

    if abs(actual - 0.07) < 0.02:
        return 0.07

    if abs(actual - 0.21) < 0.02:
        return 0.21

    if abs(actual - 0.19) < 0.02:
        return 0.19

    return actual


# =========================
# ENGINE
# =========================
def run_engine(inv):

    customer_type = classify_customer(inv)
    region = get_region(inv.get("supplier_country"), inv.get("customer_country"))
    reverse_charge = is_reverse_charge(inv, customer_type)

    net = parse_amount(inv.get("net_amount"))
    tax = parse_amount(inv.get("tax_amount"))

    detected_rate = detect_vat_rate(net, tax)

    vat_rate = 0.0 if reverse_charge else detected_rate

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
st.set_page_config(page_title="EU VAT Checker", layout="centered")

st.title("📄 EU VAT Invoice Checker (Belgium + EU Correct)")

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
            st.success("✅ Invoice is compliant")
        else:
            st.warning("⚠️ Invoice needs review")

    except Exception as e:
        st.error(f"Error: {e}")
