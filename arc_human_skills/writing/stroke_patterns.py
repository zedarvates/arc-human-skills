"""Stroke pattern learning for writing track."""
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
import json
from pathlib import Path

from arc_human_skills.paint_automation import Stroke
from arc_human_skills.config import load_config

class StrokeType(Enum):
    """Basic stroke types for handwriting."""
    VERTICAL_DOWN = "vertical_down"
    VERTICAL_UP = "vertical_up"
    HORIZONTAL_LEFT = "horizontal_left"
    HORIZONTAL_RIGHT = "horizontal_right"
    DIAGONAL_DOWN_RIGHT = "diagonal_down_right"
    DIAGONAL_DOWN_LEFT = "diagonal_down_left"
    DIAGONAL_UP_RIGHT = "diagonal_up_right"
    DIAGONAL_UP_LEFT = "diagonal_up_left"
    CURVE_CW = "curve_clockwise"
    CURVE_CCW = "curve_counterclockwise"
    HOOK_RIGHT = "hook_right"
    HOOK_LEFT = "hook_left"

@dataclass
class StrokePattern:
    """A named stroke pattern with template strokes."""
    name: str
    stroke_type: StrokeType
    strokes: List[Stroke]  # Relative to origin (0,0)
    description: str = ""

# Fundamental stroke patterns (Zaner-Bloser / D'Nealian basics)
FUNDAMENTAL_STROKES = {
    "vertical_down": StrokePattern(
        name="Vertical Down",
        stroke_type=StrokeType.VERTICAL_DOWN,
        strokes=[Stroke((0, 0), (0, -50))],
        description="Straight line top to bottom"
    ),
    "vertical_up": StrokePattern(
        name="Vertical Up",
        stroke_type=StrokeType.VERTICAL_UP,
        strokes=[Stroke((0, -50), (0, 0))],
        description="Straight line bottom to top"
    ),
    "horizontal_right": StrokePattern(
        name="Horizontal Right",
        stroke_type=StrokeType.HORIZONTAL_RIGHT,
        strokes=[Stroke((0, 0), (50, 0))],
        description="Left to right line"
    ),
    "horizontal_left": StrokePattern(
        name="Horizontal Left",
        stroke_type=StrokeType.HORIZONTAL_LEFT,
        strokes=[Stroke((50, 0), (0, 0))],
        description="Right to left line"
    ),
    "diagonal_down_right": StrokePattern(
        name="Diagonal Down-Right",
        stroke_type=StrokeType.DIAGONAL_DOWN_RIGHT,
        strokes=[Stroke((0, 0), (50, -50))],
        description="Top-left to bottom-right"
    ),
    "diagonal_down_left": StrokePattern(
        name="Diagonal Down-Left",
        stroke_type=StrokeType.DIAGONAL_DOWN_LEFT,
        strokes=[Stroke((50, 0), (0, -50))],
        description="Top-right to bottom-left"
    ),
    "curve_cw_top": StrokePattern(
        name="Curve Clockwise (Top)",
        stroke_type=StrokeType.CURVE_CW,
        strokes=[
            Stroke((25, 0), (50, -15)),
            Stroke((50, -15), (35, -35)),
            Stroke((35, -35), (0, -50)),
        ],
        description="Clockwise curve from top-right"
    ),
    "curve_ccw_top": StrokePattern(
        name="Curve Counter-Clockwise (Top)",
        stroke_type=StrokeType.CURVE_CCW,
        strokes=[
            Stroke((25, 0), (0, -15)),
            Stroke((0, -15), (15, -35)),
            Stroke((15, -35), (50, -50)),
        ],
        description="Counter-clockwise curve from top-left"
    ),
    "hook_right": StrokePattern(
        name="Hook Right",
        stroke_type=StrokeType.HOOK_RIGHT,
        strokes=[
            Stroke((0, -50), (0, -25)),
            Stroke((0, -25), (15, -10)),
        ],
        description="Vertical down then hook right"
    ),
    "hook_left": StrokePattern(
        name="Hook Left",
        stroke_type=StrokeType.HOOK_LEFT,
        strokes=[
            Stroke((0, -50), (0, -25)),
            Stroke((0, -25), (-15, -10)),
        ],
        description="Vertical down then hook left"
    ),
}

# Letter compositions from fundamental strokes (simplified print/manuscript)
LETTER_COMPOSITIONS = {
    "A": [  # Diagonals + crossbar
        ("diagonal_down_left", (0, 0)),
        ("diagonal_down_right", (50, 0)),  # Adjusted origin
        ("horizontal_right", (12, -25)),   # Crossbar at middle
    ],
    "B": [  # Vertical + two curves
        ("vertical_down", (0, 0)),
        ("curve_cw_top", (0, 0)),
        ("curve_cw_top", (0, -25)),  # Lower curve
    ],
    "C": [  # Single large curve
        ("curve_ccw_top", (0, 0)),
    ],
    "D": [  # Vertical + large curve
        ("vertical_down", (0, 0)),
        ("curve_cw_top", (0, 0)),  # Big curve right side
    ],
    "E": [  # Vertical + 3 horizontals
        ("vertical_down", (0, 0)),
        ("horizontal_right", (0, 0)),       # Top
        ("horizontal_right", (0, -25)),     # Middle
        ("horizontal_right", (0, -50)),     # Bottom
    ],
    "F": [  # Vertical + 2 horizontals
        ("vertical_down", (0, 0)),
        ("horizontal_right", (0, 0)),       # Top
        ("horizontal_right", (0, -25)),     # Middle
    ],
    "G": [  # C + horizontal
        ("curve_ccw_top", (0, 0)),
        ("horizontal_right", (15, -50)),    # Bottom closure
    ],
    "H": [  # Two verticals + crossbar
        ("vertical_down", (0, 0)),
        ("vertical_down", (50, 0)),
        ("horizontal_right", (0, -25)),
    ],
    "I": [  # Single vertical + top/bottom bars
        ("vertical_down", (25, 0)),
        ("horizontal_right", (0, 0)),
        ("horizontal_right", (0, -50)),
    ],
    "J": [  # Vertical + hook left + top bar
        ("vertical_down", (25, 0)),
        ("hook_left", (0, -25)),
        ("horizontal_right", (0, 0)),
    ],
    "K": [  # Vertical + two diagonals
        ("vertical_down", (0, 0)),
        ("diagonal_down_right", (0, -15)),
        ("diagonal_down_right", (0, -35)),  # Inverted for lower
    ],
    "L": [  # Vertical + bottom horizontal
        ("vertical_down", (0, 0)),
        ("horizontal_right", (0, -50)),
    ],
    "M": [  # Two verticals + two diagonals meeting at top
        ("vertical_down", (0, 0)),
        ("vertical_down", (50, 0)),
        ("diagonal_down_left", (0, -50)),  # Left peak
        ("diagonal_down_right", (50, -50)),  # Right peak
    ],
    "N": [  # Two verticals + diagonal
        ("vertical_down", (0, 0)),
        ("vertical_down", (50, 0)),
        ("diagonal_down_right", (0, -50)),
    ],
    "O": [  # Large oval (two curves)
        ("curve_ccw_top", (0, 0)),
        ("curve_cw_top", (0, -25)),  # Lower half
    ],
    "P": [  # Vertical + top curve
        ("vertical_down", (0, 0)),
        ("curve_cw_top", (0, 0)),
    ],
    "Q": [  # O + diagonal tail
        ("curve_ccw_top", (0, 0)),
        ("curve_cw_top", (0, -25)),
        ("diagonal_down_right", (35, -50)),
    ],
    "R": [  # P + diagonal leg
        ("vertical_down", (0, 0)),
        ("curve_cw_top", (0, 0)),
        ("diagonal_down_right", (25, -25)),
    ],
    "S": [  # Two opposite curves
        ("curve_cw_top", (0, -15)),
        ("curve_ccw_top", (0, -35)),
    ],
    "T": [  # Top horizontal + vertical
        ("horizontal_right", (0, 0)),
        ("vertical_down", (25, 0)),
    ],
    "U": [  # Two verticals + bottom curve
        ("vertical_down", (0, 0)),
        ("vertical_down", (50, 0)),
        ("curve_ccw_top", (0, -50)),
    ],
    "V": [  # Two diagonals meeting at bottom
        ("diagonal_down_left", (0, 0)),
        ("diagonal_down_right", (0, -50)),
    ],
    "W": [  # Four diagonals (double V)
        ("diagonal_down_left", (0, 0)),
        ("diagonal_down_right", (0, -50)),
        ("diagonal_down_left", (50, -50)),
        ("diagonal_down_right", (50, -100)),
    ],
    "X": [  # Two crossing diagonals
        ("diagonal_down_right", (0, 0)),
        ("diagonal_down_left", (50, 0)),
    ],
    "Y": [  # V + vertical stem
        ("diagonal_down_left", (0, 0)),
        ("diagonal_down_right", (0, -50)),
        ("vertical_down", (25, -25)),
    ],
    "Z": [  # Top horizontal + diagonal + bottom horizontal
        ("horizontal_right", (0, 0)),
        ("diagonal_down_left", (50, 0)),
        ("horizontal_right", (0, -50)),
    ],
}

class StrokePatternManager:
    """Manages stroke patterns and letter compositions."""
    
    def __init__(self, config=None):
        self.config = config or load_config()
        self.storage_dir = Path(self.config.storage_root) / "patterns"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.patterns = dict(FUNDAMENTAL_STROKES)
        self.compositions = dict(LETTER_COMPOSITIONS)
    
    def get_stroke_pattern(self, name: str) -> Optional[StrokePattern]:
        """Get a fundamental stroke pattern by name."""
        return self.patterns.get(name)
    
    def get_letter_composition(self, letter: str) -> List[tuple]:
        """Get stroke sequence for a letter: list of (pattern_name, origin_offset)."""
        return self.compositions.get(letter.upper(), [])
    
    def expand_letter_strokes(self, letter: str, base_origin: tuple = (0, 0)) -> List[Stroke]:
        """Expand letter composition into absolute Stroke objects."""
        composition = self.get_letter_composition(letter)
        if not composition:
            return []
        
        strokes = []
        bx, by = base_origin
        
        for pattern_name, offset in composition:
            pattern = self.patterns.get(pattern_name)
            if not pattern:
                continue
            
            ox, oy = offset
            for stroke in pattern.strokes:
                # Apply base origin + letter offset + stroke coordinates
                new_stroke = Stroke(
                    start=(bx + ox + stroke.start[0], by + oy + stroke.start[1]),
                    end=(bx + ox + stroke.end[0], by + oy + stroke.end[1]),
                    color=stroke.color,
                    thickness=stroke.thickness
                )
                strokes.append(new_stroke)
        
        return strokes
    
    def save_custom_pattern(self, pattern: StrokePattern):
        """Save a custom stroke pattern to disk."""
        file_path = self.storage_dir / f"{pattern.name.lower().replace(' ', '_')}.json"
        data = {
            "name": pattern.name,
            "stroke_type": pattern.stroke_type.value,
            "strokes": [
                {"start": s.start, "end": s.end, "color": s.color, "thickness": s.thickness}
                for s in pattern.strokes
            ],
            "description": pattern.description
        }
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        self.patterns[pattern.name.lower().replace(' ', '_')] = pattern
    
    def load_custom_pattern(self, name: str) -> Optional[StrokePattern]:
        """Load a custom stroke pattern from disk."""
        file_path = self.storage_dir / f"{name}.json"
        if not file_path.exists():
            return None
        with open(file_path) as f:
            data = json.load(f)
        strokes = [Stroke(**s) for s in data["strokes"]]
        pattern = StrokePattern(
            name=data["name"],
            stroke_type=StrokeType(data["stroke_type"]),
            strokes=strokes,
            description=data["description"]
        )
        self.patterns[name] = pattern
        return pattern
    
    def list_all_patterns(self) -> Dict[str, StrokePattern]:
        """Return all available patterns (built-in + custom)."""
        return self.patterns.copy()
    
    def practice_stroke_sequence(self, paint_ctrl, pattern_name: str, origin: tuple = (400, 300)):
        """Draw a stroke pattern on Paint for practice."""
        pattern = self.get_stroke_pattern(pattern_name)
        if not pattern:
            raise ValueError(f"Pattern not found: {pattern_name}")
        
        ox, oy = origin
        for stroke in pattern.strokes:
            abs_stroke = Stroke(
                start=(ox + stroke.start[0], oy + stroke.start[1]),
                end=(ox + stroke.end[0], oy + stroke.end[1]),
                color=stroke.color,
                thickness=stroke.thickness
            )
            paint_ctrl.draw_stroke(abs_stroke)
        
        return len(pattern.strokes)


class WritingPracticeSession:
    """Manages writing practice: strokes -> letters -> words."""
    
    def __init__(self, config=None):
        self.config = config or load_config()
        self.pattern_mgr = StrokePatternManager(self.config)
        self.practice_per_session = self.config.learning_tracks["writing"].practice_per_session
        self.recognizer = None  # Lazy init
    
    def get_recognizer(self):
        if self.recognizer is None:
            from arc_human_skills.reading.recognizer import LetterRecognizer
            self.recognizer = LetterRecognizer(self.config)
        return self.recognizer
    
    def practice_fundamental_strokes(self, paint_ctrl, stroke_names: list[str] = None, reps: int = 3):
        """Practice fundamental stroke patterns."""
        if stroke_names is None:
            stroke_names = [
                "vertical_down", "horizontal_right",
                "diagonal_down_right", "diagonal_down_left",
                "curve_cw_top", "curve_ccw_top"
            ]
        
        results = []
        for name in stroke_names:
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
                
                # Draw pattern
                self.pattern_mgr.practice_stroke_sequence(paint_ctrl, name)
                
                # TODO: Evaluate with vision model
                results.append({"pattern": name, "rep": rep+1})
        
        return results
    
    def practice_letters(self, paint_ctrl, letters: list[str] = None, reps: int = 2):
        """Practice full letter compositions."""
        if letters is None:
            letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")[:10]
        
        recognizer = self.get_recognizer()
        results = []
        
        for letter in letters:
            composition = self.pattern_mgr.get_letter_composition(letter)
            if not composition:
                continue
            
            for rep in range(reps):
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
                
                # Draw letter using stroke patterns
                strokes = self.pattern_mgr.expand_letter_strokes(letter, (400, 300))
                for stroke in strokes:
                    paint_ctrl.draw_stroke(stroke)
                
                # Recognize
                result = recognizer.recognize_from_paint(paint_ctrl, letter)
                results.append({
                    "letter": letter,
                    "rep": rep+1,
                    "predicted": result.predicted_letter,
                    "confidence": result.confidence,
                    "correct": result.is_correct
                })
        
        return results