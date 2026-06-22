from typing import List

from pydantic import BaseModel

from decimal import Decimal

from datetime import datetime


class CartItemSchema(BaseModel):
    name: str
    price: Decimal
    genre: str
    release_year: int
    added_at: datetime


class CartListSchema(BaseModel):
    added_movies: List[CartItemSchema]


class CartAddSchema(BaseModel):
    movie_id: int


class CartRemoveSchema(CartAddSchema):
    pass
