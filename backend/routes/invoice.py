from fastapi import APIRouter
from vat_engine import check_invoice

router = APIRouter()

@router.post("/check-invoice")
def validate_invoice(data: dict):
    result = check_invoice(data)
    return result
