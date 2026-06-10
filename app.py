import streamlit as st
import fitz
import json
from openai import OpenAI
from pdf2image import convert_from_bytes
import pytesseract

client = OpenAI()

# =========================
# APP SETUP
# =========================
st.set_page_config(page_title="EU VAT Invoice Checker", layout="centered")
st.title("📄 EU VAT Invoice Checker")

st.write("🚀 App running...")


# =========================
# PDF EXTRACTION
# =========================
def extract_text_from_pdf(file):
    file_bytes = file.read()

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""

    for page in doc:
        page_text = page.get_text("text")
        if page_text:
            text += page_text

    text = text.strip()

    # OCR fallback
    if len(text) < 50:
        st.warning("⚠️ Scanned PDF detected → using OCR")
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
net_amount, tax_amount, gross_amount

Return empty string if unknown.

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

    return json.loads(raw)


# =========================
# COUNTRY NORMALIZER
# =========================
def normalize_country(c):
    if not c:
        return ""

    c = c.lower().strip()

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
# CLASSIFIER
# =========================
def classify_customer(inv):
    vat_id = (inv.get("customer_vat_id") or "").strip()
    name = (inv.get("customer_name") or "").lower()

    keywords = ["gmbh", "ltd", "kg", "ag", "inc", "llc", "sa", "bv"]

    if vat_id:
        return "B2B"

    if any(k in name for k in keywords):
        return "B2B"

    return "B2C"


# =========================
# EU SET
# =========================
EU = {"de", "fr", "it", "es", "be", "nl", "at", "pl", "pt", "cz"}


# =========================
# REGION LOGIC
# =========================
def get_region(supplier, customer):

    s = normalize_country(supplier)
    c = normalize_country(customer)

    if s == c:
        return "Domestic"

    if s in EU and c in EU:
        return "Non-Domestic-EU"

    return "Non-EU"


# =========================
# VAT CHECK
# =========================
def is_vat_charged(inv):
    tax = inv.get("tax_amount")
    try:
        return float(tax) > 0
    except:
        return False


# =========================
# TAX INFO (FIXED)
# =========================
def get_tax_info(region):

    # ONLY show for Non-EU
    if region == "Non-EU":
        return "0% VAT on invoice (export/import transaction). Customs VAT may apply separately"

    # hide for EU cases
    return ""


# =========================
# ENGINE
# =========================
def run_engine(inv):

    customer_type = classify_customer(inv)
    region = get_region(inv.get("supplier_country"), inv.get("customer_country"))

    supplier_vat = (inv.get("supplier_vat_id") or "").strip()
    customer_vat = (inv.get("customer_vat_id") or "").strip()

    reverse_charge = region == "Non-Domestic-EU"
    vat_present = bool(supplier_vat and customer_vat)
    vat_charged = is_vat_charged(inv)

    # =========================
    # RISK ENGINE
    # =========================
    errors = []
    warnings = []

    # ❌ Non-EU VAT charged
    if region == "Non-EU" and vat_charged:
        errors.append("🚨 VAT charged in Non-EU transaction (review required)")

    # ⚠️ VAT missing
    if not vat_present:
        warnings.append("⚠️ VAT missing (supplier or customer VAT ID missing) – review needed")

    return {
        "customer_type": customer_type,
        "region": region,
        "reverse_charge": reverse_charge,
        "vat_present": vat_present,
        "vat_charged": vat_charged,
        "errors": errors,
        "warnings": warnings,
        "tax_info": get_tax_info(region)
    }


# =========================
# UI
# =========================
uploaded_file = st.file_uploader("Upload Invoice PDF", type="pdf")

if uploaded_file:

    st.success("File uploaded ✔")

    text = extract_text_from_pdf(uploaded_file)

    st.subheader("📄 Extracted Text")
    st.text(text)

    st.write("📏 Text length:", len(text))

    if len(text) < 10:
        st.error("No readable text found")
        st.stop()

    st.info("Extracting invoice data...")

    inv = extract_invoice_data(text)

    st.info("Running VAT engine...")

    result = run_engine(inv)

    # =========================
    # OUTPUT
    # =========================
    st.subheader("📊 Invoice Analysis")

    st.write(f"👤 Customer Type: **{result['customer_type']}**")
    st.write(f"🌍 Region: **{result['region']}**")

    # only show tax info if not empty
    if result["tax_info"]:
        st.write(f"🧾 Tax Info: **{result['tax_info']}**")

    st.write(f"🔁 Reverse Charge: **{'YES' if result['reverse_charge'] else 'NO'}**")
    st.write(f"💰 VAT Present: **{'YES' if result['vat_present'] else 'NO'}**")

    # =========================
    # ERRORS
    # =========================
    for e in result["errors"]:
        st.error(e)

    # =========================
    # WARNINGS
    # =========================
    for w in result["warnings"]:
        st.warning(w)

    # =========================
    # SUCCESS
    # =========================
    if not result["errors"] and not result["warnings"]:
        st.success("✔ Invoice compliant (no issues detected)")
