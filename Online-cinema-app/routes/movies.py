from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from crud.movies import (
    get_movies_list,
    create_movie,
    movie_detail,
    movie_update,
    movie_delete,
    like_or_dislike_movie,
)
from db.session_postgresql import get_db
from dependencies.users import get_current_user_model
from models.movies import LikeTypeEnum
from models.users import UserModel
from schemas.movies import MovieCreateSchema, MovieUpdateSchema

router = APIRouter()


@router.get("/movies/", status_code=200)
async def movies_list(
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
    db: AsyncSession = Depends(get_db),
):
    return await get_movies_list(
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
        db=db,
    )


@router.post("/movies/", status_code=201)
async def movie_create(
    movie_data: MovieCreateSchema, db: AsyncSession = Depends(get_db)
):
    return await create_movie(movie_data=movie_data, db=db)


@router.get("/movies/{movie_id}/", status_code=200)
async def movie_details(movie_id: int, db: AsyncSession = Depends(get_db)):
    return await movie_detail(movie_id=movie_id, db=db)


@router.patch("/movies/{movie_id}/", status_code=200)
async def update_movie(
    movie_id: int, movie_data: MovieUpdateSchema, db: AsyncSession = Depends(get_db)
):
    return await movie_update(movie_id=movie_id, movie_data=movie_data, db=db)


@router.delete("/movies/{movie_id}/", status_code=200)
async def delete_movie(movie_id, db: AsyncSession = Depends(get_db)):
    return await movie_delete(movie_id=movie_id, db=db)


@router.post("/movies/{movie_id}/like/", status_code=200)
async def like_and_dislike(
    movie_id: int,
    like_type: LikeTypeEnum,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_model),
):
    return await like_or_dislike_movie(
        movie_id=movie_id, like_type=like_type, db=db, current_user=current_user
    )
