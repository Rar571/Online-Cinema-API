from contextlib import asynccontextmanager

from fastapi import FastAPI

from db.session_postgresql import postgresql_engine, Base, AsyncPostgresqlSessionLocal
from dependencies.authorization import get_groups_id
from routes.shopping_cart import cart_router
from routes.users import users_router
from routes.movies import movies_router


app = FastAPI()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with postgresql_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncPostgresqlSessionLocal() as db:
        await get_groups_id(db)
    yield
    await postgresql_engine.dispose()


app.include_router(users_router, prefix="/users")
app.include_router(movies_router)
app.include_router(cart_router)

