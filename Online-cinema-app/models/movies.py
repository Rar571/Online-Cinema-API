import enum
from typing import List, Optional
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Enum,
    Integer,
    String,
    Float,
    Text,
    Numeric,
    ForeignKey,
    UniqueConstraint,
    Table,
    Column,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session_postgresql import Base

movie_genres = Table(
    "movie_genres",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id"), primary_key=True),
    Column("genre_id", Integer, ForeignKey("genres.id"), primary_key=True),
)


movie_stars = Table(
    "movie_stars",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id"), primary_key=True),
    Column("star_id", Integer, ForeignKey("stars.id"), primary_key=True),
)


movie_directors = Table(
    "movie_directors",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id"), primary_key=True),
    Column("director_id", Integer, ForeignKey("directors.id"), primary_key=True),
)


class LikeTypeEnum(str, enum.Enum):
    LIKE = "like"
    DISLIKE = "dislike"


class GenreModel(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)

    movies: Mapped[List["MovieModel"]] = relationship(
        "MovieModel",
        secondary="movie_genres",
        back_populates="genres",
    )


class StarModel(Base):
    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)

    movies: Mapped[List["MovieModel"]] = relationship(
        "MovieModel",
        secondary="movie_stars",
        back_populates="stars",
    )


class DirectorModel(Base):
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)

    movies: Mapped[List["MovieModel"]] = relationship(
        "MovieModel",
        secondary="movie_directors",
        back_populates="directors",
    )


class CertificationModel(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)

    movies: Mapped[List["MovieModel"]] = relationship(
        "MovieModel", back_populates="certification", cascade="all, delete-orphan"
    )


class MovieModel(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    time: Mapped[int] = mapped_column(Integer, nullable=False)
    imdb: Mapped[float] = mapped_column(Float, nullable=False)
    votes: Mapped[int] = mapped_column(Integer, nullable=False)
    meta_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gross: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2, asdecimal=True)
    )
    certification_id: Mapped[int] = mapped_column(
        ForeignKey("certifications.id", ondelete="CASCADE"), nullable=False
    )
    certification: Mapped[CertificationModel] = relationship(
        CertificationModel, back_populates="movies"
    )
    genres: Mapped[List[GenreModel]] = relationship(
        GenreModel, secondary=movie_genres, back_populates="movies"
    )
    directors: Mapped[List[DirectorModel]] = relationship(
        DirectorModel, secondary=movie_directors, back_populates="movies"
    )
    stars: Mapped[List[StarModel]] = relationship(
        StarModel, secondary=movie_stars, back_populates="movies"
    )
    movie_likes_and_dislikes: Mapped[List["LikeAndDislikeModel"]] = relationship(
        "LikeAndDislikeModel", back_populates="movie", cascade="all, delete-orphan"
    )
    movie_favorite_movies: Mapped[List["FavoriteMovieModel"]] = relationship(
        "FavoriteMovieModel", back_populates="movie", cascade="all, delete-orphan"
    )
    movie_rates: Mapped[List["RateMovieModel"]] = relationship(
        "RateMovieModel", back_populates="movie", cascade="all, delete-orphan"
    )
    movie_comments: Mapped[List["CommentMovieModel"]] = relationship(
        "CommentMovieModel", back_populates="movie", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("name", "year", "time", name="unique_movie"),)


class LikeAndDislikeModel(Base):
    __tablename__ = "likes_and_dislikes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    like_type: Mapped[LikeTypeEnum] = mapped_column(
        Enum(LikeTypeEnum, name="like_and_dislike_enum"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="user_likes_and_dislikes"
    )
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), nullable=False
    )
    movie: Mapped[MovieModel] = relationship(
        MovieModel, back_populates="movie_likes_and_dislikes"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="unique_movie_user_like"),
    )


class FavoriteMovieModel(MovieModel):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), nullable=False
    )
    movie: Mapped[MovieModel] = relationship(
        MovieModel, back_populates="movie_favorite_movies"
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="user_favorite_movies"
    )


class RateMovieModel(Base):
    __tablename__ = "rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rate: Mapped[int] = mapped_column(Integer, nullable=False)
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), nullable=False
    )
    movie: Mapped[MovieModel] = relationship(MovieModel, back_populates="movie_rates")
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="user_rates")

    __table_args__ = (
        CheckConstraint("rate > 0 AND rate < 11", name="range from 1 to 10"),
    )


class CommentMovieModel(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), nullable=False
    )
    movie: Mapped[MovieModel] = relationship(
        MovieModel, back_populates="movie_comments"
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="user_comments"
    )

    replies: Mapped[List["CommentRepliesModel"]] = relationship(
        "CommentRepliesModel", back_populates="comment", cascade="all, delete-orphan"
    )

    @property
    def user_name(self) -> str | None:
        if not self.user.user_profile:
            return None
        return f"{self.user.user_profile.first_name} {self.user.user_profile.last_name}"


class CommentRepliesModel(Base):
    __tablename__ = "replies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    comment_id: Mapped[int] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), nullable=False
    )
    comment: Mapped[CommentMovieModel] = relationship(
        CommentMovieModel, back_populates="replies"
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="user_replies")

    @property
    def user_name(self) -> str | None:
        if not self.user.user_profile:
            return ""
        return f"{self.user.user_profile.first_name} {self.user.user_profile.last_name}"
