"""Pagination, search, and filtering utilities for AI Content OS."""

import math
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Query

ModelType = TypeVar("ModelType")


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(default=None, description="Field to sort by")
    sort_order: str = Field(
        default="desc", pattern="^(asc|desc)$", description="Sort direction"
    )


class PaginatedResponse(BaseModel, Generic[ModelType]):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class SearchFilter(BaseModel):
    query: Optional[str] = Field(default=None, description="Full-text search query")
    filters: Dict[str, Any] = Field(
        default_factory=dict, description="Field-specific filters"
    )
    date_from: Optional[datetime] = Field(default=None, description="Start date filter")
    date_to: Optional[datetime] = Field(default=None, description="End date filter")


def paginate_query(
    query: Query,
    pagination: PaginationParams,
    model: Optional[Type] = None,
) -> Dict[str, Any]:
    """Apply pagination and sorting to a SQLAlchemy query.

    Returns a dict compatible with PaginatedResponse construction.
    """
    count_query = query
    total = count_query.count()

    total_pages = max(1, math.ceil(total / pagination.page_size))
    offset = (pagination.page - 1) * pagination.page_size

    if pagination.sort_by:
        sort_column = getattr(model, pagination.sort_by, None) if model else None
        if sort_column is not None:
            if pagination.sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            try:
                col = getattr(model, pagination.sort_by, None)
                if col is not None:
                    order = col.desc() if pagination.sort_order == "desc" else col.asc()
                    query = query.order_by(order)
            except AttributeError:
                pass

    items = query.offset(offset).limit(pagination.page_size).all()

    return {
        "items": items,
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "total_pages": total_pages,
        "has_next": pagination.page < total_pages,
        "has_prev": pagination.page > 1,
    }


def search_query(
    query: Query,
    search_filter: SearchFilter,
    search_fields: List[str],
    model: Optional[Type] = None,
) -> Query:
    """Apply text search and filters to a SQLAlchemy query.

    Args:
        query: The base SQLAlchemy query.
        search_filter: Search/filter parameters.
        search_fields: List of model field names to search across.
        model: The SQLAlchemy model class (used for column resolution).

    Returns:
        The filtered query.
    """
    if search_filter.query and model:
        search_term = f"%{search_filter.query}%"
        conditions = []
        for field_name in search_fields:
            column = getattr(model, field_name, None)
            if column is not None:
                conditions.append(column.ilike(search_term))
        if conditions:
            query = query.filter(or_(*conditions))

    if search_filter.filters and model:
        for field_name, value in search_filter.filters.items():
            if value is None:
                continue
            column = getattr(model, field_name, None)
            if column is not None:
                if isinstance(value, list):
                    query = query.filter(column.in_(value))
                else:
                    query = query.filter(column == value)

    if search_filter.date_from:
        timestamp_col = getattr(model, "created_at", None)
        if timestamp_col is not None:
            query = query.filter(timestamp_col >= search_filter.date_from)

    if search_filter.date_to:
        timestamp_col = getattr(model, "created_at", None)
        if timestamp_col is not None:
            query = query.filter(timestamp_col <= search_filter.date_to)

    return query
