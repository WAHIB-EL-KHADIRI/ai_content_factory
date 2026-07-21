"""API routes for AI Content OS"""

import json
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, Depends, Body, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db.models import get_db
from backend.core.config import get_config
from backend.core.auth import (
    create_access_token, decode_access_token, authenticate_user,
    create_user, generate_api_key
)
from backend.services.model_router import ModelRouter, TaskType
from backend.services.content import ContentService
from backend.services.brand import BrandService
from backend.services.memory import MemoryService
from backend.analytics.engine import AnalyticsEngine
from backend.agents.router import AgentRouter, AgentRole
from backend.workflows.engine import Workflow, get_workflow_engine
from backend.workflows.builder import WorkflowBuilder
from backend.plugins.base import PluginRegistry

router = APIRouter()


# --- Auth Dependencies ---


async def require_auth(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    from backend.db.models import User
    user = db.query(User).filter(User.id == user_id, User.is_active).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


# --- Auth Request Models ---


class RegisterRequest(BaseModel):
    email: str
    name: str
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class APIKeyCreateRequest(BaseModel):
    name: str


# --- Request/Response Models ---


class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    model: Optional[str] = None
    task_type: str = "chat"
    temperature: float = 0.7
    max_tokens: int = 2000
    stream: bool = False


class ContentCreateRequest(BaseModel):
    project_id: str
    topic: str
    content_type: str = "article"
    brand_id: Optional[str] = None
    language: str = "en"
    word_count: int = 1500
    extra_instructions: str = ""


class ContentEditRequest(BaseModel):
    content_id: str
    instructions: str
    edit_type: str = "comprehensive"


class ContentReviewRequest(BaseModel):
    content_id: str
    review_type: str = "comprehensive"


class SEORequest(BaseModel):
    content_id: Optional[str] = None
    content: Optional[str] = None
    action: str = "analyze"
    keywords: List[str] = []


class TranslateRequest(BaseModel):
    content_id: str
    target_language: str


class BrandCreateRequest(BaseModel):
    project_id: str
    name: str
    description: str = ""
    voice_tone: str = "professional"
    target_audience: str = ""
    keywords: List[str] = []
    color_palette: List[str] = []
    guidelines: str = ""


class WorkflowCreateRequest(BaseModel):
    name: str
    steps: List[Dict[str, Any]]
    variables: Dict[str, Any] = {}


class WorkflowRunRequest(BaseModel):
    workflow_id: str
    context: Dict[str, Any] = {}


class AgentTaskRequest(BaseModel):
    agent_role: str
    task: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None


class MemoryStoreRequest(BaseModel):
    content: str
    memory_type: str
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    brand_id: Optional[str] = None
    importance: float = 0.5


class MemoryRecallRequest(BaseModel):
    query: str
    memory_type: Optional[str] = None
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    limit: int = 10


# --- Chat & Model Routes ---


@router.post("/chat")
async def chat(request: ChatRequest):
    router_model = ModelRouter()
    task_type = TaskType(request.task_type) if request.task_type in [t.value for t in TaskType] else TaskType.CHAT

    if request.stream:
        async def event_generator():
            async for event in router_model.chat_stream(
                task_type=task_type,
                messages=request.messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ):
                yield f"data: {json.dumps(event)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    result = router_model.chat(
        task_type=task_type,
        messages=request.messages,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )
    return result


@router.get("/models")
async def list_models():
    from backend.services.model_router import MODELS, TASK_MODEL_PREFERENCES
    return {
        "models": {
            k: {
                "provider": v.provider,
                "model": v.model,
                "tier": v.tier.value,
                "cost_per_1k_input": v.cost_per_1k_input,
                "cost_per_1k_output": v.cost_per_1k_output,
                "max_tokens": v.max_tokens,
                "supports_vision": v.supports_vision,
                "quality_rating": v.quality_rating,
                "latency_rating": v.latency_rating,
            }
            for k, v in MODELS.items()
        },
        "task_preferences": {
            k.value: v for k, v in TASK_MODEL_PREFERENCES.items()
        },
    }


@router.get("/models/estimate-cost")
async def estimate_cost(task_type: str, input_tokens: int = 1000, output_tokens: int = 500):
    router_model = ModelRouter()
    return router_model.estimate_cost(
        TaskType(task_type) if task_type in [t.value for t in TaskType] else TaskType.CHAT,
        input_tokens, output_tokens
    )


@router.get("/models/usage")
async def model_usage():
    router_model = ModelRouter()
    return router_model.get_usage_stats()


# --- Auth Routes ---


@router.post("/auth/register")
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    user = create_user(db, request.email, request.name, request.password)
    if not user:
        raise HTTPException(status_code=409, detail="Email already registered")
    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role,
        },
    }


@router.post("/auth/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, request.email, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role,
        },
    }


@router.get("/auth/me")
async def get_me(user=Depends(require_auth)):
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.post("/auth/change-password")
async def change_password(request: ChangePasswordRequest,
                          user=Depends(require_auth),
                          db: Session = Depends(get_db)):
    from backend.core.auth import verify_password, hash_password
    if not verify_password(request.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.hashed_password = hash_password(request.new_password)
    db.commit()
    return {"message": "Password changed successfully"}


# --- API Key Routes ---


@router.post("/api-keys")
async def create_api_key(request: APIKeyCreateRequest,
                         user=Depends(require_auth),
                         db: Session = Depends(get_db)):
    from backend.db.models import APIKey
    raw_key, key_with_prefix, key_hash = generate_api_key()
    api_key = APIKey(
        name=request.name,
        key_hash=key_hash,
        key_prefix=key_with_prefix[:12],
        user_id=user.id,
        is_active=True,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return {
        "id": str(api_key.id),
        "name": api_key.name,
        "key": key_with_prefix,
        "prefix": api_key.key_prefix,
        "message": "Save this key - it won't be shown again",
    }


@router.get("/api-keys")
async def list_api_keys(user=Depends(require_auth), db: Session = Depends(get_db)):
    from backend.db.models import APIKey
    keys = db.query(APIKey).filter(APIKey.user_id == user.id).all()
    return {
        "api_keys": [
            {
                "id": str(k.id),
                "name": k.name,
                "prefix": k.key_prefix,
                "is_active": k.is_active,
                "created_at": k.created_at.isoformat() if k.created_at else None,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            }
            for k in keys
        ]
    }


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: str, user=Depends(require_auth),
                         db: Session = Depends(get_db)):
    from backend.db.models import APIKey
    key = db.query(APIKey).filter(APIKey.id == key_id, APIKey.user_id == user.id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    key.is_active = False
    db.commit()
    return {"message": "API key revoked"}


# --- Agent Routes ---


@router.get("/agents")
async def list_agents():
    agent_router = AgentRouter()
    return {"agents": agent_router.list_agents()}


@router.post("/agents/run")
async def run_agent(request: AgentTaskRequest):
    agent_router = AgentRouter()
    try:
        role = AgentRole(request.agent_role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid agent role: {request.agent_role}")

    result = await agent_router.run_single(role, request.task, request.context)
    return result.to_dict()


@router.post("/agents/pipeline")
async def run_content_pipeline(request: ContentCreateRequest):
    agent_router = AgentRouter()
    brand_service = BrandService()

    brand_context = None
    if request.brand_id:
        brand_context = brand_service.get_brand_context(request.brand_id)

    result = await agent_router.run_content_pipeline(
        topic=request.topic,
        content_type=request.content_type,
        brand=brand_context,
        language=request.language,
    )
    return result


# --- Content Routes ---


@router.post("/content")
async def create_content(request: ContentCreateRequest):
    content_service = ContentService(model_router=ModelRouter())

    result = await content_service.create_content(
        project_id=request.project_id,
        topic=request.topic,
        content_type=request.content_type,
        brand_id=request.brand_id,
        language=request.language,
        word_count=request.word_count,
        extra_instructions=request.extra_instructions,
    )
    return result


@router.post("/content/edit")
async def edit_content(request: ContentEditRequest):
    content_service = ContentService(model_router=ModelRouter())
    result = await content_service.edit_content(
        content_id=request.content_id,
        instructions=request.instructions,
        edit_type=request.edit_type,
    )
    return result


@router.post("/content/review")
async def review_content(request: ContentReviewRequest):
    content_service = ContentService(model_router=ModelRouter())
    result = await content_service.review_content(
        content_id=request.content_id,
        review_type=request.review_type,
    )
    return result


@router.post("/content/seo")
async def optimize_seo(request: SEORequest):
    content_service = ContentService(model_router=ModelRouter())

    if request.content_id:
        result = await content_service.optimize_seo(
            content_id=request.content_id,
            keywords=request.keywords,
        )
        return result
    elif request.content:
        seo_agent = AgentRouter()
        result = await seo_agent.run_single(
            role=AgentRole.SEO,
            task={
                "action": request.action,
                "content": request.content,
                "keywords": request.keywords,
            },
        )
        return result.to_dict()
    else:
        raise HTTPException(status_code=400, detail="Either content_id or content is required")


@router.post("/content/translate")
async def translate_content(request: TranslateRequest):
    content_service = ContentService(model_router=ModelRouter())
    result = await content_service.translate_content(
        content_id=request.content_id,
        target_language=request.target_language,
    )
    return result


@router.get("/content/{content_id}")
async def get_content(content_id: str):
    content_service = ContentService()
    content = content_service.get_content(content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content


@router.get("/content")
async def list_content(project_id: str, content_type: Optional[str] = None,
                       status: Optional[str] = None):
    content_service = ContentService()
    return content_service.list_content(project_id, content_type, status)


# --- Brand Routes ---


@router.post("/brands")
async def create_brand(request: BrandCreateRequest):
    brand_service = BrandService()
    return brand_service.create_brand(
        project_id=request.project_id,
        data=request.model_dump(exclude={"project_id"}),
    )


@router.get("/brands/{brand_id}")
async def get_brand(brand_id: str):
    brand_service = BrandService()
    brand = brand_service.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand


@router.put("/brands/{brand_id}")
async def update_brand(brand_id: str, data: Dict[str, Any] = Body(...)):
    brand_service = BrandService()
    brand = brand_service.update_brand(brand_id, data)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand


@router.get("/brands/project/{project_id}")
async def get_project_brands(project_id: str):
    brand_service = BrandService()
    return brand_service.get_project_brands(project_id)


@router.post("/brands/{brand_id}/analyze")
async def analyze_brand(brand_id: str, content: str = Body(..., embed=True)):
    brand_service = BrandService()
    return brand_service.analyze_brand_consistency(content, brand_id)


# --- Workflow Routes ---


@router.post("/workflows")
async def create_workflow(request: WorkflowCreateRequest):
    engine = get_workflow_engine()
    workflow = Workflow(
        name=request.name,
        steps=request.steps,
        variables=request.variables,
    )
    workflow_id = engine.register_workflow(workflow)
    return {"id": workflow_id, "name": workflow.name, "steps": len(workflow.steps)}


@router.post("/workflows/run")
async def run_workflow(request: WorkflowRunRequest):
    engine = get_workflow_engine()
    run = await engine.execute_workflow(request.workflow_id, request.context)
    return run.to_dict()


@router.get("/workflows")
async def list_workflows():
    engine = get_workflow_engine()
    return {"workflows": engine.list_workflows()}


@router.get("/workflows/{workflow_id}/runs")
async def list_workflow_runs(workflow_id: str):
    engine = get_workflow_engine()
    return {"runs": engine.list_runs(workflow_id)}


@router.post("/workflows/templates/article")
async def create_article_workflow(topic: str, brand: Optional[Dict[str, Any]] = None):
    engine = get_workflow_engine()
    workflow = WorkflowBuilder.create_article_workflow(topic, brand)
    workflow_id = engine.register_workflow(workflow)
    return {"id": workflow_id, "name": workflow.name}


@router.post("/workflows/templates/video")
async def create_video_workflow(topic: str):
    engine = get_workflow_engine()
    workflow = WorkflowBuilder.create_video_workflow(topic)
    workflow_id = engine.register_workflow(workflow)
    return {"id": workflow_id, "name": workflow.name}


@router.post("/workflows/templates/social")
async def create_social_workflow(topic: str, platforms: List[str] = ["twitter", "linkedin"]):
    engine = get_workflow_engine()
    workflow = WorkflowBuilder.create_social_media_batch(topic, platforms)
    workflow_id = engine.register_workflow(workflow)
    return {"id": workflow_id, "name": workflow.name}


# --- Memory Routes ---


@router.post("/memory/store")
async def store_memory(request: MemoryStoreRequest):
    memory_service = MemoryService()
    return memory_service.store(
        content=request.content,
        memory_type=request.memory_type,
        user_id=request.user_id,
        project_id=request.project_id,
        brand_id=request.brand_id,
        importance=request.importance,
    )


@router.post("/memory/recall")
async def recall_memory(request: MemoryRecallRequest):
    memory_service = MemoryService()
    return {
        "memories": memory_service.recall(
            query=request.query,
            memory_type=request.memory_type,
            user_id=request.user_id,
            project_id=request.project_id,
            limit=request.limit,
        )
    }


@router.get("/memory/context/user/{user_id}")
async def get_user_memory(user_id: str):
    memory_service = MemoryService()
    return memory_service.get_user_context(user_id)


@router.get("/memory/context/project/{project_id}")
async def get_project_memory(project_id: str):
    memory_service = MemoryService()
    return memory_service.get_project_context(project_id)


# --- Analytics Routes ---


@router.get("/analytics/dashboard")
async def get_dashboard(project_id: Optional[str] = None, hours: int = 24):
    analytics = AnalyticsEngine()
    return analytics.get_dashboard_data(project_id, hours)


@router.get("/analytics/usage")
async def get_usage(user_id: Optional[str] = None, project_id: Optional[str] = None):
    analytics = AnalyticsEngine()
    return analytics.get_usage_report(user_id, project_id)


@router.get("/analytics/costs")
async def get_costs(hours: int = 24):
    analytics = AnalyticsEngine()
    return analytics.collector.get_cost_breakdown(hours)


@router.get("/analytics/performance")
async def get_performance(hours: int = 24):
    analytics = AnalyticsEngine()
    return analytics.collector.get_performance_report(hours)


# --- Plugin Routes ---


@router.get("/plugins")
async def list_plugins():
    registry = PluginRegistry()
    return {"plugins": registry.list_plugins()}


# --- Video Routes ---


class VideoGenerateRequest(BaseModel):
    topic: str
    output_filename: Optional[str] = None
    mock: bool = False


class VideoScriptRequest(BaseModel):
    topic: str
    mock: bool = True


@router.get("/video/info")
async def video_pipeline_info():
    from backend.services.video import VideoService
    return VideoService().get_pipeline_info()


@router.get("/video/validate")
async def video_validate_config():
    from backend.services.video import VideoService
    return await VideoService().validate_config()


@router.post("/video/generate")
async def generate_video(request: VideoGenerateRequest):
    from backend.services.video import VideoService
    result = await VideoService().generate_video(
        topic=request.topic,
        output_filename=request.output_filename,
        mock=request.mock,
    )
    return result


@router.post("/video/script")
async def generate_video_script(request: VideoScriptRequest):
    from backend.services.video import VideoService
    result = await VideoService().generate_script_only(
        topic=request.topic,
        mock=request.mock,
    )
    return result


# --- RAG Studio Routes ---


class ResearchRequest(BaseModel):
    query: str
    num_results: int = 5
    model: Optional[str] = None


class DeepResearchRequest(BaseModel):
    query: str
    depth: int = 3


@router.post("/rag/research")
async def research_topic(request: ResearchRequest):
    from backend.services.rag import RAGStudio
    rag = RAGStudio()
    result = await rag.research(
        query=request.query,
        num_results=request.num_results,
        model=request.model,
    )
    return {
        "query": result.query,
        "summary": result.summary,
        "sources": [
            {"id": s.id, "title": s.title, "url": s.url, "snippet": s.snippet, "relevance": s.relevance}
            for s in result.sources
        ],
        "model_used": result.model_used,
        "latency_ms": result.latency_ms,
    }


@router.post("/rag/deep-research")
async def deep_research_topic(request: DeepResearchRequest):
    from backend.services.rag import RAGStudio
    rag = RAGStudio()
    return await rag.deep_research(
        query=request.query,
        depth=request.depth,
    )


# --- System Routes ---


@router.get("/system/health")
async def system_health():
    config = get_config()
    return {
        "status": "healthy",
        "version": config.version,
        "database": "connected",
        "config": {
            "model_provider": config.models.default_provider,
            "debug": config.debug,
        },
    }
