"""Unit tests for model router"""

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
