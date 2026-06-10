import streamlit as st
from vat_engine import analyze_invoice
import fitz  # PyMuPDF

st.set_page_config(page_title="VAT Invoice Checker", layout="centered")

st.title("VAT Decision Result")

uploaded_file = st.file_uploader(
    "Upload Invoice (PDF)",
    type=["pdf"]
)

def extract_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

if uploaded_file:

    text = extract_pdf(uploaded_file)

    # AUTO RUN (NO BUTTON)
    result = analyze_invoice(text)

    st.subheader("VAT Decision Result")

    st.write("👤 Customer Type:", result["customer_type"])
    st.write("🌍 Seller Country:", result["supplier_country"])
    st.write("🌍 Buyer Country:", result["customer_country"])
    st.write("🧾 Seller VAT:", result["supplier_vat"])
    st.write("🧾 Buyer VAT:", result["customer_vat"])
    st.write("🔁 Reverse Charge:", result["reverse_charge"])
    st.write("💰 VAT Status:", result["vat_status"])
    st.write("📊 Compliance:", result["compliance"])
