from fastapi import HTTPException, status, Response
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
    GenreModel,
    RateMovieModel,
    CommentMovieModel,
    CommentRepliesModel,
    StarModel,
)
from models.users import UserModel
from schemas.movies import (
    MovieCreateSchema,
    MovieDetailSchema,
    MovieUpdateSchema,
    MovieListSchema,
    FavoriteMovieAddOrDeleteSchema,
    FavoriteMovieListSchema,
    GenreListSchema,
    GenreSchema,
    RateCreateSchema,
    CommentsListSchema,
    CommentCreateSchema,
    CommentDetail,
    CommentUpdateSchema,
    CommentReplyListSchema,
    CommentReplyCreateSchema,
    CommentReplyUpdateSchema,
    StarListSchema,
    StarCreateSchema,
    StarDetailSchema,
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
    movie = movie_result.one_or_none()
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
    movie = movie_result.one_or_none()
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
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def like_or_dislike_movie(
    movie_id: int, like_type: LikeTypeEnum, db: AsyncSession, current_user: UserModel
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
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found"
        )


async def get_genres_list(db: AsyncSession):
    genres_result = await db.execute(
        select(
            GenreModel.id,
            GenreModel.name,
            func.count(MovieModel.id).label("related_movies"),
        )
        .outerjoin(GenreModel.movies)
        .group_by(GenreModel.id)
    )
    genres = genres_result.scalars().all()
    if not genres:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="There are no genres"
        )
    genres_list = [
        GenreListSchema(id=row[0], name=row[1], related_movies=row[2]) for row in genres
    ]
    return genres_list


async def create_genre(genre_data: GenreSchema, db: AsyncSession):
    genre = GenreModel(name=genre_data.name)
    db.add(genre)
    await db.commit()
    await db.refresh(genre)
    genre_schema = GenreListSchema.model_validate(genre, from_attributes=True)
    return genre_schema


async def detail_genre(genre_id, db: AsyncSession):
    genre_result = await db.execute(select(GenreModel).where(GenreModel.id == genre_id))
    genre = genre_result.one_or_none()
    if not genre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Genre not found"
        )
    genre_schema = GenreListSchema.model_validate(genre, from_attributes=True)
    return genre_schema


async def update_genre(genre_id: int, genre_data: GenreSchema, db: AsyncSession):
    genre_result = await db.execute(select(GenreModel).where(GenreModel.id == genre_id))
    genre = genre_result.one_or_none()
    if not genre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Genre not found"
        )
    genre.name = genre_data.name
    await db.commit()
    await db.refresh(genre)
    genre_schema = GenreListSchema.model_validate(genre, from_attributes=True)
    return genre_schema


async def delete_genre(genre_id, db: AsyncSession):
    genre_result = await db.execute(select(GenreModel).where(GenreModel.id == genre_id))
    genre = genre_result.scalar_one_or_none()
    if not genre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Genre not found"
        )
    await db.delete(genre)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def list_actors(db: AsyncSession):
    actors_result = await db.execute(select(StarModel))
    actors = actors_result.scalars().all()
    actors_list = [
        StarListSchema.model_validate(actor, from_attributes=True) for actor in actors
    ]
    return actors_list


async def create_actor(actor_data: StarCreateSchema, db: AsyncSession):
    actor = StarModel(name=actor_data.name)
    db.add(actor)
    await db.commit()
    await db.refresh(actor)
    related_movies_result = await db.execute(
        select(MovieModel.name).filter(MovieModel.stars.any(StarModel.id == actor.id))
    )
    related_movies = related_movies_result.scalars().all()
    actor_detail = StarDetailSchema(
        id=actor.id, name=actor.name, related_movies=related_movies
    )
    return actor_detail


async def detail_actor(actor_id: int, db: AsyncSession):
    actor_result = await db.execute(
        select(
            StarModel.id,
            StarModel.name,
            func.array_agg(MovieModel.name).label("related_movies"),
        )
        .outerjoin(MovieModel)
        .where(StarModel.id == actor_id)
        .group_by(StarModel.id, StarModel.name)
    )
    actor = actor_result.one_or_none()
    if not actor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Star not found"
        )
    actor_detail = StarDetailSchema(
        id=actor.id, name=actor.name, related_movies=actor.related_movies
    )
    return actor_detail


async def update_actor(actor_id: int, actor_data, db: AsyncSession):
    actor_result = await db.execute(select(StarModel).where(StarModel.id == actor_id))
    actor = actor_result.one_or_none()
    if not actor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Star not found"
        )
    actor.name = actor_data.name
    await db.commit()
    related_movies_result = await db.execute(
        select(MovieModel.name).filter(MovieModel.stars.any(StarModel.id == actor.id))
    )
    related_movies = related_movies_result.scalars().all()
    actor_detail = StarDetailSchema(
        id=actor.id, name=actor.name, related_movies=related_movies
    )
    return actor_detail


async def delete_actor(actor_id: int, db: AsyncSession):
    actor_result = await db.execute(select(StarModel).where(StarModel.id == actor_id))
    actor = actor_result.scalar_one_or_none()
    if not actor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Star not found"
        )
    await db.delete(actor)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def rate_movie(
    rate_data: RateCreateSchema,
    movie_id: int,
    db: AsyncSession,
    current_user: UserModel,
):
    rate_result = await db.execute(
        select(RateMovieModel).where(
            RateMovieModel.movie_id == movie_id,
            RateMovieModel.user_id == current_user.id,
        )
    )
    rate_model = rate_result.one_or_none()
    if rate_model:
        if rate_model.rate == rate_data.rate:
            movie_rate_average_result = await db.execute(
                select(func.avg(RateMovieModel.rate)).where(
                    RateMovieModel.movie_id == movie_id
                )
            )
            movie_rate_average = movie_rate_average_result.scalar()
            return movie_rate_average
        else:
            rate_model.rate = rate_data.rate
            await db.commit()
            await db.refresh(rate_model)
    else:
        rate = RateMovieModel(
            rate=rate_data.rate, movie_id=movie_id, user_id=current_user.id
        )
        db.add(rate)
        await db.commit()
        await db.refresh(rate)
    movie_rate_average_result = await db.execute(
        select(func.avg(RateMovieModel.rate)).where(RateMovieModel.movie_id == movie_id)
    )
    movie_rate_average = movie_rate_average_result.scalar()
    return movie_rate_average


async def list_comments(db: AsyncSession):
    comments_result = await db.execute(
        select(
            CommentMovieModel.user_name,
            CommentMovieModel.text,
            func.count(CommentRepliesModel.id).label("replies_count"),
        )
        .outerjoin(
            CommentRepliesModel, CommentRepliesModel.comment_id == CommentMovieModel.id
        )
        .group_by(
            CommentMovieModel.id, CommentMovieModel.user_name, CommentMovieModel.text
        )
    )
    comments = comments_result.scalars().all()
    if not comments:
        return []
    comments_list = [
        CommentsListSchema(
            user_name=comment.user_name,
            text=comment.text,
            replies_count=comment.replies_count,
        )
        for comment in comments
    ]
    return comments_list


async def create_comment(comment_data: CommentCreateSchema, db: AsyncSession):
    comment = CommentMovieModel(**comment_data.model_dump())
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    comment_detail = CommentDetail.model_validate(comment, from_attributes=True)
    return comment_detail


async def comment_detail(comment_id: int, db: AsyncSession):
    comment_result = await db.execute(
        select(
            CommentMovieModel.user_name,
            CommentMovieModel.text,
            CommentMovieModel.replies,
        )
        .where(CommentMovieModel.id == comment_id)
        .options(selectinload(CommentMovieModel.replies))
    )
    comment = comment_result.one_or_none()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
        )
    if not comment.replies:
        replies = []
    else:
        replies = [
            CommentReplyListSchema(user_name=reply.user_name, text=reply.text)
            for reply in comment.replies
        ]
    comment_detail = CommentDetail(
        user_name=comment.user_name, text=comment.text, replies=replies
    )
    return comment_detail


async def update_comment(
    comment_id: int, comment_data: CommentUpdateSchema, db: AsyncSession
):
    comment_result = await db.execute(
        select(CommentMovieModel)
        .where(CommentMovieModel.id == comment_id)
        .options(selectinload(CommentMovieModel.replies))
    )
    comment = comment_result.one_or_none()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
        )
    replies = comment.replies
    for field, value in comment_data.model_dump(exclude_unset=True).items():
        setattr(comment, field, value)
    await db.commit()
    replies_schemas = [
        CommentReplyListSchema(user_name=reply.user_name, text=reply.text)
        for reply in replies
    ]
    comment_detail = CommentDetail(
        user_name=comment.user_name, text=comment.text, replies=replies_schemas
    )
    return comment_detail


async def delete_comment(comment_id: int, db: AsyncSession):
    comment_result = await db.execute(
        select(CommentMovieModel).where(CommentMovieModel.id == comment_id)
    )
    comment = comment_result.scalar_one_or_none()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
        )
    await db.delete(comment)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def create_reply(reply_data: CommentReplyCreateSchema, db: AsyncSession):
    reply = CommentRepliesModel(**reply_data.model_dump())
    db.add(reply)
    await db.commit()
    await db.refresh(reply)
    reply_detail = CommentReplyListSchema.model_validate(reply, from_attributes=True)
    return reply_detail


async def update_reply(
    reply_data: CommentReplyUpdateSchema, reply_id: int, db: AsyncSession
):
    reply_result = await db.execute(
        select(CommentRepliesModel).where(CommentRepliesModel.id == reply_id)
    )
    reply = reply_result.one_or_none()
    if not reply:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reply to the comment not found",
        )
    for field, value in reply_data.model_dump(exclude_unset=True).items():
        setattr(reply, field, value)
    await db.commit()
    reply_detail = CommentReplyListSchema.model_validate(reply, from_attributes=True)
    return reply_detail


async def delete_reply(reply_id: int, db: AsyncSession):
    reply_result = await db.execute(
        select(CommentRepliesModel).where(CommentRepliesModel.id == reply_id)
    )
    reply = reply_result.scalar_one_or_none()
    if not reply:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reply to the comment not found",
        )
    await db.delete(reply)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
