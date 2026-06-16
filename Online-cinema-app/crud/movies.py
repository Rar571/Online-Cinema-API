from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.movies import MovieModel
from schemas.movies import MovieCreateSchema, MovieDetailSchema, MovieUpdateSchema, MovieListSchema


async def get_movies_list(db: AsyncSession, page: int = 1, limit: int = 10):
    offset = (page - 1) * limit
    movies_result = await db.execute(select(MovieModel).offset(offset).limit(limit))
    movies = movies_result.scalars().all()
    if not movies:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="There are no movies")
    movies_list = [MovieListSchema.model_validate(movie, from_attributes=True) for movie in movies]
    total = await db.execute(select(func.count(MovieModel.id)))
    total_count = total.scalar()
    return {
        "items": movies_list,
        "total": total_count,
        "page": page,
        "limit": limit
    }


async def create_movie(movie_data: MovieCreateSchema, db: AsyncSession):
    movie = MovieModel(
        **movie_data.model_dump()
    )
    db.add(movie)
    await db.commit()
    await db.refresh(movie)
    movie_detail = MovieDetailSchema.model_validate(movie, from_attributes=True)
    return movie_detail


async def movie_detail(movie_id: int, db: AsyncSession):
    movie_result = await db.execute(select(MovieModel).where(
        MovieModel.id == movie_id,
    ).options(selectinload(MovieModel.certification)))
    movie = movie_result.scalar_one_or_none()
    if not movie:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")
    movie_detail = MovieDetailSchema.model_validate(movie, from_attributes=True)
    return movie_detail


async def movie_update(movie_id: int, movie_data: MovieUpdateSchema, db: AsyncSession):
    movie_result = await db.execute(select(MovieModel).where(
        MovieModel.id == movie_id
    ).options(selectinload(MovieModel.certification)))
    movie = movie_result.scalar_one_or_none()
    if not movie:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")
    for field, value in movie_data.model_dump(exclude_unset=True).items():
        setattr(movie, field, value)
    await db.commit()
    await db.refresh(movie)
    movie_detail = MovieDetailSchema.model_validate(movie, from_attributes=True)
    return movie_detail


async def movie_delete(movie_id: int, db: AsyncSession):
    movie_result = await db.execute(select(MovieModel).where(
        MovieModel.id == movie_id
    ))
    movie = movie_result.scalar_one_or_none()
    if not movie:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")
    await db.delete(movie)
    await db.commit()
    return await get_movies_list(db=db)
