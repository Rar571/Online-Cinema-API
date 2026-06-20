from fastapi import Depends, HTTPException, APIRouter, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


from db.session_postgresql import get_db
from dependencies.authorization import (
    require_admin,
    group_admins_id,
    group_moderators_id,
    group_users_id,
)
from dependencies.users import get_user_by_id, get_user_by_email
from models.users import (
    UserModel,
    UserGroupModel,
    UserGroupEnum,
    ActivationTokenModel,
    RefreshTokenModel,
    PasswordResetTokenModel,
)
from schemas.users import (
    UserRegistrationSchema,
    UserActivationSchema,
    UserBaseSchema,
    UserLoginSchema,
    UserChangePasswordSchema,
    UserResetPasswordRequestSchema,
    UserResetPasswordCompleteSchema,
    UserRefreshAccessTokenSchema,
)
from security.passwords import hash_password, verify_password
from security.token import generate_access_token, generate_refresh_token, decode_token
from tasks.celery import send_email
from datetime import datetime, timezone, timedelta

users_router = APIRouter()


@users_router.post("/register/", status_code=201)
async def register_user(
    user_data: UserRegistrationSchema, db: AsyncSession = Depends(get_db)
):
    user_result = await db.execute(
        select(UserModel).where(UserModel.email == user_data.email)
    )
    existing_user = user_result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )
    result_group = await db.execute(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    )
    group = result_group.scalar_one()
    hashed_password = hash_password(user_data.password)
    try:
        new_user = UserModel(
            email=user_data.email, hashed_password=hashed_password, group_id=group.id
        )
        db.add(new_user)
        await db.flush()
        activation_token = ActivationTokenModel(user_id=new_user.id)
        db.add(activation_token)
        await db.commit()
        await db.refresh(new_user)
        send_email.delay(
            subject="Activation email",
            body=f"http://127.0.0.1:8000/users/activate?token={activation_token.token}. This link is valid for 24 hours",
            receiver_email=user_data.email,
        )
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error was occurred during user creation. Try again later.",
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=f"User was registered successfully. "
            f"The email with activation token has been "
            f"already sent to your {user_data.email}",
        )


@users_router.post("/activation_token/")
async def get_new_activation_token(
    user_data: UserBaseSchema, db: AsyncSession = Depends(get_db)
):
    user = await get_user_by_email(user_email=user_data.email, db=db)
    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User is already active"
        )
    token_result = await db.execute(
        select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    )
    token = token_result.scalar_one_or_none()
    if token and token.expires_at > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your old token is still valid. Use it to activate your account.",
        )
    if token:
        await db.delete(token)
    try:
        new_token = ActivationTokenModel(user_id=user.id)
        db.add(new_token)
        await db.commit()
        await db.refresh(new_token)
        send_email.delay(
            subject="Activation email",
            body=f"http://127.0.0.1:8000/users/activate?token={new_token.token}. This link is valid for 24 hours",
            receiver_email=user.email,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error was occurred during email sending",
        )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "detail": f"New link has been already sent to your {user.email} to activate account. Use it for 24 hours."
        },
    )


@users_router.get("/activate/")
async def activate_account(
    user_data: UserActivationSchema, db: AsyncSession = Depends(get_db)
):
    user = await get_user_by_email(user_email=user_data.email, db=db)
    result_token = await db.execute(
        select(ActivationTokenModel).where(
            ActivationTokenModel.user_id == user.id,
            ActivationTokenModel.token == user_data.token,
        )
    )
    token = result_token.scalar_one_or_none()
    if not token or token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired",
        )
    await db.delete(token)
    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User is already active"
        )
    user.is_active = True
    await db.commit()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"detail": "Account has been activated."},
    )


@users_router.get("/login/")
async def user_login(user_data: UserLoginSchema, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(user_email=user_data.email, db=db)
    hashed_password = user.hashed_password
    if not verify_password(user_data.password, hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User's account is not activated",
        )
    access_token = generate_access_token({"sub": user.id})
    refresh_token = generate_refresh_token({"sub": user.id})
    expiration_date = datetime.now(timezone.utc) + timedelta(days=7)
    refresh_token_model = RefreshTokenModel(
        user_id=user.id, token=refresh_token, expires_at=expiration_date
    )
    db.add(refresh_token_model)
    await db.commit()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "access token": access_token,
            "refresh token": refresh_token,
        },
    )


@users_router.post("/logout/")
async def user_logout(request: Request, db: AsyncSession = Depends(get_db)):
    headers = request.headers.get("Authorization")
    if not headers:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
        )
    headers_list = headers.split()
    if headers_list[0] != "Bearer" or len(headers_list) != 2:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
        )
    access_token = headers_list[1]
    try:
        user_id = decode_token(access_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )
    refresh_token_result = await db.execute(
        select(RefreshTokenModel).where(RefreshTokenModel.user_id == user_id)
    )
    refresh_token = refresh_token_result.scalar_one_or_none()
    if refresh_token:
        await db.delete(refresh_token)
        await db.commit()
    return JSONResponse(
        status_code=status.HTTP_200_OK, content={"detail": "You have logged out"}
    )


@users_router.post("/change-password/")
async def change_user_password(
    request: Request,
    user_data: UserChangePasswordSchema,
    db: AsyncSession = Depends(get_db),
):
    headers = request.headers.get("Authorization")
    if not headers:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
        )
    headers_list = headers.split()
    if len(headers_list) != 2 or headers_list[0] != "Bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
        )
    access_token = headers_list[1]
    try:
        user_id = decode_token(access_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )
    user = await get_user_by_id(user_id=user_id, db=db)
    hashed_password = user.hashed_password
    if not verify_password(user_data.old_password, hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Old password is incorrect"
        )
    new_hashed_password = hash_password(user_data.new_password)
    user.hashed_password = new_hashed_password
    await db.commit()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"detail": "password was changed successfully"},
    )


@users_router.post("/reset-password-request/")
async def reset_user_password_request(
    user_data: UserResetPasswordRequestSchema, db: AsyncSession = Depends(get_db)
):
    user = await get_user_by_email(user_email=user_data.email, db=db)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"If your account is registered and active, the email with instructions was sent to your {user_data.email}",
        )

    old_reset_token_result = await db.execute(
        select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.user_id == user.id
        )
    )
    old_reset_token = old_reset_token_result.scalar_one_or_none()
    if old_reset_token:
        await db.delete(old_reset_token)
        await db.flush()

    try:
        reset_password_token = PasswordResetTokenModel(user_id=user.id)
        db.add(reset_password_token)
        await db.commit()
        await db.refresh(reset_password_token)
        send_email.delay(
            subject="Reset Password Email",
            body=f"Your link to reset old password is: http://127.0.0.1:8000/users/reset-password-complete?token={reset_password_token.token}",
            receiver_email=user.email,
        )
    except Exception:
        raise HTTPException(
            status_code=500, detail="An error was occurred during email sending"
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "detail": f"If your account is registered and active, the email with instructions was sent to your {user_data.email}"
        },
    )


@users_router.post("/reset-password-complete/")
async def reset_user_password_complete(
    user_data: UserResetPasswordCompleteSchema, db: AsyncSession = Depends(get_db)
):
    user = await get_user_by_email(user_email=user_data.email, db=db)
    reset_token_result = await db.execute(
        select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.user_id == user.id,
            PasswordResetTokenModel.token == user_data.token,
        )
    )
    reset_token = reset_token_result.scalar_one_or_none()
    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is invalid"
        )
    if reset_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is expired"
        )
    hashed_password = hash_password(user_data.new_password)
    user.hashed_password = hashed_password
    await db.delete(reset_token)
    await db.commit()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"detail": "Password was successfully changed"},
    )


@users_router.post("/refresh-access-token/")
async def refresh_user_access_token(
    user_data: UserRefreshAccessTokenSchema, db: AsyncSession = Depends(get_db)
):
    refresh_token_result = await db.execute(
        select(RefreshTokenModel).where(
            RefreshTokenModel.token == user_data.refresh_token
        )
    )
    refresh_token = refresh_token_result.scalar_one_or_none()
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is invalid"
        )
    if refresh_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is expired"
        )
    user = await get_user_by_id(user_id=refresh_token.user_id, db=db)
    await db.delete(refresh_token)
    new_refresh_token = generate_refresh_token({"sub": user.id})
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    new_refresh_token_model = RefreshTokenModel(
        user_id=user.id, token=new_refresh_token, expires_at=expires_at
    )
    db.add(new_refresh_token_model)
    access_token = generate_access_token({"sub": user.id})
    await db.commit()
    await db.refresh(new_refresh_token_model)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "refresh token": new_refresh_token_model.token,
            "access token": access_token,
        },
    )


@users_router.post("/{user_id}/make-admin/")
async def make_admin(
    user_id: int,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can not change your own group",
        )
    user = await get_user_by_id(user_id=user_id, db=db)
    if user.group_id == group_admins_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User is already an admin"
        )
    user.group_id = group_admins_id
    await db.commit()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"detail": "User's group was changed to 'admin'"},
    )


@users_router.post("/{user_id}/make-moderator/")
async def make_moderator(
    user_id: int,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can not change your own group",
        )
    user = await get_user_by_id(user_id=user_id, db=db)
    if user.group_id == group_moderators_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a moderator",
        )
    user.group_id = group_moderators_id
    await db.commit()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"detail": "User's group was changed to 'moderator'"},
    )


@users_router.post("/{user_id}/make-user/")
async def make_user(
    user_id: int,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can not change your own group",
        )
    user = await get_user_by_id(user_id=user_id, db=db)
    if user.group_id == group_users_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already in users group",
        )
    user.group_id = group_users_id
    await db.commit()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"detail": "User's group was changed to 'user'"},
    )


@users_router.post("/{user_id}/activate_user/")
async def activate_user_by_id(
    user_id: int,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_id(user_id=user_id, db=db)
    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User is already active"
        )
    user.is_active = True
    await db.commit()
    return JSONResponse(
        status_code=status.HTTP_200_OK, content={"detail": "User has been activated"}
    )
