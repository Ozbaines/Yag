import hashlib
import hmac

import httpx

from shared.config import settings
from shared.logger import logger

PRODUCTS = {
    "pro_monthly": {"price": 299, "name": "PRO-доступ 30 дней", "days": 30},
    "pro_yearly":  {"price": 1990, "name": "PRO-доступ 365 дней", "days": 365},
}

PRODAMUS_BASE = "https://pay.prodamus.ru/api/v2"


def create_payment_link(product_code: str, tg_id: int, email: str = "") -> dict:
    """Prodamus uses form-based checkout; we build a signed link."""
    product = PRODUCTS.get(product_code)
    if not product:
        raise ValueError(f"Unknown product: {product_code}")

    params = {
        "shop": settings.PRODAMUS_SHOP,
        "amount": str(product["price"]),
        "currency": "RUB",
        "name": product["name"],
        "email": email or "",
        "custom_tg_id": str(tg_id),
        "custom_product_code": product_code,
    }
    # Prodamus signature: HMAC-SHA256 over sorted key=value pairs
    sig_string = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    signature = hmac.new(settings.PRODAMUS_SECRET.encode(), sig_string.encode(), hashlib.sha256).hexdigest()
    params["signature"] = signature

    url = f"https://pay.prodamus.ru/pay?{'&'.join(f'{k}={v}' for k, v in params.items())}"
    return {"payment_id": None, "confirmation_url": url}


def verify_webhook(payload: dict, received_sign: str) -> bool:
    """Verify incoming Prodamus webhook signature."""
    data = {k: v for k, v in payload.items() if k != "signature"}
    sig_string = "&".join(f"{k}={v}" for k, v in sorted(data.items()))
    expected = hmac.new(settings.PRODAMUS_SECRET.encode(), sig_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received_sign)


def parse_webhook(payload: dict) -> dict | None:
    status = payload.get("status")
    if status != "success":
        return None
    custom = payload.get("custom", {})
    return {
        "provider": "prodamus",
        "provider_payment_id": payload.get("payment_id") or payload.get("id", ""),
        "status": "succeeded",
        "amount": float(payload.get("amount", 0)),
        "currency": "RUB",
        "tg_id": int(custom["tg_id"]) if custom.get("tg_id") else None,
        "email": payload.get("email"),
        "product_code": custom.get("product_code", "pro_monthly"),
        "days": PRODUCTS.get(custom.get("product_code", "pro_monthly"), {}).get("days", 30),
        "raw": payload,
    }
