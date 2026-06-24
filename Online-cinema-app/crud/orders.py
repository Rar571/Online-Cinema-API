from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse

from models.orders import OrderModel, OrderItemModel, OrderStatusEnum
from models.users import UserModel

from fastapi import status, HTTPException

from schemas.orders import OrderListSchema, Movie


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


async def cancel_order_if_not_paid(order_id: int, db: AsyncSession, current_user: UserModel):
    order_result = await db.execute(select(OrderModel).where(
        OrderModel.id == order_id,
        OrderModel.user_id == current_user.id,
        OrderModel.status == OrderStatusEnum.PENDING
    ))
    order = order_result.one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    order.status = OrderStatusEnum.CANCELED
    await db.commit()
    return JSONResponse(status_code=status.HTTP_200_OK, content={"detail": "Order is canceled"})
