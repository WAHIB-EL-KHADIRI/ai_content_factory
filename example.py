"""
Example script showing how to use the Video Generation Pipeline
"""

from modules import VideoGenerationPipeline


def example_basic():
    """Basic example of video generation"""
    print("=== Basic Video Generation Example ===\n")
    
    # Initialize pipeline
    pipeline = VideoGenerationPipeline()
    
    # Generate video
    video_path = pipeline.generate_video(
        topic="The Benefits of Meditation",
        output_filename="meditation_video.mp4"
    )
    
    print(f"\n✅ Video created: {video_path}")


def example_custom_config():
    """Example with custom configuration"""
    print("=== Custom Configuration Example ===\n")
    
    # Use custom config file
    pipeline = VideoGenerationPipeline(config_path="my_config.yaml")
    
    video_path = pipeline.generate_video(
        topic="Climate Change Solutions"
    )
    
    print(f"\n✅ Video created: {video_path}")


def example_validation():
    """Example of configuration validation"""
    print("=== Configuration Validation Example ===\n")
    
    pipeline = VideoGenerationPipeline()
    
    # Validate configuration
    is_valid = pipeline.validate_configuration()
    
    if is_valid:
        print("✅ Configuration is valid!")
    else:
        print("❌ Configuration has errors. Please check config.yaml")


def example_batch():
    """Example of generating multiple videos"""
    print("=== Batch Video Generation Example ===\n")
    
    topics = [
        "The History of the Internet",
        "How Photosynthesis Works",
        "The Solar System Explained"
    ]
    
    pipeline = VideoGenerationPipeline()
    
    for i, topic in enumerate(topics):
        print(f"\nGenerating video {i+1}/{len(topics)}: {topic}")
        
        try:
            video_path = pipeline.generate_video(topic)
            print(f"✅ Created: {video_path}")
        except Exception as e:
            print(f"❌ Failed: {e}")


if __name__ == "__main__":
    # Run validation first
    example_validation()
    
    # Uncomment to run examples:
    # example_basic()
    # example_custom_config()
    # example_batch()
