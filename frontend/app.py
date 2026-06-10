import streamlit as st
import requests

st.title("EU VAT Invoice Checker SaaS")

uploaded = st.file_uploader("Upload Invoice")

if uploaded:
    st.write("Processing invoice...")

    payload = {
        "country": "DE",
        "vat_rate": 19,
        "is_b2b": True
    }

    response = requests.post(
        "http://localhost:8000/api/check-invoice",
        json=payload
    )

    st.json(response.json())
