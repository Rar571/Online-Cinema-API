from typing import Optional
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CertificationSchema(BaseModel):
    id: int
    name: str


class MovieSchema(BaseModel):
    id: int
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
    model_config = ConfigDict(from_attributes=True)


class MovieDetailSchema(MovieSchema):
    certification: CertificationSchema

    model_config = ConfigDict(from_attributes=True)


class MovieCreateSchema(MovieSchema):
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
