"""Base agent class for the Multi-Agent system"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    RESEARCH = "research"
    WRITER = "writer"
    SEO = "seo"
    EDITOR = "editor"
    TRANSLATOR = "translator"
    DESIGNER = "designer"
    PUBLISHER = "publisher"
    REVIEWER = "reviewer"


@dataclass
class AgentResult:
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    agent_role: str = ""
    model_used: str = ""
    tokens_used: int = 0
    cost_usd: float = 0.0
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "agent_role": self.agent_role,
            "model_used": self.model_used,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
        }


class BaseAgent(ABC):
    role: AgentRole
    name: str
    description: str

    def __init__(self, model_router=None, config: Optional[Dict[str, Any]] = None):
        self.model_router = model_router
        self.config = config or {}
        self._tools: List[Dict[str, Any]] = []

    @abstractmethod
    async def execute(self, task: Dict[str, Any],
                      context: Optional[Dict[str, Any]] = None) -> AgentResult:
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        pass

    def register_tool(self, name: str, description: str, parameters: Dict[str, Any]):
        self._tools.append({
            "name": name,
            "description": description,
            "parameters": parameters,
        })

    def get_tools(self) -> List[Dict[str, Any]]:
        return self._tools.copy()

    def _build_messages(self, user_prompt: str,
                        context: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": self.get_system_prompt()}]

        if context:
            context_parts = []
            for key, value in context.items():
                if isinstance(value, str):
                    context_parts.append(f"{key}: {value}")
                else:
                    context_parts.append(f"{key}: {str(value)[:500]}")
            if context_parts:
                messages.append({
                    "role": "system",
                    "content": "Context:\n" + "\n".join(context_parts)
                })

        messages.append({"role": "user", "content": user_prompt})
        return messages

    def _call_model(self, messages: List[Dict[str, str]],
                    task_type: str = "chat",
                    temperature: float = 0.7,
                    max_tokens: int = 2000) -> Dict[str, Any]:
        if self.model_router is None:
            raise RuntimeError("Model router not initialized")

        from backend.services.model_router import TaskType
        task_enum = TaskType(task_type) if task_type in [t.value for t in TaskType] else TaskType.CHAT

        return self.model_router.chat(
            task_type=task_enum,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def _create_result(self, success: bool, data: Optional[Dict[str, Any]] = None,
                       error: Optional[str] = None,
                       model_response: Optional[Dict[str, Any]] = None,
                       duration: float = 0.0) -> AgentResult:
        return AgentResult(
            success=success,
            data=data or {},
            error=error,
            agent_role=self.role.value,
            model_used=model_response.get("model", "") if model_response else "",
            tokens_used=(
                model_response.get("usage", {}).get("input_tokens", 0) +
                model_response.get("usage", {}).get("output_tokens", 0)
            ) if model_response else 0,
            cost_usd=model_response.get("cost_usd", 0.0) if model_response else 0.0,
            duration_seconds=duration,
        )
