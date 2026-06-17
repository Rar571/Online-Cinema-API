from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.movies import MovieModel, StarModel, DirectorModel, FavoriteMovieModel


async def filter_sort_search_movies(
    db: AsyncSession,
    movie_model: MovieModel | FavoriteMovieModel,
    user_id: int | None = None,
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
    if user_id:
        movies_table = (
            select(movie_model)
            .where(movie_model.user_id == user_id)
            .offset(offset)
            .limit(limit)
        )
    else:
        movies_table = select(movie_model).offset(offset).limit(limit)
    if year:
        movies_table = movies_table.filter_by(year=year)
    if imdb:
        movies_table = movies_table.filter_by(imdb=imdb)
    if name:
        movies_table = movies_table.filter(movie_model.name.ilike(f"%{name}%"))
    if actor_name:
        movies_table = movies_table.filter(
            movie_model.stars.any(StarModel.name.ilike(f"%{actor_name}%"))
        )
    if description:
        movies_table = movies_table.filter(
            movie_model.description.ilike(f"%{description}%")
        )
    if director_name:
        movies_table = movies_table.filter(
            movie_model.directors.any(DirectorModel.name.ilike(f"%{director_name}%"))
        )
    valid_fields = {"id", "price", "time"}
    if sort_field not in valid_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can only sort movies by price and time",
        )
    if sort_order == "asc":
        movies_table = movies_table.order_by(getattr(movie_model, sort_field).asc())
    else:
        movies_table = movies_table.order_by(getattr(movie_model, sort_field).desc())
    movies_result = await db.execute(movies_table)
    movies = movies_result.scalars().all()
    return movies
