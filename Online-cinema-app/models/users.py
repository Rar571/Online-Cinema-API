from datetime import datetime, date, timedelta, timezone
import enum
from typing import List, Optional

from sqlalchemy import (
    Integer,
    Enum,
    String,
    Boolean,
    DateTime,
    func,
    ForeignKey,
    Date,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session_postgresql import Base
from security.token import generate_token


class UserGroupEnum(str, enum.Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class GenderEnum(str, enum.Enum):
    MAN = "man"
    WOMAN = "woman"


class UserGroupModel(Base):
    __tablename__ = "user_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[UserGroupEnum] = mapped_column(
        Enum(UserGroupEnum), unique=True, nullable=False
    )

    users: Mapped[List["UserModel"]] = relationship("UserModel", back_populates="group")


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    _hashed_password: Mapped[str] = mapped_column(
        "hashed_password", String(255), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    group_id: Mapped[int] = mapped_column(
        ForeignKey("user_groups.id", ondelete="CASCADE"), nullable=False
    )
    group: Mapped["UserGroupModel"] = relationship(
        "UserGroupModel", back_populates="users"
    )
    user_profile: Mapped[Optional["UserProfileModel"]] = relationship(
        "UserProfileModel", back_populates="user", cascade="all, delete-orphan"
    )
    activation_token: Mapped[List["ActivationTokenModel"]] = relationship(
        "ActivationTokenModel", back_populates="user", cascade="all, delete-orphan"
    )
    refresh_token: Mapped[List["RefreshTokenModel"]] = relationship(
        "RefreshTokenModel", back_populates="user", cascade="all, delete-orphan"
    )
    password_reset_token: Mapped[List["PasswordResetTokenModel"]] = relationship(
        "PasswordResetTokenModel", back_populates="user", cascade="all, delete-orphan"
    )
    user_likes_and_dislikes: Mapped[List["LikeAndDislikeModel"]] = relationship(
        "LikeAndDislikeModel", back_populates="user", cascade="all, delete-orphan"
    )
    user_favorite_movies: Mapped[List["FavoriteMovieModel"]] = relationship(
        "FavoriteMovieModel", back_populates="user", cascade="all, delete-orphan"
    )
    user_rates: Mapped[List["RateMovieModel"]] = relationship(
        "RateMovieModel", back_populates="user", cascade="all, delete-orphan"
    )
    user_comments: Mapped[List["CommentMovieModel"]] = relationship(
        "CommentMovieModel", back_populates="user", cascade="all, delete-orphan"
    )
    user_replies: Mapped[List["CommentRepliesModel"]] = relationship(
        "CommentRepliesModel", back_populates="user", cascade="all, delete-orphan"
    )
    cart: Mapped[Optional["CartModel"]] = relationship(
        "CartModel", back_populates="user", uselist=False
    )
    orders: Mapped[List["OrderModel"]] = relationship("OrderModel", back_populates="user")
    user_payments: Mapped[List["PaymentModel"]] = relationship(
        "PaymentModel", back_populates="user"
    )


class UserProfileModel(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="user_profile")
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gender: Mapped[Optional[GenderEnum]] = mapped_column(
        Enum("GenderEnum"), nullable=True
    )
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    info: Mapped[str] = mapped_column(Text, nullable=False)


class ActivationTokenModel(Base):
    __tablename__ = "activation_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="activation_token"
    )
    token: Mapped[str] = mapped_column(
        String(64), default=generate_token, nullable=False, unique=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc) + timedelta(days=1),
        nullable=False,
    )


class PasswordResetTokenModel(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="password_reset_token"
    )
    token: Mapped[str] = mapped_column(
        String(64), default=generate_token, unique=True, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc) + timedelta(days=1),
    )


class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="refresh_token"
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
