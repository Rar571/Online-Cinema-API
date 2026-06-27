from typing import Optional, List

from sqlalchemy import Integer, ForeignKey, DateTime, func, Enum, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session_postgresql import Base
from datetime import datetime
import enum

from models.movies import MovieModel
from models.users import UserModel
from decimal import Decimal


class OrderStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELED = "canceled"


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped[UserModel] = relationship(UserModel, back_populates="orders")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status: Mapped[OrderStatusEnum] = mapped_column(
        Enum(OrderStatusEnum), nullable=False, default=OrderStatusEnum.PENDING
    )
    total_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=10, scale=2, asdecimal=True), nullable=True
    )

    order_items: Mapped[List["OrderItemModel"]] = relationship(
        "OrderItemModel", back_populates="order", cascade="all, delete-orphan"
    )
    order_payments: Mapped[List["PaymentModel"]] = relationship(
        "PaymentModel",
        back_populates="order"
    )


class OrderItemModel(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    order: Mapped[OrderModel] = relationship(OrderModel, back_populates="order_items")
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), nullable=False
    )
    movie: Mapped[MovieModel] = relationship(
        MovieModel, back_populates="movie_order_items"
    )
    price_at_order: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2, asdecimal=True), nullable=False
    )
    order_payment_items: Mapped[List["PaymentItemModel"]] = relationship("PaymentItemModel", back_populates="order_item")
