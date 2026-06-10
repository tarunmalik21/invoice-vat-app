import streamlit as st
import fitz
import re
import json
from openai import OpenAI
from pdf2image import convert_from_bytes
import pytesseract

client = OpenAI()

# =========================
# APP TITLE
# =========================
st.set_page_config(page_title="EU VAT Invoice Checker", layout="centered")
st.title("📄 EU VAT Invoice Checker")


# =========================
# DEBUG START
# =========================
st.write("🚀 App loaded successfully")


# =========================
# PDF TEXT EXTRACTION (AUTO OCR FALLBACK)
# =========================
def extract_text_from_pdf(file):
    file_bytes = file.read()

    # --- Try normal PDF text extraction ---
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""

    for page in doc:
        page_text = page.get_text("text")
        if page_text:
            text += page_text

    text = text.strip()

    # --- If empty → OCR fallback ---
    if len(text) < 50:
        st.warning("⚠️ No selectable text found → using OCR")

        images = convert_from_bytes(file_bytes)
        text = ""

        for img in images:
            text += pytesseract.image_to_string(img)

    return text.strip()


# =========================
# OPENAI EXTRACTION
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

Rules:
- Fix OCR mistakes (e.g. SPRZEDAWCA → VAT ID if possible)
- If unknown, return empty string
- Output ONLY JSON

TEXT:
{text}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    raw = response.choices[0].message.content
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except Exception as e:
        st.error("❌ JSON parsing failed")
        st.text(raw)
        raise e


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
# REVERSE CHARGE RULE
# =========================
def is_reverse_charge(region):
    return region == "Non-Domestic-EU"


# =========================
# VAT CHECK (SIMPLIFIED)
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
# FILE UPLOAD
# =========================
uploaded_file = st.file_uploader("Upload Invoice PDF", type="pdf")


if uploaded_file:

    st.success("📥 File uploaded")

    # STEP 1
    text = extract_text_from_pdf(uploaded_file)

    st.write("📄 Extracted text length:", len(text))
    st.text(text[:800])

    if len(text) < 10:
        st.error("❌ No text extracted from PDF")
        st.stop()

    # STEP 2
    st.info("🔍 Extracting invoice data using AI...")

    inv = extract_invoice_data(text)

    st.write("📦 Extracted JSON:")
    st.json(inv)

    # STEP 3
    st.info("⚙️ Running VAT engine...")

    result = run_engine(inv)

    # STEP 4
    st.subheader("📊 Result")

    st.write(f"👤 Customer Type: **{result['customer_type']}**")
    st.write(f"🌍 Region: **{result['region']}**")
    st.write(f"🔁 Reverse Charge: **{'YES' if result['reverse_charge'] else 'NO'}**")
    st.write(f"💰 VAT Present (valid): **{'YES' if result['vat_correct'] else 'NO'}**")

    if result["vat_correct"]:
        st.success("✅ Invoice OK (VAT IDs present)")
    else:
        st.warning("⚠️ Missing VAT information")
