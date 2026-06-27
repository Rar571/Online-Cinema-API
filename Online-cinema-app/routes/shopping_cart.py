from fastapi import APIRouter, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from crud.shopping_cart import (
    cart_movies_list,
    add_movie_to_cart,
    remove_movie_from_cart,
    clear_cart,
    pay_for_cart,
    view_user_cart,
)
from db.session_postgresql import get_db
from dependencies.authorization import require_admin
from dependencies.users import get_current_user_model
from models.users import UserModel
from schemas.shopping_cart import CartAddSchema

cart_router = APIRouter()


@cart_router.get("/cart/", status_code=status.HTTP_200_OK)
async def cart_list(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_model),
):
    return await cart_movies_list(db=db, current_user=current_user)


@cart_router.post("/cart/", status_code=status.HTTP_201_CREATED)
async def add_movie(
    movie_data: CartAddSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_model),
):
    return await add_movie_to_cart(
        movie_data=movie_data, db=db, current_user=current_user
    )


@cart_router.delete("/cart/{movie_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie_from_cart(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_model),
):
    return await remove_movie_from_cart(
        movie_id=movie_id, db=db, current_user=current_user
    )


@cart_router.delete("/cart/", status_code=status.HTTP_200_OK)
async def clear_user_cart(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_model),
):
    return await clear_cart(db=db, current_user=current_user)


@cart_router.post("/cart/pay/", status_code=status.HTTP_201_CREATED)
async def pay_for_user_cart(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_model),
):
    return await pay_for_cart(db=db, current_user=current_user)


@cart_router.get("/cart/{user_id}/", status_code=status.HTTP_200_OK)
async def view_cart(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_model),
):
    await require_admin(current_user=current_user)
    return await view_user_cart(user_id=user_id, db=db, current_user=current_user)
