from fastapi import HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

from models.movies import MovieModel, StarModel, DirectorModel, FavoriteMovieModel


async def filter_sort_search_movies(
    db: AsyncSession,
    smth,
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
    model = smth.column_descriptions[0]["entity"]
    if model is MovieModel:
        movies_table = smth.offset(offset).limit(limit)
        filter_model = MovieModel
    else:
        movies_table = (
            smth.join(MovieModel, FavoriteMovieModel.movie_id == MovieModel.id)
            .offset(offset)
            .limit(limit)
        )
        filter_model = MovieModel
    if year:
        movies_table = movies_table.filter_by(year=year)
    if imdb:
        movies_table = movies_table.filter_by(imdb=imdb)
    if name:
        movies_table = movies_table.filter(filter_model.name.ilike(f"%{name}%"))
    if actor_name:
        movies_table = movies_table.filter(
            filter_model.stars.any(StarModel.name.ilike(f"%{actor_name}%"))
        )
    if description:
        movies_table = movies_table.filter(
            filter_model.description.ilike(f"%{description}%")
        )
    if director_name:
        movies_table = movies_table.filter(
            filter_model.directors.any(DirectorModel.name.ilike(f"%{director_name}%"))
        )
    valid_fields = {"id", "price", "time"}
    if sort_field not in valid_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can only sort movies by price and time",
        )
    if sort_order == "asc":
        movies_table = movies_table.order_by(getattr(filter_model, sort_field).asc())
    else:
        movies_table = movies_table.order_by(getattr(filter_model, sort_field).desc())
    movies_result = await db.execute(movies_table)
    movies = movies_result.scalars().all()
    return movies
