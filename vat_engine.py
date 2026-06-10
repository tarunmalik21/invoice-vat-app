import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io

st.set_page_config(page_title="VAT Checker", layout="centered")

st.title("VAT Decision Result")

# =========================
# PDF TEXT EXTRACTION
# =========================
def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text


# =========================
# IMAGE TEXT EXTRACTION (basic fallback)
# =========================
def extract_text_from_image(file):
    img = Image.open(file)
    return str(img.info)  # placeholder (OCR can be added later)


# =========================
# UPLOAD
# =========================
uploaded_file = st.file_uploader(
    "📄 Upload Invoice (PDF or Image)",
    type=["pdf", "png", "jpg", "jpeg"]
)

def g(r, k):
    return r.get(k, "UNKNOWN")


if uploaded_file:

    file_type = uploaded_file.type
    text = ""

    # PDF
    if "pdf" in file_type:
        text = extract_text_from_pdf(uploaded_file)

    # IMAGE
    else:
        text = extract_text_from_image(uploaded_file)

    if st.button("Analyze Invoice"):

        result = analyze_invoice(text)

        st.subheader("VAT Decision Result")

        st.write(f"👤 Customer Type: {g(result,'customer_type')}")
        st.write(f"🌍 Supplier Country: {g(result,'supplier_country')}")
        st.write(f"🌍 Customer Country: {g(result,'customer_country')}")
        st.write(f"🧾 Supplier VAT: {g(result,'supplier_vat')}")
        st.write(f"🧾 Customer VAT: {g(result,'customer_vat')}")
        st.write(f"🔁 Reverse Charge: {g(result,'reverse_charge')}")
        st.write(f"💰 VAT Status: {g(result,'vat_status')}")
        st.write(f"📊 Compliance: {g(result,'compliance')}")
