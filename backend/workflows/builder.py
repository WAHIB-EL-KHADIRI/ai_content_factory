"""Workflow Builder - declarative workflow construction"""

from typing import Dict, Any, List, Optional
from backend.workflows.engine import Workflow


class WorkflowBuilder:
    def __init__(self, name: str):
        self._name = name
        self._steps: List[Dict[str, Any]] = []
        self._variables: Dict[str, Any] = {}
        self._triggers: Dict[str, Any] = {}

    def add_step(
        self,
        name: str,
        agent_role: str,
        task: Dict[str, Any],
        conditions: Optional[List[Dict[str, Any]]] = None,
        requires_approval: bool = False,
        retry_config: Optional[Dict[str, Any]] = None,
        output_key: Optional[str] = None,
    ) -> "WorkflowBuilder":
        step = {
            "name": name,
            "agent_role": agent_role,
            "task": task,
            "conditions": conditions or [],
            "requires_approval": requires_approval,
            "retry_config": retry_config or {"max_retries": 3, "delay": 1.0},
            "output_key": output_key or f"{name}_result",
        }
        self._steps.append(step)
        return self

    def add_condition(
        self, step_name: str, condition_type: str, key: str, value: Any = None
    ) -> "WorkflowBuilder":
        for step in self._steps:
            if step["name"] == step_name:
                step["conditions"].append(
                    {
                        "type": condition_type,
                        "key": key,
                        "value": value,
                    }
                )
                break
        return self

    def set_variable(self, key: str, value: Any) -> "WorkflowBuilder":
        self._variables[key] = value
        return self

    def set_trigger(self, trigger_type: str, **kwargs) -> "WorkflowBuilder":
        self._triggers = {"type": trigger_type, **kwargs}
        return self

    def build(self) -> Workflow:
        return Workflow(
            name=self._name,
            steps=self._steps,
            triggers=self._triggers,
            variables=self._variables,
        )

    @staticmethod
    def create_article_workflow(topic: str, brand: Optional[Dict] = None) -> Workflow:
        builder = WorkflowBuilder(f"Article: {topic}")
        builder.add_step(
            name="research",
            agent_role="research",
            task={"topic": topic, "research_type": "general"},
        ).add_step(
            name="seo_keywords",
            agent_role="seo",
            task={"action": "keywords", "topic": topic},
            conditions=[{"type": "exists", "key": "research_result"}],
        ).add_step(
            name="write_draft",
            agent_role="writer",
            task={
                "content_type": "article",
                "topic": topic,
                "word_count": 1500,
            },
        ).add_step(
            name="seo_optimize",
            agent_role="seo",
            task={"action": "optimize", "content": "{{write_draft_result}}"},
        ).add_step(
            name="edit",
            agent_role="editor",
            task={"content": "{{seo_optimize_result}}", "edit_type": "comprehensive"},
        ).add_step(
            name="design_assets",
            agent_role="designer",
            task={
                "design_type": "image_prompt",
                "content": "{{write_draft_result}}",
            },
        ).add_step(
            name="review",
            agent_role="reviewer",
            task={"content": "{{edit_result}}", "review_type": "comprehensive"},
        ).add_step(
            name="publish_format",
            agent_role="publisher",
            task={
                "action": "format",
                "content": "{{edit_result}}",
                "platforms": ["blog", "twitter", "linkedin"],
            },
        )

        if brand:
            builder.set_variable("brand", brand)

        return builder.build()

    @staticmethod
    def create_video_workflow(topic: str) -> Workflow:
        builder = WorkflowBuilder(f"Video: {topic}")
        builder.add_step(
            name="research",
            agent_role="research",
            task={"topic": topic, "research_type": "general"},
        ).add_step(
            name="write_script",
            agent_role="writer",
            task={
                "content_type": "video_script",
                "topic": topic,
                "word_count": 800,
            },
        ).add_step(
            name="design_visuals",
            agent_role="designer",
            task={
                "design_type": "video_scenes",
                "content": "{{write_script_result}}",
            },
        ).add_step(
            name="review_script",
            agent_role="reviewer",
            task={"content": "{{write_script_result}}", "review_type": "comprehensive"},
        ).add_step(
            name="generate",
            agent_role="publisher",
            task={"action": "format", "content": "{{write_script_result}}"},
        )
        return builder.build()

    @staticmethod
    def create_social_media_batch(topic: str, platforms: List[str]) -> Workflow:
        builder = WorkflowBuilder(f"Social Media: {topic}")
        builder.add_step(
            name="research",
            agent_role="research",
            task={"topic": topic, "depth": "quick"},
        ).add_step(
            name="create_content",
            agent_role="writer",
            task={
                "content_type": "social_media",
                "topic": topic,
                "word_count": 500,
            },
        ).add_step(
            name="design",
            agent_role="designer",
            task={
                "design_type": "social_media",
                "content": "{{create_content_result}}",
            },
        ).add_step(
            name="optimize",
            agent_role="seo",
            task={"action": "analyze", "content": "{{create_content_result}}"},
        ).add_step(
            name="format",
            agent_role="publisher",
            task={
                "action": "format",
                "content": "{{create_content_result}}",
                "platforms": platforms,
            },
        )
        return builder.build()
