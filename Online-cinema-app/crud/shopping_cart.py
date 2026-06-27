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


async def pay_for_cart(db: AsyncSession, current_user: UserModel):
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please activate account on the website first before purchasing the movies",
        )
    cart_result = await db.execute(
        select(CartModel)
        .where(CartModel.user_id == current_user.id)
        .options(selectinload(CartModel.cart_items))
    )
    cart = cart_result.one_or_none()
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found"
        )
    cart_items_id = [cart_item.movie_id for cart_item in cart.cart_items]
    purchased_movies_result = await db.execute(
        select(OrderModel).where(
            OrderModel.user_id == current_user.id,
            OrderModel.status == OrderStatusEnum.PAID,
            OrderModel.order_items.any(OrderItemModel.movie_id.in_(cart_items_id)),
        )
    )
    purchased_movies = purchased_movies_result.scalars().all()
    if purchased_movies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already bought these movies",
        )
    order = OrderModel(user_id=current_user.id, status=OrderStatusEnum.PENDING)
    db.add(order)
    await db.flush()
    cart_items_result = await db.execute(
        select(CartItemModel)
        .where(CartItemModel.cart_id == cart.id)
        .options(selectinload(CartItemModel.movie))
    )
    cart_items = cart_items_result.scalars().all()
    deleted_movies_id = [
        cart_item.movie_id for cart_item in cart_items if not cart_item.movie
    ]
    order_items = [
        OrderItemModel(
            order_id=order.id,
            movie_id=cart_item.movie_id,
            price_at_order=cart_item.movie.price,
        )
        for cart_item in cart_items
        if cart_item.movie
    ]
    if not order_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All movies from your cart are unavailable to buy",
        )
    movies_id = [order_item.movie_id for order_item in order_items]
    existing_order = await db.execute(
        select(OrderModel)
        .join(OrderItemModel)
        .where(
            OrderModel.user_id == current_user.id,
            OrderModel.status == OrderStatusEnum.PENDING,
            OrderItemModel.movie_id.in_(movies_id),
        )
    )
    existing_order = existing_order.scalar_one_or_none()
    if existing_order:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have created this pending order",
        )
    current_movies_result = await db.execute(
        select(MovieModel).where(MovieModel.id.in_(movies_id))
    )
    current_movies = current_movies_result.scalars().all()
    total_amount = Decimal("0")
    movies_dict = {movie.id: movie.price for movie in current_movies}
    for order_item in order_items:
        order_item.price_at_order = movies_dict.get(order_item.movie_id)
        db.add(order_item)
        total_amount += movies_dict.get(order_item.movie_id)
    order.order_items = order_items
    order.total_amount = total_amount
    await db.commit()
    try:
        result = await create_checkout_session(
            order_id=order.id, db=db, current_user=current_user
        )
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Try later, an error with stripe occurred",
        )
    if deleted_movies_id:
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "detail": f"Movie(s) with id: ({deleted_movies_id}) "
                f"were excluded from your order, "
                f"but order created successfully, "
                f"url address for payment: {result}"
            },
        )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "detail": f"Order was created successfully, "
            f"url address for payment: {result}"
        },
    )


async def view_user_cart(user_id: int, db: AsyncSession, current_user: UserModel):
    cart_result = await db.execute(
        select(CartModel).where(CartModel.user_id == user_id)
    )
    cart = cart_result.scalar_one_or_none()
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found"
        )
    cart_items_result = await db.execute(
        select(CartItemModel)
        .where(CartItemModel.cart_id == cart.id)
        .options(selectinload(CartItemModel.movie).selectinload(MovieModel.genres))
    )
    cart_items = cart_items_result.scalars().all()
    if not cart_items:
        return []
    movies = [
        CartItemSchema(
            name=cart_item.movie.name,
            price=cart_item.movie.price,
            genre=cart_item.movie.genre,
            release_year=cart_item.movie.release_year,
            added_at=cart_item.added_at,
        )
        for cart_item in cart_items
    ]
    return movies
