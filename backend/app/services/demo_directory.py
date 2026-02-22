from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.user import User
from app.services.auth import AuthService, UserRecord


def _org_slug(org_id: str) -> str:
    return org_id


def _org_name(org_id: str) -> str:
    suffix = org_id.removeprefix("org-").replace("-", " ").strip()
    return suffix.title() if suffix else org_id


def _user_email(record: UserRecord) -> str:
    org_domain = record.org_id.replace("_", "-")
    return f"{record.username}@{org_domain}.local"


async def ensure_demo_directory_seeded(
    session: AsyncSession,
    auth_service: AuthService,
) -> None:
    records = auth_service.list_user_records()
    if not records:
        return

    changed = False
    org_ids = sorted({record.org_id for record in records})
    user_ids = [record.id for record in records]

    existing_org_ids = set(
        (
            await session.scalars(
                select(Organization.id).where(Organization.id.in_(org_ids))
            )
        ).all()
    )

    for org_id in org_ids:
        if org_id not in existing_org_ids:
            session.add(
                Organization(
                    id=org_id,
                    slug=_org_slug(org_id),
                    name=_org_name(org_id),
                )
            )
            changed = True

    existing_users = {
        user.id: user
        for user in (
            await session.scalars(select(User).where(User.id.in_(user_ids)))
        ).all()
    }

    for record in records:
        db_user = existing_users.get(record.id)
        generated_email = _user_email(record)
        if db_user is None:
            session.add(
                User(
                    id=record.id,
                    org_id=record.org_id,
                    email=generated_email,
                    username=record.username,
                    full_name=record.full_name,
                    role=record.role,
                    status=record.status,
                    password_hash=record.password_hash,
                    created_at=record.created_at,
                )
            )
            changed = True
            continue

        if db_user.org_id != record.org_id:
            db_user.org_id = record.org_id
            changed = True
        if db_user.email != generated_email:
            db_user.email = generated_email
            changed = True
        if db_user.username != record.username:
            db_user.username = record.username
            changed = True
        if db_user.full_name != record.full_name:
            db_user.full_name = record.full_name
            changed = True
        if db_user.role != record.role:
            db_user.role = record.role
            changed = True
        if db_user.status != record.status:
            db_user.status = record.status
            changed = True
        if db_user.password_hash != record.password_hash:
            db_user.password_hash = record.password_hash
            changed = True

    if changed:
        await session.commit()
