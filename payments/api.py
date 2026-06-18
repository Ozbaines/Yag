from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel

from payments.providers.yookassa import create_payment_link as yk_link, parse_webhook as yk_parse
from payments.providers.prodamus import create_payment_link as pd_link, parse_webhook as pd_parse, verify_webhook as pd_verify
from shared.config import settings
from shared.db import Payment, PaymentStatus, get_session, init_db
from shared.logger import logger
from shared.queue import Q_PAYMENT_EVENT, push


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="YAg Payments API", lifespan=lifespan)


class CheckoutRequest(BaseModel):
    provider: str  # "yookassa" | "prodamus"
    product_code: str
    tg_id: int
    email: str = ""


class CheckoutResponse(BaseModel):
    payment_id: str | None
    confirmation_url: str


@app.post("/checkout", response_model=CheckoutResponse)
async def checkout(req: CheckoutRequest) -> CheckoutResponse:
    if req.provider == "yookassa":
        if not settings.YOOKASSA_SHOP_ID:
            raise HTTPException(status_code=503, detail="YooKassa not configured")
        result = yk_link(req.product_code, req.tg_id, req.email)
    elif req.provider == "prodamus":
        if not settings.PRODAMUS_SHOP:
            raise HTTPException(status_code=503, detail="Prodamus not configured")
        result = pd_link(req.product_code, req.tg_id, req.email)
    else:
        raise HTTPException(status_code=400, detail="Unknown provider")
    return CheckoutResponse(**result)


@app.post("/webhooks/yookassa", status_code=status.HTTP_200_OK)
async def webhook_yookassa(request: Request):
    payload = await request.json()
    event = yk_parse(payload)
    if not event:
        return {"ok": True}
    await _process_event(event)
    return {"ok": True}


@app.post("/webhooks/prodamus", status_code=status.HTTP_200_OK)
async def webhook_prodamus(request: Request, x_signature: str = Header(default="")):
    payload = await request.json()
    if settings.PRODAMUS_SECRET and not pd_verify(payload, x_signature):
        raise HTTPException(status_code=403, detail="Bad signature")
    event = pd_parse(payload)
    if not event:
        return {"ok": True}
    await _process_event(event)
    return {"ok": True}


async def _process_event(event: dict) -> None:
    logger.info("payment event: provider={} status={} tg_id={}", event["provider"], event["status"], event["tg_id"])
    async with get_session() as s:
        pay = Payment(
            provider=event["provider"],
            provider_payment_id=event["provider_payment_id"],
            subscriber_tg_id=event.get("tg_id"),
            email=event.get("email"),
            amount=event["amount"],
            currency=event.get("currency", "RUB"),
            product_code=event.get("product_code", ""),
            status=PaymentStatus(event["status"]) if event["status"] in PaymentStatus.__members__.values() else PaymentStatus.failed,
            raw=event.get("raw"),
        )
        s.add(pay)

    if event["status"] == "succeeded" and event.get("tg_id"):
        await push(Q_PAYMENT_EVENT, {
            "tg_id": event["tg_id"],
            "status": "succeeded",
            "product_code": event.get("product_code"),
            "days": event.get("days", 30),
        })


@app.get("/health")
async def health():
    return {"ok": True}
