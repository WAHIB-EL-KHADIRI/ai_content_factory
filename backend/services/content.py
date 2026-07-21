"""Content Service - manages content lifecycle"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from backend.agents.router import AgentRouter
from backend.services.brand import BrandService
from backend.services.memory import MemoryService

logger = logging.getLogger(__name__)


class ContentService:
    def __init__(self, db=None, model_router=None):
        self.db = db
        self.agent_router = AgentRouter(model_router=model_router)
        self.brand_service = BrandService(db=db)
        self.memory_service = MemoryService(db=db)

    async def create_content(self, project_id: str, topic: str,
                             content_type: str = "article",
                             brand_id: Optional[str] = None,
                             language: str = "en",
                             word_count: int = 1500,
                             extra_instructions: str = "") -> Dict[str, Any]:
        brand_context = None
        if brand_id:
            brand_context = self.brand_service.get_brand_context(brand_id)

        result = await self.agent_router.run_content_pipeline(
            topic=topic,
            content_type=content_type,
            brand=brand_context,
            language=language,
        )

        content_data = result.get("steps", {}).get("editing", {}).get("data", {})
        edited_content = content_data.get("edited_content", "")

        content_record = {
            "project_id": project_id,
            "title": content_data.get("title", topic),
            "content_type": content_type,
            "body": edited_content,
            "status": "draft",
            "word_count": len(edited_content.split()),
            "language": language,
            "brand_id": brand_id,
            "metadata_": {
                "topic": topic,
                "pipeline_result": {
                    "quality_score": result.get("quality_score", 0),
                    "total_cost": result.get("total_cost_usd", 0),
                    "total_tokens": result.get("total_tokens", 0),
                },
            },
        }

        if self.db:
            from backend.db.models import Content
            db_content = Content(**content_record)
            self.db.add(db_content)
            self.db.commit()
            self.db.refresh(db_content)
            content_record["id"] = db_content.id

            self._create_revision(db_content.id, edited_content, "Initial creation")
        else:
            content_record["id"] = f"content_{project_id}_{topic[:20]}"

        self.memory_service.store(
            content=f"Created {content_type} about {topic}",
            memory_type="project_context",
            project_id=project_id,
            importance=0.6,
        )

        return {
            "content": content_record,
            "pipeline_result": result,
        }

    async def edit_content(self, content_id: str, instructions: str,
                           edit_type: str = "comprehensive") -> Dict[str, Any]:
        content = self._get_content(content_id)
        if not content:
            raise ValueError(f"Content not found: {content_id}")

        result = await self.agent_router.run_single(
            role="editor",
            task={
                "content": content.get("body", ""),
                "edit_type": edit_type,
                "instructions": instructions,
            },
            context={"brand": content.get("brand_context")},
        )

        if result.success:
            new_body = result.data.get("edited_content", content.get("body", ""))
            self._update_content(content_id, {"body": new_body})
            self._create_revision(content_id, new_body, instructions)

        return {
            "success": result.success,
            "data": result.data,
            "content_id": content_id,
        }

    async def review_content(self, content_id: str,
                             review_type: str = "comprehensive") -> Dict[str, Any]:
        content = self._get_content(content_id)
        if not content:
            raise ValueError(f"Content not found: {content_id}")

        result = await self.agent_router.run_single(
            role="reviewer",
            task={
                "content": content.get("body", ""),
                "review_type": review_type,
            },
        )

        return {
            "success": result.success,
            "review": result.data,
            "content_id": content_id,
        }

    async def optimize_seo(self, content_id: str,
                           keywords: Optional[List[str]] = None) -> Dict[str, Any]:
        content = self._get_content(content_id)
        if not content:
            raise ValueError(f"Content not found: {content_id}")

        result = await self.agent_router.run_single(
            role="seo",
            task={
                "action": "optimize",
                "content": content.get("body", ""),
                "keywords": keywords or [],
            },
        )

        if result.success:
            optimized = result.data.get("optimized_content", "")
            if optimized:
                self._update_content(content_id, {"body": optimized})

        return {
            "success": result.success,
            "data": result.data,
            "content_id": content_id,
        }

    async def translate_content(self, content_id: str,
                                target_language: str) -> Dict[str, Any]:
        content = self._get_content(content_id)
        if not content:
            raise ValueError(f"Content not found: {content_id}")

        result = await self.agent_router.run_single(
            role="translator",
            task={
                "content": content.get("body", ""),
                "target_language": target_language,
                "source_language": content.get("language", "en"),
            },
        )

        return {
            "success": result.success,
            "data": result.data,
            "content_id": content_id,
            "target_language": target_language,
        }

    async def generate_visuals(self, content_id: str) -> Dict[str, Any]:
        content = self._get_content(content_id)
        if not content:
            raise ValueError(f"Content not found: {content_id}")

        result = await self.agent_router.run_single(
            role="designer",
            task={
                "design_type": "image_prompt",
                "content": content.get("body", "")[:2000],
            },
        )

        return {
            "success": result.success,
            "data": result.data,
            "content_id": content_id,
        }

    async def publish_content(self, content_id: str,
                              platforms: List[str]) -> Dict[str, Any]:
        content = self._get_content(content_id)
        if not content:
            raise ValueError(f"Content not found: {content_id}")

        result = await self.agent_router.run_single(
            role="publisher",
            task={
                "action": "format",
                "content": content.get("body", ""),
                "platforms": platforms,
            },
        )

        if result.success:
            self._update_content(content_id, {
                "status": "published",
                "published_at": datetime.now(timezone.utc).isoformat(),
            })

        return {
            "success": result.success,
            "data": result.data,
            "content_id": content_id,
        }

    def _get_content(self, content_id: str) -> Optional[Dict[str, Any]]:
        if self.db:
            from backend.db.models import Content
            content = self.db.query(Content).filter(Content.id == content_id).first()
            if content:
                brand_context = None
                if content.brand_id:
                    brand_context = self.brand_service.get_brand_context(content.brand_id)
                return {
                    "id": content.id,
                    "title": content.title,
                    "body": content.body,
                    "content_type": content.content_type,
                    "status": content.status,
                    "language": content.language,
                    "brand_id": content.brand_id,
                    "brand_context": brand_context,
                }
        return None

    def _update_content(self, content_id: str, data: Dict[str, Any]) -> bool:
        if self.db:
            from backend.db.models import Content
            content = self.db.query(Content).filter(Content.id == content_id).first()
            if content:
                for key, value in data.items():
                    if hasattr(content, key):
                        setattr(content, key, value)
                self.db.commit()
                return True
        return False

    def _create_revision(self, content_id: str, body: str, change_summary: str):
        if self.db:
            from backend.db.models import ContentRevision
            latest = self.db.query(ContentRevision).filter(
                ContentRevision.content_id == content_id
            ).order_by(ContentRevision.version.desc()).first()

            version = (latest.version + 1) if latest else 1

            revision = ContentRevision(
                content_id=content_id,
                version=version,
                title="",
                body=body,
                change_summary=change_summary,
            )
            self.db.add(revision)
            self.db.commit()

    def list_content(self, project_id: str, content_type: Optional[str] = None,
                     status: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.db:
            from backend.db.models import Content
            query = self.db.query(Content).filter(Content.project_id == project_id)
            if content_type:
                query = query.filter(Content.content_type == content_type)
            if status:
                query = query.filter(Content.status == status)

            contents = query.all()
            return [
                {
                    "id": c.id,
                    "title": c.title,
                    "content_type": c.content_type,
                    "status": c.status,
                    "word_count": c.word_count,
                    "language": c.language,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                }
                for c in contents
            ]
        return []

    def get_content(self, content_id: str) -> Optional[Dict[str, Any]]:
        return self._get_content(content_id)
