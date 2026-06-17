"""Tests for painting shapes."""
import pytest
from arc_human_skills.painting.shapes import (
    ShapeManager,
    ColorMixer,
    GuidedPaintingSession,
    SHAPE_TEMPLATES,
    PAINT_COLORS,
    COLOR_MIXES,
    LANDSCAPE_ELEMENTS,
    ShapeTemplate,
    ShapeType,
)

def test_shape_templates_exist():
    """All fundamental shape templates should be defined."""
    expected = ["circle", "square", "triangle", "rectangle", "oval", "star_5"]
    for name in expected:
        assert name in SHAPE_TEMPLATES
        template = SHAPE_TEMPLATES[name]
        assert isinstance(template, ShapeTemplate)
        assert len(template.strokes) > 0
        assert template.difficulty >= 1

def test_paint_colors_defined():
    """Standard MS Paint colors should be available."""
    essential = ["black", "white", "red", "green", "blue", "yellow", "brown"]
    for color in essential:
        assert color in PAINT_COLORS
        rgb = PAINT_COLORS[color]
        assert len(rgb) == 3
        assert all(0 <= c <= 255 for c in rgb)

def test_color_mixes():
    """Basic color mixing rules."""
    # Note: COLOR_MIXES uses sorted tuple keys
    assert COLOR_MIXES[("red", "yellow")] == "orange"
    assert COLOR_MIXES[("blue", "red")] == "purple"
    assert COLOR_MIXES[("blue", "yellow")] == "green"
    assert COLOR_MIXES[("green", "red")] == "brown"
    assert COLOR_MIXES[("red", "white")] == "pink"
    assert COLOR_MIXES[("blue", "white")] == "light_blue"
    assert COLOR_MIXES[("white", "yellow")] == "light_yellow"
    assert COLOR_MIXES[("black", "white")] == "gray"
    expected = ["sky_gradient", "happy_cloud", "happy_tree_trunk", 
                "happy_tree_foliage", "mountain", "water_reflection", "ground_grass"]
    for elem in expected:
        assert elem in LANDSCAPE_ELEMENTS
        assert "description" in LANDSCAPE_ELEMENTS[elem]
        assert "colors" in LANDSCAPE_ELEMENTS[elem]

def test_shape_manager_init():
    """Shape manager should initialize with templates."""
    mgr = ShapeManager()
    assert len(mgr.templates) >= len(SHAPE_TEMPLATES)

def test_get_template():
    """Should retrieve template by name."""
    mgr = ShapeManager()
    circle = mgr.get_template("circle")
    assert circle is not None
    assert circle.shape_type == ShapeType.CIRCLE
    assert len(circle.strokes) == 8  # 8 arc segments

def test_color_mixer():
    """Color mixer should return RGB values."""
    mixer = ColorMixer()
    red = mixer.get_color("red")
    assert red == (237, 28, 36)
    
    # Case insensitive
    RED = mixer.get_color("RED")
    assert RED == red

def test_color_mixing():
    """Should return mixed color name."""
    mixer = ColorMixer()
    assert mixer.mix_colors("red", "yellow") == "orange"
    assert mixer.mix_colors("yellow", "red") == "orange"  # Order independent
    # Note: dict key is sorted tuple, so ("green", "red") not ("red", "green")
    assert mixer.mix_colors("green", "red") == "brown"

def test_guided_session_elements():
    """Guided session should have landscape elements."""
    session = GuidedPaintingSession()
    cloud = session.get_element("happy_cloud")
    assert cloud is not None
    assert "white" in cloud["colors"]

def test_mesh_template_strokes():
    """All template strokes should have valid coordinates."""
    for name, template in SHAPE_TEMPLATES.items():
        for stroke in template.strokes:
            assert hasattr(stroke, 'start')
            assert hasattr(stroke, 'end')
            assert len(stroke.start) == 2
            assert len(stroke.end) == 2
            # Coordinates should be reasonable for size=100
            for coord in stroke.start + stroke.end:
                assert -100 <= coord <= 100