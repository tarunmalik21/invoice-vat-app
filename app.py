import streamlit as st
from vat_engine import analyze_invoice
import fitz  # PyMuPDF
from PIL import Image
import pytesseract

st.set_page_config(page_title="VAT Invoice Checker", layout="centered")

st.title("VAT Decision Result")

uploaded_file = st.file_uploader(
    "Upload Invoice (PDF / Image)",
    type=["pdf", "png", "jpg", "jpeg"]
)

# ---------------- OCR FUNCTIONS ---------------- #

def extract_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def extract_image(file):
    return pytesseract.image_to_string(Image.open(file))

# ---------------- MAIN FLOW ---------------- #

if uploaded_file:

    st.success("File uploaded successfully ✔")

    file_type = uploaded_file.type

    if file_type == "application/pdf":
        text = extract_pdf(uploaded_file)
    else:
        text = extract_image(uploaded_file)

    st.subheader("OCR Extracted Text")
    st.text_area("", text, height=250)

    st.write("OCR Length:", len(text))

    if st.button("Analyze Invoice"):

        if not text.strip():
            st.error("No text detected in invoice")
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
