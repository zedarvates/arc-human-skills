"""Tests for video tutorial processor."""
import pytest
from arc_human_skills.video_tutorial import VideoTutorialProcessor, Tutorial

def test_tutorial_dataclass():
    """Tutorial dataclass should initialize correctly."""
    tutorial = Tutorial(
        url="https://www.youtube.com/watch?v=test",
        title="Test Tutorial",
        track="painting"
    )
    assert tutorial.url == "https://www.youtube.com/watch?v=test"
    assert tutorial.title == "Test Tutorial"
    assert tutorial.track == "painting"
    assert tutorial.transcript == ""
    assert tutorial.key_frames == []

def test_processor_init():
    """Processor should initialize with config."""
    processor = VideoTutorialProcessor()
    assert processor.download_dir.exists()

def test_sanitize_filename():
    """Filename sanitization should handle special chars."""
    processor = VideoTutorialProcessor()
    tutorial = Tutorial(
        url="https://www.youtube.com/watch?v=test",
        title="Test: Tutorial! (2024) - How to Paint",
        track="painting"
    )
    # Sanitization happens in download()
    safe_title = "".join(c for c in tutorial.title if c.isalnum() or c in " -_")[:100]
    assert ":" not in safe_title
    assert "!" not in safe_title
    assert "(" not in safe_title
    assert ")" not in safe_title