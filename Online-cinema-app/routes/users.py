import jwt
from fastapi import Depends, HTTPException, APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import select, cast
from sqlalchemy.ext.asyncio import AsyncSession
from typing import cast


from db.session_postgresql import get_db
from models.users import (
    UserModel,
    UserGroupModel,
    UserGroupEnum,
    ActivationTokenModel,
    RefreshTokenModel,
)
from schemas.users import (
    UserRegistrationSchema,
    UserActivationSchema,
    UserBaseSchema,
    UserLoginSchema,
)
from security.passwords import hash_password, verify_password
from security.token import generate_access_token, generate_refresh_token
from tasks.celery import send_email
from datetime import datetime, timezone, timedelta

router = APIRouter()


@router.post("/register/", status_code=201)
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
        send_email.delay(
            subject="Activation email",
            body=f"http://127.0.0.1:8000/activate?token={activation_token.token}. This link is valid for 24 hours",
            receiver_email=user_data.email,
        )
        await db.commit()
        await db.refresh(new_user)
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


@router.post("/activation_token/")
async def get_new_activation_token(
    user_data: UserBaseSchema, db: AsyncSession = Depends(get_db)
):
    user_result = await db.execute(
        select(UserModel).where(UserModel.email == user_data.email)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with the provided email is not registered, please register first.",
        )
    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User is already active"
        )
    token_result = await db.execute(
        select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    )
    token = token_result.scalar_one_or_none()
    if token and cast(datetime, token.expires_at).replace(
        tzinfo=timezone.utc
    ) > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your old token is still valid. Use it to activate your account.",
        )
    if token:
        await db.delete(token)
    new_token = ActivationTokenModel(user_id=user.id)
    db.add(new_token)
    send_email.delay(
        subject="Activation email",
        body=f"http://127.0.0.1:8000/activate?token={new_token.token}. This link is valid for 24 hours",
        receiver_email=user.email,
    )
    await db.commit()
    await db.refresh(new_token)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "detail": f"New link has been already sent to your {user.email} to activate account. Use it for 24 hours."
        },
    )


@router.post("/activate/")
async def activate_account(
    user_data: UserActivationSchema, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserModel).where(
            UserModel.email == user_data.email,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=400, detail="User with provided email is not registered"
        )
    result_token = await db.execute(
        select(ActivationTokenModel).where(
            ActivationTokenModel.user_id == user.id,
            ActivationTokenModel.token == user_data.token,
        )
    )
    token = result_token.scalar_one_or_none()
    if not token or cast(datetime, token.expires_at).replace(
        tzinfo=timezone.utc
    ) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token is invalid or expired")
    await db.delete(token)
    if user.is_active:
        raise HTTPException(status_code=400, detail="User is already active")
    user.is_active = True
    await db.commit()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"detail": "Account has been activated."},
    )


@router.post("/login/")
async def user_login(user_data: UserLoginSchema, db: AsyncSession = Depends(get_db)):
    user_result = await db.execute(
        select(UserModel).where(UserModel.email == user_data.email)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with provided email is not registered",
        )
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


