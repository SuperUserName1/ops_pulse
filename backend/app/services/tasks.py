from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.errors import AppException
from app.models.task import Task
from app.models.user import User
from app.schemas.dashboard import DashboardSummaryResponse, TaskStatusCounts
from app.schemas.task import (
    TaskCreateRequest,
    TaskListFilters,
    TaskPublic,
    TaskResponse,
    TaskUpdateRequest,
)

_TASK_STATUSES = ("open", "in_progress", "blocked", "done")


def to_task_public(task: Task) -> TaskPublic:
    return TaskPublic(
        id=task.id,
        org_id=task.org_id,
        title=task.title,
        description=task.description,
        status=task.status,  # type: ignore[arg-type]
        assignee_user_id=task.assignee_user_id,
        created_at=task.created_at,
    )


def _validate_created_range(filters: TaskListFilters) -> None:
    if filters.created_from and filters.created_to and filters.created_from > filters.created_to:
        raise AppException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="invalid_filters",
            message="`created_from` must be less than or equal to `created_to`.",
        )


def _apply_task_filters(
    stmt: Select[Any],
    *,
    org_id: str,
    filters: TaskListFilters,
    assignee_user_id: str | None = None,
) -> Select[Any]:
    stmt = stmt.where(Task.org_id == org_id)

    if filters.search:
        needle = f"%{filters.search.strip()}%"
        stmt = stmt.where(
            or_(
                Task.title.ilike(needle),
                Task.description.ilike(needle),
            )
        )

    if filters.status:
        stmt = stmt.where(Task.status == filters.status)

    if assignee_user_id:
        stmt = stmt.where(Task.assignee_user_id == assignee_user_id)

    if filters.created_from:
        stmt = stmt.where(Task.created_at >= filters.created_from)

    if filters.created_to:
        stmt = stmt.where(Task.created_at <= filters.created_to)

    return stmt


async def _validate_assignee_user(
    session: AsyncSession,
    *,
    org_id: str,
    assignee_user_id: str | None,
) -> None:
    if assignee_user_id is None:
        return

    assignee = await session.scalar(
        select(User.id).where(
            User.id == assignee_user_id,
            User.org_id == org_id,
        )
    )
    if assignee is None:
        raise AppException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="invalid_assignee",
            message="Assignee user not found in current organization.",
        )


async def list_tasks(
    session: AsyncSession,
    *,
    org_id: str,
    filters: TaskListFilters,
    limit: int,
    offset: int,
    assignee_user_id: str | None = None,
) -> tuple[list[TaskPublic], int]:
    _validate_created_range(filters)

    list_stmt = _apply_task_filters(
        select(Task),
        org_id=org_id,
        filters=filters,
        assignee_user_id=assignee_user_id,
    ).order_by(Task.created_at.desc()).limit(limit).offset(offset)

    total_stmt = _apply_task_filters(
        select(func.count()).select_from(Task),
        org_id=org_id,
        filters=filters,
        assignee_user_id=assignee_user_id,
    )

    items = (await session.scalars(list_stmt)).all()
    total = int((await session.execute(total_stmt)).scalar_one())
    return [to_task_public(item) for item in items], total


async def get_task_for_org(
    session: AsyncSession,
    *,
    task_id: str,
    org_id: str,
) -> Task:
    task = await session.scalar(
        select(Task).where(
            Task.id == task_id,
            Task.org_id == org_id,
        )
    )
    if task is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="not_found",
            message="Task not found.",
        )
    return task


async def create_task(
    session: AsyncSession,
    *,
    org_id: str,
    payload: TaskCreateRequest,
) -> TaskResponse:
    await _validate_assignee_user(
        session,
        org_id=org_id,
        assignee_user_id=payload.assignee_user_id,
    )

    task = Task(
        id=str(uuid4()),
        org_id=org_id,
        title=payload.title.strip(),
        description=payload.description.strip() if payload.description is not None else None,
        status=payload.status,
        assignee_user_id=payload.assignee_user_id,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return TaskResponse(task=to_task_public(task))


async def update_task(
    session: AsyncSession,
    *,
    org_id: str,
    task_id: str,
    payload: TaskUpdateRequest,
) -> TaskResponse:
    task = await get_task_for_org(session, task_id=task_id, org_id=org_id)
    patch = payload.model_dump(exclude_unset=True)

    if "assignee_user_id" in patch:
        await _validate_assignee_user(
            session,
            org_id=org_id,
            assignee_user_id=patch["assignee_user_id"],
        )

    if "title" in patch and patch["title"] is not None:
        patch["title"] = patch["title"].strip()

    if "description" in patch and patch["description"] is not None:
        patch["description"] = patch["description"].strip()

    for key, value in patch.items():
        setattr(task, key, value)

    await session.commit()
    await session.refresh(task)
    return TaskResponse(task=to_task_public(task))


async def delete_task(
    session: AsyncSession,
    *,
    org_id: str,
    task_id: str,
) -> None:
    task = await get_task_for_org(session, task_id=task_id, org_id=org_id)
    await session.delete(task)
    await session.commit()


async def build_dashboard_summary(
    session: AsyncSession,
    *,
    org_id: str,
) -> DashboardSummaryResponse:
    counts_by_status = {key: 0 for key in _TASK_STATUSES}

    grouped = await session.execute(
        select(Task.status, func.count())
        .where(Task.org_id == org_id)
        .group_by(Task.status)
    )
    total_tasks = 0
    for task_status, count in grouped.all():
        status_key = str(task_status)
        count_value = int(count)
        total_tasks += count_value
        if status_key in counts_by_status:
            counts_by_status[status_key] = count_value

    recent = (
        await session.scalars(
            select(Task)
            .where(Task.org_id == org_id)
            .order_by(Task.created_at.desc())
            .limit(5)
        )
    ).all()

    return DashboardSummaryResponse(
        org_id=org_id,
        total_tasks=total_tasks,
        counts=TaskStatusCounts(**counts_by_status),
        recent_tasks=[to_task_public(task) for task in recent],
    )
