from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from decimal import Decimal

from dependencies.users import get_current_user_model
from main import app


@pytest.mark.asyncio
async def test_cart_movies_list_success(client, mock_db):
    mock_movie = MagicMock(price=Decimal("9.99"), genre="Action", year=2020)
    mock_movie.name = "Test Movie"
    mock_item = MagicMock(movie=mock_movie, added_at="2024-01-01")
    mock_cart = MagicMock(user_id=3, cart_items=[mock_item])
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_cart
    response = await client.get(
        "/cart/",
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_cart_movies_list_cart_not_found(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    response = await client.get(
        "/cart/",
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cart_movies_list_not_added_items(client, mock_db):
    mock_cart = MagicMock(user_id=3, cart_items=[])
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_cart
    response = await client.get(
        "/cart/",
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_movie_to_cart_create_new_cart(client, mock_db):
    mock_movie = MagicMock(id=1)
    mock_db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=MagicMock(return_value=None)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=None)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=None)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_movie))
    ]
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    response = await client.post(
        "/cart/",
        json={
            "movie_id": 1
        }
    )
    assert mock_db.add.call_count == 2
    assert mock_db.commit.call_count == 2
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_add_movie_to_cart_is_already(client, mock_db):
    mock_movie = MagicMock(id=1)
    mock_cart = MagicMock(id=1, user_id=3)
    mock_db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=MagicMock(return_value=None)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=None)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_cart)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_movie)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=None))
    ]
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    response = await client.post(
        "/cart/",
        json={
            "movie_id": 1
        }
    )
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_add_movie_to_cart_cannot_buy_movie_twice(client, mock_db):
    mock_order = MagicMock(user_id=3, movie_id=1, status="paid")
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_order
    response = await client.post(
        "/cart/",
        json={
            "movie_id": 1
        }
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_add_movie_to_cart_movie_is_already_in_cart(client, mock_db):
    mock_existing_movie = MagicMock(id=1)
    mock_db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=MagicMock(return_value=None)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_existing_movie))
    ]
    response = await client.post(
        "/cart/",
        json={
            "movie_id": 1
        }
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_remove_movie_from_cart_success(client, mock_db):
    mock_cart = MagicMock(user_id=3)
    mock_item = MagicMock(movie_id=1)
    mock_db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_cart)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_item))
    ]
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()
    response = await client.delete(
        "/cart/1/"
    )
    mock_db.delete.assert_called_once_with(mock_item)
    mock_db.commit.assert_called_once()
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_remove_movie_from_cart_not_cart(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    response = await client.delete(
        "/cart/1/"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_remove_movie_from_cart_not_cart_item(client, mock_db):
    mock_cart = MagicMock(user_id=3)
    mock_db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_cart)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=None))
    ]
    response = await client.delete(
        "/cart/1/"
    )
    assert response.status_code == 404


def make_result(scalar_one_or_none=None, scalars_all=None):
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_one_or_none
    result.scalars.return_value.all.return_value = scalars_all if scalars_all is not None else []
    return result


@pytest.mark.asyncio
async def test_pay_for_cart_success(client, mock_db):
    mock_cart = MagicMock(id=1, user_id=3, cart_items=[MagicMock(movie_id=10)])
    mock_movie = MagicMock(id=10, price=Decimal("9.99"))
    mock_cart_item = MagicMock(movie_id=10, movie=mock_movie, cart_id=1)

    mock_db.execute.side_effect = [
        make_result(scalar_one_or_none=mock_cart),
        make_result(scalars_all=[]),
        make_result(scalars_all=[mock_cart_item]),
        make_result(scalar_one_or_none=None),
        make_result(scalars_all=[mock_movie]),
    ]
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    with patch("crud.shopping_cart.create_checkout_session", new_callable=AsyncMock) as session:
        session.return_value = "https://stripe.session/url"
        response = await client.post("/cart/pay/")

    assert mock_db.add.call_count == 2
    mock_db.flush.assert_called_once()
    mock_db.commit.assert_called_once()
    assert response.status_code == 201
    session.assert_called_once()


@pytest.mark.asyncio
async def test_pay_for_cart_user_is_not_active(client, mock_db):
    app.dependency_overrides[get_current_user_model] = lambda: MagicMock(id=3, is_active=False)
    try:
        response = await client.post("/cart/pay/")
        assert response.status_code == 400
    finally:
        app.dependency_overrides[get_current_user_model] = lambda: MagicMock(id=3, is_active=True)


@pytest.mark.asyncio
async def test_pay_for_cart_not_cart(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    response = await client.post("/cart/pay/")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_pay_for_cart_movies_already_bought(client, mock_db):
    mock_cart = MagicMock(id=1, user_id=3, cart_items=[MagicMock(movie_id=1)])
    purchased_order = MagicMock()
    mock_db.execute.side_effect = [
        make_result(scalar_one_or_none=mock_cart),
        make_result(scalars_all=[purchased_order]),
    ]
    response = await client.post("/cart/pay/")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_pay_for_cart_movies_are_unavailable(client, mock_db):
    mock_cart = MagicMock(id=1, user_id=3, cart_items=[MagicMock(movie_id=99)])
    unavailable_item = MagicMock(movie_id=99, movie=None)
    mock_db.execute.side_effect = [
        make_result(scalar_one_or_none=mock_cart),
        make_result(scalars_all=[]),
        make_result(scalars_all=[unavailable_item]),
    ]
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    response = await client.post("/cart/pay/")
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_pay_for_cart_movies_order_is_pending(client, mock_db):
    mock_cart = MagicMock(id=1, user_id=3, cart_items=[MagicMock(movie_id=1)])
    mock_movie = MagicMock(id=1, price=Decimal("9.99"))
    mock_cart_item = MagicMock(movie_id=1, movie=mock_movie)
    existing_order = MagicMock()
    mock_db.execute.side_effect = [
        make_result(scalar_one_or_none=mock_cart),
        make_result(scalars_all=[]),
        make_result(scalars_all=[mock_cart_item]),
        make_result(scalar_one_or_none=existing_order),
    ]
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    response = await client.post("/cart/pay/")
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_pay_for_cart_stripe_error(client, mock_db):
    mock_cart = MagicMock(id=1, user_id=3, cart_items=[MagicMock(movie_id=10)])
    mock_movie = MagicMock(id=10, price=Decimal("9.99"))
    mock_cart_item = MagicMock(movie_id=10, movie=mock_movie, cart_id=1)

    mock_db.execute.side_effect = [
        make_result(scalar_one_or_none=mock_cart),
        make_result(scalars_all=[]),
        make_result(scalars_all=[mock_cart_item]),
        make_result(scalar_one_or_none=None),
        make_result(scalars_all=[mock_movie]),
    ]
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()

    with patch("crud.shopping_cart.create_checkout_session", new_callable=AsyncMock) as session:
        session.side_effect = Exception("stripe error")
        response = await client.post("/cart/pay/")

    assert mock_db.add.call_count == 2
    mock_db.flush.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_awaited_once()
    assert response.status_code == 400
    session.assert_called_once()
