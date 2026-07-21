"""Agent Router - orchestrates multi-agent workflows"""

import logging
from typing import Dict, Any, Optional, List, Type
from backend.agents.base import BaseAgent, AgentRole, AgentResult

logger = logging.getLogger(__name__)

AGENT_REGISTRY: Dict[AgentRole, Type[BaseAgent]] = {}


def register_agent(role: AgentRole, agent_class: Type[BaseAgent]):
    AGENT_REGISTRY[role] = agent_class


def _load_default_agents():
    from backend.agents.research import ResearchAgent
    from backend.agents.writer import WriterAgent
    from backend.agents.seo import SEOAgent
    from backend.agents.editor import EditorAgent
    from backend.agents.translator import TranslatorAgent
    from backend.agents.designer import DesignerAgent
    from backend.agents.publisher import PublisherAgent
    from backend.agents.reviewer import ReviewAgent

    register_agent(AgentRole.RESEARCH, ResearchAgent)
    register_agent(AgentRole.WRITER, WriterAgent)
    register_agent(AgentRole.SEO, SEOAgent)
    register_agent(AgentRole.EDITOR, EditorAgent)
    register_agent(AgentRole.TRANSLATOR, TranslatorAgent)
    register_agent(AgentRole.DESIGNER, DesignerAgent)
    register_agent(AgentRole.PUBLISHER, PublisherAgent)
    register_agent(AgentRole.REVIEWER, ReviewAgent)


class AgentRouter:
    def __init__(self, model_router=None):
        self.model_router = model_router
        self._agents: Dict[AgentRole, BaseAgent] = {}
        self._initialized = False

    def _ensure_initialized(self):
        if not self._initialized:
            _load_default_agents()
            self._initialized = True

    def get_agent(self, role: AgentRole) -> BaseAgent:
        self._ensure_initialized()

        if role not in self._agents:
            agent_class = AGENT_REGISTRY.get(role)
            if agent_class is None:
                raise ValueError(f"No agent registered for role: {role}")
            self._agents[role] = agent_class(model_router=self.model_router)

        return self._agents[role]

    async def run_single(self, role: AgentRole, task: Dict[str, Any],
                         context: Optional[Dict[str, Any]] = None) -> AgentResult:
        agent = self.get_agent(role)
        logger.info(f"Running {agent.name} for task: {task.get('task_type', 'default')}")
        return await agent.execute(task, context)

    async def run_pipeline(self, steps: List[Dict[str, Any]],
                           initial_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = initial_context or {}
        results = {}
        total_cost = 0.0
        total_tokens = 0

        for i, step in enumerate(steps):
            role = AgentRole(step["role"])
            task = step.get("task", {})
            task.update(step.get("params", {}))

            logger.info(f"Pipeline step {i + 1}/{len(steps)}: {role.value}")

            result = await self.run_single(role, task, context)

            results[step.get("name", f"step_{i}")] = result.to_dict()
            total_cost += result.cost_usd
            total_tokens += result.tokens_used

            if not result.success:
                logger.error(f"Pipeline failed at step {i + 1}: {result.error}")
                break

            context[step.get("output_key", f"step_{i}_result")] = result.data

        return {
            "success": all(r.get("success", False) for r in results.values()),
            "steps": results,
            "total_cost_usd": total_cost,
            "total_tokens": total_tokens,
        }

    async def run_content_pipeline(self, topic: str, content_type: str = "article",
                                   brand: Optional[Dict[str, Any]] = None,
                                   language: str = "en") -> Dict[str, Any]:
        context = {"topic": topic, "content_type": content_type}
        if brand:
            context["brand"] = brand

        steps = [
            {
                "role": "research",
                "name": "research",
                "task": {"topic": topic, "research_type": "general"},
                "output_key": "research",
            },
            {
                "role": "writer",
                "name": "writing",
                "task": {
                    "content_type": content_type,
                    "topic": topic,
                    "word_count": 1500,
                },
                "output_key": "draft",
            },
            {
                "role": "seo",
                "name": "seo_analysis",
                "task": {"action": "analyze", "content": ""},
                "output_key": "seo_analysis",
            },
            {
                "role": "editor",
                "name": "editing",
                "task": {"content": "", "edit_type": "comprehensive"},
                "output_key": "edited",
            },
            {
                "role": "reviewer",
                "name": "review",
                "task": {"content": "", "review_type": "comprehensive"},
                "output_key": "review",
            },
        ]

        result = await self.run_pipeline(steps, context)

        if result["success"] and "review" in result.get("steps", {}):
            review_data = result["steps"]["review"].get("data", {})
            result["quality_score"] = review_data.get("overall_score", 0)
            result["review_status"] = review_data.get("status", "unknown")

        return result

    def list_agents(self) -> List[Dict[str, str]]:
        self._ensure_initialized()
        return [
            {"role": role.value, "name": cls.name, "description": cls.description}
            for role, cls in AGENT_REGISTRY.items()
        ]
