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
    list_comments,
    create_comment,
    comment_detail,
    delete_comment,
    update_comment,
    create_reply,
    update_reply,
    delete_reply,
    list_actors,
    create_actor,
    detail_actor,
    update_actor,
    delete_actor,
    list_favorite_movies,
)
from db.session_postgresql import get_db
from dependencies.authorization import require_moderator
from dependencies.users import get_current_user_model
from models.movies import LikeTypeEnum, MovieModel, GenreModel
from models.users import UserModel
from schemas.movies import (
    MovieCreateSchema,
    MovieUpdateSchema,
    FavoriteMovieAddOrDeleteSchema,
    GenreSchema,
    RateCreateSchema,
    CommentCreateSchema,
    CommentUpdateSchema,
    CommentReplyCreateSchema,
    CommentReplyUpdateSchema,
    StarCreateSchema,
    StarUpdateSchema,
)

movies_router = APIRouter()


@movies_router.post("/comments/replies/", status_code=status.HTTP_201_CREATED)
async def comment_reply_create(
    reply_data: CommentReplyCreateSchema, db: AsyncSession = Depends(get_db)
):
    return await create_reply(reply_data=reply_data, db=db)


@movies_router.get("/movies/favorites/", status_code=status.HTTP_200_OK)
async def favorite_movies_list_endpoint(
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
    current_user: UserModel = Depends(get_current_user_model),
):
    return await list_favorite_movies(
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
        current_user=current_user,
    )


@movies_router.post("/movies/favorites/", status_code=status.HTTP_201_CREATED)
async def add_favorite_movie_endpoint(
    movie_data: FavoriteMovieAddOrDeleteSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_model),
):
    return await add_favorite_movie(
        movie_data=movie_data, db=db, current_user=current_user
    )


@movies_router.delete("/movies/favorites/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_favorite_movie_endpoint(
    movie_data: FavoriteMovieAddOrDeleteSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_model),
):
    return await delete_favorite_movie(
        movie_data=movie_data, db=db, current_user=current_user
    )


@movies_router.get("/movies/", status_code=status.HTTP_200_OK)
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


@movies_router.post("/movies/", status_code=status.HTTP_201_CREATED)
async def movie_create(
    movie_data: MovieCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_moderator),
):
    return await create_movie(movie_data=movie_data, db=db)


@movies_router.get("/genres/", status_code=status.HTTP_200_OK)
async def genres_list(db: AsyncSession = Depends(get_db)):
    return await get_genres_list(db=db)


@movies_router.post("/genres/", status_code=status.HTTP_201_CREATED)
async def genre_create(
    genre_data: GenreSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_moderator),
):
    return await create_genre(genre_data=genre_data, db=db)


@movies_router.get("/comments/", status_code=status.HTTP_200_OK)
async def comments_list(db: AsyncSession = Depends(get_db)):
    return await list_comments(db=db)


@movies_router.post("/comments/", status_code=status.HTTP_201_CREATED)
async def comment_create(
    comment_data: CommentCreateSchema, db: AsyncSession = Depends(get_db)
):
    return await create_comment(comment_data=comment_data, db=db)


@movies_router.get("/stars/", status_code=status.HTTP_200_OK)
async def stars_list(
    db: AsyncSession = Depends(get_db), current_user=Depends(require_moderator)
):
    return await list_actors(db=db)


@movies_router.post("/stars/", status_code=status.HTTP_201_CREATED)
async def create_star(
    star_data: StarCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_moderator),
):
    return await create_actor(actor_data=star_data, db=db)


@movies_router.post("/movies/{movie_id}/like/", status_code=status.HTTP_200_OK)
async def like_and_dislike(
    movie_id: int,
    like_type: LikeTypeEnum,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_model),
):
    return await like_or_dislike_movie(
        movie_id=movie_id, like_type=like_type, db=db, current_user=current_user
    )


@movies_router.get("/genres/{genre_id}/movies/", status_code=status.HTTP_200_OK)
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


@movies_router.post("/movies/{movie_id}/rate/", status_code=status.HTTP_200_OK)
async def movie_rate(
    movie_id: int,
    rate_data: RateCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user_model),
):
    return await rate_movie(
        movie_id=movie_id, rate_data=rate_data, db=db, current_user=current_user
    )


@movies_router.patch("/comments/replies/{reply_id}/", status_code=status.HTTP_200_OK)
async def comment_reply_update(
    reply_data: CommentReplyUpdateSchema,
    reply_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await update_reply(reply_data=reply_data, reply_id=reply_id, db=db)


@movies_router.delete(
    "/comments/replies/{reply_id}/", status_code=status.HTTP_204_NO_CONTENT
)
async def comment_reply_delete(reply_id: int, db: AsyncSession = Depends(get_db)):
    return await delete_reply(reply_id=reply_id, db=db)


@movies_router.get("/movies/{movie_id}/", status_code=status.HTTP_200_OK)
async def movie_detail_endpoint(movie_id: int, db: AsyncSession = Depends(get_db)):
    return await movie_detail(movie_id=movie_id, db=db)


@movies_router.patch("/movies/{movie_id}/", status_code=status.HTTP_200_OK)
async def update_movie(
    movie_id: int,
    movie_data: MovieUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_moderator),
):
    return await movie_update(movie_id=movie_id, movie_data=movie_data, db=db)


@movies_router.delete("/movies/{movie_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(
    movie_id,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_moderator),
):
    return await movie_delete(movie_id=movie_id, db=db)


@movies_router.get("/genres/{genre_id}/", status_code=status.HTTP_200_OK)
async def genre_detail(genre_id: int, db: AsyncSession = Depends(get_db)):
    return await detail_genre(genre_id=genre_id, db=db)


@movies_router.patch("/genres/{genre_id}/", status_code=status.HTTP_200_OK)
async def genre_update(
    genre_id: int,
    genre_data: GenreSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_moderator),
):
    return await update_genre(genre_id=genre_id, genre_data=genre_data, db=db)


@movies_router.delete("/genres/{genre_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def genre_delete(
    genre_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_moderator),
):
    return await delete_genre(genre_id=genre_id, db=db)


@movies_router.get("/comments/{comment_id}/", status_code=status.HTTP_200_OK)
async def detail_comment(comment_id: int, db: AsyncSession = Depends(get_db)):
    return await comment_detail(comment_id=comment_id, db=db)


@movies_router.patch("/comments/{comment_id}/", status_code=status.HTTP_200_OK)
async def comment_update(
    comment_id: int,
    comment_data: CommentUpdateSchema,
    db: AsyncSession = Depends(get_db),
):
    return await update_comment(comment_id=comment_id, comment_data=comment_data, db=db)


@movies_router.delete("/comments/{comment_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def comment_delete(comment_id: int, db: AsyncSession = Depends(get_db)):
    return await delete_comment(comment_id=comment_id, db=db)


@movies_router.get("/stars/{star_id}/", status_code=status.HTTP_200_OK)
async def star_detail(
    star_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_moderator),
):
    return await detail_actor(actor_id=star_id, db=db)


@movies_router.patch("/stars/{star_id}/", status_code=status.HTTP_200_OK)
async def update_star(
    star_id: int,
    star_data: StarUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_moderator),
):
    return await update_actor(actor_id=star_id, actor_data=star_data, db=db)


@movies_router.delete("/stars/{star_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_star(
    star_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_moderator),
):
    return await delete_actor(actor_id=star_id, db=db)
