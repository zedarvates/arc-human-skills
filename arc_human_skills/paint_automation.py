"""Windows Paint automation for human-like drawing practice."""
import sys
import time
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import numpy as np
import cv2

IS_WINDOWS = sys.platform == "win32"

try:
    import pywinauto
    from pywinauto import Application, Desktop
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
except SystemExit:
    # pyautogui.mouseinfo requires tkinter on Linux - ignore for testing
    PYAUTOGUI_AVAILABLE = False

from arc_human_skills.config import load_config, PaintConfig

@dataclass
class Stroke:
    start: tuple[int, int]
    end: tuple[int, int]
    color: tuple[int, int, int] = (0, 0, 0)
    thickness: int = 2

class PaintController:
    """Controls Windows Paint for drawing practice."""
    
    def __init__(self, config: PaintConfig = None):
        self.config = config or load_config().paint
        self.app: Optional[Application] = None
        self.window = None
        self._canvas_rect = None
    
    def launch(self) -> bool:
        """Launch Paint and wait for ready."""
        if not PYWINAUTO_AVAILABLE:
            raise RuntimeError("pywinauto not installed")
        
        self.app = Application(backend="uia").start(self.config.exe_path)
        time.sleep(2)  # Wait for launch
        
        # Get main window
        self.window = Desktop(backend="uia").window(title_re=".*Paint.*")
        self.window.wait("visible ready", timeout=10)
        
        # Handle "Save changes?" dialog if appears
        try:
            dialog = Desktop(backend="uia").window(title="Paint")
            if dialog.exists():
                dialog.child_window(title="Don't Save", control_type="Button").click()
        except:
            pass
        
        return self.is_ready()
    
    def is_ready(self) -> bool:
        return self.window is not None and self.window.exists()
    
    def setup_canvas(self, width: int, height: int):
        """Resize canvas to exact dimensions."""
        if not self.is_ready():
            raise RuntimeError("Paint not ready")
        
        # Use Ctrl+W for Resize dialog (or ribbon)
        self.window.type_keys("^w")  # Ctrl+W = Resize
        time.sleep(0.5)
        
        resize_dialog = Desktop(backend="uia").window(title="Resize and Skew")
        if resize_dialog.exists():
            # Select "Pixels" radio
            resize_dialog.child_window(title="Pixels", control_type="RadioButton").click()
            # Enter dimensions
            horizontal = resize_dialog.child_window(auto_id="1003", control_type="Edit")  # Horizontal
            vertical = resize_dialog.child_window(auto_id="1004", control_type="Edit")    # Vertical
            horizontal.set_text(str(width))
            vertical.set_text(str(height))
            resize_dialog.child_window(title="OK", control_type="Button").click()
        
        time.sleep(0.5)
        self._update_canvas_rect()
    
    def _update_canvas_rect(self):
        """Get canvas rectangle in screen coordinates."""
        # Canvas is child of main window
        canvas = self.window.child_window(control_type="Image", found_index=0)
        if canvas.exists():
            rect = canvas.rectangle()
            self._canvas_rect = (rect.left, rect.top, rect.right, rect.bottom)
    
    def draw_stroke(self, stroke: Stroke):
        """Draw a single stroke on canvas."""
        if not self._canvas_rect:
            self._update_canvas_rect()
        if not self._canvas_rect:
            raise RuntimeError("Canvas not found")
        
        cx1, cy1, cx2, cy2 = self._canvas_rect
        
        # Convert canvas-relative to screen coordinates
        sx1, sy1 = cx1 + stroke.start[0], cy1 + stroke.start[1]
        sx2, sy2 = cx1 + stroke.end[0], cy1 + stroke.end[1]
        
        # Set brush color via ribbon (simplified - assumes black/default)
        # For full color support, would need ribbon navigation
        
        # Drag from start to end
        pyautogui.moveTo(sx1, sy1, duration=0.1)
        pyautogui.dragTo(sx2, sy2, duration=0.3, button='left')
        time.sleep(0.1)
    
    def screenshot(self) -> np.ndarray:
        """Capture canvas as numpy array."""
        if not self._canvas_rect:
            self._update_canvas_rect()
        if not self._canvas_rect:
            raise RuntimeError("Canvas not found")
        
        cx1, cy1, cx2, cy2 = self._canvas_rect
        img = pyautogui.screenshot(region=(cx1, cy1, cx2-cx1, cy2-cy1))
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    
    def save(self, path: str):
        """Save current canvas to file."""
        self.window.type_keys("^s")  # Ctrl+S
        time.sleep(0.5)
        
        save_dialog = Desktop(backend="uia").window(title="Save As")
        if save_dialog.exists():
            edit = save_dialog.child_window(control_type="Edit", found_index=0)
            edit.set_text(path)
            save_dialog.child_window(title="Save", control_type="Button").click()
            time.sleep(0.5)
    
    def close(self):
        """Close Paint without saving."""
        if self.app:
            try:
                self.window.type_keys("%fx")  # Alt+F, X (Close)
                time.sleep(0.3)
                # Don't save dialog
                try:
                    dialog = Desktop(backend="uia").window(title="Paint")
                    if dialog.exists():
                        dialog.child_window(title="Don't Save", control_type="Button").click()
                except:
                    pass
            except:
                pass
            self.app = None
            self.window = None