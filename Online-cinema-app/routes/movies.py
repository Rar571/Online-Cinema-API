from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


from crud.movies import (
    get_movies_list,
    create_movie,
    movie_detail,
    movie_update,
    movie_delete,
    like_or_dislike_movie,
    add_favorite_movie,
    delete_favorite_movie,
    get_genres_list,
    create_genre,
    update_genre,
    delete_genre,
    detail_genre,
    rate_movie,
)
from db.session_postgresql import get_db
from dependencies.users import get_current_user_model
from models.movies import LikeTypeEnum, MovieModel, GenreModel
from models.users import UserModel
from schemas.movies import (
    MovieCreateSchema,
    MovieUpdateSchema,
    FavoriteMovieAddOrDeleteSchema,
    GenreSchema,
    RateCreateSchema,
)

router = APIRouter()


@router.get("/movies/", status_code=status.HTTP_200_OK)
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


@router.post("/movies/", status_code=status.HTTP_201_CREATED)
async def movie_create(
    movie_data: MovieCreateSchema, db: AsyncSession = Depends(get_db)
):
    return await create_movie(movie_data=movie_data, db=db)


@router.get("/movies/{movie_id}/", status_code=status.HTTP_200_OK)
async def movie_details(movie_id: int, db: AsyncSession = Depends(get_db)):
    return await movie_detail(movie_id=movie_id, db=db)


@router.patch("/movies/{movie_id}/", status_code=status.HTTP_200_OK)
async def update_movie(
    movie_id: int, movie_data: MovieUpdateSchema, db: AsyncSession = Depends(get_db)
):
    return await movie_update(movie_id=movie_id, movie_data=movie_data, db=db)


@router.delete("/movies/{movie_id}/", status_code=status.HTTP_200_OK)
async def delete_movie(movie_id, db: AsyncSession = Depends(get_db)):
    return await movie_delete(movie_id=movie_id, db=db)


@router.post("/movies/{movie_id}/like/", status_code=status.HTTP_200_OK)
async def like_and_dislike(
    movie_id: int,
    like_type: LikeTypeEnum,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_model),
):
    return await like_or_dislike_movie(
        movie_id=movie_id, like_type=like_type, db=db, current_user=current_user
    )


@router.get("/movies/favorites/", status_code=status.HTTP_200_OK)
async def favorite_movies_list(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_model),
):
    return await favorite_movies_list(db=db, current_user=current_user)


@router.post("/movies/favorites/", status_code=status.HTTP_201_CREATED)
async def add_favorite_movie(
    movie_data: FavoriteMovieAddOrDeleteSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_model),
):
    return await add_favorite_movie(
        movie_data=movie_data, db=db, current_user=current_user
    )


@router.delete("/movies/favorites/", status_code=status.HTTP_200_OK)
async def delete_favorite_movie(
    movie_data: FavoriteMovieAddOrDeleteSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_model),
):
    return await delete_favorite_movie(
        movie_data=movie_data, db=db, current_user=current_user
    )


@router.get("/genres/", status_code=status.HTTP_200_OK)
async def genres_list(db: AsyncSession = Depends(get_db)):
    return await get_genres_list(db=db)


@router.post("/genres/", status_code=status.HTTP_201_CREATED)
async def genre_create(genre_data: GenreSchema, db: AsyncSession = Depends(get_db)):
    return await create_genre(genre_data=genre_data, db=db)


@router.get("/genres/{genre_id}/", status_code=status.HTTP_200_OK)
async def genre_detail(genre_id: int, db: AsyncSession = Depends(get_db)):
    return await detail_genre(genre_id=genre_id, db=db)


@router.get("/genres/{genre_id}/movies/", status_code=status.HTTP_200_OK)
async def get_related_movies(genre_id: int, db: AsyncSession = Depends(get_db)):
    genre_result = await db.execute(select(GenreModel).where(GenreModel.id == genre_id))
    genre = genre_result.scalar_one_or_none()
    if not genre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Genre not found"
        )
    movies_result = await db.execute(
        select(MovieModel).filter(MovieModel.genres.any(GenreModel.name == genre.name))
    )
    movies = movies_result.scalars().all()
    if not movies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="There are no related movies with this genre",
        )
    return movies


@router.patch("/genres/{genre_id}/", status_code=status.HTTP_200_OK)
async def genre_update(
    genre_id: int, genre_data: GenreSchema, db: AsyncSession = Depends(get_db)
):
    return await update_genre(genre_id=genre_id, genre_data=genre_data, db=db)


@router.delete("/genres/{genre_id}/", status_code=status.HTTP_200_OK)
async def genre_delete(genre_id: int, db: AsyncSession = Depends(get_db)):
    return await delete_genre(genre_id=genre_id, db=db)


@router.post("/movies/{movie_id}/rate/", status_code=status.HTTP_200_OK)
async def movie_rate(
    movie_id: int,
    rate_data: RateCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_model),
):
    return await rate_movie(
        movie_id=movie_id, rate_data=rate_data, db=db, current_user=current_user
    )
