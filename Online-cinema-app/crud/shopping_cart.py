from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, Response
from fastapi.responses import JSONResponse

from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from crud.payments import create_checkout_session
from models.movies import MovieModel
from models.orders import OrderModel, OrderStatusEnum, OrderItemModel
from models.shopping_cart import CartModel, CartItemModel
from models.users import UserModel
from schemas.shopping_cart import CartItemSchema, CartAddSchema
from decimal import Decimal


async def cart_movies_list(db: AsyncSession, current_user: UserModel):
    cart_result = await db.execute(
        select(CartModel).where(CartModel.user_id == current_user.id)
    )
    cart = cart_result.one_or_none()
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cart is not created yet"
        )
    added_cart_items = [
        CartItemSchema(
            name=item.movie.name,
            price=item.movie.price,
            genre=item.movie.genre,
            release_year=item.movie.year,
            added_at=item.added_at,
        )
        for item in cart.cart_items
    ]
    if not added_cart_items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="There are no added movies to your cart yet",
        )
    return added_cart_items


async def add_movie_to_cart(
    movie_data: CartAddSchema, db: AsyncSession, current_user: UserModel
):
    order_result = await db.execute(
        select(OrderModel).where(
            OrderModel.user_id == current_user.id,
            OrderModel.status == OrderStatusEnum.PAID,
            OrderModel.order_items.any(OrderItemModel.movie_id == movie_data.movie_id),
        )
    )
    order = order_result.one_or_none()
    if order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can not buy movie twice",
        )
    existing_movie_result = await db.execute(
        select(CartModel).where(
            CartModel.user_id == current_user.id,
            CartModel.cart_items.any(CartItemModel.movie_id == movie_data.movie_id),
        )
    )
    existing_movie = existing_movie_result.one_or_none()
    if existing_movie:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This movie is already in your cart",
        )

    cart_result = await db.execute(
        select(CartModel).where(CartModel.user_id == current_user.id)
    )
    cart = cart_result.one_or_none()
    movie_result = await db.execute(
        select(MovieModel).where(MovieModel.id == movie_data.movie_id)
    )
    movie = movie_result.scalar_one_or_none()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found"
        )
    if not cart:
        new_cart = CartModel(user_id=current_user.id)
        db.add(new_cart)
        await db.commit()
        await db.refresh(new_cart)
        cart_item = CartItemModel(cart_id=new_cart.id, movie_id=movie.id)
    else:
        existing_movie_result = await db.execute(
            select(CartItemModel).where(
                CartItemModel.cart_id == cart.id, CartItemModel.movie_id == movie.id
            )
        )
        existing_movie = existing_movie_result.scalar_one_or_none()
        if existing_movie:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Movie is already in the cart",
            )
        cart_item = CartItemModel(cart_id=cart.id, movie_id=movie.id)
    db.add(cart_item)
    await db.commit()
    await db.refresh(cart_item)
    return Response(status_code=status.HTTP_201_CREATED)


async def remove_movie_from_cart(
    movie_id: int, db: AsyncSession, current_user: UserModel
):
    cart_result = await db.execute(
        select(CartModel).where(CartModel.user_id == current_user.id)
    )
    cart = cart_result.one_or_none()
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="There is no existing cart for this user",
        )
    cart_item_result = await db.execute(
        select(CartItemModel).where(
            CartItemModel.cart_id == cart.id, CartItemModel.movie_id == movie_id
        )
    )
    cart_item = cart_item_result.scalar_one_or_none()
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found"
        )
    await db.delete(cart_item)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def clear_cart(db: AsyncSession, current_user: UserModel):
    cart_result = await db.execute(
        select(CartModel).where(CartModel.user_id == current_user.id)
    )
    cart = cart_result.one_or_none()
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="There is no existing cart for this user",
        )
    await db.execute(delete(CartItemModel).where(CartItemModel.cart_id == cart.id))
    await db.commit()
    return JSONResponse(
        status_code=status.HTTP_200_OK, content={"detail": "Cart is cleared"}
    )
