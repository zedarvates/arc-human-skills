"""Tests for writing stroke patterns."""
import pytest
from arc_human_skills.writing.stroke_patterns import (
    StrokePatternManager,
    FUNDAMENTAL_STROKES,
    LETTER_COMPOSITIONS,
    StrokePattern,
    StrokeType,
)
from arc_human_skills.paint_automation import Stroke

def test_fundamental_strokes_exist():
    """All fundamental stroke patterns should be defined."""
    expected = [
        "vertical_down", "vertical_up", "horizontal_right", "horizontal_left",
        "diagonal_down_right", "diagonal_down_left",
        "curve_cw_top", "curve_ccw_top", "hook_right", "hook_left"
    ]
    for name in expected:
        assert name in FUNDAMENTAL_STROKES
        pattern = FUNDAMENTAL_STROKES[name]
        assert isinstance(pattern, StrokePattern)
        assert len(pattern.strokes) > 0

def test_letter_compositions_exist():
    """All 26 letters should have compositions."""
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        assert letter in LETTER_COMPOSITIONS
        comp = LETTER_COMPOSITIONS[letter]
        assert len(comp) > 0
        for pattern_name, offset in comp:
            assert pattern_name in FUNDAMENTAL_STROKES

def test_stroke_pattern_manager_init():
    """Manager should initialize with all patterns."""
    mgr = StrokePatternManager()
    assert len(mgr.patterns) >= len(FUNDAMENTAL_STROKES)
    assert len(mgr.compositions) >= 26

def test_get_letter_composition():
    """Should return stroke sequence for letter."""
    mgr = StrokePatternManager()
    comp = mgr.get_letter_composition("A")
    assert len(comp) == 3  # Two diagonals + crossbar
    assert comp[0][0] == "diagonal_down_left"

def test_expand_letter_strokes():
    """Should expand letter into absolute strokes."""
    mgr = StrokePatternManager()
    strokes = mgr.expand_letter_strokes("A", (100, 100))
    assert len(strokes) > 0
    for stroke in strokes:
        assert isinstance(stroke, Stroke)
        assert len(stroke.start) == 2
        assert len(stroke.end) == 2

def test_invalid_letter_returns_empty():
    """Invalid letter should return empty list."""
    mgr = StrokePatternManager()
    strokes = mgr.expand_letter_strokes("?")
    assert strokes == []

def test_custom_pattern_save_load(tmp_path):
    """Should save and load custom patterns."""
    import json
    mgr = StrokePatternManager()
    mgr.storage_dir = tmp_path
    
    custom = StrokePattern(
        name="Test Pattern",
        stroke_type=StrokeType.VERTICAL_DOWN,
        strokes=[Stroke((0,0), (0, -30))],
        description="Custom test"
    )
    mgr.save_custom_pattern(custom)
    
    # Should be loadable
    loaded = mgr.load_custom_pattern("test_pattern")
    assert loaded is not None
    assert loaded.name == "Test Pattern"
    assert loaded.stroke_type == StrokeType.VERTICAL_DOWN