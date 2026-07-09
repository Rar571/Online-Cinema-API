from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


from dependencies.users import get_current_user_model
from models.users import UserModel, UserGroupModel, UserGroupEnum

group_moderators_id = None
group_admins_id = None
group_users_id = None


async def get_groups_id(db: AsyncSession):
    global group_moderators_id, group_admins_id, group_users_id
    group_moderators_result = await db.execute(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.MODERATOR)
    )
    group_moderators = group_moderators_result.scalar_one_or_none()
    if group_moderators is None:
        group_moderators = UserGroupModel(name=UserGroupEnum.MODERATOR)
        db.add(group_moderators)
        await db.flush()

    group_moderators_id = group_moderators.id

    group_admins_result = await db.execute(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.ADMIN)
    )
    group_admins = group_admins_result.scalar_one_or_none()
    if group_admins is None:
        group_admins = UserGroupModel(name=UserGroupEnum.ADMIN)
        db.add(group_admins)
        await db.flush()

    group_admins_id = group_admins.id

    group_users_result = await db.execute(
        select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    )
    group_users = group_users_result.scalar_one_or_none()
    if group_users is None:
        group_users = UserGroupModel(name=UserGroupEnum.USER)
        db.add(group_users)
        await db.flush()
    group_users_id = group_users.id
    await db.commit()


async def require_moderator(current_user: UserModel = Depends(get_current_user_model)):
    if current_user.group_id == group_admins_id:
        return current_user
    if current_user.group_id != group_moderators_id:
        raise HTTPException(
            status_code=403, detail="You do not have access to this feature"
        )
    return current_user


async def require_admin(current_user: UserModel = Depends(get_current_user_model)):
    if current_user.group_id != group_admins_id:
        raise HTTPException(
            status_code=403, detail="You do not have access to this feature"
        )
    return current_user
