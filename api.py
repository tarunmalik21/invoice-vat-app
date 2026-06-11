from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
title="EU VAT Invoice Checker API",
version="1.0"
)

class InvoiceRequest(BaseModel):
invoice_text: str

@app.get("/")
def home():
return {
"message": "EU VAT Invoice Checker API",
"status": "running"
}

@app.get("/health")
def health():
return {
"status": "healthy"
}

@app.post("/validate")
def validate_invoice(request: InvoiceRequest):

```
text = request.invoice_text

reverse_charge = "reverse charge" in text.lower()

return {
    "status": "Analysis Complete",
    "reverse_charge_detected": reverse_charge,
    "invoice_length": len(text)
}
```
