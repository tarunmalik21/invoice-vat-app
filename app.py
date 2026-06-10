import streamlit as st
import sys
import importlib
from pypdf import PdfReader

sys.path.append(".")

import backend.vat_engine as vat_engine
importlib.reload(vat_engine)

st.set_page_config(page_title="EU VAT Invoice Checker")

st.title("EU VAT Invoice Checker")

uploaded_file = st.file_uploader("Upload Invoice", type=["txt", "pdf"])


def extract_text(file):
    if file.name.endswith(".txt"):
        return file.read().decode("utf-8")

    elif file.name.endswith(".pdf"):
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text

    return ""


if uploaded_file:

    text = extract_text(uploaded_file)

    result = vat_engine.analyze_invoice(text)

    st.subheader("VAT Decision Result")

    st.write(f"👤 Customer Type: {result['customer_type']}")
    st.write(f"🔁 Reverse Charge: {'YES' if result['reverse_charge'] else 'NO'}")
    st.write(f"💰 VAT Status: {result['vat_status']}")
    st.write(f"📊 Compliance: {result['compliance']}")

    if result["compliance"] == "COMPLIANT":
        st.success("✅ Invoice is compliant")
    else:
        st.error("❌ Invoice is NOT compliant")
