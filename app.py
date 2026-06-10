import streamlit as st
import fitz
import json
from openai import OpenAI
from pdf2image import convert_from_bytes
import pytesseract

client = OpenAI()

# =========================
# APP UI
# =========================
st.set_page_config(page_title="EU VAT Invoice Checker", layout="centered")
st.title("📄 EU VAT Invoice Checker")

st.write("🚀 App running...")


# =========================
# PDF TEXT EXTRACTION
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
# EU COUNTRIES
# =========================
EU = {"de", "fr", "it", "es", "be", "nl", "at", "pl", "pt", "cz"}


# =========================
# REGION
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
# TAX DESCRIPTION
# =========================
def get_tax_info(region):
    if region == "Non-Domestic-EU":
        return "Import VAT applicable (paid at EU customs, not on invoice)"
    elif region == "Non-EU":
        return "Import / Export transaction (0% invoice VAT, customs tax may apply)"
    else:
        return "Standard EU VAT rules apply"


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

    return {
        "customer_type": customer_type,
        "region": region,
        "reverse_charge": reverse_charge,
        "vat_present": vat_present,
        "tax_info": get_tax_info(region)
    }


# =========================
# UI
# =========================
uploaded_file = st.file_uploader("Upload Invoice PDF", type="pdf")


if uploaded_file:

    st.success("File uploaded ✔")

    text = extract_text_from_pdf(uploaded_file)

    st.write("📄 Extracted text length:", len(text))

    if len(text) < 10:
        st.error("No readable text found")
        st.stop()

    st.info("Extracting invoice data...")

    inv = extract_invoice_data(text)

    # 🔒 Hidden debug JSON (NOT visible by default)
    with st.expander("🔍 Developer View (JSON)"):
        st.json(inv)

    st.info("Running VAT engine...")

    result = run_engine(inv)

    # =========================
    # CLEAN SaaS OUTPUT
    # =========================
    st.subheader("📊 Invoice Analysis")

    st.write(f"👤 Customer Type: **{result['customer_type']}**")
    st.write(f"🌍 Region: **{result['region']}**")
    st.write(f"🧾 Tax Info: **{result['tax_info']}**")

    st.write(f"🔁 Reverse Charge: **{'YES' if result['reverse_charge'] else 'NO'}**")
    st.write(f"💰 VAT Data Complete: **{'YES' if result['vat_present'] else 'NO'}**")

    if result["vat_present"]:
        st.success("✅ VAT details complete")
    else:
        st.warning("⚠️ Missing VAT IDs (review required)")
