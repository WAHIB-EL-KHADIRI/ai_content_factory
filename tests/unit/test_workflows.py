"""Unit tests for workflow engine"""

from backend.workflows.engine import (
    Workflow
)
from backend.workflows.builder import WorkflowBuilder


class TestWorkflowBuilder:
    def test_build_simple_workflow(self):
        workflow = (
            WorkflowBuilder("Test Workflow")
            .add_step("step1", "research", {"topic": "test"})
            .add_step("step2", "writer", {"content_type": "article"})
            .build()
        )
        assert workflow.name == "Test Workflow"
        assert len(workflow.steps) == 2

    def test_build_with_variables(self):
        workflow = (
            WorkflowBuilder("Variable Test")
            .set_variable("topic", "AI")
            .add_step("step1", "research", {"topic": "{{topic}}"})
            .build()
        )
        assert workflow.variables["topic"] == "AI"

    def test_add_condition(self):
        workflow = (
            WorkflowBuilder("Conditional")
            .add_step("step1", "research", {"topic": "test"})
            .add_condition("step1", "exists", "some_key")
            .build()
        )
        assert len(workflow.steps[0]["conditions"]) == 1

    def test_create_article_workflow(self):
        workflow = WorkflowBuilder.create_article_workflow("Test Topic")
        assert "Test Topic" in workflow.name
        assert len(workflow.steps) >= 5

    def test_create_video_workflow(self):
        workflow = WorkflowBuilder.create_video_workflow("Test Video")
        assert "Test Video" in workflow.name

    def test_create_social_workflow(self):
        workflow = WorkflowBuilder.create_social_media_batch(
            "Test Social", ["twitter", "linkedin"]
        )
        assert len(workflow.steps) >= 4


class TestWorkflow:
    def test_workflow_to_dict(self):
        workflow = Workflow(
            name="Test",
            steps=[{"name": "s1", "agent_role": "writer"}],
        )
        d = workflow.to_dict()
        assert d["name"] == "Test"
        assert len(d["steps"]) == 1

    def test_workflow_has_id(self):
        workflow = Workflow(name="Test", steps=[])
        assert workflow.id is not None
        assert len(workflow.id) > 0
