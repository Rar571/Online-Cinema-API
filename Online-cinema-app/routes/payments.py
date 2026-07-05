from fastapi import APIRouter, status, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from crud.payments import (
    create_checkout_session,
    stripe_webhook,
    user_payment_history,
    view_all_payment_history,
)
from db.session_postgresql import get_db
from dependencies.authorization import require_admin
from dependencies.users import get_current_user_model
from models.payments import StatusEnum
from models.users import UserModel
from schemas.payments import CheckoutSessionResponse
from datetime import datetime

payment_router = APIRouter()


@payment_router.post(
    "/payments/{order_id}/pay/",
    status_code=status.HTTP_201_CREATED,
    response_model=CheckoutSessionResponse,
)
async def pay_for_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_model),
):
    return await create_checkout_session(
        order_id=order_id, db=db, current_user=current_user
    )


@payment_router.post("/webhook/")
async def webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    return await stripe_webhook(request=request, db=db)


@payment_router.get("/payments/", status_code=status.HTTP_200_OK)
async def payments_for_user(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_model),
):
    return await user_payment_history(db=db, current_user=current_user)


@payment_router.get("/payments/all/", status_code=status.HTTP_200_OK)
async def all_payments(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_model),
    users_id: list[int] | None = None,
    dates: list[datetime] | None = None,
    statuses: list[StatusEnum] | None = None,
):
    await require_admin(current_user=current_user)
    return await view_all_payment_history(
        db=db,
        current_user=current_user,
        users_id=users_id,
        dates=dates,
        statuses=statuses,
    )
