from typing import Optional
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CertificationSchema(BaseModel):
    id: int
    name: str


class MovieSchema(BaseModel):
    uuid: str
    name: str
    year: int
    time: int
    imdb: float
    votes: int
    meta_score: Optional[float] = None
    gross: Optional[float] = None
    description: str
    price: Decimal
    certification_id: int


class MovieListSchema(MovieSchema):
    id: int

    model_config = ConfigDict(from_attributes=True)


class MovieDetailSchema(MovieSchema):
    id: int
    certification: CertificationSchema

    model_config = ConfigDict(from_attributes=True)


class MovieCreateSchema(MovieSchema):
    pass


class MovieUpdateSchema(MovieSchema):
    uuid: Optional[str] = None
    name: Optional[str] = None
    year: Optional[int] = None
    time: Optional[int] = None
    imdb: Optional[float] = None
    votes: Optional[int] = None
    meta_score: Optional[float] = None
    gross: Optional[float] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    certification_id: Optional[int] = None


class FavoriteMovieListSchema(MovieListSchema):
    pass


class FavoriteMovieAddOrDeleteSchema(BaseModel):
    movie_id: int


class GenreSchema(BaseModel):
    name: str


class GenreListSchema(GenreSchema):
    id: int
    related_movies: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class RateCreateSchema(BaseModel):
    rate: int = Field(ge=1, le=10)
    movie_id: int
