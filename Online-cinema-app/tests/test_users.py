import secrets
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from datetime import datetime, timezone, timedelta

from dependencies.authorization import group_admins_id, group_users_id, group_moderators_id
from security.passwords import hash_password
from security.token import generate_access_token, generate_refresh_token


@pytest.mark.asyncio
async def test_registration_success(client, mock_db):
    with patch("tasks.celery.send_email.delay") as mock_send_email:
        mock_db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=None)
        response = await client.post(
            "/users/register/",
            json={
                "email": "test@example.com",
                "password": "Strongpassword123#",
            },
        )
        assert response.status_code == 201
        mock_send_email.assert_called_once()


@pytest.mark.asyncio
async def test_registration_duplicate_email(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=None)
    await client.post(
        "/users/register/",
        json={"email": "test@test.com", "password": "Strongpassword123#"},
    )
    mock_db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=MagicMock(id=1))
    response = await client.post(
        "/users/register/",
        json={"email": "test@test.com", "password": "Strongpassword123#"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_registration_invalid_email(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=None)
    response = await client.post(
        "/users/register/",
        json={
            "email": "invalidemail",
            "password": "Strongpassword123"
        }
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_registration_invalid_password(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=None)
    response = await client.post(
        "/users/register/",
        json={
            "email": "test@test.com",
            "password": "123"
        }
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_activation_token_success(client, mock_db):
    with patch("tasks.celery.send_email.delay") as mock_send_email:
        mock_user = MagicMock(id=1, is_active=False)
        mock_db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=None)
        mock_db.execute.side_effect = [
            AsyncMock(scalar_one_or_none=mock_user),
            AsyncMock(scalar_one_or_none=None),
        ]
        response = await client.post(
            "/users/activation_token/",
            json={
                "email": "test@test.com"
            }
        )
        assert response.status_code == 201
        mock_send_email.assert_called_once()


@pytest.mark.asyncio
async def test_activation_token_user_is_already_active(client, mock_db):
    mock_user = MagicMock(id=1, is_active=True)
    mock_db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=mock_user)
    response = await client.post(
        "/users/activation_token/",
        json={
            "email": "test@test.com"
        }
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_activation_token_unused(client, mock_db):
    mock_user = MagicMock(id=1, is_active=False)
    mock_token = MagicMock(expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc))
    mock_db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=mock_user),
        AsyncMock(scalar_one_or_none=mock_token)
    ]
    response = await client.post(
        "/users/activation_token/",
        json={
            "email": "test@test.com"
        }
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_activate_user_success(client, mock_db):
    token = secrets.token_urlsafe(32)
    mock_user = MagicMock(id=1, is_active=False)
    mock_token = MagicMock(token=token, expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc))
    mock_db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=mock_user),
        AsyncMock(scalar_one_or_none=mock_token)
    ]
    response = await client.get(
        "/users/activate/",
        params={
            "email": "test@test.com",
            "token": token
        }
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_activate_user_token_is_invalid(client, mock_db):
    mock_user = MagicMock(id=1, is_active=False)
    mock_token = MagicMock(expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc))
    mock_db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=mock_user),
        AsyncMock(scalar_one_or_none=mock_token)
    ]
    response = await client.get(
        "/users/activate/",
        params={
            "email": "test@test.com",
            "token": "invalid_token"
        }
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_activate_user_is_already_active(client, mock_db):
    token = secrets.token_urlsafe(32)
    mock_user = MagicMock(id=1, is_active=True)
    mock_token = MagicMock(token=token, expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc))
    mock_db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=mock_user),
        AsyncMock(scalar_one_or_none=mock_token)
    ]
    response = await client.get(
        "/users/activate/",
        params={
            "email": "test@test.com",
            "token": token
        }
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_login_success(client, mock_db):
    hashed_password = hash_password("Strongpassword123")
    mock_user = MagicMock(id=1, hashed_password=hashed_password, is_active=True)
    mock_db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=mock_user)
    mock_db.add = AsyncMock()
    mock_db.commit = AsyncMock()
    response = await client.get(
        "/users/login/",
        params={
            "email": "test@test.com",
            "password": "Strongpassword123"
        }
    )
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()



@pytest.mark.asyncio
async def test_login_invalid_password(client, mock_db):
    hashed_password = hash_password("Strongpassword123")
    mock_user = MagicMock(id=1, hashed_password=hashed_password, is_active=True)
    mock_db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=mock_user)
    mock_db.commit = AsyncMock()
    response = await client.get(
        "/users/login/",
        params={
            "email": "test@test.com",
            "password": "invalid_password"
        }
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_user_is_not_active(client, mock_db):
    hashed_password = hash_password("Strongpassword123")
    mock_user = MagicMock(id=1, hashed_password=hashed_password, is_active=False)
    mock_db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=mock_user)
    mock_db.commit = AsyncMock()
    response = await client.get(
        "/users/login/",
        params={
            "email": "test@test.com",
            "password": "Strongpassword123"
        }
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_logout_success(client, mock_db):
    mock_user = MagicMock(id=1, is_active=True)
    access_token = generate_access_token({"sub": mock_user.id})
    refresh_token = generate_refresh_token({"sub": mock_user.id})
    expiration_date = datetime.now(timezone.utc) + timedelta(days=7)
    mock_refresh_token = MagicMock(token=refresh_token, user_id=mock_user.id, expires_at=expiration_date)
    mock_user.refresh_token = mock_refresh_token
    mock_db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=mock_refresh_token)
    mock_db.commit = AsyncMock()
    response = await client.post(
        "/users/logout/",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    mock_db.delete.assert_called_once_with(mock_refresh_token)
    mock_db.commit.assert_called_once()
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_logout_not_headers(client, mock_db):
    response = await client.post(
        "/users/logout/",
        headers={}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_invalid_headers(client, mock_db):
    response = await client.post(
        "/users/logout/",
        headers={"Authorization": "invalid_bearer"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_user_unauthorized(client, mock_db):
    access_token = "invalid_token"
    with patch("security.token.decode_token", side_effect=ValueError()):
        response = await client.post(
            "/users/logout/",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_change_user_password_success(client, mock_db):
    old_password = "Strongpassword123"
    mock_user = MagicMock(id=1, is_active=True, hashed_password=hash_password(old_password))
    access_token = generate_access_token({"sub": mock_user.id})
    mock_db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=mock_user)
    mock_db.commit = AsyncMock()
    response = await client.post(
        "/users/change-password/",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "old_password": old_password,
            "new_password": "Newstrongpassword123"
        }
    )
    mock_db.commit.assert_called_once()
    assert response.status_code == 200



@pytest.mark.asyncio
async def test_change_user_password_not_headers(client, mock_db):
    old_password = "Strongpassword123"
    response = await client.post(
        "/users/change-password/",
        headers={},
        json={
            "old_password": old_password,
            "new_password": "Newstrongpassword123"
        }
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_change_user_password_invalid_headers(client, mock_db):
    old_password = "Strongpassword123"
    response = await client.post(
        "/users/change-password/",
        headers={"Authorization": "invalid_bearer"},
        json={
            "old_password": old_password,
            "new_password": "Newstrongpassword123"
        }
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_change_user_password_unauthorized(client, mock_db):
    old_password = "Strongpassword123"
    access_token = "invalid_token"
    with patch("security.token.decode_token", side_effect=ValueError()):
        response = await client.post(
            "/users/change-password/",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "old_password": old_password,
                "new_password": "Newstrongpassword123"
            }
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_change_password_invalid_old_password(client, mock_db):
    old_password = "Strongpassword"
    mock_user = MagicMock(id=1, is_active=True, hashed_password=hash_password(old_password))
    access_token = generate_access_token({"sub": mock_user.id})
    mock_db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=mock_user)
    with patch("security.passwords.verify_password", return_value=False):
        response = await client.post(
            "/users/change-password/",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "old_password": old_password,
                "new_password": "Newstrongpassword123"
            }
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_reset_password_request_success(client, mock_db):
    mock_reset_token = MagicMock(expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc))
    mock_user = MagicMock(id=1, is_active=True)
    mock_db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_user)),
        AsyncMock(scalar_one_or_none=MagicMock(return_value=mock_reset_token))
    ]
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()
    with patch("tasks.celery.send_email.delay") as mock_send_email:
        response = await client.post(
            "/users/reset-password-request/",
            json={
                "email": "test@test.com"
            }
        )
        mock_send_email.assert_called_once()
        mock_db.delete.assert_called_once_with(mock_reset_token)
        mock_db.commit.assert_called_once()
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_request_user_not_active(client, mock_db):
    mock_user = MagicMock(id=1, is_active=False)
    with patch("users.service.get_user_by_email", new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = mock_user
        response = await client.post(
            "/users/reset-password-request/",
            json={
                "email": "test@test.com"
            }
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_reset_password_complete_success(client, mock_db):
    token = secrets.token_urlsafe(32)
    mock_user = MagicMock(id=1, is_active=True)
    mock_reset_password_token = MagicMock(token=token, user_id=mock_user.id, expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc))
    mock_db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=mock_reset_password_token)
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()
    with patch("users.service.get_user_by_email", new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = mock_user
        response = await client.post(
            "/users/reset-password-complete/",
            json={
                "email": "test@test.com",
                "new_password": "Newstrongpassword123",
                "token": mock_reset_password_token.token
            }
        )
        mock_db.delete.assert_called_once_with(mock_reset_password_token)
        mock_db.commit.assert_called_once()
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_complete_not_token(client, mock_db):
    mock_user = MagicMock(id=1, is_active=True)
    mock_reset_password_token = MagicMock(user_id=mock_user.id, expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc))
    mock_db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=None)
    with patch("users.service.get_user_by_email", new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = mock_user
        response = await client.post(
            "/users/reset-password-complete/",
            json={
                "email": "test@test.com",
                "new_password": "Newstrongpassword123",
                "token": "invalid_token"
            }
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_reset_password_complete_token_is_expired(client, mock_db):
    token = secrets.token_urlsafe(32)
    mock_user = MagicMock(id=1, is_active=True)
    expiration_date = datetime.now(timezone.utc) - timedelta(days=1)
    mock_password_reset_token = MagicMock(token=token, user_id=mock_user.id, expires_at=expiration_date)
    mock_db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=mock_password_reset_token)
    with patch("users.service.get_user_by_email", new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = mock_user
        response = await client.post(
            "/users/reset-password-complete/",
            json={
                "email": "test@test.com",
                "new_password": "Newstrongpassword123",
                "token": mock_password_reset_token.token
            }
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_access_token_success(client, mock_db):
    mock_user = MagicMock(id=1, is_active=True)
    expiration_date = datetime.now(timezone.utc) + timedelta(days=7)
    mock_refresh_token = MagicMock(token=generate_refresh_token({"sub": mock_user.id}), user_id=mock_user.id, expires_at=expiration_date)
    mock_db.delete = AsyncMock()
    mock_db.add = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=mock_refresh_token)
    with patch("dependencies.users.get_user_by_id", new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = mock_user
        response = await client.post(
            "/users/refresh-access-token/",
            json={"refresh_token": mock_refresh_token.token}
        )
        mock_db.delete.assert_called_once_with(mock_refresh_token)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_refresh_access_token_not_token(client, mock_db):
    mock_user = MagicMock(id=1, is_active=True)
    mock_db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=None)
    response = await client.post(
        "/users/refresh-access-token/",
        json={"refresh_token": "invalid_token"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_access_token_is_expired(client, mock_db):
    mock_user = MagicMock(id=1, is_active=True)
    expiration_date = datetime.now(timezone.utc) - timedelta(days=1)
    mock_refresh_token = MagicMock(token=generate_refresh_token({"sub": mock_user.id}), user_id=mock_user.id, expires_at=expiration_date)
    mock_db.execute.return_value.scalar_one_or_none = AsyncMock(return_value=mock_refresh_token)
    response = await client.post(
        "/users/refresh-access-token/",
        json={"refresh_token": mock_refresh_token.token}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_make_admin_success(client, mock_db):
    mock_admin = MagicMock(id=1, group_id=group_admins_id)
    mock_user = MagicMock(id=2, group_id=group_users_id)

    with patch("dependencies.authorization.require_admin", new_callable=AsyncMock) as mock_require:
        mock_require.return_value = mock_admin
        with patch("dependencies.users.get_user_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            mock_db.commit = AsyncMock()

            response = await client.post("/users/2/make-admin/")

            assert response.status_code == 200
            assert mock_user.group_id == group_admins_id
            mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_make_admin_own_group(client, mock_db):
    mock_admin = MagicMock(id=1, group_id=group_admins_id)

    with patch("dependencies.authorization.require_admin", new_callable=AsyncMock) as mock_require:
        mock_require.return_value = mock_admin
        with patch("dependencies.users.get_user_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_admin

            response = await client.post("/users/1/make-admin/")

            assert response.status_code == 400


@pytest.mark.asyncio
async def test_make_admin_already_admin(client, mock_db):
    mock_admin = MagicMock(id=1, group_id=group_admins_id)
    mock_user = MagicMock(id=2, group_id=group_admins_id)

    with patch("dependencies.authorization.require_admin", new_callable=AsyncMock) as mock_require:
        mock_require.return_value = mock_admin
        with patch("dependencies.users.get_user_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user

            response = await client.post("/users/2/make-admin/")

            assert response.status_code == 400


@pytest.mark.asyncio
async def test_make_moderator_success(client, mock_db):
    mock_moderator = MagicMock(id=1, group_id=group_admins_id)
    mock_user = MagicMock(id=2, group_id=group_users_id)

    with patch("dependencies.authorization.require_admin", new_callable=AsyncMock) as mock_require:
        mock_require.return_value = mock_moderator
        with patch("dependencies.users.get_user_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            mock_db.commit = AsyncMock()

            response = await client.post("/users/2/make-moderator/")

            assert response.status_code == 200
            assert mock_user.group_id == group_moderators_id
            mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_make_moderator_own_group(client, mock_db):
    mock_moderator = MagicMock(id=1, group_id=group_moderators_id)

    with patch("dependencies.authorization.require_admin", new_callable=AsyncMock) as mock_require:
        mock_require.return_value = mock_moderator
        with patch("dependencies.users.get_user_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_moderator

            response = await client.post("/users/1/make-moderator/")

            assert response.status_code == 400


@pytest.mark.asyncio
async def test_make_moderator_already_moderator(client, mock_db):
    mock_admin = MagicMock(id=1, group_id=group_admins_id)
    mock_user = MagicMock(id=2, group_id=group_moderators_id)

    with patch("dependencies.authorization.require_admin", new_callable=AsyncMock) as mock_require:
        mock_require.return_value = mock_admin
        with patch("dependencies.users.get_user_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user

            response = await client.post("/users/2/make-moderator/")

            assert response.status_code == 400


@pytest.mark.asyncio
async def test_make_user_success(client, mock_db):
    mock_admin = MagicMock(id=1, group_id=group_admins_id)
    mock_user = MagicMock(id=2, group_id=group_moderators_id)

    with patch("dependencies.authorization.require_admin", new_callable=AsyncMock) as mock_require:
        mock_require.return_value = mock_admin
        with patch("dependencies.users.get_user_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            mock_db.commit = AsyncMock()

            response = await client.post("/users/2/make-user/")

            assert response.status_code == 200
            assert mock_user.group_id == group_users_id
            mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_make_user_own_group(client, mock_db):
    mock_admin = MagicMock(id=1, group_id=group_admins_id)
    mock_user = MagicMock(id=1, group_id=group_users_id)

    with patch("dependencies.authorization.require_admin", new_callable=AsyncMock) as mock_require:
        mock_require.return_value = mock_admin
        with patch("dependencies.users.get_user_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user

            response = await client.post("/users/1/make-user/")

            assert response.status_code == 400


@pytest.mark.asyncio
async def test_make_user_already_user(client, mock_db):
    mock_admin = MagicMock(id=1, group_id=group_admins_id)
    mock_user = MagicMock(id=2, group_id=group_users_id)

    with patch("dependencies.authorization.require_admin", new_callable=AsyncMock) as mock_require:
        mock_require.return_value = mock_admin
        with patch("dependencies.users.get_user_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user

            response = await client.post("/users/2/make-user/")

            assert response.status_code == 400


@pytest.mark.asyncio
async def test_activate_user_by_id_success(client, mock_db):
    mock_admin = MagicMock(id=1, group_id=group_admins_id)
    mock_user = MagicMock(id=2, is_active=False)
    with patch("dependencies.authorization.require_admin", new_callable=AsyncMock) as mock_require:
        mock_require.return_value = mock_admin
        with patch("dependencies.users.get_user_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            mock_db.commit = AsyncMock()
            response = await client.post("/users/2/activate_user/")
            mock_db.commit.assert_called_once()
            assert mock_user.is_active == True
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_activate_user_by_id_already_activated(client, mock_db):
    mock_admin = MagicMock(id=1, group_id=group_admins_id)
    mock_user = MagicMock(id=2, is_active=True)
    with patch("dependencies.authorization.require_admin", new_callable=AsyncMock) as mock_require:
        mock_require.return_value = mock_admin
        with patch("dependencies.users.get_user_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            response = await client.post("/users/2/activate_user/")
            assert response.status_code == 400
