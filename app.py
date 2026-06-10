import streamlit as st
import sys
import importlib

# -----------------------------
# FIX PATH (important for Streamlit Cloud)
# -----------------------------
sys.path.append(".")

# -----------------------------
# IMPORT VAT ENGINE (fresh reload to avoid old cache)
# -----------------------------
import backend.vat_engine as vat_engine
importlib.reload(vat_engine)

# -----------------------------
# UI
# -----------------------------
st.set_page_config(page_title="EU VAT Invoice Checker")

st.title("EU VAT Invoice Checker")

st.write("Upload an invoice file to analyze VAT compliance")

# -----------------------------
# FILE UPLOAD
# -----------------------------
uploaded_file = st.file_uploader("Upload Invoice", type=["txt"])

if uploaded_file:

    # Read invoice
    text = uploaded_file.read().decode("utf-8")

    st.subheader("📄 Invoice Text")
    st.text(text)

    # -----------------------------
    # CALL BACKEND ENGINE
    # -----------------------------
    result = vat_engine.analyze_invoice(text)

    # -----------------------------
    # DISPLAY RESULT
    # -----------------------------
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
