import streamlit as st
import sys
import importlib
from pypdf import PdfReader

# -----------------------------
# FIX IMPORT PATH (Streamlit Cloud safe)
# -----------------------------
sys.path.append(".")

import backend.vat_engine as vat_engine
importlib.reload(vat_engine)

# -----------------------------
# UI
# -----------------------------
st.set_page_config(page_title="EU VAT Invoice Checker")

st.title("EU VAT Invoice Checker")

st.write("Upload a TXT or PDF invoice for VAT analysis")

# -----------------------------
# FILE UPLOAD
# -----------------------------
uploaded_file = st.file_uploader("Upload Invoice", type=["txt", "pdf"])

# -----------------------------
# TEXT EXTRACTION FUNCTION
# -----------------------------
def extract_text(file):
    if file.name.endswith(".txt"):
        return file.read().decode("utf-8")

    elif file.name.endswith(".pdf"):
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
        return text

    return ""

# -----------------------------
# MAIN LOGIC
# -----------------------------
if uploaded_file:

    text = extract_text(uploaded_file)

    st.subheader("📄 Extracted Invoice Text")
    st.text(text)

    # Call backend VAT engine
    result = vat_engine.analyze_invoice(text)

    st.subheader("VAT Decision Result")

    st.write(f"👤 Customer Type: {result['customer_type']}")
    st.write(f"🏢 Supplier VAT: {result['supplier_vat']}")
    st.write(f"🌍 Supplier Country: {result['supplier_country']}")
    st.write(f"🌍 Customer Country: {result['customer_country']}")
    st.write(f"🔁 Reverse Charge: {'YES' if result['reverse_charge'] else 'NO'}")
    st.write(f"⚠️ VAT Status: {result['vat_status']}")
    st.write(f"📊 Compliance: {result['compliance']}")

    # Final status
    if result["compliance"] == "COMPLIANT":
        st.success("✅ Invoice is compliant")
    else:
        st.error("❌ Invoice is NOT compliant")
