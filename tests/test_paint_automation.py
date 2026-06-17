"""Tests for Paint automation."""
import pytest
import sys
from arc_human_skills.paint_automation import PaintController, Stroke, IS_WINDOWS, PYAUTOGUI_AVAILABLE

# Skip tests on Linux/WSL where Paint automation isn't available
pytestmark = pytest.mark.skipif(
    not IS_WINDOWS or not PYAUTOGUI_AVAILABLE,
    reason="Paint automation tests require Windows with pyautogui/tkinter"
)

def test_paint_launch():
    """Paint should launch and be ready."""
    ctrl = PaintController()
    ctrl.launch()
    assert ctrl.is_ready()
    ctrl.close()

def test_canvas_setup():
    """Canvas should be set to configured size."""
    ctrl = PaintController()
    ctrl.launch()
    ctrl.setup_canvas(800, 600)
    img = ctrl.screenshot()
    assert img.shape[1] == 800  # width
    assert img.shape[0] == 600  # height
    ctrl.close()

def test_draw_stroke():
    """Should draw a straight line stroke."""
    ctrl = PaintController()
    ctrl.launch()
    ctrl.setup_canvas(800, 600)
    stroke = Stroke(start=(100, 100), end=(200, 100), color=(0,0,0), thickness=2)
    ctrl.draw_stroke(stroke)
    img = ctrl.screenshot()
    # Check middle of line - should be dark
    assert img[100, 150, 0] < 50  # Black pixel
    ctrl.close()

def test_save_image():
    """Should save canvas to file."""
    import tempfile
    ctrl = PaintController()
    ctrl.launch()
    ctrl.setup_canvas(400, 300)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
    ctrl.save(path)
    assert Path(path).exists()
    ctrl.close()