"""
Example script showing how to use the AI Content OS Platform

This file demonstrates both the Video Generation Pipeline (src/)
and the backend API services.
"""

from src.main import VideoGenerationPipeline


def example_video_generation():
    """Basic example of video generation"""
    print("=== Video Generation Example ===\n")

    # Initialize pipeline
    pipeline = VideoGenerationPipeline()

    # Validate configuration first
    if not pipeline.validate_configuration():
        print("Configuration is invalid. Check config/config.yaml")
        return

    # Generate video
    video_path = pipeline.generate_video(
        topic="The Benefits of Meditation",
        output_filename="meditation_video.mp4"
    )

    print(f"\nVideo created: {video_path}")


def example_backend_api():
    """Example of using the backend API"""
    print("=== Backend API Example ===\n")

    from backend.services.model_router import ModelRouter, TaskType

    router = ModelRouter()

    # Select best model for writing
    model = router.select_model(TaskType.CONTENT_WRITING)
    print(f"Selected model: {model.model} ({model.provider})")

    # Estimate cost
    cost = router.estimate_cost(TaskType.CONTENT_WRITING, 1000, 500)
    print(f"Estimated cost: ${cost['estimated_cost_usd']:.6f}")


def example_content_pipeline():
    """Example of the multi-agent content pipeline"""
    print("=== Content Pipeline Example ===\n")

    from backend.agents.router import AgentRouter

    agent_router = AgentRouter()

    # List available agents
    agents = agent_router.list_agents()
    for agent in agents:
        print(f"  - {agent['name']}: {agent['description']}")


if __name__ == "__main__":
    print("AI Content OS - Examples\n")
    print("1. Video Generation (requires API keys)")
    print("2. Backend API")
    print("3. Content Pipeline")
    print()

    # Run examples (uncomment as needed)
    # example_video_generation()
    example_backend_api()
    example_content_pipeline()
