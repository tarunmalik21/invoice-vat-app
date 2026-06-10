import streamlit as st
from vat_engine import analyze_invoice
import fitz
from PIL import Image
import pytesseract

st.title("VAT Decision Result")

uploaded_file = st.file_uploader("Upload Invoice", type=["pdf","png","jpg","jpeg"])

def extract_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    return "".join([p.get_text() for p in doc])

def extract_img(file):
    return pytesseract.image_to_string(Image.open(file))

if uploaded_file:

    if uploaded_file.type == "application/pdf":
        text = extract_pdf(uploaded_file)
    else:
        text = extract_img(uploaded_file)

    st.text_area("OCR Text", text, height=200)

    if st.button("Analyze"):
        r = analyze_invoice(text)

        st.write("👤 Customer Type:", r["customer_type"])
        st.write("🌍 Supplier Country:", r["supplier_country"])
        st.write("🌍 Customer Country:", r["customer_country"])
        st.write("🧾 Supplier VAT:", r["supplier_vat"])
        st.write("🧾 Customer VAT:", r["customer_vat"])
        st.write("🔁 Reverse Charge:", r["reverse_charge"])
        st.write("💰 VAT Status:", r["vat_status"])
        st.write("📊 Compliance:", r["compliance"])
