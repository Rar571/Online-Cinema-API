from fastapi import FastAPI

from dependencies.authorization import get_groups_id
from routes.users import users_router
from routes.movies import movies_router

app = FastAPI()


@app.on_event("startup")
async def startup():
    await get_groups_id()


app.include_router(users_router, prefix="/users")
app.include_router(movies_router)
