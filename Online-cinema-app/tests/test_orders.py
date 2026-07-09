import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from datetime import datetime, timezone

import stripe

from models.orders import OrderStatusEnum
from models.payments import StatusEnum


def make_result(scalar_one_or_none=None, scalars_all=None):
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_one_or_none
    result.scalars.return_value.all.return_value = scalars_all if scalars_all is not None else []
    return result


@pytest.mark.asyncio
async def test_view_orders_list_success(client, mock_db):
    mock_movie = MagicMock(name="Test movie", year=2024)
    mock_movie.name = "Test movie"
    mock_order_item = MagicMock(movie=mock_movie, price_at_order=Decimal("9.99"))
    mock_order = MagicMock(
        id=1,
        created_at=datetime.now(timezone.utc),
        total_amount=Decimal("9.99"),
        status=OrderStatusEnum.PENDING,
    )
    mock_db.execute.side_effect = [
        make_result(scalars_all=[mock_order]),
        make_result(scalars_all=[mock_order_item]),
    ]

    response = await client.get("/orders/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_view_orders_list_empty(client, mock_db):
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    response = await client.get("/orders/")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_order_success(client, mock_db):
    mock_order = MagicMock(id=1, user_id=3, status=OrderStatusEnum.PENDING)
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_order
    mock_db.commit = AsyncMock()

    response = await client.post("/orders/1/cancel/")

    mock_db.commit.assert_called_once()
    assert response.status_code == 200
    assert mock_order.status == OrderStatusEnum.CANCELED


@pytest.mark.asyncio
async def test_cancel_order_not_found(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    response = await client.post("/orders/1/cancel/")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_refund_request_success(client, mock_db):
    mock_order = MagicMock(id=1, user_id=3, status=OrderStatusEnum.PAID)
    mock_payment = MagicMock(
        order_id=1,
        user_id=3,
        status=StatusEnum.SUCCESSFUL,
        external_payment_id="pi_12345",
    )
    mock_db.execute.side_effect = [
        make_result(scalar_one_or_none=mock_order),
        make_result(scalar_one_or_none=mock_payment),
    ]
    mock_db.commit = AsyncMock()

    with patch("crud.orders.stripe.Refund.create") as mock_refund, \
         patch("crud.orders.send_email.delay") as mock_send_email:
        mock_refund.return_value = {"id": "re_12345", "status": "succeeded"}
        response = await client.post("/orders/1/refund/")
        print(response.json())
        mock_refund.assert_called_once_with(payment_intent="pi_12345")
        mock_send_email.assert_called_once()
        mock_db.commit.assert_called_once()
        assert response.status_code == 201
        assert mock_order.status == OrderStatusEnum.CANCELED
        assert mock_payment.status == StatusEnum.REFUNDED


@pytest.mark.asyncio
async def test_refund_request_order_not_found(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    response = await client.post("/orders/1/refund/")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_refund_request_payment_not_found(client, mock_db):
    mock_order = MagicMock(id=1, user_id=3, status=OrderStatusEnum.PAID)
    mock_db.execute.side_effect = [
        make_result(scalar_one_or_none=mock_order),
        make_result(scalar_one_or_none=None),
    ]
    response = await client.post("/orders/1/refund/")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_refund_request_stripe_error(client, mock_db):
    mock_order = MagicMock(id=1, user_id=3, status=OrderStatusEnum.PAID)
    mock_payment = MagicMock(
        order_id=1,
        user_id=3,
        status=StatusEnum.SUCCESSFUL,
        external_payment_id="pi_12345",
    )
    mock_db.execute.side_effect = [
        make_result(scalar_one_or_none=mock_order),
        make_result(scalar_one_or_none=mock_payment),
    ]

    with patch(
        "crud.orders.stripe.Refund.create",
        side_effect=stripe.error.StripeError("card declined"),
    ):
        response = await client.post("/orders/1/refund/")

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_view_users_orders_success(client, mock_db):
    mock_movie = MagicMock(name="Test movie", year=2024)
    mock_movie.name = "Test movie"
    mock_order_item = MagicMock(movie=mock_movie, price_at_order=Decimal("9.99"))
    mock_order = MagicMock(
        id=1,
        created_at=datetime.now(timezone.utc),
        status=OrderStatusEnum.PAID,
        order_items=[mock_order_item],
    )
    mock_db.execute.return_value.scalars.return_value.all.return_value = [mock_order]

    with patch("routes.orders.require_admin", new_callable=AsyncMock) as mock_require:
        mock_require.return_value = None
        response = await client.get("/orders/history/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_view_users_orders_with_filters(client, mock_db):
    mock_movie = MagicMock(name="Test movie", year=2024)
    mock_movie.name = "Test movie"
    mock_order_item = MagicMock(movie=mock_movie, price_at_order=Decimal("9.99"))
    mock_order = MagicMock(
        id=1,
        created_at=datetime.now(timezone.utc),
        status=OrderStatusEnum.PAID,
        order_items=[mock_order_item],
    )
    mock_db.execute.return_value.scalars.return_value.all.return_value = [mock_order]

    with patch("routes.orders.require_admin", new_callable=AsyncMock) as mock_require:
        mock_require.return_value = None
        response = await client.get("/orders/history/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_view_users_orders_empty(client, mock_db):
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    with patch("routes.orders.require_admin", new_callable=AsyncMock) as mock_require:
        mock_require.return_value = None
        response = await client.get("/orders/history/")
    assert response.status_code == 404
