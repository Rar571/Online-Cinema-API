from sqlalchemy.ext.asyncio import AsyncSession
import stripe
from sqlalchemy.orm import selectinload
from stripe._util import logger

from models.orders import OrderModel, OrderStatusEnum
from models.payments import PaymentModel, StatusEnum, PaymentItemModel
from models.users import UserModel
from sqlalchemy import select
import os
from fastapi import Request, HTTPException, status

from schemas.payments import PaymentListSchema
from tasks.celery import send_email


async def create_checkout_session(
    order_id: int, db: AsyncSession, current_user: UserModel
):
    order_result = await db.execute(select(OrderModel).where(OrderModel.id == order_id))
    order = order_result.one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )
    if order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access")
    if order.status != OrderStatusEnum.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="order already paid or canceled",
        )
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"Order #{order.id}"},
                    "unit_amount": int(order.total_amount * 100),
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url="http://localhost:8000/payments/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="http://localhost:8000/payments/cancel",
        metadata={"order_id": order.id, "user_id": current_user.id},
    )
    return {"checkout_url": session.url}


async def stripe_webhook(request: Request, db: AsyncSession):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    event = stripe.Webhook.construct_event(
        payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
    )

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        order_id = session["metadata"]["order_id"]
        order_result = await db.execute(
            select(OrderModel).where(OrderModel.id == order_id).options(
                selectinload(OrderModel.user),
                selectinload(OrderModel.order_items))
        )
        order = order_result.one_or_none()
        if not order:
            logger.error(f"Order not found: {order_id}")
            return {"status": "received"}
        order.status = OrderStatusEnum.PAID
        db.add(order)
        await db.flush()
        payment = PaymentModel(
            user_id=session["metadata"]["user_id"],
            order_id=order_id,
            amount=session["amount_total"] / 100,
            status=StatusEnum.SUCCESSFUL,
            external_payment_id=session.get("payment_intent"),
        )
        db.add(payment)
        await db.flush()
        for item in order.order_items:
            payment_item = PaymentItemModel(
                payment_id=payment.id,
                order_item_id=item.id,
                price_at_payment=item.price_at_order,
            )
            db.add(payment_item)
        await db.commit()
        send_email.delay(
            subject="Payment is successful",
            body=f"Payment is successful for order with id: {order.id}",
            receiver_email=order.user.email,
        )
    elif event["type"] == "payment_intent.payment_failed":
        session = event["data"]["object"]
        order_id = session.get("metadata", {}).get("order_id")
        order_result = await db.execute(
            select(OrderModel).where(OrderModel.id == order_id)
        )
        order = order_result.one_or_none()
        if not order:
            logger.error(f"Order not found: {order_id}")
            return {"status": "received"}
        order.status = OrderStatusEnum.CANCELED
        await db.commit()
        return {"status": "received"}
    elif event["type"] == "checkout.session.expired":
        session = event["data"]["object"]
        order_id = session.get("metadata", {}).get("order_id")
        order_result = await db.execute(
            select(OrderModel).where(OrderModel.id == order_id)
        )
        order = order_result.one_or_none()
        if not order:
            logger.error(f"Order not found: {order_id}")
            return {"status": "received"}
        order.status = OrderStatusEnum.CANCELED
        await db.commit()
        return {"status": "received"}
    return {"status": "success"}


async def user_payment_history(db: AsyncSession, current_user: UserModel):
    payments = await db.execute(
        select(PaymentModel).where(PaymentModel.user_id == current_user.id)
    )
    payments = payments.scalars().all()
    if not payments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="There are no payments yet"
        )
    payment_schemas = [
        PaymentListSchema(
            date_and_time=payment.created_at,
            amount=payment.amount,
            status=payment.status,
        )
        for payment in payments
    ]
    return payment_schemas
