from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from models.orders import OrderStatusEnum
from decimal import Decimal


@pytest.mark.asyncio
async def test_create_session_success(client, mock_db):
    mock_order = MagicMock(id=1, user_id=3, status=OrderStatusEnum.PENDING, total_amount=Decimal("9.99"))
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_order

    with patch("crud.payments.stripe.checkout.Session.create") as mock_session:
        mock_session.return_value = MagicMock(url="https://checkout.stripe.com/session123")
        response = await client.post("/payments/1/pay/")

    assert response.status_code == 201
    assert response.json()["checkout_url"] == "https://checkout.stripe.com/session123"


@pytest.mark.asyncio
async def test_create_session_not_order(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    response = await client.post("/payments/3/pay/")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_session_not_current_user(client, mock_db):
    mock_order = MagicMock(id=1, user_id=9, status=OrderStatusEnum.PENDING)
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_order
    response = await client.post("/payments/1/pay/")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_session_invalid_status(client, mock_db):
    mock_order = MagicMock(id=1, user_id=3, status=OrderStatusEnum.CANCELED)
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_order
    response = await client.post("/payments/1/pay/")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_webhook_checkout_completed_success(client, mock_db):
    mock_user = MagicMock(email="test@test.com")
    mock_order_item = MagicMock(id=1, price_at_order=Decimal("9.99"))
    mock_order = MagicMock(id=1, user=mock_user, order_items=[mock_order_item])
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_order
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"order_id": "1", "user_id": "3"},
                "amount_total": 999,
                "payment_intent": "pi_12345",
            }
        },
    }

    with patch("crud.payments.stripe.Webhook.construct_event", return_value=event), \
         patch("tasks.celery.send_email.delay") as mock_send_email:
        response = await client.post(
            "/webhook/",
            content=b"{}",
            headers={"stripe-signature": "test-signature"},
        )

    assert response.status_code == 200
    assert mock_order.status == OrderStatusEnum.PAID
    mock_db.commit.assert_called_once()
    mock_send_email.assert_called_once()


@pytest.mark.asyncio
async def test_webhook_checkout_completed_order_not_found(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    event = {
        "type": "checkout.session.completed",
        "data": {"object": {"metadata": {"order_id": "999", "user_id": "3"}, "amount_total": 999}},
    }

    with patch("crud.payments.stripe.Webhook.construct_event", return_value=event):
        response = await client.post(
            "/webhook/",
            content=b"{}",
            headers={"stripe-signature": "test-signature"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "received"}


def make_stripe_event(event_type: str, data_object: dict) -> dict:
    return {"type": event_type, "data": {"object": data_object}}


@pytest.mark.asyncio
async def test_webhook_checkout_completed_success(client, mock_db):
    mock_user = MagicMock(email="test@test.com")
    mock_order_item = MagicMock(id=1, price_at_order=Decimal("9.99"))
    mock_order = MagicMock(id=1, user=mock_user, order_items=[mock_order_item])
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_order
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    event = make_stripe_event(
        "checkout.session.completed",
        {
            "metadata": {"order_id": "1", "user_id": "3"},
            "amount_total": 999,
            "payment_intent": "pi_12345",
        },
    )

    with patch("crud.payments.stripe.Webhook.construct_event", return_value=event), \
         patch("crud.payments.send_email.delay") as mock_send_email:
        response = await client.post(
            "/webhook/",
            content=b"{}",
            headers={"stripe-signature": "test-signature"},
        )

    assert response.status_code == 200
    assert mock_order.status == OrderStatusEnum.PAID
    mock_db.commit.assert_called_once()
    mock_send_email.assert_called_once()


@pytest.mark.asyncio
async def test_webhook_checkout_completed_order_not_found(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    event = make_stripe_event(
        "checkout.session.completed",
        {"metadata": {"order_id": "999", "user_id": "3"}, "amount_total": 999},
    )

    with patch("crud.payments.stripe.Webhook.construct_event", return_value=event):
        response = await client.post(
            "/webhook/",
            content=b"{}",
            headers={"stripe-signature": "test-signature"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "received"}


@pytest.mark.asyncio
async def test_webhook_payment_failed_success(client, mock_db):
    mock_user = MagicMock(email="test@test.com")
    mock_order = MagicMock(id=1, status=OrderStatusEnum.PENDING, user=mock_user)
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_order
    mock_db.commit = AsyncMock()

    event = make_stripe_event(
        "payment_intent.payment_failed",
        {"metadata": {"order_id": "1"}},
    )

    with patch("crud.payments.stripe.Webhook.construct_event", return_value=event), \
         patch("crud.payments.send_email.delay") as mock_send_email:
        response = await client.post(
            "/webhook/",
            content=b"{}",
            headers={"stripe-signature": "test-signature"},
        )

    assert response.status_code == 200
    assert mock_order.status == OrderStatusEnum.CANCELED
    mock_db.commit.assert_called_once()
    mock_send_email.assert_called_once()


@pytest.mark.asyncio
async def test_webhook_payment_failed_order_not_found(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    event = make_stripe_event(
        "payment_intent.payment_failed",
        {"metadata": {"order_id": "999"}},
    )

    with patch("crud.payments.stripe.Webhook.construct_event", return_value=event):
        response = await client.post(
            "/webhook/",
            content=b"{}",
            headers={"stripe-signature": "test-signature"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "received"}


@pytest.mark.asyncio
async def test_webhook_checkout_session_expired_success(client, mock_db):
    mock_order = MagicMock(id=1, status=OrderStatusEnum.PENDING)
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_order
    mock_db.commit = AsyncMock()

    event = make_stripe_event(
        "checkout.session.expired",
        {"metadata": {"order_id": "1"}},
    )

    with patch("crud.payments.stripe.Webhook.construct_event", return_value=event):
        response = await client.post(
            "/webhook/",
            content=b"{}",
            headers={"stripe-signature": "test-signature"},
        )

    assert response.status_code == 200
    assert mock_order.status == OrderStatusEnum.CANCELED
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_webhook_checkout_session_expired_order_not_found(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    event = make_stripe_event(
        "checkout.session.expired",
        {"metadata": {"order_id": "999"}},
    )

    with patch("crud.payments.stripe.Webhook.construct_event", return_value=event):
        response = await client.post(
            "/webhook/",
            content=b"{}",
            headers={"stripe-signature": "test-signature"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "received"}


@pytest.mark.asyncio
async def test_webhook_unhandled_event_type(client, mock_db):
    event = make_stripe_event("some.other.event", {})

    with patch("crud.payments.stripe.Webhook.construct_event", return_value=event):
        response = await client.post(
            "/webhook/",
            content=b"{}",
            headers={"stripe-signature": "test-signature"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "success"}

