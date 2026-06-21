from sqlalchemy import Integer, ForeignKey, DateTime, func, Enum, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session_postgresql import Base
from models.users import UserModel

from datetime import datetime

import enum

from decimal import Decimal
from typing import Optional


class StatusEnum(str, enum.Enum):
    SUCCESSFUL = "successful"
    CANCELED = "canceled"
    REFUNDED = "refunded"


class PaymentModel(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="user_payments")
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    order: Mapped["OrderModel"] = relationship("OrderModel", back_populates="order_payments")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status: Mapped[StatusEnum] = mapped_column(Enum(StatusEnum), nullable=False, default=StatusEnum.SUCCESSFUL)
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2, asdecimal=True), nullable=False)
    external_payment_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    payment_items: Mapped["PaymentItemModel"] = relationship("PaymentItemModel", back_populates="payment", cascade="all, delete-orphan")


class PaymentItemModel(Base):
    __tablename__ = "payment_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), nullable=False)
    payment: Mapped[PaymentModel] = relationship(PaymentModel, back_populates="payment_items")
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False)
    order_item: Mapped["OrderItemModel"] = relationship("OrderItemModel", back_populates="order_payment_items")
    price_at_payment: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2, asdecimal=True), nullable=False)
