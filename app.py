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
# COUNTRY + SUFFIX MAP
# =========================
COUNTRY_SUFFIX_MAP = {
    "de": ["gmbh", "ag", "kg", "ug", "ohg", "gbr"],
    "fr": ["sarl", "sas", "sa", "eurl", "sasu"],
    "it": ["srl", "spa", "snc", "sas"],
    "es": ["sl", "s.l", "sa", "s.a", "slne"],
    "nl": ["bv", "nv"],
    "be": ["bv", "nv", "sprl", "scrl"],
    "at": ["gmbh", "ag", "og", "kg"],
    "pl": ["sp. z o.o", "s.a", "spolka z oo"],
    "pt": ["lda", "sa"],
    "cz": ["sro", "a.s", "as"],
    "uk": ["ltd", "limited", "plc", "llp"],
    "us": ["inc", "llc", "corp", "corporation"]
}


def detect_country_by_suffix(name):
    if not name:
        return None

    name = name.lower()

    for country, suffixes in COUNTRY_SUFFIX_MAP.items():
        for s in suffixes:
            if s in name:
                return country

    return None


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

IMPORTANT:
- Map VAT / NIF / Tax ID correctly
- Extract country even if written as abbreviation or missing

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
# NORMALIZE COUNTRY
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
# REGION LOGIC
# =========================
EU = {"de", "fr", "it", "es", "be", "nl", "at", "pl", "pt", "cz"}


def get_region(supplier, customer):

    s = normalize_country(supplier)
    c = normalize_country(customer)

    if not s or not c:
        return "UNKNOWN"

    if s == c:
        return "Domestic"

    if s in EU and c in EU:
        return "Non-Domestic-EU"

    return "Non-EU"


# =========================
# VAT CHECK
# =========================
def is_vat_charged(inv):
    try:
        return float(inv.get("tax_amount", 0)) > 0
    except:
        return False


# =========================
# ENGINE
# =========================
def run_engine(inv):

    # =========================
    # 🔥 FIX: infer missing countries using suffix
    # =========================
    supplier_name = inv.get("supplier_name", "")
    customer_name = inv.get("customer_name", "")

    if not inv.get("supplier_country"):
        inv["supplier_country"] = detect_country_by_suffix(supplier_name)

    if not inv.get("customer_country"):
        inv["customer_country"] = detect_country_by_suffix(customer_name)

    customer_type = classify_customer(inv)
    region = get_region(inv.get("supplier_country"), inv.get("customer_country"))

    supplier_vat = (inv.get("supplier_vat_id") or "").strip()
    customer_vat = (inv.get("customer_vat_id") or "").strip()

    reverse_charge = region == "Non-Domestic-EU"
    vat_present = bool(supplier_vat and customer_vat)
    vat_charged = is_vat_charged(inv)

    errors = []
    warnings = []

    # ❌ Non-EU VAT charged
    if region == "Non-EU" and vat_charged:
        errors.append("🚨 VAT charged in Non-EU transaction (review required)")

    # ❌ Reverse charge but VAT charged
    if reverse_charge and vat_charged:
        errors.append("🚨 VAT shall be 0% under reverse charge (EU intra-community supply)")

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
        "warnings": warnings
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
