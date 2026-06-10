# -----------------------------
# VAT RULE ENGINE (FIXED)
# -----------------------------

if customer_type == "B2B" and cross_border:

    reverse_charge = True
    vat_status = "REVERSE CHARGE (0% VAT - NO VAT CHARGED BY SUPPLIER)"

    # Compliance rule: reverse charge requires valid EU B2B setup
    if not supplier_country or not customer_country:
        compliance = "NOT COMPLIANT"
    else:
        compliance = "COMPLIANT"

elif customer_type == "B2B":

    reverse_charge = False
    vat_status = "VAT CHARGED (DOMESTIC RATE APPLIES)"
    compliance = "COMPLIANT"

else:

    reverse_charge = False
    vat_status = "B2C VAT APPLIES"
    compliance = "COMPLIANT"
