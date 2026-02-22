from pydantic import BaseModel, Field

from app.schemas.task import TaskPublic


class TaskStatusCounts(BaseModel):
    open: int = Field(default=0, ge=0)
    in_progress: int = Field(default=0, ge=0)
    blocked: int = Field(default=0, ge=0)
    done: int = Field(default=0, ge=0)


class DashboardSummaryResponse(BaseModel):
    org_id: str = Field(..., examples=["org-acme"])
    total_tasks: int = Field(..., ge=0)
    counts: TaskStatusCounts
    recent_tasks: list[TaskPublic]
