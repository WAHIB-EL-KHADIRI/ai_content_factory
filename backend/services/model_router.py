"""Model Router - selects the best model for each task"""

import time
import logging
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from backend.core.config import get_config

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    SCRIPT_GENERATION = "script_generation"
    CONTENT_WRITING = "content_writing"
    SEO_ANALYSIS = "seo_analysis"
    TRANSLATION = "translation"
    EDITING = "editing"
    VISUAL_GENERATION = "visual_generation"
    TTS = "tts"
    SUMMARIZATION = "summarization"
    CLASSIFICATION = "classification"
    CHAT = "chat"


class ModelTier(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    PREMIUM = "premium"


@dataclass
class ModelInfo:
    provider: str
    model: str
    tier: ModelTier
    cost_per_1k_input: float
    cost_per_1k_output: float
    max_tokens: int
    supports_vision: bool = False
    supports_function_calling: bool = False
    latency_rating: int = 5  # 1-10, 10 is fastest
    quality_rating: int = 5  # 1-10, 10 is best


MODELS: Dict[str, ModelInfo] = {
    "gpt-4o": ModelInfo(
        provider="openai",
        model="gpt-4o",
        tier=ModelTier.PREMIUM,
        cost_per_1k_input=0.005,
        cost_per_1k_output=0.015,
        max_tokens=128000,
        supports_vision=True,
        supports_function_calling=True,
        latency_rating=7,
        quality_rating=9,
    ),
    "gpt-4o-mini": ModelInfo(
        provider="openai",
        model="gpt-4o-mini",
        tier=ModelTier.FAST,
        cost_per_1k_input=0.00015,
        cost_per_1k_output=0.0006,
        max_tokens=128000,
        supports_vision=True,
        supports_function_calling=True,
        latency_rating=9,
        quality_rating=7,
    ),
    "claude-sonnet-4-20250514": ModelInfo(
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        tier=ModelTier.PREMIUM,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        max_tokens=200000,
        supports_vision=True,
        supports_function_calling=True,
        latency_rating=6,
        quality_rating=10,
    ),
    "claude-haiku-4-20250414": ModelInfo(
        provider="anthropic",
        model="claude-haiku-4-20250414",
        tier=ModelTier.FAST,
        cost_per_1k_input=0.00025,
        cost_per_1k_output=0.00125,
        max_tokens=200000,
        supports_vision=False,
        supports_function_calling=True,
        latency_rating=9,
        quality_rating=7,
    ),
    "deepseek-chat": ModelInfo(
        provider="deepseek",
        model="deepseek-chat",
        tier=ModelTier.BALANCED,
        cost_per_1k_input=0.00014,
        cost_per_1k_output=0.00028,
        max_tokens=32000,
        supports_vision=False,
        supports_function_calling=True,
        latency_rating=8,
        quality_rating=7,
    ),
    "deepseek-reasoner": ModelInfo(
        provider="deepseek",
        model="deepseek-reasoner",
        tier=ModelTier.BALANCED,
        cost_per_1k_input=0.00055,
        cost_per_1k_output=0.00219,
        max_tokens=64000,
        supports_vision=False,
        supports_function_calling=False,
        latency_rating=5,
        quality_rating=8,
    ),
}

TASK_MODEL_PREFERENCES: Dict[TaskType, List[str]] = {
    TaskType.SCRIPT_GENERATION: ["gpt-4o", "claude-sonnet-4-20250514", "deepseek-chat"],
    TaskType.CONTENT_WRITING: ["claude-sonnet-4-20250514", "gpt-4o", "deepseek-chat"],
    TaskType.SEO_ANALYSIS: ["gpt-4o-mini", "claude-haiku-4-20250414", "deepseek-chat"],
    TaskType.TRANSLATION: ["claude-sonnet-4-20250514", "gpt-4o", "deepseek-chat"],
    TaskType.EDITING: ["claude-sonnet-4-20250514", "gpt-4o", "deepseek-chat"],
    TaskType.VISUAL_GENERATION: ["gpt-4o", "gpt-4o-mini"],
    TaskType.TTS: ["gpt-4o-mini"],
    TaskType.SUMMARIZATION: ["gpt-4o-mini", "claude-haiku-4-20250414", "deepseek-chat"],
    TaskType.CLASSIFICATION: [
        "gpt-4o-mini",
        "claude-haiku-4-20250414",
        "deepseek-chat",
    ],
    TaskType.CHAT: ["gpt-4o-mini", "claude-haiku-4-20250414", "deepseek-chat"],
}


class ModelRouter:
    def __init__(
        self,
        preferred_tier: Optional[ModelTier] = None,
        max_cost_per_task: Optional[float] = None,
    ):
        self.config = get_config()
        self.preferred_tier = preferred_tier
        self.max_cost_per_task = max_cost_per_task
        self._usage_stats: Dict[str, Dict[str, Any]] = {}

    def select_model(
        self,
        task_type: TaskType,
        required_features: Optional[List[str]] = None,
        prefer_speed: bool = False,
        prefer_quality: bool = False,
    ) -> ModelInfo:
        preferences = TASK_MODEL_PREFERENCES.get(task_type, ["gpt-4o-mini"])
        candidates = []

        for model_key in preferences:
            model = MODELS.get(model_key)
            if model is None:
                continue

            if self.preferred_tier and model.tier != self.preferred_tier:
                continue

            if required_features:
                if "vision" in required_features and not model.supports_vision:
                    continue
                if (
                    "function_calling" in required_features
                    and not model.supports_function_calling
                ):
                    continue

            if self.max_cost_per_task:
                estimated_cost = (
                    model.cost_per_1k_input + model.cost_per_1k_output
                ) * 0.5
                if estimated_cost > self.max_cost_per_task:
                    continue

            candidates.append(model)

        if not candidates:
            fallback_key = preferences[0] if preferences else "gpt-4o-mini"
            return MODELS[fallback_key]

        if prefer_speed:
            candidates.sort(key=lambda m: m.latency_rating, reverse=True)
        elif prefer_quality:
            candidates.sort(key=lambda m: m.quality_rating, reverse=True)
        else:
            candidates.sort(key=lambda m: (m.cost_per_1k_input + m.cost_per_1k_output))

        return candidates[0]

    def get_client(self, model: ModelInfo):
        config = self.config

        if model.provider == "openai":
            from openai import OpenAI

            return OpenAI(api_key=config.models.openai_api_key)

        elif model.provider == "anthropic":
            import anthropic

            return anthropic.Anthropic(api_key=config.models.anthropic_api_key)

        elif model.provider == "deepseek":
            from openai import OpenAI

            return OpenAI(
                api_key=config.models.deepseek_api_key,
                base_url=config.models.deepseek_base_url,
            )

        raise ValueError(f"Unsupported provider: {model.provider}")

    def chat(
        self,
        task_type: TaskType,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        prefer_speed: bool = False,
        prefer_quality: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        model = self.select_model(
            task_type, prefer_speed=prefer_speed, prefer_quality=prefer_quality
        )

        start_time = time.time()
        client = self.get_client(model)

        try:
            if model.provider == "anthropic":
                system_msg = ""
                user_messages = []
                for msg in messages:
                    if msg["role"] == "system":
                        system_msg = msg["content"]
                    else:
                        user_messages.append(msg)

                response = client.messages.create(
                    model=model.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_msg,
                    messages=user_messages,
                    **kwargs,
                )
                content = response.content[0].text
                usage = {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                }
            else:
                response = client.chat.completions.create(
                    model=model.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
                content = response.choices[0].message.content
                usage = {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens,
                }

            latency_ms = (time.time() - start_time) * 1000
            total_tokens = usage["input_tokens"] + usage["output_tokens"]
            cost = (
                usage["input_tokens"] * model.cost_per_1k_input / 1000
                + usage["output_tokens"] * model.cost_per_1k_output / 1000
            )

            self._track_usage(model, task_type, total_tokens, cost, latency_ms)

            return {
                "content": content,
                "model": model.model,
                "provider": model.provider,
                "usage": usage,
                "cost_usd": cost,
                "latency_ms": latency_ms,
            }

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(
                "Model call failed: %s/%s after %.0fms: %s",
                model.provider,
                model.model,
                latency_ms,
                e,
            )
            raise

    def get_async_client(self, model: ModelInfo):
        config = self.config

        if model.provider == "openai":
            from openai import AsyncOpenAI

            return AsyncOpenAI(api_key=config.models.openai_api_key)

        elif model.provider == "anthropic":
            import anthropic

            return anthropic.AsyncAnthropic(api_key=config.models.anthropic_api_key)

        elif model.provider == "deepseek":
            from openai import AsyncOpenAI

            return AsyncOpenAI(
                api_key=config.models.deepseek_api_key,
                base_url=config.models.deepseek_base_url,
            )

        raise ValueError(f"Unsupported provider: {model.provider}")

    async def chat_stream(
        self,
        task_type: TaskType,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        prefer_speed: bool = False,
        prefer_quality: bool = False,
        **kwargs,
    ):
        model = self.select_model(
            task_type, prefer_speed=prefer_speed, prefer_quality=prefer_quality
        )

        start_time = time.time()
        client = self.get_async_client(model)
        total_content = ""
        input_tokens = 0
        output_tokens = 0

        try:
            if model.provider == "anthropic":
                system_msg = ""
                user_messages = []
                for msg in messages:
                    if msg["role"] == "system":
                        system_msg = msg["content"]
                    else:
                        user_messages.append(msg)

                async with client.messages.stream(
                    model=model.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_msg,
                    messages=user_messages,
                    **kwargs,
                ) as stream:
                    async for text in stream.text_stream:
                        total_content += text
                        yield {"type": "delta", "content": text}

                    final_message = await stream.get_final_message()
                    input_tokens = final_message.usage.input_tokens
                    output_tokens = final_message.usage.output_tokens
            else:
                response = await client.chat.completions.create(
                    model=model.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                    **kwargs,
                )
                async for chunk in response:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if delta and delta.content:
                        total_content += delta.content
                        yield {"type": "delta", "content": delta.content}
                    if chunk.usage:
                        input_tokens = chunk.usage.prompt_tokens or 0
                        output_tokens = chunk.usage.completion_tokens or 0

            latency_ms = (time.time() - start_time) * 1000
            total_tokens = input_tokens + output_tokens
            cost = (
                input_tokens * model.cost_per_1k_input / 1000
                + output_tokens * model.cost_per_1k_output / 1000
            )

            self._track_usage(model, task_type, total_tokens, cost, latency_ms)

            yield {
                "type": "done",
                "content": total_content,
                "model": model.model,
                "provider": model.provider,
                "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
                "cost_usd": cost,
                "latency_ms": latency_ms,
            }

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            # This payload is streamed to the browser over SSE, and /chat is
            # not authenticated -- so the client gets a stable string and an
            # id to quote, never the provider's exception. Provider errors
            # routinely carry the endpoint URL, a request id, the model
            # deployment name and occasionally a key prefix.
            error_id = uuid.uuid4().hex[:12]
            logger.error(
                "Stream call failed [%s]: %s/%s after %.0fms: %s",
                error_id,
                model.provider,
                model.model,
                latency_ms,
                e,
            )
            yield {
                "type": "error",
                "error": "The model call failed.",
                "error_id": error_id,
            }

    def _track_usage(
        self,
        model: ModelInfo,
        task_type: TaskType,
        tokens: int,
        cost: float,
        latency_ms: float,
    ):
        key = f"{model.provider}:{model.model}"
        if key not in self._usage_stats:
            self._usage_stats[key] = {
                "total_calls": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "total_latency_ms": 0.0,
                "tasks": {},
            }
        stats = self._usage_stats[key]
        stats["total_calls"] += 1
        stats["total_tokens"] += tokens
        stats["total_cost"] += cost
        stats["total_latency_ms"] += latency_ms

        task_key = task_type.value
        if task_key not in stats["tasks"]:
            stats["tasks"][task_key] = {"calls": 0, "tokens": 0, "cost": 0.0}
        stats["tasks"][task_key]["calls"] += 1
        stats["tasks"][task_key]["tokens"] += tokens
        stats["tasks"][task_key]["cost"] += cost

    def get_usage_stats(self) -> Dict[str, Any]:
        return self._usage_stats.copy()

    def estimate_cost(
        self,
        task_type: TaskType,
        estimated_input_tokens: int,
        estimated_output_tokens: int,
    ) -> Dict[str, Any]:
        model = self.select_model(task_type)
        cost = (
            estimated_input_tokens * model.cost_per_1k_input / 1000
            + estimated_output_tokens * model.cost_per_1k_output / 1000
        )
        return {
            "model": model.model,
            "provider": model.provider,
            "estimated_cost_usd": cost,
            "input_cost": estimated_input_tokens * model.cost_per_1k_input / 1000,
            "output_cost": estimated_output_tokens * model.cost_per_1k_output / 1000,
        }
