from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal

from models.payments import StatusEnum


class CheckoutSessionResponse(BaseModel):
    checkout_url: str


class PaymentListSchema(BaseModel):
    date_and_time: datetime
    amount: Decimal
    status: StatusEnum
