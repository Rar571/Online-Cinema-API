from fastapi import APIRouter, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from crud.orders import (
    view_orders_list,
    cancel_order_if_not_paid,
    refund_request,
    view_users_orders,
)
from db.session_postgresql import get_db
from dependencies.authorization import require_admin
from dependencies.users import get_current_user_model
from models.orders import OrderStatusEnum
from models.users import UserModel
from datetime import datetime

orders_router = APIRouter()


@orders_router.get("/orders/", status_code=status.HTTP_200_OK)
async def list_orders(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_model),
):
    """
    Gets orders list for current user.
    """
    return await view_orders_list(db=db, current_user=current_user)


@orders_router.post("/orders/{order_id}/cancel/", status_code=status.HTTP_200_OK)
async def cancel_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_model),
):
    """
    Cancels an pending order for current user.
    """
    return await cancel_order_if_not_paid(
        order_id=order_id, db=db, current_user=current_user
    )


@orders_router.post("/orders/{order_id}/refund/", status_code=status.HTTP_201_CREATED)
async def refund(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_model),
):
    """
    Refunds payment via stripe refund. Changes order status to 'canceled' and payment status to 'refunded'.
    """
    return await refund_request(order_id=order_id, db=db, current_user=current_user)


@orders_router.get("/orders/history/", status_code=status.HTTP_200_OK)
async def view_orders_list_for_admin(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_model),
    users_id: list[int] | None = None,
    dates: list[datetime] | None = None,
    statuses: list[OrderStatusEnum] | None = None,
):
    """
    Gets orders list for a specific user with filters (available only for admin).
    """
    await require_admin(current_user=current_user)
    return await view_users_orders(
        db=db,
        current_user=current_user,
        users_id=users_id,
        dates=dates,
        statuses=statuses,
    )
