"""Admin-only routes for system management."""

import logging
import os
import platform
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.db.models import (
    User,
    Project,
    Content,
    AuditLog,
    UsageRecord,
    get_db,
)
from backend.core.pagination import (
    PaginationParams,
    SearchFilter,
    paginate_query,
    search_query,
)
from backend.api.routes import require_auth

logger = logging.getLogger("ai_content_os.admin")

router = APIRouter(prefix="/admin", tags=["admin"])


async def require_admin(user=Depends(require_auth)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


class RoleUpdateRequest(BaseModel):
    role: str = Field(..., pattern="^(admin|member|viewer)$")


class AuditLogFilter(BaseModel):
    user_id: Optional[str] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None


@router.get("/stats")
async def get_system_stats(
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = (
        db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0
    )
    total_projects = db.query(func.count(Project.id)).scalar() or 0
    total_content = db.query(func.count(Content.id)).scalar() or 0
    published_content = (
        db.query(func.count(Content.id)).filter(Content.status == "published").scalar()
        or 0
    )
    total_api_calls = db.query(func.count(UsageRecord.id)).scalar() or 0
    total_tokens = db.query(func.sum(UsageRecord.total_tokens)).scalar() or 0
    total_cost = db.query(func.sum(UsageRecord.cost_usd)).scalar() or 0.0

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "inactive": total_users - active_users,
        },
        "projects": {
            "total": total_projects,
        },
        "content": {
            "total": total_content,
            "published": published_content,
            "draft": total_content - published_content,
        },
        "api_usage": {
            "total_calls": total_api_calls,
            "total_tokens": total_tokens,
            "total_cost_usd": round(float(total_cost), 4),
        },
    }


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    pagination = PaginationParams(page=page, page_size=page_size)
    query = db.query(User)

    if search:
        search_filter = SearchFilter(query=search)
        query = search_query(query, search_filter, ["email", "name"], model=User)

    if role:
        query = query.filter(User.role == role)

    result = paginate_query(query, pagination, model=User)
    result["items"] = [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "last_login": u.updated_at.isoformat() if u.updated_at else None,
        }
        for u in result["items"]
    ]
    return result


@router.put("/users/{user_id}/role")
async def change_user_role(
    user_id: str,
    request: RoleUpdateRequest,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    old_role = user.role
    user.role = request.role
    db.commit()

    audit = AuditLog(
        user_id=admin.id,
        action="role_changed",
        resource_type="user",
        resource_id=user_id,
        details={"old_role": old_role, "new_role": request.role},
    )
    db.add(audit)
    db.commit()

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "message": f"Role updated from '{old_role}' to '{request.role}'",
    }


@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: str,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    if user_id == admin.id:
        raise HTTPException(
            status_code=400, detail="Cannot deactivate your own account"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    db.commit()

    audit = AuditLog(
        user_id=admin.id,
        action="user_deactivated",
        resource_type="user",
        resource_id=user_id,
        details={"email": user.email},
    )
    db.add(audit)
    db.commit()

    return {"message": f"User '{user.email}' has been deactivated", "id": user.id}


@router.get("/audit-log")
async def get_audit_log(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    pagination = PaginationParams(
        page=page,
        page_size=page_size,
        sort_by="created_at",
        sort_order="desc",
    )
    query = db.query(AuditLog)

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)

    search_filter = SearchFilter(date_from=date_from, date_to=date_to)
    query = search_query(query, search_filter, [], model=AuditLog)

    result = paginate_query(query, pagination, model=AuditLog)
    result["items"] = [
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in result["items"]
    ]
    return result


@router.get("/system/health")
async def system_health(
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    db_status = "healthy"
    db_latency_ms = 0.0
    try:
        start = datetime.now(timezone.utc)
        db.execute(func.now())
        db_latency_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
    except Exception as exc:
        db_status = f"unhealthy: {exc}"

    disk_usage: Dict[str, Any] = {}
    try:
        import shutil

        total, used, free = shutil.disk_usage(os.getcwd())
        disk_usage = {
            "workspace": {
                "total_bytes": total,
                "used_bytes": used,
                "free_bytes": free,
                "used_percent": round((used / total) * 100, 2) if total > 0 else 0,
            }
        }
    except (OSError, AttributeError):
        disk_usage = {"error": "Unable to retrieve disk usage"}

    memory_info: Dict[str, Any] = {}
    try:
        import psutil

        mem = psutil.virtual_memory()
        memory_info = {
            "total_bytes": mem.total,
            "available_bytes": mem.available,
            "used_bytes": mem.used,
            "used_percent": mem.percent,
        }
    except ImportError:
        memory_info = {
            "error": "psutil not installed",
            "platform": platform.platform(),
            "python_version": platform.python_version(),
        }

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": {
            "status": db_status,
            "latency_ms": round(db_latency_ms, 2),
        },
        "disk": disk_usage,
        "memory": memory_info,
        "system": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
        },
    }
