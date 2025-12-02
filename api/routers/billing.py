"""
Router de Billing y Suscripciones.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from core.database import fetchrow, execute, fetch
from core.config import settings
from .users import get_current_user

router = APIRouter()

# Schemas
class Plan(BaseModel):
    id: str
    name: str
    price_monthly: float
    price_yearly: float
    max_symbols: int
    max_capital: float
    features: dict

class Subscription(BaseModel):
    plan: str
    status: str
    started_at: datetime
    expires_at: Optional[datetime]

class SubscribeRequest(BaseModel):
    plan_id: str
    billing_cycle: str = "monthly"  # monthly, yearly

# Endpoints
@router.get("/plans", response_model=List[Plan])
async def list_plans():
    """Lista todos los planes disponibles."""
    rows = await fetch(
        """
        SELECT id, name, price_monthly, price_yearly, max_symbols, max_capital, features
        FROM plans
        WHERE is_active = TRUE
        ORDER BY price_monthly ASC
        """
    )

    return [
        Plan(
            id=str(row["id"]),
            name=row["name"],
            price_monthly=float(row["price_monthly"] or 0),
            price_yearly=float(row["price_yearly"] or 0),
            max_symbols=row["max_symbols"],
            max_capital=float(row["max_capital"]),
            features=row["features"] or {}
        )
        for row in rows
    ]

@router.get("/subscription", response_model=Subscription)
async def get_subscription(current_user: dict = Depends(get_current_user)):
    """Obtiene la suscripción actual del usuario."""
    user_id = str(current_user["id"])

    row = await fetchrow(
        """
        SELECT p.name, s.status, s.started_at, s.expires_at
        FROM subscriptions s
        JOIN plans p ON s.plan_id = p.id
        WHERE s.user_id = $1 AND s.status = 'active'
        """,
        user_id
    )

    if not row:
        return Subscription(
            plan="Free",
            status="active",
            started_at=datetime.utcnow(),
            expires_at=None
        )

    return Subscription(
        plan=row["name"],
        status=row["status"],
        started_at=row["started_at"],
        expires_at=row["expires_at"]
    )

@router.post("/subscribe")
async def subscribe_to_plan(
    request: SubscribeRequest,
    current_user: dict = Depends(get_current_user)
):
    """Inicia proceso de suscripción a un plan."""
    user_id = str(current_user["id"])

    # Obtener plan
    plan = await fetchrow(
        "SELECT id, name, price_monthly, price_yearly FROM plans WHERE id = $1",
        request.plan_id
    )

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )

    # Si es plan gratuito, activar directamente
    if plan["price_monthly"] == 0:
        await execute(
            """
            UPDATE subscriptions SET status = 'cancelled' WHERE user_id = $1;
            INSERT INTO subscriptions (user_id, plan_id, status)
            VALUES ($1, $2, 'active')
            """,
            user_id, request.plan_id
        )
        return {"message": "Subscribed to Free plan"}

    # TODO: Integrar con Stripe para planes de pago
    # Por ahora, solo retornamos un placeholder

    return {
        "message": "Stripe integration required",
        "checkout_url": "https://stripe.com/checkout/placeholder",
        "plan": plan["name"],
        "price": float(plan["price_monthly"] if request.billing_cycle == "monthly" else plan["price_yearly"])
    }

@router.post("/cancel")
async def cancel_subscription(current_user: dict = Depends(get_current_user)):
    """Cancela la suscripción actual."""
    user_id = str(current_user["id"])

    await execute(
        """
        UPDATE subscriptions
        SET status = 'cancelled'
        WHERE user_id = $1 AND status = 'active'
        """,
        user_id
    )

    # Cambiar a plan Free
    free_plan = await fetchrow("SELECT id FROM plans WHERE name = 'Free'")
    if free_plan:
        await execute(
            """
            INSERT INTO subscriptions (user_id, plan_id, status)
            VALUES ($1, $2, 'active')
            """,
            user_id, str(free_plan["id"])
        )

    return {"message": "Subscription cancelled. Downgraded to Free plan."}

@router.get("/invoices")
async def list_invoices(current_user: dict = Depends(get_current_user)):
    """Lista el historial de facturas."""
    # TODO: Integrar con Stripe
    return {"invoices": [], "message": "Stripe integration required"}

@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Webhook para eventos de Stripe."""
    # TODO: Implementar manejo de webhooks de Stripe
    payload = await request.body()

    # Verificar firma del webhook
    # stripe_signature = request.headers.get("stripe-signature")

    return {"received": True}
