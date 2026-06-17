from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse

from dependencies.movies import filter_sort_search_movies
from models.movies import (
    MovieModel,
    LikeAndDislikeModel,
    LikeTypeEnum,
    FavoriteMovieModel,
)
from models.users import UserModel
from schemas.movies import (
    MovieCreateSchema,
    MovieDetailSchema,
    MovieUpdateSchema,
    MovieListSchema,
    FavoriteMovieAddOrDeleteSchema,
    FavoriteMovieListSchema,
)


async def get_movies_list(
    db: AsyncSession,
    name: str | None = None,
    description: str | None = None,
    actor_name: str | None = None,
    director_name: str | None = None,
    year: int | None = None,
    imdb: float | None = None,
    page: int = 1,
    limit: int = 10,
    sort_field: str = "id",
    sort_order: str = "asc",
):
    movies = await filter_sort_search_movies(
        db=db,
        movie_model=MovieModel,
        name=name,
        description=description,
        actor_name=actor_name,
        director_name=director_name,
        year=year,
        imdb=imdb,
        page=page,
        limit=limit,
        sort_field=sort_field,
        sort_order=sort_order,
    )
    if not movies:
        movies = []
        return movies
    movies_list = [
        MovieListSchema.model_validate(movie, from_attributes=True) for movie in movies
    ]
    total = await db.execute(select(func.count(MovieModel.id)))
    total_count = total.scalar()
    return {"items": movies_list, "total": total_count, "page": page, "limit": limit}


async def create_movie(movie_data: MovieCreateSchema, db: AsyncSession):
    movie = MovieModel(**movie_data.model_dump())
    db.add(movie)
    await db.commit()
    await db.refresh(movie)
    movie_detail = MovieDetailSchema.model_validate(movie, from_attributes=True)
    return movie_detail


async def movie_detail(movie_id: int, db: AsyncSession):
    movie_result = await db.execute(
        select(MovieModel)
        .where(
            MovieModel.id == movie_id,
        )
        .options(selectinload(MovieModel.certification))
    )
    movie = movie_result.scalar_one_or_none()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found"
        )
    movie_detail = MovieDetailSchema.model_validate(movie, from_attributes=True)
    return movie_detail


async def movie_update(movie_id: int, movie_data: MovieUpdateSchema, db: AsyncSession):
    movie_result = await db.execute(
        select(MovieModel)
        .where(MovieModel.id == movie_id)
        .options(selectinload(MovieModel.certification))
    )
    movie = movie_result.scalar_one_or_none()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found"
        )
    for field, value in movie_data.model_dump(exclude_unset=True).items():
        setattr(movie, field, value)
    await db.commit()
    await db.refresh(movie)
    movie_detail = MovieDetailSchema.model_validate(movie, from_attributes=True)
    return movie_detail


async def movie_delete(movie_id: int, db: AsyncSession):
    movie_result = await db.execute(select(MovieModel).where(MovieModel.id == movie_id))
    movie = movie_result.scalar_one_or_none()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found"
        )
    await db.delete(movie)
    await db.commit()
    return await get_movies_list(db=db)


async def like_or_dislike_movie(
    movie_id, like_type: LikeTypeEnum, db: AsyncSession, current_user: UserModel
):
    movie_result = await db.execute(select(MovieModel).where(MovieModel.id == movie_id))
    movie = movie_result.scalar_one_or_none()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found"
        )
    existing_like = await db.execute(
        select(LikeAndDislikeModel).where(
            LikeAndDislikeModel.user_id == current_user.id,
            LikeAndDislikeModel.movie_id == movie_id,
        )
    )
    existing_like_model = existing_like.scalar_one_or_none()
    if existing_like_model:
        if existing_like_model.like_type == like_type:
            await db.delete(existing_like_model)
            await db.commit()
        else:
            existing_like_model.like_type = like_type
            await db.commit()
    else:
        like_or_dislike = LikeAndDislikeModel(
            like_type=like_type, user_id=current_user.id, movie_id=movie_id
        )
        db.add(like_or_dislike)
        await db.commit()
        await db.refresh(like_or_dislike)
    total_movie_likes = await db.execute(
        select(func.count(LikeAndDislikeModel.id)).where(
            LikeAndDislikeModel.movie_id == movie.id,
            LikeAndDislikeModel.like_type == like_type,
        )
    )
    movie_likes = total_movie_likes.scalar()
    return movie_likes


async def list_favorite_movies(
    db: AsyncSession,
    current_user: UserModel,
    name: str | None = None,
    description: str | None = None,
    actor_name: str | None = None,
    director_name: str | None = None,
    year: int | None = None,
    imdb: float | None = None,
    page: int = 1,
    limit: int = 10,
    sort_field: str = "id",
    sort_order: str = "asc",
):
    movies = await filter_sort_search_movies(
        db=db,
        movie_model=FavoriteMovieModel,
        user_id=current_user.id,
        name=name,
        description=description,
        actor_name=actor_name,
        director_name=director_name,
        year=year,
        imdb=imdb,
        page=page,
        limit=limit,
        sort_field=sort_field,
        sort_order=sort_order,
    )
    if not movies:
        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"detail": "There are no favorites"}
        )
    movies_list = [
        FavoriteMovieListSchema.model_validate(movie, from_attributes=True)
        for movie in movies
    ]
    total = await db.execute(
        select(func.count(FavoriteMovieModel.id)).where(
            FavoriteMovieModel.user_id == current_user.id
        )
    )
    total_count = total.scalar()
    return {"items": movies_list, "total": total_count, "page": page, "limit": limit}


async def add_favorite_movie(
    movie_data: FavoriteMovieAddOrDeleteSchema,
    db: AsyncSession,
    current_user: UserModel,
):
    movie_result = await db.execute(
        select(MovieModel).where(MovieModel.id == movie_data.movie_id)
    )
    movie = movie_result.scalar_one_or_none()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found"
        )
    existing_favorite_movie = await db.execute(
        select(FavoriteMovieModel).where(
            FavoriteMovieModel.movie_id == movie_data.movie_id,
            FavoriteMovieModel.user_id == current_user.id,
        )
    )
    existing_favorite = existing_favorite_movie.scalar_one_or_none()
    if existing_favorite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Movie is already in favorites",
        )
    new_favorite_movie = FavoriteMovieModel(movie_id=movie.id, user_id=current_user.id)
    db.add(new_favorite_movie)
    await db.commit()
    await db.refresh(new_favorite_movie)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"detail": "Movie added to favorites"},
    )


async def delete_favorite_movie(
    movie_data: FavoriteMovieAddOrDeleteSchema,
    db: AsyncSession,
    current_user: UserModel,
):
    existing_favorite_movie = await db.execute(
        select(FavoriteMovieModel).where(
            FavoriteMovieModel.movie_id == movie_data.movie_id,
            FavoriteMovieModel.user_id == current_user.id,
        )
    )
    existing_favorite = existing_favorite_movie.scalar_one_or_none()
    if existing_favorite:
        await db.delete(existing_favorite)
        await db.commit()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"detail": "Movie was removed from favorites"},
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found"
        )
