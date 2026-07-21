"""Workflow Engine - orchestrates complex content workflows"""

import uuid
import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone
from enum import Enum

from backend.agents.router import AgentRouter
from backend.agents.base import AgentRole


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


logger = logging.getLogger(__name__)


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_APPROVAL = "waiting_approval"


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class Workflow:
    def __init__(self, name: str, steps: List[Dict[str, Any]],
                 triggers: Optional[Dict[str, Any]] = None,
                 variables: Optional[Dict[str, Any]] = None):
        self.id = str(uuid.uuid4())
        self.name = name
        self.steps = steps
        self.triggers = triggers or {}
        self.variables = variables or {}
        self.created_at = _utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "steps": self.steps,
            "triggers": self.triggers,
            "variables": self.variables,
            "created_at": self.created_at.isoformat(),
        }


class WorkflowStep:
    def __init__(self, name: str, agent_role: str, task: Dict[str, Any],
                 conditions: Optional[List[Dict[str, Any]]] = None,
                 retry_config: Optional[Dict[str, Any]] = None,
                 requires_approval: bool = False,
                 timeout_seconds: int = 300):
        self.id = str(uuid.uuid4())
        self.name = name
        self.agent_role = agent_role
        self.task = task
        self.conditions = conditions or []
        self.retry_config = retry_config or {"max_retries": 3, "delay": 1.0}
        self.requires_approval = requires_approval
        self.timeout_seconds = timeout_seconds
        self.status = StepStatus.PENDING
        self.result = None
        self.error = None
        self.started_at = None
        self.completed_at = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "agent_role": self.agent_role,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class WorkflowRun:
    def __init__(self, workflow: Workflow):
        self.id = str(uuid.uuid4())
        self.workflow = workflow
        self.status = WorkflowStatus.RUNNING
        self.steps: List[WorkflowStep] = []
        self.context: Dict[str, Any] = {}
        self.started_at = _utcnow()
        self.completed_at = None
        self.error = None
        self.output_data = {}

    @property
    def duration_seconds(self) -> float:
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return (_utcnow() - self.started_at).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_id": self.workflow.id,
            "workflow_name": self.workflow.name,
            "status": self.status.value,
            "steps": [s.to_dict() for s in self.steps],
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
            "output_data": self.output_data,
        }


class WorkflowEngine:
    def __init__(self, agent_router: Optional[AgentRouter] = None):
        self.agent_router = agent_router or AgentRouter()
        self._workflows: Dict[str, Workflow] = {}
        self._runs: Dict[str, WorkflowRun] = {}
        self._custom_steps: Dict[str, Callable] = {}
        self._approval_callbacks: Dict[str, Callable] = {}

    def register_workflow(self, workflow: Workflow) -> str:
        self._workflows[workflow.id] = workflow
        return workflow.id

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        return self._workflows.get(workflow_id)

    def list_workflows(self) -> List[Dict[str, Any]]:
        return [w.to_dict() for w in self._workflows.values()]

    def register_custom_step(self, name: str, handler: Callable):
        self._custom_steps[name] = handler

    def register_approval_callback(self, step_id: str, callback: Callable):
        self._approval_callbacks[step_id] = callback

    async def execute_workflow(self, workflow_id: str,
                               initial_context: Optional[Dict[str, Any]] = None) -> WorkflowRun:
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            raise ValueError(f"Workflow not found: {workflow_id}")

        run = WorkflowRun(workflow)
        run.context = initial_context or {}
        self._runs[run.id] = run

        logger.info(f"Starting workflow run: {workflow.name} (run: {run.id})")

        for step_def in workflow.steps:
            step = WorkflowStep(
                name=step_def["name"],
                agent_role=step_def.get("agent_role", ""),
                task=step_def.get("task", {}),
                conditions=step_def.get("conditions", []),
                retry_config=step_def.get("retry_config", {}),
                requires_approval=step_def.get("requires_approval", False),
                timeout_seconds=step_def.get("timeout_seconds", 300),
            )
            run.steps.append(step)

            if not self._check_conditions(step.conditions, run.context):
                step.status = StepStatus.SKIPPED
                logger.info(f"Skipping step {step.name}: conditions not met")
                continue

            if step.requires_approval:
                step.status = StepStatus.WAITING_APPROVAL
                approved = await self._wait_for_approval(step, run)
                if not approved:
                    step.status = StepStatus.SKIPPED
                    continue

            step.status = StepStatus.RUNNING
            step.started_at = _utcnow()

            try:
                result = await self._execute_step(step, run.context)
                step.result = result
                step.status = StepStatus.COMPLETED
                step.completed_at = _utcnow()
                run.context[f"{step.name}_result"] = result

                logger.info(f"Step {step.name} completed")

            except Exception as e:
                step.error = str(e)
                step.status = StepStatus.FAILED
                step.completed_at = _utcnow()
                logger.error(f"Step {step.name} failed: {e}")

                max_retries = step.retry_config.get("max_retries", 3)
                retry_count = step.retry_config.get("_current_retry", 0)

                if retry_count < max_retries:
                    step.retry_config["_current_retry"] = retry_count + 1
                    step.status = StepStatus.PENDING
                    step.error = None
                    step.started_at = None
                    step.completed_at = None
                    run.steps.pop()
                    delay = step.retry_config.get("delay", 1.0) * (2 ** retry_count)
                    await asyncio.sleep(delay)
                    run.steps.append(step)
                    continue

                run.status = WorkflowStatus.FAILED
                run.error = f"Step {step.name} failed: {e}"
                run.completed_at = _utcnow()
                return run

        run.status = WorkflowStatus.COMPLETED
        run.completed_at = _utcnow()
        run.output_data = {k: v for k, v in run.context.items() if k.endswith("_result")}

        logger.info(f"Workflow completed: {workflow.name} in {run.duration_seconds:.1f}s")
        return run

    async def _execute_step(self, step: WorkflowStep, context: Dict[str, Any]) -> Any:
        custom_handler = self._custom_steps.get(step.name)
        if custom_handler:
            if asyncio.iscoroutinefunction(custom_handler):
                return await custom_handler(step.task, context)
            return custom_handler(step.task, context)

        if not step.agent_role:
            raise ValueError(f"No agent role specified for step: {step.name}")

        role = AgentRole(step.agent_role)
        task_data = self._resolve_variables(step.task, context)
        return await self.agent_router.run_single(role, task_data, context)

    def _check_conditions(self, conditions: List[Dict[str, Any]],
                          context: Dict[str, Any]) -> bool:
        for condition in conditions:
            condition_type = condition.get("type", "exists")
            key = condition.get("key", "")
            value = condition.get("value")

            if condition_type == "exists" and key not in context:
                return False
            elif condition_type == "not_exists" and key in context:
                return False
            elif condition_type == "equals" and context.get(key) != value:
                return False
            elif condition_type == "not_equals" and context.get(key) == value:
                return False
            elif condition_type == "contains":
                ctx_val = str(context.get(key, ""))
                if value not in ctx_val:
                    return False

        return True

    def _resolve_variables(self, task: Dict[str, Any],
                           context: Dict[str, Any]) -> Dict[str, Any]:
        resolved = {}
        for key, value in task.items():
            if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                var_name = value[2:-2].strip()
                resolved[key] = context.get(var_name, value)
            elif isinstance(value, dict):
                resolved[key] = self._resolve_variables(value, context)
            else:
                resolved[key] = value
        return resolved

    async def _wait_for_approval(self, step: WorkflowStep, run: WorkflowRun) -> bool:
        callback = self._approval_callbacks.get(step.id)
        if callback:
            if asyncio.iscoroutinefunction(callback):
                return await callback(step, run)
            return callback(step, run)
        return True

    def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        return self._runs.get(run_id)

    def list_runs(self, workflow_id: Optional[str] = None) -> List[Dict[str, Any]]:
        runs = list(self._runs.values())
        if workflow_id:
            runs = [r for r in runs if r.workflow.id == workflow_id]
        return [r.to_dict() for r in runs]


_engine_instance: Optional[WorkflowEngine] = None


def get_workflow_engine() -> WorkflowEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = WorkflowEngine()
    return _engine_instance
