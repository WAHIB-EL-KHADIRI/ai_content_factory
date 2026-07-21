"""Unit tests for agents"""

import pytest
from backend.agents.base import AgentRole, AgentResult
from backend.agents.router import AgentRouter


class TestAgentResult:
    def test_create_success_result(self):
        result = AgentResult(
            success=True,
            data={"key": "value"},
            agent_role="writer",
            model_used="gpt-4o",
            tokens_used=100,
            cost_usd=0.01,
        )
        assert result.success is True
        assert result.data["key"] == "value"
        d = result.to_dict()
        assert d["success"] is True

    def test_create_failure_result(self):
        result = AgentResult(success=False, error="Something went wrong")
        assert result.success is False
        assert result.error == "Something went wrong"


class TestAgentRouter:
    def test_list_agents(self):
        router = AgentRouter()
        agents = router.list_agents()
        assert len(agents) >= 8
        roles = [a["role"] for a in agents]
        assert "research" in roles
        assert "writer" in roles
        assert "seo" in roles
        assert "editor" in roles
        assert "translator" in roles
        assert "designer" in roles
        assert "publisher" in roles
        assert "reviewer" in roles

    def test_get_agent(self):
        router = AgentRouter()
        agent = router.get_agent(AgentRole.RESEARCH)
        assert agent is not None
        assert agent.role == AgentRole.RESEARCH

    def test_get_invalid_agent_raises(self):
        router = AgentRouter()
        with pytest.raises(ValueError):
            router.get_agent("invalid_role")
