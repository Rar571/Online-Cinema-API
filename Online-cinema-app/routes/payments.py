from fastapi import APIRouter, status, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from crud.payments import create_checkout_session, stripe_webhook
from db.session_postgresql import get_db
from dependencies.users import get_current_user_model
from models.users import UserModel
from schemas.payments import CheckoutSessionResponse

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
async def webhook(request: Request, db: AsyncSession = Depends(get_db)):
    return await stripe_webhook(request=request, db=db)
