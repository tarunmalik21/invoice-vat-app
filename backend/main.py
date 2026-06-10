
from fastapi import FastAPI
from routes.invoice import router as invoice_router

app = FastAPI(title="EU VAT SaaS API")

app.include_router(invoice_router, prefix="/api")
