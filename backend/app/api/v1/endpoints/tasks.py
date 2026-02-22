from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from starlette import status

from app.core.deps import DbSessionDep
from app.core.rate_limit import rate_limit_dependency
from app.core.security import (
    CurrentOrgDep,
    CurrentUserDep,
    get_auth_service_dep,
    require_role,
)
from app.schemas.task import (
    TaskCreateRequest,
    TaskListFilters,
    TaskResponse,
    TasksListResponse,
    TaskStatusLiteral,
    TaskUpdateRequest,
)
from app.services.auth import AuthenticatedUser, AuthService
from app.services.demo_directory import ensure_demo_directory_seeded
from app.services.tasks import (
    create_task as create_task_service,
)
from app.services.tasks import (
    delete_task as delete_task_service,
)
from app.services.tasks import (
    get_task_for_org,
    to_task_public,
)
from app.services.tasks import (
    list_tasks as list_tasks_service,
)
from app.services.tasks import (
    update_task as update_task_service,
)

router = APIRouter(prefix="/tasks")

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service_dep)]


@router.get(
    "",
    response_model=TasksListResponse,
    tags=["tasks"],
    summary="List tasks for current organization",
)
async def list_tasks(
    user: CurrentUserDep,
    org_id: CurrentOrgDep,
    session: DbSessionDep,
    auth_service: AuthServiceDep,
    _: Annotated[
        None,
        Depends(
            rate_limit_dependency(
                "tasks_list",
                fail_closed=True,
                include_user_id_from_request=True,
            )
        ),
    ],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    status_filter: TaskStatusLiteral | None = Query(default=None, alias="status"),
    assignee_user_id: str | None = Query(default=None, min_length=1, max_length=64),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
) -> TasksListResponse:
    del user
    await ensure_demo_directory_seeded(session, auth_service)
    filters = TaskListFilters(
        search=search,
        status=status_filter,
        created_from=created_from,
        created_to=created_to,
    )
    items, total = await list_tasks_service(
        session,
        org_id=org_id,
        filters=filters,
        limit=limit,
        offset=offset,
        assignee_user_id=assignee_user_id,
    )
    return TasksListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    tags=["tasks"],
    summary="Get task by id",
)
async def get_task(
    user: CurrentUserDep,
    org_id: CurrentOrgDep,
    task_id: str,
    session: DbSessionDep,
    auth_service: AuthServiceDep,
    _: Annotated[
        None,
        Depends(
            rate_limit_dependency(
                "tasks_get",
                fail_closed=True,
                include_user_id_from_request=True,
            )
        ),
    ],
) -> TaskResponse:
    del user
    await ensure_demo_directory_seeded(session, auth_service)
    task = await get_task_for_org(session, task_id=task_id, org_id=org_id)
    return TaskResponse(task=to_task_public(task))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=TaskResponse,
    tags=["tasks"],
    summary="Create task in current organization",
)
async def create_task(
    _editor: Annotated[AuthenticatedUser, Depends(require_role("admin", "agent"))],
    org_id: CurrentOrgDep,
    payload: TaskCreateRequest,
    session: DbSessionDep,
    auth_service: AuthServiceDep,
    __: Annotated[
        None,
        Depends(
            rate_limit_dependency(
                "tasks_create",
                fail_closed=True,
                include_user_id_from_request=True,
            )
        ),
    ],
) -> TaskResponse:
    await ensure_demo_directory_seeded(session, auth_service)
    return await create_task_service(session, org_id=org_id, payload=payload)


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    tags=["tasks"],
    summary="Update task",
)
async def update_task(
    _editor: Annotated[AuthenticatedUser, Depends(require_role("admin", "agent"))],
    org_id: CurrentOrgDep,
    task_id: str,
    payload: TaskUpdateRequest,
    session: DbSessionDep,
    auth_service: AuthServiceDep,
    __: Annotated[
        None,
        Depends(
            rate_limit_dependency(
                "tasks_update",
                fail_closed=True,
                include_user_id_from_request=True,
            )
        ),
    ],
) -> TaskResponse:
    await ensure_demo_directory_seeded(session, auth_service)
    return await update_task_service(session, org_id=org_id, task_id=task_id, payload=payload)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["tasks"],
    summary="Delete task",
)
async def delete_task(
    _admin: Annotated[AuthenticatedUser, Depends(require_role("admin"))],
    org_id: CurrentOrgDep,
    task_id: str,
    session: DbSessionDep,
    auth_service: AuthServiceDep,
    __: Annotated[
        None,
        Depends(
            rate_limit_dependency(
                "tasks_delete",
                fail_closed=True,
                include_user_id_from_request=True,
            )
        ),
    ],
) -> None:
    await ensure_demo_directory_seeded(session, auth_service)
    await delete_task_service(session, org_id=org_id, task_id=task_id)
