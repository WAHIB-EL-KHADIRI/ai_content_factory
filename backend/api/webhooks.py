"""Webhook management routes for event notifications."""

import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl

from backend.api.routes import require_auth

logger = logging.getLogger("ai_content_os.webhooks")

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

VALID_EVENTS = {
    "content.created",
    "content.published",
    "workflow.completed",
    "agent.task_completed",
}

_in_memory_webhooks: Dict[str, Dict[str, Any]] = {}
_in_memory_deliveries: Dict[str, List[Dict[str, Any]]] = {}
_delivery_counter = 0


class WebhookCreateRequest(BaseModel):
    url: HttpUrl
    events: List[str] = Field(..., min_length=1, description="Events to subscribe to")
    secret: Optional[str] = Field(
        default=None, description="Secret for signature verification"
    )
    description: str = ""
    is_active: bool = True


class WebhookUpdateRequest(BaseModel):
    url: Optional[HttpUrl] = None
    events: Optional[List[str]] = None
    secret: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


def _validate_events(events: List[str]) -> None:
    invalid = set(events) - VALID_EVENTS
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid events: {', '.join(sorted(invalid))}. "
            f"Valid events: {', '.join(sorted(VALID_EVENTS))}",
        )


def _compute_signature(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def _get_user_id(user) -> str:
    return str(user.id)


@router.post("", status_code=201)
async def create_webhook(
    request: WebhookCreateRequest,
    user=Depends(require_auth),
):
    _validate_events(request.events)

    webhook_id = secrets.token_urlsafe(16)
    secret = request.secret or secrets.token_urlsafe(32)

    webhook = {
        "id": webhook_id,
        "user_id": _get_user_id(user),
        "url": str(request.url),
        "events": request.events,
        "secret": secret,
        "description": request.description,
        "is_active": request.is_active,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "delivery_count": 0,
    }
    _in_memory_webhooks[webhook_id] = webhook
    _in_memory_deliveries[webhook_id] = []

    logger.info("Webhook created: %s by user %s", webhook_id, _get_user_id(user))

    return {
        "id": webhook_id,
        "url": webhook["url"],
        "events": webhook["events"],
        "secret": secret,
        "description": webhook["description"],
        "is_active": webhook["is_active"],
        "created_at": webhook["created_at"],
        "message": "Webhook created. Store the secret securely - it won't be shown again.",
    }


@router.get("")
async def list_webhooks(
    user=Depends(require_auth),
):
    user_id = _get_user_id(user)
    webhooks = [
        {
            "id": wh["id"],
            "url": wh["url"],
            "events": wh["events"],
            "description": wh["description"],
            "is_active": wh["is_active"],
            "created_at": wh["created_at"],
            "updated_at": wh["updated_at"],
            "delivery_count": wh["delivery_count"],
        }
        for wh in _in_memory_webhooks.values()
        if wh["user_id"] == user_id
    ]
    return {"webhooks": webhooks, "total": len(webhooks)}


@router.get("/{webhook_id}")
async def get_webhook(
    webhook_id: str,
    user=Depends(require_auth),
):
    webhook = _in_memory_webhooks.get(webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    if webhook["user_id"] != _get_user_id(user):
        raise HTTPException(status_code=404, detail="Webhook not found")

    return {
        "id": webhook["id"],
        "url": webhook["url"],
        "events": webhook["events"],
        "description": webhook["description"],
        "is_active": webhook["is_active"],
        "created_at": webhook["created_at"],
        "updated_at": webhook["updated_at"],
        "delivery_count": webhook["delivery_count"],
    }


@router.put("/{webhook_id}")
async def update_webhook(
    webhook_id: str,
    request: WebhookUpdateRequest,
    user=Depends(require_auth),
):
    webhook = _in_memory_webhooks.get(webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    if webhook["user_id"] != _get_user_id(user):
        raise HTTPException(status_code=404, detail="Webhook not found")

    if request.events is not None:
        _validate_events(request.events)
        webhook["events"] = request.events
    if request.url is not None:
        webhook["url"] = str(request.url)
    if request.secret is not None:
        webhook["secret"] = request.secret
    if request.description is not None:
        webhook["description"] = request.description
    if request.is_active is not None:
        webhook["is_active"] = request.is_active

    webhook["updated_at"] = datetime.now(timezone.utc).isoformat()

    return {
        "id": webhook["id"],
        "url": webhook["url"],
        "events": webhook["events"],
        "description": webhook["description"],
        "is_active": webhook["is_active"],
        "created_at": webhook["created_at"],
        "updated_at": webhook["updated_at"],
    }


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    user=Depends(require_auth),
):
    webhook = _in_memory_webhooks.get(webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    if webhook["user_id"] != _get_user_id(user):
        raise HTTPException(status_code=404, detail="Webhook not found")

    del _in_memory_webhooks[webhook_id]
    _in_memory_deliveries.pop(webhook_id, None)

    return {"message": "Webhook deleted", "id": webhook_id}


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    user=Depends(require_auth),
):
    webhook = _in_memory_webhooks.get(webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    if webhook["user_id"] != _get_user_id(user):
        raise HTTPException(status_code=404, detail="Webhook not found")

    sample_payload = {
        "event": "content.created",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "content_id": "test-content-001",
            "title": "Test Content",
            "content_type": "article",
            "status": "draft",
            "project_id": "test-project-001",
        },
    }

    delivery = await _deliver_webhook(webhook, "content.created", sample_payload)
    return delivery


@router.get("/{webhook_id}/deliveries")
async def get_deliveries(
    webhook_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    user=Depends(require_auth),
):
    webhook = _in_memory_webhooks.get(webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    if webhook["user_id"] != _get_user_id(user):
        raise HTTPException(status_code=404, detail="Webhook not found")

    deliveries = _in_memory_deliveries.get(webhook_id, [])

    if status:
        deliveries = [d for d in deliveries if d["status"] == status]

    deliveries = sorted(deliveries, key=lambda d: d["delivered_at"], reverse=True)

    total = len(deliveries)
    start = (page - 1) * page_size
    end = start + page_size
    items = deliveries[start:end]
    total_pages = max(1, -(-total // page_size))

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }


async def _deliver_webhook(
    webhook: Dict[str, Any],
    event: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    global _delivery_counter
    _delivery_counter += 1
    delivery_id = f"del_{_delivery_counter:08d}"

    body = json.dumps(payload, default=str).encode()
    signature = _compute_signature(body, webhook["secret"])
    timestamp = datetime.now(timezone.utc).isoformat()

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": f"sha256={signature}",
        "X-Webhook-Event": event,
        "X-Webhook-Delivery": delivery_id,
        "User-Agent": "AIContentOS-Webhook/1.0",
    }

    status_code = None
    response_body = ""
    delivery_status = "success"
    error_message = None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook["url"],
                content=body,
                headers=headers,
            )
            status_code = response.status_code
            response_body = response.text[:500]
            if status_code >= 400:
                delivery_status = "failed"
    except httpx.TimeoutException:
        delivery_status = "failed"
        error_message = "Request timed out"
    except httpx.RequestError as exc:
        delivery_status = "failed"
        error_message = str(exc)

    delivery = {
        "id": delivery_id,
        "webhook_id": webhook["id"],
        "event": event,
        "status": delivery_status,
        "status_code": status_code,
        "response_body": response_body,
        "error": error_message,
        "payload": payload,
        "delivered_at": timestamp,
    }

    _in_memory_deliveries.setdefault(webhook["id"], []).append(delivery)
    webhook["delivery_count"] = webhook.get("delivery_count", 0) + 1

    if delivery_status == "success":
        logger.info(
            "Webhook %s delivered: %s -> %d", delivery_id, event, status_code or 0
        )
    else:
        logger.warning("Webhook %s failed: %s -> %s", delivery_id, event, error_message)

    return delivery


async def fire_event(event: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fire a webhook event to all matching webhooks.

    Call this from application code when an event occurs.
    """
    if event not in VALID_EVENTS:
        logger.warning("Invalid webhook event: %s", event)
        return []

    payload = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }

    results = []
    for webhook in _in_memory_webhooks.values():
        if not webhook["is_active"]:
            continue
        if event not in webhook["events"]:
            continue
        delivery = await _deliver_webhook(webhook, event, payload)
        results.append(delivery)

    return results
