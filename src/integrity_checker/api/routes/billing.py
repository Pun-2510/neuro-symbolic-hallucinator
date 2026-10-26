"""Billing & Subscription routes — Plans catalog, Stripe Demo Checkout, Verification & Management."""

from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from integrity_checker.api.deps import get_current_user, get_current_user_optional, get_db
from integrity_checker.api.routes.auth import _to_response_dict
from integrity_checker.billing.plans import (
    BILLING_CYCLES,
    PLAN_CATALOG,
    PLAN_TIERS,
    ensure_user_quota_current,
    get_plan_catalog_list,
    get_plan_policy,
    get_user_subscription_summary,
)
from integrity_checker.db.models import BillingTransaction, User
from integrity_checker.db.repository import Repository

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------- Schemas ----------


class CreateCheckoutSessionRequest(BaseModel):
    plan_tier: str = Field(..., description="Target tier: 'pro' or 'ultra'")
    billing_cycle: str = Field(default="monthly", description="'monthly' or 'annual'")
    force_demo: bool = Field(default=False, description="Force built-in Stripe demo sandbox")


class VerifyCheckoutSessionRequest(BaseModel):
    session_id: str = Field(..., min_length=5, max_length=120)
    card_last4: str = Field(default="4242", max_length=4)
    card_brand: str = Field(default="visa", max_length=20)


class CancelSubscriptionRequest(BaseModel):
    immediate: bool = Field(
        default=False,
        description="If True, immediately downgrade to basic; otherwise cancel at period end.",
    )


def _serialize_transaction(tx: BillingTransaction) -> dict[str, Any]:
    policy = get_plan_policy(tx.plan_tier)
    return {
        "id": tx.id,
        "user_id": tx.user_id,
        "stripe_session_id": tx.stripe_session_id,
        "stripe_payment_intent_id": tx.stripe_payment_intent_id,
        "plan_tier": tx.plan_tier,
        "plan_name": policy.name,
        "billing_cycle": tx.billing_cycle,
        "amount_usd": tx.amount_usd,
        "currency": tx.currency,
        "status": tx.status,
        "payment_mode": tx.payment_mode,
        "card_brand": tx.card_brand,
        "card_last4": tx.card_last4,
        "created_at": tx.created_at.isoformat() if tx.created_at else None,
        "paid_at": tx.paid_at.isoformat() if tx.paid_at else None,
    }


# ---------- Endpoints ----------


@router.get("/plans")
def list_billing_plans(
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return full 3-tier pricing catalog (Basic, Pro, Ultra) and current user subscription if logged in."""
    current_sub = None
    if current_user is not None:
        if ensure_user_quota_current(current_user):
            db.commit()
        current_sub = get_user_subscription_summary(current_user)

    return {
        "plans": get_plan_catalog_list(),
        "current_subscription": current_sub,
    }


@router.get("/subscription")
def get_my_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return authenticated user's current subscription, quota usage, and billing history."""
    repo = Repository(db)
    if ensure_user_quota_current(current_user):
        repo.commit()

    txs = repo.list_billing_transactions_for_user(current_user.id, limit=30)
    return {
        "subscription": get_user_subscription_summary(current_user),
        "transactions": [_serialize_transaction(t) for t in txs],
    }


@router.post("/create-checkout-session")
def create_checkout_session(
    request: CreateCheckoutSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Create a Stripe Checkout Session (Real Stripe Test Mode if configured, else Built-in Stripe Demo Sandbox)."""
    tier = request.plan_tier.strip().lower()
    cycle = request.billing_cycle.strip().lower()

    if tier not in PLAN_TIERS or tier == "basic":
        raise HTTPException(
            status_code=400,
            detail="Invalid paid plan_tier. Must be 'pro' or 'ultra'.",
        )
    if cycle not in BILLING_CYCLES:
        raise HTTPException(
            status_code=400,
            detail="Invalid billing_cycle. Must be 'monthly' or 'annual'.",
        )

    policy = PLAN_CATALOG[tier]
    amount_usd = float(
        policy.annual_price_usd if cycle == "annual" else policy.monthly_price_usd
    )

    repo = Repository(db)
    stripe_secret = os.getenv("STRIPE_SECRET_KEY", "").strip()
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")

    # Attempt Real Stripe Test Mode if sk_test_ key is provided and not force_demo
    if stripe_secret.startswith("sk_test_") and not request.force_demo:
        try:
            import stripe  # type: ignore

            stripe.api_key = stripe_secret
            interval = "year" if cycle == "annual" else "month"
            unit_amount_cents = int(round(amount_usd * 100))

            stripe_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="subscription",
                customer_email=current_user.email or f"{current_user.username}@citra.edu.vn",
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": f"CITRA {policy.name} Plan ({cycle.capitalize()})",
                                "description": policy.tagline_en,
                            },
                            "unit_amount": unit_amount_cents,
                            "recurring": {"interval": interval},
                        },
                        "quantity": 1,
                    }
                ],
                metadata={
                    "user_id": str(current_user.id),
                    "plan_tier": tier,
                    "billing_cycle": cycle,
                },
                success_url=f"{frontend_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{frontend_url}/pricing?canceled=1",
            )
            tx = repo.create_billing_transaction(
                user_id=current_user.id,
                stripe_session_id=stripe_session.id,
                plan_tier=tier,
                billing_cycle=cycle,
                amount_usd=amount_usd,
                status="pending",
                payment_mode="stripe_test",
            )
            repo.commit()
            return {
                "session_id": stripe_session.id,
                "checkout_url": stripe_session.url,
                "mode": "stripe_test",
                "plan_tier": tier,
                "plan_name": policy.name,
                "billing_cycle": cycle,
                "amount_usd": amount_usd,
                "transaction_id": tx.id,
            }
        except Exception as exc:
            logger.warning(f"Stripe SDK fallback to built-in demo checkout: {exc}")

    # Built-in Interactive Stripe Demo Checkout Session (works 100% offline/local without external keys)
    session_id = f"cs_test_demo_{secrets.token_hex(16)}"
    tx = repo.create_billing_transaction(
        user_id=current_user.id,
        stripe_session_id=session_id,
        plan_tier=tier,
        billing_cycle=cycle,
        amount_usd=amount_usd,
        status="pending",
        payment_mode="stripe_demo",
    )
    repo.commit()

    return {
        "session_id": session_id,
        "checkout_url": f"/billing/checkout?session_id={session_id}",
        "mode": "stripe_demo",
        "plan_tier": tier,
        "plan_name": policy.name,
        "billing_cycle": cycle,
        "amount_usd": amount_usd,
        "transaction_id": tx.id,
    }


@router.get("/checkout-session/{session_id}")
def get_checkout_session_details(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Fetch checkout session summary for the Built-in Stripe Demo Checkout UI."""
    repo = Repository(db)
    tx = repo.get_billing_transaction_by_session(session_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Checkout session not found")
    if tx.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    policy = get_plan_policy(tx.plan_tier)
    monthly_equiv = (
        policy.annual_monthly_equiv_usd
        if tx.billing_cycle == "annual"
        else policy.monthly_price_usd
    )
    savings_usd = policy.annual_savings_usd if tx.billing_cycle == "annual" else 0

    return {
        "session_id": tx.stripe_session_id,
        "status": tx.status,
        "payment_mode": tx.payment_mode,
        "merchant_name": "CITRA (SourceLogic) Inc.",
        "customer_email": current_user.email or f"{current_user.username}@citra.edu.vn",
        "customer_name": current_user.full_name or current_user.username,
        "plan_tier": tx.plan_tier,
        "plan_name": f"CITRA {policy.name}",
        "billing_cycle": tx.billing_cycle,
        "amount_usd": tx.amount_usd,
        "monthly_equivalent_usd": monthly_equiv,
        "annual_savings_usd": savings_usd,
        "currency": tx.currency,
        "features_en": list(policy.features_en[:6]),
        "features_vi": list(policy.features_vi[:6]),
    }


@router.post("/verify-session")
def verify_checkout_session(
    request: VerifyCheckoutSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Verify and finalize a Stripe Demo / Test checkout session, activating the user's paid plan."""
    repo = Repository(db)
    tx = repo.get_billing_transaction_by_session(request.session_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Checkout session not found")
    if tx.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    target_user = repo.get_user_by_id(tx.user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now(timezone.utc)

    # Idempotent activation: only mutate if not already succeeded
    if tx.status != "succeeded":
        tx.status = "succeeded"
        tx.paid_at = now
        tx.stripe_payment_intent_id = f"pi_demo_{secrets.token_hex(12)}"
        clean_last4 = "".join(ch for ch in (request.card_last4 or "4242") if ch.isdigit())[-4:]
        tx.card_last4 = clean_last4 if len(clean_last4) == 4 else "4242"
        tx.card_brand = (request.card_brand or "visa").strip().lower()[:20]

        period_days = 365 if tx.billing_cycle == "annual" else 30
        target_user.plan_tier = tx.plan_tier
        target_user.billing_cycle = tx.billing_cycle
        target_user.subscription_status = "active"
        target_user.cancel_at_period_end = 0
        target_user.current_period_start = now
        target_user.current_period_end = now + timedelta(days=period_days)
        if not target_user.stripe_customer_id:
            target_user.stripe_customer_id = f"cus_demo_{target_user.id}"
        target_user.stripe_subscription_id = f"sub_demo_{secrets.token_hex(8)}"
        if target_user.quota_reset_at is None:
            target_user.quota_reset_at = now + timedelta(days=30)

        repo.commit()
        db.refresh(target_user)
        db.refresh(tx)

    return {
        "status": "succeeded",
        "message": f"Successfully upgraded to CITRA {get_plan_policy(target_user.plan_tier).name} ({tx.billing_cycle})!",
        "transaction": _serialize_transaction(tx),
        "subscription": get_user_subscription_summary(target_user),
        "user": _to_response_dict(target_user),
    }


@router.post("/cancel")
def cancel_subscription(
    request: CancelSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Cancel auto-renewal at period end or downgrade immediately to Basic."""
    repo = Repository(db)
    current_tier = (current_user.plan_tier or "basic").lower()
    if current_tier == "basic":
        raise HTTPException(
            status_code=400,
            detail="You are currently on the free Basic plan.",
        )

    if request.immediate:
        current_user.plan_tier = "basic"
        current_user.billing_cycle = None
        current_user.subscription_status = "canceled"
        current_user.cancel_at_period_end = 0
        current_user.current_period_end = None
        current_user.stripe_subscription_id = None
        msg = "Subscription canceled immediately. Your account is now on the Basic plan."
    else:
        current_user.cancel_at_period_end = 1
        msg = "Subscription auto-renewal canceled. You will retain paid benefits until the end of your billing period."

    repo.commit()
    db.refresh(current_user)

    return {
        "message": msg,
        "subscription": get_user_subscription_summary(current_user),
        "user": _to_response_dict(current_user),
    }


@router.post("/reactivate")
def reactivate_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Resume auto-renewal for a subscription scheduled to cancel at period end."""
    repo = Repository(db)
    if (current_user.plan_tier or "basic").lower() == "basic":
        raise HTTPException(
            status_code=400,
            detail="No active paid subscription to reactivate.",
        )

    current_user.cancel_at_period_end = 0
    current_user.subscription_status = "active"
    repo.commit()
    db.refresh(current_user)

    return {
        "message": "Subscription auto-renewal has been reactivated.",
        "subscription": get_user_subscription_summary(current_user),
        "user": _to_response_dict(current_user),
    }
