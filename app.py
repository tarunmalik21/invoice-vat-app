import streamlit as st
from vat_engine import analyze_invoice

st.set_page_config(page_title="VAT Checker", layout="centered")

st.title("VAT Decision Result")

text = st.text_area("Paste Invoice OCR Text")

def g(r, k):
    return r.get(k, "UNKNOWN")

if st.button("Analyze"):

    if not text:
        st.warning("Please paste invoice text")
    else:
        result = analyze_invoice(text)

        st.write(f"👤 Customer Type: {g(result,'customer_type')}")
        st.write(f"🌍 Supplier Country: {g(result,'supplier_country')}")
        st.write(f"🌍 Customer Country: {g(result,'customer_country')}")
        st.write(f"🧾 Supplier VAT: {g(result,'supplier_vat')}")
        st.write(f"🧾 Customer VAT: {g(result,'customer_vat')}")
        st.write(f"🔁 Reverse Charge: {g(result,'reverse_charge')}")
        st.write(f"💰 VAT Status: {g(result,'vat_status')}")
        st.write(f"📊 Compliance: {g(result,'compliance')}")
