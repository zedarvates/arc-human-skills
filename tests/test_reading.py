"""Tests for letter recognizer."""
import pytest
import numpy as np
from arc_human_skills.reading.recognizer import LetterRecognizer, ReadingPracticeSession, RecognitionResult
from arc_human_skills.paint_automation import IS_WINDOWS, PYAUTOGUI_AVAILABLE

# Skip on Linux/WSL where Paint automation isn't available
pytestmark = pytest.mark.skipif(
    not IS_WINDOWS or not PYAUTOGUI_AVAILABLE,
    reason="Paint automation tests require Windows with pyautogui/tkinter"
)

def test_recognizer_init():
    """Recognizer should initialize with config."""
    recognizer = LetterRecognizer()
    assert recognizer.vision_model == "qwen3.6-27b"
    assert recognizer.localai_url == "http://192.168.1.47:8080"

def test_preprocess_canvas():
    """Canvas preprocessing should produce 224x224 3-channel image."""
    recognizer = LetterRecognizer()
    # Create test canvas (white background with black stroke)
    canvas = np.ones((600, 800, 3), dtype=np.uint8) * 255
    cv2.line(canvas, (100, 100), (200, 100), (0, 0, 0), 5)
    
    processed = recognizer._preprocess_canvas(canvas)
    assert processed.shape == (224, 224, 3)
    assert processed.dtype == np.uint8

def test_build_prompt():
    """Prompt building should include target letter."""
    recognizer = LetterRecognizer()
    prompt_with = recognizer._build_recognition_prompt("A")
    prompt_without = recognizer._build_recognition_prompt("")
    
    assert "A" in prompt_with
    assert "letter" in prompt_with
    assert "confidence" in prompt_with
    assert "JSON" in prompt_without

def test_parse_response():
    """Response parsing should extract letter and confidence."""
    recognizer = LetterRecognizer()
    
    # Valid JSON response
    content = '{"letter": "A", "confidence": 0.85, "reasoning": "Clear shape"}'
    result = recognizer._parse_recognition_response(content, "A")
    assert result.predicted_letter == "A"
    assert result.confidence == 0.85
    assert result.is_correct == True
    
    # Incorrect prediction
    result = recognizer._parse_recognition_response(content, "B")
    assert result.is_correct == False
    
    # Malformed response
    result = recognizer._parse_recognition_response("no json here", "A")
    assert result.predicted_letter == "?"
    assert result.confidence == 0.0

def test_letter_stroke_patterns():
    """Stroke patterns should return valid strokes for known letters."""
    session = ReadingPracticeSession()
    
    for letter in ["A", "B", "C"]:
        strokes = session._get_letter_stroke_pattern(letter)
        assert len(strokes) > 0
        for stroke in strokes:
            assert hasattr(stroke, 'start')
            assert hasattr(stroke, 'end')
            assert len(stroke.start) == 2
            assert len(stroke.end) == 2

def test_practice_session_init():
    """Practice session should initialize with config."""
    session = ReadingPracticeSession()
    assert session.practice_per_session == 10

# Need cv2 for test_preprocess_canvas
import cv2