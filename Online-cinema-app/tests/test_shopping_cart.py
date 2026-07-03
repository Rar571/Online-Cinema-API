from unittest.mock import MagicMock, patch, AsyncMock

import pytest


@pytest.mark.asyncio
async def test_cart_movies_list_success(client, mock_db):
    mock_item = MagicMock()
    mock_cart = MagicMock(user_id=3, cart_items=mock_item)
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
    mock_cart = MagicMock(user_id=3)
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_cart
    response = await client.get(
        "/cart/",
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_movie_to_cart_create_new_cart(client, mock_db):
    mock_movie = MagicMock(id=1)
    mock_cart = MagicMock(user_id=3)
    mock_db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=MagicMock(return_value=None)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=None)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=None)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_movie))
    ]
    mock_db.add = AsyncMock()
    mock_db.commit = AsyncMock()
    response = await client.post(
        "/cart/",
        json={
            "movie_id": 1
        }
    )
    mock_db.add.assert_called_once_with(mock_cart)
    mock_db.commit.assert_called_once()
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_add_movie_to_cart_is_already(client, mock_db):
    mock_movie = MagicMock(id=1)
    mock_cart = MagicMock(user_id=3)
    cart_item = MagicMock()
    mock_db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=MagicMock(return_value=None)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=None)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_cart)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_movie)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=None))
    ]
    mock_db.add = AsyncMock()
    mock_db.commit = AsyncMock()
    response = await client.post(
        "/cart/",
        json={
            "movie_id": 1
        }
    )
    mock_db.add.assert_called_once_with(cart_item)
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
    mock_movie = MagicMock(id=1)
    mock_db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=MagicMock(return_value=None)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_movie))
    ]
    response = await client.post(
        "/cart/",
        json={
            "movie_id": 1
        }
    )
    assert response.status_code == 400
