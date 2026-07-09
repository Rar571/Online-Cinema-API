from contextlib import asynccontextmanager

from fastapi import FastAPI

from db.session_postgresql import postgresql_engine, Base, AsyncPostgresqlSessionLocal
from dependencies.authorization import get_groups_id
from routes.orders import orders_router
from routes.shopping_cart import cart_router
from routes.payments import payment_router
from routes.users import users_router
from routes.movies import movies_router
from models.users import (
    UserGroupModel,
    UserModel,
    UserProfileModel,
    ActivationTokenModel,
    PasswordResetTokenModel,
    RefreshTokenModel,
)
from models.movies import (
    MovieModel,
    GenreModel,
    StarModel,
    DirectorModel,
    CertificationModel,
    LikeAndDislikeModel,
    FavoriteMovieModel,
    RateMovieModel,
    CommentMovieModel,
    CommentRepliesModel,
)
from models.shopping_cart import CartModel, CartItemModel
from models.orders import OrderModel, OrderItemModel
from models.payments import PaymentModel, PaymentItemModel


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with postgresql_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncPostgresqlSessionLocal() as db:
        await get_groups_id(db)
    yield
    await postgresql_engine.dispose()


app = FastAPI(lifespan=lifespan)


app.include_router(users_router, prefix="/users")
app.include_router(movies_router)
app.include_router(cart_router)
app.include_router(orders_router)
app.include_router(payment_router)
