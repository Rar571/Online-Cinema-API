from fastapi import Depends, HTTPException, APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session_postgresql import get_db
from models.users import UserModel, UserGroupModel, UserGroupEnum, ActivationTokenModel
from schemas.users import UserRegistrationSchema
from security.passwords import hash_password
from tasks.celery import send_email

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
            status_code=409, detail="User with this email already exists"
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
            body=f"Your activation token is: {activation_token.token}. This token is valid for 24 hours",
            receiver_email=user_data.email,
        )
        await db.commit()
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="An error was occurred during user creation. Try again later.",
        )
    else:
        return {
            f"User was registered successfully. "
            f"The email with activation token has been "
            f"already sent to your {user_data.email}"
        }
