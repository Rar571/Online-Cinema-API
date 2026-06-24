from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse
import stripe
from models.orders import OrderModel, OrderItemModel, OrderStatusEnum
from models.payments import PaymentModel, StatusEnum
from models.users import UserModel

from fastapi import status, HTTPException

from schemas.orders import OrderListSchema, Movie
from tasks.celery import send_email


async def view_orders_list(db: AsyncSession, current_user: UserModel):
    orders_result = await db.execute(
        select(OrderModel).where(OrderModel.user_id == current_user.id)
    )
    orders = orders_result.scalars().all()
    if not orders:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "There are no orders yet"},
        )
    orders_list = []
    for order in orders:
        items_result = await db.execute(
            select(OrderItemModel)
            .where(
                OrderItemModel.order_id == order.id,
            )
            .options(selectinload(OrderItemModel.movie))
        )
        items = items_result.scalars().all()
        movies_schemas = [
            Movie(
                name=item.movie.name,
                year=item.movie.year,
                price_at_order=item.price_at_order,
            )
            for item in items
        ]
        order_schema = OrderListSchema(
            created_at=order.created_at,
            movies=movies_schemas,
            total_amount=order.total_amount,
            status=order.status,
        )
        orders_list.append(order_schema)
    return orders_list


async def cancel_order_if_not_paid(
    order_id: int, db: AsyncSession, current_user: UserModel
):
    order_result = await db.execute(
        select(OrderModel).where(
            OrderModel.id == order_id,
            OrderModel.user_id == current_user.id,
            OrderModel.status == OrderStatusEnum.PENDING,
        )
    )
    order = order_result.one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )
    order.status = OrderStatusEnum.CANCELED
    await db.commit()
    return JSONResponse(
        status_code=status.HTTP_200_OK, content={"detail": "Order is canceled"}
    )


async def refund_request(order_id: int, db: AsyncSession, current_user: UserModel):
    order_result = await db.execute(
        select(OrderModel).where(
            OrderModel.id == order_id,
            OrderModel.user_id == current_user.id,
            OrderModel.status == OrderStatusEnum.PAID,
        )
    )
    order = order_result.one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    payment_result = await db.execute(
        select(PaymentModel).where(
            PaymentModel.order_id == order.id,
            PaymentModel.status == StatusEnum.SUCCESSFUL,
            PaymentModel.user_id == current_user.id,
        )
    )
    payment = payment_result.one_or_none()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
        )
    try:
        refund = stripe.Refund.create(payment_intent=payment.external_payment_id)
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Refund failed: {e}"
        )
    order.status = OrderStatusEnum.CANCELED
    payment.status = StatusEnum.REFUNDED
    await db.commit()
    send_email.delay(
        subject="Stripe refund",
        body=f"Your payment is refunded successfully: {refund}",
        receiver_email=current_user.email,
    )
    return refund
