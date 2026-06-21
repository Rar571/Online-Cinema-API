from typing import List

from sqlalchemy import Integer, ForeignKey, DateTime, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session_postgresql import Base
from models.movies import MovieModel
from models.users import UserModel
from datetime import datetime


class CartModel(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="cart")

    cart_items: Mapped[List["CartItemModel"]] = relationship(
        "CartItem", back_populates="cart", cascade="all, delete-orphan"
    )


class CartItemModel(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(
        ForeignKey("carts.id", ondelete="CASCADE"), nullable=False
    )
    cart: Mapped[CartModel] = relationship(CartModel, back_populates="cart_items")
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), nullable=False
    )
    movie: Mapped["MovieModel"] = relationship(
        "MovieModel", back_populates="cart_items"
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = UniqueConstraint("cart_id", "movie_id", name="unique_cart_movie")
