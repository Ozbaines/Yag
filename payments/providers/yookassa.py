import uuid

from yookassa import Configuration, Payment
from yookassa.domain.models import Currency

from shared.config import settings
from shared.logger import logger

PRODUCTS = {
    "pro_monthly": {"amount": "299.00", "description": "PRO-доступ на 30 дней", "days": 30},
    "pro_yearly":  {"amount": "1990.00", "description": "PRO-доступ на 365 дней", "days": 365},
}


def _configure():
    Configuration.account_id = settings.YOOKASSA_SHOP_ID
    Configuration.secret_key = settings.YOOKASSA_SECRET_KEY


def create_payment_link(product_code: str, tg_id: int, email: str = "") -> dict:
    """Returns {"payment_id": ..., "confirmation_url": ...}"""
    _configure()
    product = PRODUCTS.get(product_code)
    if not product:
        raise ValueError(f"Unknown product: {product_code}")

    payment = Payment.create({
        "amount": {"value": product["amount"], "currency": Currency.RUB},
        "confirmation": {"type": "redirect", "return_url": f"{settings.TG_CHANNEL_URL}"},
        "capture": True,
        "description": product["description"],
        "metadata": {"tg_id": str(tg_id), "product_code": product_code},
        "receipt": {
            "customer": {"email": email or "noreply@yag.app"},
            "items": [{
                "description": product["description"],
                "quantity": "1.0",
                "amount": {"value": product["amount"], "currency": Currency.RUB},
                "vat_code": "1",
            }],
        },
    }, uuid.uuid4())
    return {
        "payment_id": payment.id,
        "confirmation_url": payment.confirmation.confirmation_url,
    }


def parse_webhook(payload: dict) -> dict | None:
    """
    Parse YooKassa webhook event.
    Returns normalized event or None if not actionable.
    """
    event = payload.get("event")
    obj = payload.get("object", {})
    if event not in ("payment.succeeded", "payment.canceled"):
        return None
    metadata = obj.get("metadata", {})
    return {
        "provider": "yookassa",
        "provider_payment_id": obj.get("id"),
        "status": "succeeded" if event == "payment.succeeded" else "failed",
        "amount": float(obj.get("amount", {}).get("value", 0)),
        "currency": obj.get("amount", {}).get("currency", "RUB"),
        "tg_id": int(metadata["tg_id"]) if metadata.get("tg_id") else None,
        "email": (obj.get("receipt", {}).get("customer") or {}).get("email"),
        "product_code": metadata.get("product_code", "pro_monthly"),
        "days": PRODUCTS.get(metadata.get("product_code", "pro_monthly"), {}).get("days", 30),
        "raw": payload,
    }
