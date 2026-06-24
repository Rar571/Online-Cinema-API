from pydantic import BaseModel
from datetime import datetime
from typing import List

from decimal import Decimal

from models.orders import OrderStatusEnum


class Movie(BaseModel):
    name: str
    year: int
    price_at_order: Decimal


class OrderListSchema(BaseModel):
    created_at: datetime
    movies: List["Movie"]
    total_amount: Decimal
    status: OrderStatusEnum
