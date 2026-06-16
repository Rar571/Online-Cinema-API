from fastapi import HTTPException, status, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


from models.movies import MovieModel, StarModel, DirectorModel
from schemas.movies import (
    MovieCreateSchema,
    MovieDetailSchema,
    MovieUpdateSchema,
    MovieListSchema,
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
    offset = (page - 1) * limit
    movies_table = select(MovieModel).offset(offset).limit(limit)
    if year:
        movies_table = movies_table.filter_by(year=year)
    if imdb:
        movies_table = movies_table.filter_by(imdb=imdb)
    if name:
        movies_table = movies_table.filter(MovieModel.name.ilike(f"%{name}%"))
    if actor_name:
        movies_table = movies_table.filter(
            MovieModel.stars.any(StarModel.name.ilike(f"%{actor_name}%"))
        )
    if description:
        movies_table = movies_table.filter(
            MovieModel.description.ilike(f"%{description}%")
        )
    if director_name:
        movies_table = movies_table.filter(
            MovieModel.directors.any(DirectorModel.name.ilike(f"%{director_name}%"))
        )
    valid_fields = {"id", "price", "time"}
    if sort_field not in valid_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can only sort movies by price and time",
        )
    if sort_order == "asc":
        movies_table = movies_table.order_by(getattr(MovieModel, sort_field).asc())
    else:
        movies_table = movies_table.order_by(getattr(MovieModel, sort_field).desc())
    movies_result = await db.execute(movies_table)
    movies = movies_result.scalars().all()
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
