from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import OffsetPaginationMeta

TaskStatusLiteral = Literal["open", "in_progress", "blocked", "done"]


class TaskPublic(BaseModel):
    id: str = Field(..., examples=["tsk-1"])
    org_id: str = Field(..., examples=["org-acme"])
    title: str = Field(..., min_length=1, max_length=255, examples=["Review failed shipment"])
    description: str | None = Field(default=None, examples=["Call warehouse and confirm batch."])
    status: TaskStatusLiteral = Field(..., examples=["open"])
    assignee_user_id: str | None = Field(default=None, examples=["usr-agent-1"])
    created_at: datetime = Field(..., description="Task creation timestamp (UTC)")


class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    status: TaskStatusLiteral = Field(default="open")
    assignee_user_id: str | None = Field(default=None, min_length=1, max_length=64)


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    status: TaskStatusLiteral | None = Field(default=None)
    assignee_user_id: str | None = Field(default=None, min_length=1, max_length=64)


class TaskListFilters(BaseModel):
    search: str | None = Field(default=None, min_length=1, max_length=100)
    status: TaskStatusLiteral | None = Field(default=None)
    created_from: datetime | None = Field(default=None)
    created_to: datetime | None = Field(default=None)


class TaskResponse(BaseModel):
    task: TaskPublic


class TasksListResponse(OffsetPaginationMeta):
    items: list[TaskPublic]
