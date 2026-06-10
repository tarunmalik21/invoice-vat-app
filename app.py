import streamlit as st
from pypdf import PdfReader

import backend.vat_engine as vat_engine


# -----------------------------
# UI CONFIG
# -----------------------------
st.set_page_config(page_title="EU VAT Invoice Checker")

st.title("EU VAT Invoice Checker")


# -----------------------------
# FILE UPLOAD
# -----------------------------
uploaded_file = st.file_uploader("Upload Invoice (PDF or TXT)", type=["pdf", "txt"])


def extract_text(file):
    text = ""

    if file.name.endswith(".txt"):
        text = file.read().decode("utf-8")

    elif file.name.endswith(".pdf"):
        reader = PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() or ""

    return text


# -----------------------------
# MAIN FLOW
# -----------------------------
if uploaded_file:

    text = extract_text(uploaded_file)

    if not text.strip():
        st.error("❌ Could not extract text from file")
        st.stop()

    result = vat_engine.analyze_invoice(text)

    st.subheader("VAT Decision Result")

    st.write(f"👤 Customer Type: {result['customer_type']}")
    st.write(f"🌍 Supplier Country: {result['supplier_country']}")
    st.write(f"🌍 Customer Country: {result['customer_country']}")
    st.write(f"🧾 Supplier VAT: {result['supplier_vat']}")
    st.write(f"🧾 Customer VAT: {result['customer_vat']}")
    st.write(f"🔁 Reverse Charge: {'YES' if result['reverse_charge'] else 'NO'}")
    st.write(f"💰 VAT Status: {result['vat_status']}")
    st.write(f"📊 Compliance: {result['compliance']}")

    # -----------------------------
    # FINAL STATUS BOX
    # -----------------------------
    if result["compliance"] == "COMPLIANT":
        st.success("✅ Invoice is compliant")
    else:
        st.error("❌ Invoice is NOT compliant")
