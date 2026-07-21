"""Unit tests for services"""

from backend.services.brand import BrandService
from backend.services.memory import MemoryService


class TestBrandService:
    def test_create_brand(self):
        service = BrandService()
        brand = service.create_brand("proj_1", {
            "name": "Test Brand",
            "voice_tone": "friendly",
            "keywords": ["test", "brand"],
        })
        assert brand["name"] == "Test Brand"
        assert brand["voice_tone"] == "friendly"

    def test_analyze_brand_consistency(self):
        service = BrandService()
        brand = service.create_brand("proj_1", {
            "name": "Test Brand",
            "keywords": ["python", "fastapi"],
        })
        result = service.analyze_brand_consistency(
            "This is about python and fastapi development",
            brand["id"]
        )
        assert "score" in result
        assert "consistent" in result


class TestMemoryService:
    def test_store_and_recall(self):
        service = MemoryService()
        mem = service.store(
            content="User prefers dark mode",
            memory_type="user_preference",
            user_id="user_1",
            importance=0.8,
        )
        assert mem["content"] == "User prefers dark mode"

        results = service.recall("dark mode", user_id="user_1")
        assert len(results) > 0

    def test_get_user_context(self):
        service = MemoryService()
        service.store("preference 1", "user_preference", user_id="user_1")
        service.store("preference 2", "user_preference", user_id="user_1")

        context = service.get_user_context("user_1")
        assert "preferences" in context
        assert len(context["preferences"]) == 2

    def test_memory_relevance(self):
        service = MemoryService()
        service.store("python programming language", "factual_knowledge")
        service.store("cooking recipe pasta", "factual_knowledge")

        results = service.recall("python programming")
        assert len(results) > 0
        assert "python" in results[0]["content"].lower()
