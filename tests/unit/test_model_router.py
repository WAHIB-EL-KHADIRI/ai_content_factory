"""Unit tests for model router"""

import asyncio
import json

from backend.services.model_router import (
    ModelRouter, TaskType, MODELS, TASK_MODEL_PREFERENCES
)


class TestModelRouter:
    def setup_method(self):
        self.router = ModelRouter()

    def test_select_model_for_writing(self):
        model = self.router.select_model(TaskType.CONTENT_WRITING)
        assert model is not None
        assert model.model in [m.model for m in MODELS.values()]

    def test_select_model_for_seo(self):
        model = self.router.select_model(TaskType.SEO_ANALYSIS)
        assert model is not None

    def test_select_model_with_speed_preference(self):
        model = self.router.select_model(TaskType.CHAT, prefer_speed=True)
        assert model.latency_rating >= 7

    def test_select_model_with_quality_preference(self):
        model = self.router.select_model(TaskType.CONTENT_WRITING, prefer_quality=True)
        assert model.quality_rating >= 8

    def test_select_model_with_cost_limit(self):
        router = ModelRouter(max_cost_per_task=0.001)
        model = router.select_model(TaskType.CHAT)
        assert model is not None

    def test_select_model_with_vision_requirement(self):
        model = self.router.select_model(
            TaskType.SCRIPT_GENERATION,
            required_features=["vision"]
        )
        assert model.supports_vision is True

    def test_estimate_cost(self):
        cost = self.router.estimate_cost(TaskType.CHAT, 1000, 500)
        assert "estimated_cost_usd" in cost
        assert cost["estimated_cost_usd"] > 0

    def test_task_preferences_exist(self):
        for task_type in TaskType:
            assert task_type in TASK_MODEL_PREFERENCES

    def test_all_models_have_required_fields(self):
        for key, model in MODELS.items():
            assert model.provider
            assert model.model
            assert model.tier
            assert model.cost_per_1k_input >= 0
            assert model.cost_per_1k_output >= 0
            assert model.max_tokens > 0


# A provider exception carrying exactly the kinds of detail these errors carry
# in production: an endpoint, a request id, and a credential prefix.
_PROVIDER_ERROR = (
    "connection to https://api.internal.example/v1/messages failed "
    "(request_id=req_9f3ab2, key=sk-live-ABCDEF0123456789)"
)


class _ExplodingClient:
    """Any call on this object raises, whichever provider branch is taken."""

    def __getattr__(self, name):
        return self

    def __call__(self, *args, **kwargs):
        raise RuntimeError(_PROVIDER_ERROR)


class TestStreamErrorDisclosure:
    """`/chat` is unauthenticated and streams these events straight to the
    browser, so the error payload must not carry the provider's exception."""

    @staticmethod
    def _events():
        router = ModelRouter()
        router.get_async_client = lambda model: _ExplodingClient()

        async def drive():
            return [
                event
                async for event in router.chat_stream(
                    TaskType.CHAT, [{"role": "user", "content": "hi"}]
                )
            ]

        return asyncio.run(drive())

    def test_the_failure_is_reported_at_all(self):
        errors = [e for e in self._events() if e.get("type") == "error"]
        assert len(errors) == 1

    def test_no_provider_detail_reaches_the_client(self):
        payload = json.dumps(self._events())

        assert _PROVIDER_ERROR not in payload
        # Each fragment on its own, so a partially-redacted message still fails.
        assert "api.internal.example" not in payload
        assert "req_9f3ab2" not in payload
        assert "sk-live" not in payload

    def test_the_client_gets_a_stable_message_and_an_id_to_quote(self):
        error = [e for e in self._events() if e.get("type") == "error"][0]

        assert error["error"] == "The model call failed."
        assert len(error["error_id"]) == 12
