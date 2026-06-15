from fastapi import FastAPI

from dependencies.authorization import get_moderator_and_admin_groups_id
from routes.users import router

app = FastAPI()


@app.on_event("startup")
async def startup():
    await get_moderator_and_admin_groups_id()


app.include_router(router, prefix="/users")
