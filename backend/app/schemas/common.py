from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

StatusFilterLiteral = Literal["active", "disabled"]


class OffsetPaginationMeta(BaseModel):
    total: int = Field(..., ge=0, description="Total items count before pagination")
    limit: int = Field(..., ge=1, le=100, description="Requested page size")
    offset: int = Field(..., ge=0, description="Requested start offset")


class StandardListFilters(BaseModel):
    search: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Case-insensitive substring search",
    )
    status: StatusFilterLiteral | None = Field(
        default=None,
        description="Status filter",
    )
    created_from: datetime | None = Field(
        default=None,
        description="Include records created at or after this timestamp (UTC)",
    )
    created_to: datetime | None = Field(
        default=None,
        description="Include records created at or before this timestamp (UTC)",
    )
