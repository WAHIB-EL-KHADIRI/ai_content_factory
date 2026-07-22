"""Memory System - long-term memory for users, projects, and brands"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class MemoryType(str):
    USER_PREFERENCE = "user_preference"
    PROJECT_CONTEXT = "project_context"
    BRAND_LEARNING = "brand_learning"
    CONTENT_FEEDBACK = "content_feedback"
    INTERACTION_HISTORY = "interaction_history"
    FACTUAL_KNOWLEDGE = "factual_knowledge"
    CREATIVE_PATTERN = "creative_pattern"


class MemoryService:
    def __init__(self, db=None):
        self.db = db
        self._memories: List[Dict[str, Any]] = []

    def store(
        self,
        content: str,
        memory_type: str,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        brand_id: Optional[str] = None,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        memory = {
            "id": f"mem_{len(self._memories) + 1}",
            "content": content,
            "memory_type": memory_type,
            "user_id": user_id,
            "project_id": project_id,
            "brand_id": brand_id,
            "importance": importance,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "access_count": 0,
        }

        if self.db:
            from backend.db.models import Memory as MemoryModel

            db_memory = MemoryModel(
                content=content,
                memory_type=memory_type,
                user_id=user_id,
                project_id=project_id,
                brand_id=brand_id,
                importance=importance,
                metadata_=metadata or {},
            )
            self.db.add(db_memory)
            self.db.commit()
            self.db.refresh(db_memory)
            memory["id"] = db_memory.id

        self._memories.append(memory)
        return memory

    def recall(
        self,
        query: str,
        memory_type: Optional[str] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        brand_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        results = []

        if self.db:
            from backend.db.models import Memory as MemoryModel

            db_query = self.db.query(MemoryModel)
            if memory_type:
                db_query = db_query.filter(MemoryModel.memory_type == memory_type)
            if user_id:
                db_query = db_query.filter(MemoryModel.user_id == user_id)
            if project_id:
                db_query = db_query.filter(MemoryModel.project_id == project_id)
            if brand_id:
                db_query = db_query.filter(MemoryModel.brand_id == brand_id)

            memories = (
                db_query.order_by(MemoryModel.importance.desc()).limit(limit).all()
            )

            for mem in memories:
                relevance = self._calculate_relevance(query, mem.content)
                if relevance > 0.1:
                    results.append(
                        {
                            "id": mem.id,
                            "content": mem.content,
                            "memory_type": mem.memory_type,
                            "importance": mem.importance,
                            "relevance": relevance,
                            "metadata": mem.metadata_ or {},
                        }
                    )
        else:
            for mem in self._memories:
                if memory_type and mem["memory_type"] != memory_type:
                    continue
                if user_id and mem.get("user_id") != user_id:
                    continue
                if project_id and mem.get("project_id") != project_id:
                    continue
                if brand_id and mem.get("brand_id") != brand_id:
                    continue

                relevance = self._calculate_relevance(query, mem["content"])
                if relevance > 0.1:
                    results.append({**mem, "relevance": relevance})

        results.sort(
            key=lambda x: x.get("relevance", 0) * x.get("importance", 0.5), reverse=True
        )
        return results[:limit]

    def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        importance: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        if self.db:
            from backend.db.models import Memory as MemoryModel

            mem = self.db.query(MemoryModel).filter(MemoryModel.id == memory_id).first()
            if mem:
                if content is not None:
                    mem.content = content
                if importance is not None:
                    mem.importance = importance
                if metadata is not None:
                    mem.metadata_ = metadata
                self.db.commit()
                return True

        for mem in self._memories:
            if mem["id"] == memory_id:
                if content is not None:
                    mem["content"] = content
                if importance is not None:
                    mem["importance"] = importance
                if metadata is not None:
                    mem["metadata"] = metadata
                return True
        return False

    def delete_memory(self, memory_id: str) -> bool:
        if self.db:
            from backend.db.models import Memory as MemoryModel

            mem = self.db.query(MemoryModel).filter(MemoryModel.id == memory_id).first()
            if mem:
                self.db.delete(mem)
                self.db.commit()
                return True

        for i, mem in enumerate(self._memories):
            if mem["id"] == memory_id:
                self._memories.pop(i)
                return True
        return False

    def get_user_context(self, user_id: str) -> Dict[str, Any]:
        memories = self.recall("", user_id=user_id, limit=50)
        preferences = [
            m for m in memories if m["memory_type"] == MemoryType.USER_PREFERENCE
        ]
        history = [
            m for m in memories if m["memory_type"] == MemoryType.INTERACTION_HISTORY
        ]

        return {
            "preferences": [m["content"] for m in preferences],
            "recent_history": [m["content"] for m in history[:10]],
            "total_memories": len(memories),
        }

    def get_project_context(self, project_id: str) -> Dict[str, Any]:
        memories = self.recall("", project_id=project_id, limit=50)
        context = [
            m for m in memories if m["memory_type"] == MemoryType.PROJECT_CONTEXT
        ]
        facts = [
            m for m in memories if m["memory_type"] == MemoryType.FACTUAL_KNOWLEDGE
        ]

        return {
            "context": [m["content"] for m in context],
            "facts": [m["content"] for m in facts],
            "total_memories": len(memories),
        }

    def get_brand_context(self, brand_id: str) -> Dict[str, Any]:
        memories = self.recall("", brand_id=brand_id, limit=50)
        learnings = [
            m for m in memories if m["memory_type"] == MemoryType.BRAND_LEARNING
        ]
        patterns = [
            m for m in memories if m["memory_type"] == MemoryType.CREATIVE_PATTERN
        ]

        return {
            "learnings": [m["content"] for m in learnings],
            "patterns": [m["content"] for m in patterns],
            "total_memories": len(memories),
        }

    def _calculate_relevance(self, query: str, content: str) -> float:
        if not query:
            return 0.5

        query_words = set(query.lower().split())
        content_words = set(content.lower().split())

        if not query_words:
            return 0.5

        intersection = query_words & content_words
        return len(intersection) / len(query_words) if query_words else 0

    def summarize(
        self, user_id: Optional[str] = None, project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        memories = self.recall("", user_id=user_id, project_id=project_id, limit=1000)
        type_counts: Dict[str, int] = {}
        for m in memories:
            t = m["memory_type"]
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_memories": len(memories),
            "by_type": type_counts,
            "avg_importance": sum(m.get("importance", 0) for m in memories)
            / max(len(memories), 1),
        }
