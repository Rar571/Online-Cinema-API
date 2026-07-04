import json
from unittest.mock import MagicMock, patch, AsyncMock

import pytest


from models.movies import LikeTypeEnum
from decimal import Decimal


@pytest.mark.asyncio
async def test_get_movies_success(client, mock_db):
    mock_movie = {
        "id": 1,
        "uuid": "desfaefewfew",
        "name": "Test movie",
        "year": 2089,
        "time": 80,
        "imdb": 9.4,
        "votes": 9,
        "description": "Test description",
        "price": Decimal("7.90"),
        "certification_id": 1,
    }

    with patch("crud.movies.filter_sort_search_movies", new_callable=AsyncMock) as mock_filter:
        mock_filter.return_value = [mock_movie]

        response = await client.get("/movies/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data


@pytest.mark.asyncio
async def test_get_movies_with_filters(client, mock_db):
    with patch("crud.movies.filter_sort_search_movies", new_callable=AsyncMock) as mock_filter:
        mock_filter.return_value = []

        response = await client.get("/movies/?name=test&year=2024&page=2&limit=5")

        mock_filter.assert_called_once()
        call_kwargs = mock_filter.call_args.kwargs
        assert call_kwargs["name"] == "test"
        assert call_kwargs["year"] == 2024
        assert call_kwargs["page"] == 2
        assert call_kwargs["limit"] == 5
        assert response.status_code == 200


def make_result(scalar_one_or_none=None, scalars_all=None):
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_one_or_none
    result.scalars.return_value.all.return_value = scalars_all if scalars_all is not None else []
    return result


@pytest.mark.asyncio
async def test_delete_movie_success(client, mock_db):
    mock_movie = MagicMock(id=1)
    mock_db.execute.side_effect = [
        make_result(scalar_one_or_none=mock_movie),
        make_result(scalar_one_or_none=None),
        make_result(scalars_all=[])
    ]
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()
    response = await client.delete(
        "/movies/1/"
    )
    mock_db.commit.assert_called_once()
    mock_db.delete.assert_called_once_with(mock_movie)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_movie_not_found(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    response = await client.delete(
        "/movies/5/"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_movie_is_already_purchased(client, mock_db):
    mock_movie = MagicMock(id=1)
    purchased_movie = MagicMock(id=1, movie_id=1)
    mock_db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_movie)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=purchased_movie)),
    ]
    response = await client.delete(
        "/movies/1/"
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_like_or_dislike_success(client, mock_db):
    mock_movie = MagicMock(id=1)
    total_movie_likes = MagicMock()
    mock_db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_movie)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=None)),
        AsyncMock(scalar=MagicMock(return_value=total_movie_likes))
    ]
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    response = await client.post(
        "/movies/1/like/",
        params={
            "movie_id": 1,
            "like_type": "like"
        }
    )
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_like_or_dislike_is_already(client, mock_db):
    mock_movie = MagicMock(id=1)
    existing_like = MagicMock(id=2, like_type="like")
    total_movie_likes = MagicMock()
    mock_db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_movie)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=existing_like)),
        AsyncMock(scalar=MagicMock(return_value=total_movie_likes))
    ]
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()
    response = await client.post(
        "/movies/1/like/",
        params={
            "movie_id": 1,
            "like_type": "like"
        }
    )
    mock_db.delete.assert_called_once_with(existing_like)
    mock_db.commit.assert_called_once()
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_like_or_dislike_change(client, mock_db):
    mock_movie = MagicMock(id=1)
    existing_like = MagicMock(like_type=LikeTypeEnum.DISLIKE)
    total_movie_likes = MagicMock()
    mock_db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_movie)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=existing_like)),
        AsyncMock(scalar=MagicMock(return_value=total_movie_likes))
    ]
    mock_db.commit = AsyncMock()
    response = await client.post(
        "/movies/1/like/",
        params={
            "movie_id": 1,
            "like_type": "like"
        }
    )
    mock_db.commit.assert_called_once()
    assert existing_like.like_type == "like"
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_like_or_dislike_movie_not_found(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    response = await client.post(
        "/movies/1/like/",
        params={
            "movie_id": 2,
            "like_type": "like"
        }
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_favorite_movies_success(client, mock_db):
    mock_movie = {
        "id": 1,
        "uuid": "desfaefewfew",
        "name": "Test movie",
        "year": 2024,
        "time": 80,
        "imdb": 9.4,
        "votes": 9,
        "description": "Test description",
        "price": Decimal("7.90"),
        "certification_id": 1,
    }
    with patch("crud.movies.filter_sort_search_movies", new_callable=AsyncMock) as mock_filter:
        mock_filter.return_value = [mock_movie]
        response = await client.get(
            "/movies/favorites/"
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data


@pytest.mark.asyncio
async def test_list_favorite_movies_with_filters(client, mock_db):
    mock_movie = {
        "id": 1,
        "uuid": "desfaefewfew",
        "name": "test",
        "year": 2024,
        "time": 80,
        "imdb": 9.4,
        "votes": 9,
        "description": "Test description",
        "price": Decimal("7.90"),
        "certification_id": 1,
    }
    with patch("crud.movies.filter_sort_search_movies", new_callable=AsyncMock) as mock_filter:
        mock_filter.return_value = [mock_movie]
        response = await client.get(
            "/movies/favorites/?name=test&year=2024&page=2&limit=5"
        )
        mock_filter.assert_called_once()
        call_kwargs = mock_filter.call_args.kwargs
        assert response.status_code == 200
        assert call_kwargs["name"] == "test"
        assert call_kwargs["year"] == 2024
        assert call_kwargs["page"] == 2
        assert call_kwargs["limit"] == 5


@pytest.mark.asyncio
async def test_add_favorite_movie_success(client, mock_db):
    mock_movie = MagicMock(id=1)
    mock_db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_movie)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=None))
    ]
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    response = await client.post(
        "/movies/favorites/",
        json={
            "movie_id": 1
        }
    )
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_add_favorite_movie_not_found(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    response = await client.post(
        "/movies/favorites/",
        json={
            "movie_id": 4
        }
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_favorite_movie_is_already(client, mock_db):
    mock_movie = MagicMock(id=1)
    existing_movie = mock_movie
    mock_db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_movie)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=existing_movie))
    ]
    response = await client.post(
        "/movies/favorites/",
        json={
            "movie_id": 1
        }
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_delete_favorite_movie_success(client, mock_db):
    existing_favorite = MagicMock(id=1)
    mock_db.execute.return_value.scalar_one_or_none.return_value = existing_favorite
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()
    response = await client.request(
        "DELETE",
        "/movies/favorites/",
        json={
            "movie_id": 1
        }
    )
    mock_db.delete.assert_called_once_with(existing_favorite)
    mock_db.commit.assert_called_once()
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_favorite_movie_not_found(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    response = await client.request(
        "DELETE",
        "/movies/favorites/",
        json={
            "movie_id": 1
        }
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_rate_movie_is_rated(client, mock_db):
    rate = MagicMock(rate=1)
    movie_rate_average = MagicMock()
    mock_db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=MagicMock(return_value=rate)),
        AsyncMock(scalar=MagicMock(return_value=movie_rate_average))
    ]
    response = await client.post(
        "/movies/1/rate/",
        json={
            "rate": 1,
            "movie_id": 1,
        }
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_rate_movie_change_rate(client, mock_db):
    rate = MagicMock(rate=2)
    movie_rate_average = MagicMock()
    mock_db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=MagicMock(return_value=rate)),
        AsyncMock(scalar=MagicMock(return_value=movie_rate_average))
    ]
    mock_db.commit = AsyncMock()
    response = await client.post(
        "/movies/1/rate/",
        json={
            "rate": 1,
            "movie_id": 1,
        }
    )
    mock_db.commit.assert_called_once()
    assert response.status_code == 200
    assert rate.rate == 1


@pytest.mark.asyncio
async def test_rate_movie_create_rate(client, mock_db):
    movie_rate_average = MagicMock()
    mock_db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=MagicMock(return_value=None)),
        AsyncMock(scalar=MagicMock(return_value=movie_rate_average))
    ]
    mock_db.add = AsyncMock()
    mock_db.commit = AsyncMock()
    response = await client.post(
        "/movies/1/rate/",
        json={
            "rate": 1,
            "movie_id": 1,
        }
    )
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    assert response.status_code == 200
