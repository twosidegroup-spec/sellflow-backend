"""Payment account routes.

Mounted at the repository root (`/payment-accounts/...`) matching System A, so
the Kotlin Payment Bridge's `connect` call needs no rebuild. The tenant comes
from the device credential or a membership-checked user token; a seller only
ever sees or edits their own accounts.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.devices.bridge_dependencies import require_user_or_device_business
from app.devices.bridge_schemas import PaymentAccountConnectRequest
from app.payments.models import PaymentAccount
from app.utils.phone import normalize_phone

router = APIRouter(prefix="/payment-accounts", tags=["Payment Accounts"])

VALID_PROVIDERS = {"bkash", "nagad", "rocket", "upay"}


@router.get("")
def list_payment_accounts(
    business_id: int = Depends(require_user_or_device_business),
    db: Session = Depends(get_db),
):
    accounts = (
        db.query(PaymentAccount)
        .filter(PaymentAccount.business_id == business_id)
        .order_by(PaymentAccount.id.asc())
        .all()
    )
    return [
        {
            "id": account.id,
            "business_id": account.business_id,
            "provider": account.provider,
            "receiving_number": account.receiving_number,
            "account_type": account.account_type,
            "status": account.status,
            "mode": account.mode,
            "connected_at": account.connected_at.isoformat() if account.connected_at else None,
            "updated_at": account.updated_at.isoformat() if account.updated_at else None,
        }
        for account in accounts
    ]


@router.post("/connect", status_code=status.HTTP_200_OK)
def connect_payment_account_route(
    payload: PaymentAccountConnectRequest,
    business_id: int = Depends(require_user_or_device_business),
    db: Session = Depends(get_db),
):
    provider = payload.provider.strip().lower()
    if provider not in VALID_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail=f"provider must be one of {sorted(VALID_PROVIDERS)}",
        )
    try:
        receiving_number = normalize_phone(payload.receiving_number)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="receiving_number must be a valid Bangladesh mobile number",
        ) from exc
    if not receiving_number:
        raise HTTPException(status_code=422, detail="receiving_number is required")

    account = (
        db.query(PaymentAccount)
        .filter(
            PaymentAccount.business_id == business_id,
            PaymentAccount.provider == provider,
        )
        .first()
    )
    if account is None:
        account = PaymentAccount(
            business_id=business_id,
            provider=provider,
            receiving_number=receiving_number,
            account_type=payload.account_type,
            status="configured",
            mode="live",
        )
        db.add(account)
    else:
        account.receiving_number = receiving_number
        account.account_type = payload.account_type
        account.status = "configured"
    db.commit()
    db.refresh(account)

    return {
        "id": account.id,
        "business_id": account.business_id,
        "provider": account.provider,
        "receiving_number": account.receiving_number,
        "account_type": account.account_type,
        "status": account.status,
        "mode": account.mode,
    }
