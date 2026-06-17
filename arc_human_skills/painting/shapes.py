"""Painting track - basic shapes, color mixing, guided painting for ARC-AGI-3."""
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional, Dict
import json
from pathlib import Path
import numpy as np
import cv2

from arc_human_skills.paint_automation import Stroke, PaintController
from arc_human_skills.config import load_config

class ShapeType(Enum):
    """Basic geometric shapes."""
    CIRCLE = "circle"
    SQUARE = "square"
    TRIANGLE = "triangle"
    RECTANGLE = "rectangle"
    OVAL = "oval"
    LINE = "line"
    CURVE = "curve"
    STAR = "star"
    HEART = "heart"

@dataclass
class ShapeTemplate:
    """Template for drawing a shape - sequence of strokes."""
    name: str
    shape_type: ShapeType
    strokes: List[Stroke]  # Relative to center (0,0), normalized to size=100
    description: str = ""
    difficulty: int = 1  # 1-5

# Fundamental shape templates (vector-like, resolution independent)
SHAPE_TEMPLATES = {
    "circle": ShapeTemplate(
        name="Circle",
        shape_type=ShapeType.CIRCLE,
        strokes=[
            # Approximate circle with 8 arc segments
            Stroke(( 0, -50), ( 35, -35)),
            Stroke(( 35, -35), ( 50,  0)),
            Stroke(( 50,  0), ( 35,  35)),
            Stroke(( 35,  35), ( 0,  50)),
            Stroke(( 0,  50), (-35,  35)),
            Stroke((-35,  35), (-50,  0)),
            Stroke((-50,  0), (-35, -35)),
            Stroke((-35, -35), ( 0, -50)),
        ],
        description="Continuous circular motion",
        difficulty=2
    ),
    "square": ShapeTemplate(
        name="Square",
        shape_type=ShapeType.SQUARE,
        strokes=[
            Stroke((-50, -50), (50, -50)),   # Top
            Stroke((50, -50), (50, 50)),     # Right
            Stroke((50, 50), (-50, 50)),     # Bottom
            Stroke((-50, 50), (-50, -50)),   # Left
        ],
        description="Four straight lines, 90° corners",
        difficulty=1
    ),
    "triangle": ShapeTemplate(
        name="Triangle",
        shape_type=ShapeType.TRIANGLE,
        strokes=[
            Stroke(( 0, -50), ( 43,  25)),   # Left side
            Stroke(( 43,  25), (-43,  25)),   # Base
            Stroke((-43,  25), ( 0, -50)),    # Right side
        ],
        description="Three straight lines meeting at points",
        difficulty=1
    ),
    "rectangle": ShapeTemplate(
        name="Rectangle",
        shape_type=ShapeType.RECTANGLE,
        strokes=[
            Stroke((-60, -40), (60, -40)),   # Top
            Stroke((60, -40), (60, 40)),     # Right
            Stroke((60, 40), (-60, 40)),     # Bottom
            Stroke((-60, 40), (-60, -40)),   # Left
        ],
        description="Four straight lines, 2:1 aspect ratio",
        difficulty=1
    ),
    "oval": ShapeTemplate(
        name="Oval",
        shape_type=ShapeType.OVAL,
        strokes=[
            Stroke(( 0, -40), ( 45, -20)),
            Stroke(( 45, -20), ( 50,  20)),
            Stroke(( 50,  20), ( 30,  40)),
            Stroke(( 30,  40), (-30,  40)),
            Stroke((-30,  40), (-50,  20)),
            Stroke((-50,  20), (-45, -20)),
            Stroke((-45, -20), ( 0, -40)),
        ],
        description="Elongated circle, 3:2 aspect",
        difficulty=2
    ),
    "star_5": ShapeTemplate(
        name="5-Point Star",
        shape_type=ShapeType.STAR,
        strokes=[
            Stroke(( 0, -50), ( 15, -10)),
            Stroke(( 15, -10), ( 50, -10)),
            Stroke(( 50, -10), ( 20,  15)),
            Stroke(( 20,  15), ( 30,  50)),
            Stroke(( 30,  50), ( 0,  25)),
            Stroke(( 0,  25), (-30,  50)),
            Stroke((-30,  50), (-20,  15)),
            Stroke((-20,  15), (-50, -10)),
            Stroke((-50, -10), (-15, -10)),
            Stroke((-15, -10), ( 0, -50)),
        ],
        description="Continuous 5-point star",
        difficulty=3
    ),
}

# Color mixing basics (RGB values for MS Paint standard palette)
PAINT_COLORS = {
    "black":       (0, 0, 0),
    "white":       (255, 255, 255),
    "red":         (237, 28, 36),
    "green":       (34, 177, 76),
    "blue":        (63, 72, 204),
    "yellow":      (255, 242, 0),
    "cyan":        (0, 162, 232),
    "magenta":     (236, 0, 140),
    "orange":      (255, 127, 39),
    "brown":       (136, 62, 18),
    "purple":      (163, 73, 164),
    "pink":        (255, 174, 201),
    "gray":        (136, 136, 136),
    "light_gray":  (200, 200, 200),
    "dark_gray":   (80, 80, 80),
    "dark_red":    (163, 0, 0),
    "dark_green":  (0, 128, 0),
    "dark_blue":   (0, 0, 128),
}

# Color mixing formulas (simplified subtractive mixing for paint)
# Keys are sorted tuples for consistent lookup
COLOR_MIXES = {
    ("red", "yellow"): "orange",
    ("blue", "red"): "purple",
    ("blue", "yellow"): "green",
    ("green", "red"): "brown",
    ("red", "white"): "pink",
    ("blue", "white"): "light_blue",
    ("white", "yellow"): "light_yellow",
    ("black", "white"): "gray",
    ("black", "red"): "dark_red",
    ("black", "green"): "dark_green",
    ("black", "blue"): "dark_blue",
}

# Bob Ross style landscape elements
LANDSCAPE_ELEMENTS = {
    "sky_gradient": {
        "description": "Blue to white gradient top to bottom",
        "colors": ["dark_blue", "blue", "light_blue", "white"],
        "strokes_type": "horizontal_bands"
    },
    "happy_cloud": {
        "description": "Fluffy white clouds with gray shadows",
        "colors": ["white", "light_gray"],
        "strokes_type": "circular_dabs"
    },
    "happy_tree_trunk": {
        "description": "Vertical brown trunk with texture",
        "colors": ["brown", "dark_brown"],
        "strokes_type": "vertical_with_texture"
    },
    "happy_tree_foliage": {
        "description": "Green rounded foliage clusters",
        "colors": ["green", "dark_green", "yellow"],
        "strokes_type": "circular_dabs_layered"
    },
    "mountain": {
        "description": "Triangular mountain with snow cap",
        "colors": ["dark_gray", "gray", "white"],
        "strokes_type": "triangle_with_highlight"
    },
    "water_reflection": {
        "description": "Horizontal mirror with ripples",
        "colors": ["blue", "light_blue", "white"],
        "strokes_type": "horizontal_ripples"
    },
    "ground_grass": {
        "description": "Green horizontal strokes for grass",
        "colors": ["green", "dark_green", "yellow"],
        "strokes_type": "short_horizontal"
    },
}


class ShapeManager:
    """Manages shape templates and drawing."""
    
    def __init__(self, config=None):
        self.config = config or load_config()
        self.storage_dir = Path(self.config.storage_root) / "shapes"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.templates = dict(SHAPE_TEMPLATES)
    
    def get_template(self, name: str) -> Optional[ShapeTemplate]:
        """Get shape template by name."""
        return self.templates.get(name.lower())
    
    def list_templates(self) -> Dict[str, ShapeTemplate]:
        """Return all available templates."""
        return self.templates.copy()
    
    def draw_shape(self, paint_ctrl: PaintController, shape_name: str, 
                   center: Tuple[int, int] = (400, 300), size: float = 1.0,
                   color: Tuple[int, int, int] = (0, 0, 0)):
        """Draw a shape on Paint canvas."""
        template = self.get_template(shape_name)
        if not template:
            raise ValueError(f"Shape not found: {shape_name}")
        
        cx, cy = center
        # MS Paint color selection would go here (ribbon navigation)
        # For now, assumes current color is set
        
        for stroke in template.strokes:
            # Scale and translate
            sx1 = cx + int(stroke.start[0] * size / 2)
            sy1 = cy + int(stroke.start[1] * size / 2)
            sx2 = cx + int(stroke.end[0] * size / 2)
            sy2 = cy + int(stroke.end[1] * size / 2)
            
            abs_stroke = Stroke(
                start=(sx1, sy1),
                end=(sx2, sy2),
                color=color,
                thickness=stroke.thickness
            )
            paint_ctrl.draw_stroke(abs_stroke)
        
        return len(template.strokes)
    
    def practice_shape_sequence(self, paint_ctrl: PaintController, 
                                 shape_names: List[str] = None,
                                 reps: int = 2):
        """Practice drawing a sequence of shapes."""
        if shape_names is None:
            shape_names = ["circle", "square", "triangle", "rectangle", "oval"]
        
        results = []
        for name in shape_names:
            for rep in range(reps):
                # Clear canvas
                paint_ctrl.window.type_keys("^n")
                import time
                time.sleep(0.3)
                try:
                    dialog = paint_ctrl.window.child_window(title="Paint")
                    if dialog.exists():
                        dialog.child_window(title="Don't Save", control_type="Button").click()
                except:
                    pass
                paint_ctrl.setup_canvas(800, 600)
                
                # Draw shape
                self.draw_shape(paint_ctrl, name)
                results.append({"shape": name, "rep": rep+1})
        
        return results


class ColorMixer:
    """Handles color selection and mixing for MS Paint."""
    
    def __init__(self, config=None):
        self.config = config or load_config()
        self.colors = dict(PAINT_COLORS)
        self.mixes = dict(COLOR_MIXES)
    
    def get_color(self, name: str) -> Optional[Tuple[int, int, int]]:
        """Get RGB color by name."""
        return self.colors.get(name.lower())
    
    def list_colors(self) -> Dict[str, Tuple[int, int, int]]:
        return self.colors.copy()
    
    def mix_colors(self, color1: str, color2: str) -> Optional[str]:
        """Get mixed color name."""
        key = tuple(sorted([color1.lower(), color2.lower()]))
        return self.mixes.get(key)
    
    def select_color_in_paint(self, paint_ctrl: PaintController, color_name: str) -> bool:
        """Select color in MS Paint ribbon (simplified)."""
        # This would require navigating the Paint color picker ribbon
        # For now, returns True as placeholder
        return True


class GuidedPaintingSession:
    """Follow-along painting tutorials (Bob Ross style)."""
    
    def __init__(self, config=None):
        self.config = config or load_config()
        self.shape_mgr = ShapeManager(self.config)
        self.color_mixer = ColorMixer(self.config)
        self.elements = dict(LANDSCAPE_ELEMENTS)
    
    def get_element(self, name: str) -> Optional[Dict]:
        """Get landscape element definition."""
        return self.elements.get(name.lower())
    
    def paint_sky(self, paint_ctrl: PaintController):
        """Paint sky gradient (top 40% of canvas)."""
        # Draw horizontal bands of blue shades
        colors = ["dark_blue", "blue", "light_blue", "white"]
        band_height = 240 // len(colors)  # Top 240px of 600px canvas
        
        for i, color_name in enumerate(colors):
            color = self.color_mixer.get_color(color_name)
            if not color:
                continue
            
            y_start = i * band_height
            y_end = y_start + band_height
            
            # Draw horizontal strokes across canvas
            for y in range(y_start, y_end, 2):
                paint_ctrl.draw_stroke(Stroke(
                    start=(0, y), end=(800, y), color=color, thickness=1
                ))
    
    def paint_cloud(self, paint_ctrl: PaintController, center: Tuple[int, int] = (400, 100)):
        """Paint a fluffy cloud using white circular dabs."""
        cx, cy = center
        white = self.color_mixer.get_color("white")
        light_gray = self.color_mixer.get_color("light_gray")
        
        # Main cloud body - overlapping circles
        for dx in [-60, -30, 0, 30, 60]:
            for dy in [-20, 0, 20]:
                if dx == 0 and dy == 0:
                    continue
                x, y = cx + dx, cy + dy
                r = 30 + abs(dx)//3
                self._draw_filled_circle(paint_ctrl, (x, y), r, white)
        
        # Shadows
        for dx in [-30, 30]:
            x, y = cx + dx, cy + 30
            self._draw_filled_circle(paint_ctrl, (x, y), 25, light_gray)
    
    def _draw_filled_circle(self, paint_ctrl: PaintController, center: Tuple[int, int], 
                            radius: int, color: Tuple[int, int, int]):
        """Draw filled circle via horizontal scanlines."""
        cx, cy = center
        for y in range(-radius, radius + 1):
            x_width = int((radius**2 - y**2)**0.5)
            paint_ctrl.draw_stroke(Stroke(
                start=(cx - x_width, cy + y),
                end=(cx + x_width, cy + y),
                color=color,
                thickness=2
            ))
    
    def paint_tree(self, paint_ctrl: PaintController, 
                   trunk_base: Tuple[int, int] = (400, 400)):
        """Paint a happy little tree."""
        x, y = trunk_base
        brown = self.color_mixer.get_color("brown")
        dark_green = self.color_mixer.get_color("dark_green")
        green = self.color_mixer.get_color("green")
        yellow = self.color_mixer.get_color("yellow")
        
        # Trunk
        for i in range(80):
            paint_ctrl.draw_stroke(Stroke(
                start=(x - 4, y - i), end=(x + 4, y - i), color=brown, thickness=2
            ))
        
        # Foliage - three green clusters
        foliage_centers = [(x, y - 80), (x - 50, y - 120), (x + 50, y - 120)]
        for fx, fy in foliage_centers:
            for r in [40, 35, 30, 25]:
                self._draw_filled_circle(paint_ctrl, (fx, fy), r, 
                    dark_green if r > 30 else (green if r > 25 else yellow))
    
    def paint_mountain(self, paint_ctrl: PaintController, 
                       peak: Tuple[int, int] = (400, 200), size: float = 1.0):
        """Paint a mountain with snow cap."""
        # Mountain body - large triangle
        dark_gray = self.color_mixer.get_color("dark_gray")
        self.shape_mgr.draw_shape(paint_ctrl, "triangle", peak, size * 2, dark_gray)
        
        # Snow cap - small white triangle at top
        white = self.color_mixer.get_color("white")
        snow_peak = (peak[0], peak[1] - int(60 * size))
        self.shape_mgr.draw_shape(paint_ctrl, "triangle", snow_peak, size * 0.3, white)
    
    def paint_happy_landscape(self, paint_ctrl: PaintController):
        """Complete Bob Ross style landscape."""
        # 1. Sky
        self.paint_sky(paint_ctrl)
        
        # 2. Mountains (background)
        self.paint_mountain(paint_ctrl, (200, 250), 0.8)
        self.paint_mountain(paint_ctrl, (600, 280), 0.6)
        
        # 3. Clouds
        self.paint_cloud(paint_ctrl, (150, 80))
        self.paint_cloud(paint_ctrl, (650, 120))
        
        # 4. Ground/Grass
        green = self.color_mixer.get_color("green")
        dark_green = self.color_mixer.get_color("dark_green")
        for y in range(350, 600, 3):
            color = dark_green if y > 500 else green
            paint_ctrl.draw_stroke(Stroke((0, y), (800, y), color=color, thickness=2))
        
        # 5. Trees
        self.paint_tree(paint_ctrl, (150, 550))
        self.paint_tree(paint_ctrl, (650, 550))
        self.paint_tree(paint_ctrl, (400, 450))
        
        # 6. Water reflection (bottom)
        blue = self.color_mixer.get_color("blue")
        for y in range(400, 450):
            paint_ctrl.draw_stroke(Stroke((0, y), (800, y), color=blue, thickness=1))


class PaintingPracticeSession:
    """Practice session for painting track."""
    
    def __init__(self, config=None):
        self.config = config or load_config()
        self.shape_mgr = ShapeManager(self.config)
        self.guided = GuidedPaintingSession(self.config)
        self.practice_per_session = self.config.learning_tracks["painting"].practice_per_session
    
    def practice_shapes(self, paint_ctrl: PaintController, 
                        shapes: List[str] = None, reps: int = 2):
        """Practice fundamental shapes."""
        if shapes is None:
            shapes = ["circle", "square", "triangle", "rectangle", "oval"]
        
        return self.shape_mgr.practice_shape_sequence(paint_ctrl, shapes, reps)
    
    def practice_landscape_elements(self, paint_ctrl: PaintController):
        """Practice individual landscape elements."""
        elements = ["sky_gradient", "happy_cloud", "happy_tree_trunk", 
                    "happy_tree_foliage", "mountain", "water_reflection"]
        
        results = []
        for element_name in elements:
            # Clear
            paint_ctrl.window.type_keys("^n")
            import time
            time.sleep(0.3)
            try:
                dialog = paint_ctrl.window.child_window(title="Paint")
                if dialog.exists():
                    dialog.child_window(title="Don't Save", control_type="Button").click()
            except:
                pass
            paint_ctrl.setup_canvas(800, 600)
            
            # Draw element (uses guided methods)
            if element_name == "sky_gradient":
                self.guided.paint_sky(paint_ctrl)
            elif element_name == "happy_cloud":
                self.guided.paint_cloud(paint_ctrl)
            elif element_name == "mountain":
                self.guided.paint_mountain(paint_ctrl)
            # ... etc
            
            results.append({"element": element_name})
        
        return results
    
    def paint_full_landscape(self, paint_ctrl: PaintController):
        """Paint complete guided landscape."""
        # Clear
        paint_ctrl.window.type_keys("^n")
        import time
        time.sleep(0.3)
        try:
            dialog = paint_ctrl.window.child_window(title="Paint")
            if dialog.exists():
                dialog.child_window(title="Don't Save", control_type="Button").click()
        except:
            pass
        paint_ctrl.setup_canvas(800, 600)
        
        self.guided.paint_happy_landscape(paint_ctrl)
        return {"type": "full_landscape"}