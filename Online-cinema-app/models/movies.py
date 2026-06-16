import enum
from typing import List, Optional
from decimal import Decimal

from sqlalchemy import (
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
from models.users import UserModel

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
        cascade="all, delete-orphan",
    )


class StarModel(Base):
    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)

    movies: Mapped[List["MovieModel"]] = relationship(
        "MovieModel",
        secondary="movie_stars",
        back_populates="stars",
        cascade="all, delete-orphan",
    )


class DirectorModel(Base):
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)

    movies: Mapped[List["MovieModel"]] = relationship(
        "MovieModel",
        secondary="movie_directors",
        back_populates="directors",
        cascade="all, delete-orphan",
    )


class CertificationModel(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)

    movies: Mapped[List["MovieModel"]] = relationship(
        "MovieModel", back_populates="certification", cascade="all, delete-orphans"
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

    __table_args__ = UniqueConstraint("name", "year", "time", name="unique_movie")


class LikeAndDislikeModel(Base):
    __tablename__ = "likes_and_dislikes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    like_type: Mapped[LikeTypeEnum] = mapped_column(Enum(LikeTypeEnum), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user: Mapped[UserModel] = relationship(UserModel, back_populates="user_likes_and_dislikes")
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    movie: Mapped[MovieModel] = relationship(MovieModel, back_populates="movie_likes_and_dislikes")

    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="unique_movie_user_like")
    )
