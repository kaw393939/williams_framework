"""
Configuration for YouTube integration tests.

This module provides test video configurations for different scenarios:
- Short videos (< 30 minutes): Quick testing
- Medium videos (30-60 minutes): Standard testing
- Long videos (3+ hours): Stress testing with segmentation

Configure via environment variables or use defaults.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class TestVideoConfig:
    """Configuration for a test video."""
    url: str
    video_id: str
    expected_duration_range: tuple[int, int]  # Min, max seconds
    description: str
    has_transcript: bool = True
    has_comments: bool = True


# Default test videos
DEFAULT_TEST_VIDEOS = {
    "short": TestVideoConfig(
        url="https://youtu.be/zZtHnwoZAT8",
        video_id="zZtHnwoZAT8",
        expected_duration_range=(600, 1800),  # 10-30 minutes
        description="Short test video (15 minutes)",
        has_transcript=True,
        has_comments=True
    ),
}


class YouTubeTestConfig:
    """Centralized configuration for YouTube integration tests."""
    
    def __init__(self):
        self.test_videos = self._load_test_videos()
        self.default_video = self.get_video("short")
    
    def _load_test_videos(self) -> dict[str, TestVideoConfig]:
        """Load test video configurations from environment or use defaults."""
        configs = {}
        
        # Short video (default)
        short_url = os.getenv("TEST_YOUTUBE_SHORT", DEFAULT_TEST_VIDEOS["short"].url)
        configs["short"] = TestVideoConfig(
            url=short_url,
            video_id=self._extract_video_id(short_url),
            expected_duration_range=(600, 1800),
            description="Short test video (10-30 minutes)"
        )
        
        # Medium video (optional)
        medium_url = os.getenv("TEST_YOUTUBE_MEDIUM")
        if medium_url:
            configs["medium"] = TestVideoConfig(
                url=medium_url,
                video_id=self._extract_video_id(medium_url),
                expected_duration_range=(1800, 3600),
                description="Medium test video (30-60 minutes)"
            )
        
        # Long video (optional - for stress testing)
        long_url = os.getenv("TEST_YOUTUBE_LONG")
        if long_url:
            configs["long"] = TestVideoConfig(
                url=long_url,
                video_id=self._extract_video_id(long_url),
                expected_duration_range=(10800, 14400),  # 3-4 hours
                description="Long test video (3+ hours)"
            )
        
        return configs
    
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL."""
        import re
        match = re.search(r"(?:v=|youtu\.be/)([\w-]+)", url)
        if match:
            return match.group(1)
        return ""
    
    def get_video(self, size: str = "short") -> TestVideoConfig:
        """Get test video configuration by size."""
        if size not in self.test_videos:
            # Fall back to short video
            return self.test_videos["short"]
        return self.test_videos[size]
    
    def get_default_url(self) -> str:
        """Get default test video URL."""
        return os.getenv("TEST_YOUTUBE_URL", self.default_video.url)
    
    def has_video(self, size: str) -> bool:
        """Check if a test video is configured for the given size."""
        return size in self.test_videos
    
    def list_configured_videos(self) -> list[str]:
        """List all configured test video sizes."""
        return list(self.test_videos.keys())


# Global configuration instance
youtube_test_config = YouTubeTestConfig()


# Convenience functions
def get_test_video_url(size: str = "short") -> str:
    """Get test video URL by size."""
    return youtube_test_config.get_video(size).url


def get_test_video_config(size: str = "short") -> TestVideoConfig:
    """Get full test video configuration."""
    return youtube_test_config.get_video(size)


def has_long_video_configured() -> bool:
    """Check if long video testing is configured."""
    return youtube_test_config.has_video("long")


# Test configuration display
def print_test_configuration():
    """Print current test configuration."""
    print("\n" + "="*60)
    print("YouTube Integration Test Configuration")
    print("="*60)
    
    configured = youtube_test_config.list_configured_videos()
    print(f"\nConfigured video sizes: {', '.join(configured)}")
    
    for size in configured:
        video = youtube_test_config.get_video(size)
        print(f"\n{size.upper()}:")
        print(f"  URL: {video.url}")
        print(f"  Video ID: {video.video_id}")
        print(f"  Expected duration: {video.expected_duration_range[0]}-{video.expected_duration_range[1]}s")
        print(f"  Description: {video.description}")
    
    print("\n" + "="*60)
    print("\nEnvironment Variables:")
    print("  TEST_YOUTUBE_URL     - Override default test video")
    print("  TEST_YOUTUBE_SHORT   - Short video (< 30 min)")
    print("  TEST_YOUTUBE_MEDIUM  - Medium video (30-60 min)")
    print("  TEST_YOUTUBE_LONG    - Long video (3+ hours)")
    print("\nExample:")
    print('  export TEST_YOUTUBE_URL="https://youtu.be/YOUR_VIDEO_ID"')
    print("="*60 + "\n")


if __name__ == "__main__":
    print_test_configuration()
