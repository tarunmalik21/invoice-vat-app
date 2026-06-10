def check_invoice(data):
    country = data.get("country")
    vat_rate = data.get("vat_rate")
    is_b2b = data.get("is_b2b")

    result = {
        "status": "PASS",
        "issues": []
    }

    # Example rule engine
    if is_b2b and vat_rate != 0:
        result["status"] = "FAIL"
        result["issues"].append("B2B invoice should use 0% reverse charge")

    if country == "DE" and vat_rate not in [0, 7, 19]:
        result["status"] = "FAIL"
        result["issues"].append("Invalid VAT rate for Germany")

    return result
