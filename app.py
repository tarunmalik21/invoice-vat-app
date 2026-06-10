import streamlit as st
from vat_engine import analyze_invoice
import fitz  # PyMuPDF
from PIL import Image

st.set_page_config(page_title="VAT Invoice Checker", layout="centered")

st.title("VAT Decision Result")

uploaded_file = st.file_uploader(
    "Upload Invoice (PDF only recommended)",
    type=["pdf", "png", "jpg", "jpeg"]
)

# ---------------- PDF OCR ---------------- #

def extract_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

# ---------------- IMAGE OCR (SAFE FALLBACK) ---------------- #

def extract_image(file):
    return "IMAGE OCR DISABLED - PLEASE USE PDF FILE FOR ACCURATE RESULTS"

# ---------------- MAIN FLOW ---------------- #

if uploaded_file:

    st.success("File uploaded ✔")

    if uploaded_file.type == "application/pdf":
        text = extract_pdf(uploaded_file)
    else:
        text = extract_image(uploaded_file)

    st.subheader("Extracted Text")
    st.text_area("OCR Output", text, height=250)

    st.write("Text Length:", len(text))

    if st.button("Analyze Invoice"):

        if not text.strip():
            st.error("No readable text found in invoice")
        else:
            result = analyze_invoice(text)

            st.subheader("VAT Decision Result")

            st.write("👤 Customer Type:", result["customer_type"])
            st.write("🌍 Supplier Country:", result["supplier_country"])
            st.write("🌍 Customer Country:", result["customer_country"])
            st.write("🧾 Supplier VAT:", result["supplier_vat"])
            st.write("🧾 Customer VAT:", result["customer_vat"])
            st.write("🔁 Reverse Charge:", result["reverse_charge"])
            st.write("💰 VAT Status:", result["vat_status"])
            st.write("📊 Compliance:", result["compliance"])
