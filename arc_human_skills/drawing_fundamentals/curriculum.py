"""Drawing Fundamentals Curriculum - Master orchestrator for all 4 levels."""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
import json
from pathlib import Path

from arc_human_skills.drawing_fundamentals.line_control import (
    LineControlExercise, LineControlParams, LineOrientation,
    LineQualityMetrics, evaluate_line_drawing
)
from arc_human_skills.drawing_fundamentals.primitives_2d import (
    Primitive2DType, Primitive2DParams, PrimitiveQualityMetrics,
    get_primitive_strokes, evaluate_primitive_2d, PRIMITIVE_2D_CURRICULUM
)
from arc_human_skills.drawing_fundamentals.wireframe_3d import (
    Wireframe3DType, Wireframe3DParams, WireframeQualityMetrics,
    get_wireframe_strokes, WIREFRAME_3D_CURRICULUM
)
from arc_human_skills.drawing_fundamentals.perspective import (
    PerspectiveType, PerspectiveSetup, GridParams,
    get_ground_grid_strokes, get_ellipse_in_perspective,
    get_shadow_strokes, PERSPECTIVE_CURRICULUM, GRID_EXERCISES
)
from arc_human_skills.drawing_fundamentals.construction import (
    ConstructionType, ConstructionObject, SceneParams,
    render_scene, get_construction_curriculum
)
from arc_human_skills.paint_automation import Stroke


class DrawingLevel(Enum):
    LEVEL_0_LINE_CONTROL = 0      # Pure motor control
    LEVEL_1_PRIMITIVES_2D = 1     # Basic 2D shapes
    LEVEL_2_WIREFRAME_3D = 2      # 3D wireframes + perspective
    LEVEL_3_PERSPECTIVE = 3       # Grids, ellipses, shadows
    LEVEL_4_CONSTRUCTION = 4      # Complex scenes


@dataclass
class SkillProgress:
    """Track progress on a specific skill."""
    skill_id: str
    level: DrawingLevel
    category: str
    attempts: int = 0
    successes: int = 0
    best_score: float = 0.0
    avg_score: float = 0.0
    mastered: bool = False
    last_attempt_metrics: Optional[Dict] = None


@dataclass
class DrawingCurriculum:
    """Complete curriculum state."""
    # Level 0
    line_exercises: List[LineControlParams] = field(default_factory=list)
    
    # Level 1
    primitive_exercises: List[Primitive2DParams] = field(default_factory=list)
    
    # Level 2
    wireframe_exercises: List[Wireframe3DParams] = field(default_factory=list)
    
    # Level 3
    perspective_setups: List[PerspectiveSetup] = field(default_factory=list)
    grid_exercises: List[GridParams] = field(default_factory=list)
    
    # Level 4
    construction_scenes: List[SceneParams] = field(default_factory=list)
    
    # Progress tracking
    progress: Dict[str, SkillProgress] = field(default_factory=dict)
    
    def __post_init__(self):
        self._load_default_curriculum()
    
    def _load_default_curriculum(self):
        """Load standard curriculum."""
        # Level 0: Line control
        ex = LineControlExercise()
        self.line_exercises = ex.exercises
        
        # Level 1: Primitives
        self.primitive_exercises = PRIMITIVE_2D_CURRICULUM
        
        # Level 2: Wireframes
        self.wireframe_exercises = WIREFRAME_3D_CURRICULUM
        
        # Level 3: Perspective
        self.perspective_setups = PERSPECTIVE_CURRICULUM
        self.grid_exercises = GRID_EXERCISES
        
        # Level 4: Construction
        self.construction_scenes = get_construction_curriculum()
        
        # Initialize progress tracking
        self._init_progress()
    
    def _init_progress(self):
        """Initialize all skills as unmastered."""
        # Level 0 skills
        for i, params in enumerate(self.line_exercises):
            skill_id = f"line_{params.orientation.value}_{i}"
            self.progress[skill_id] = SkillProgress(
                skill_id=skill_id,
                level=DrawingLevel.LEVEL_0_LINE_CONTROL,
                category=params.orientation.value
            )
        
        # Level 1 skills
        for i, params in enumerate(self.primitive_exercises):
            skill_id = f"primitive_{params.prim_type.value}_{i}"
            self.progress[skill_id] = SkillProgress(
                skill_id=skill_id,
                level=DrawingLevel.LEVEL_1_PRIMITIVES_2D,
                category=params.prim_type.value
            )
        
        # Level 2 skills
        for i, params in enumerate(self.wireframe_exercises):
            skill_id = f"wireframe_{params.wire_type.value}_{i}"
            self.progress[skill_id] = SkillProgress(
                skill_id=skill_id,
                level=DrawingLevel.LEVEL_2_WIREFRAME_3D,
                category=params.wire_type.value
            )
        
        # Level 3 skills
        for i, p in enumerate(self.perspective_setups):
            skill_id = f"perspective_{p.ptype.value}_{i}"
            self.progress[skill_id] = SkillProgress(
                skill_id=skill_id,
                level=DrawingLevel.LEVEL_3_PERSPECTIVE,
                category=p.ptype.value
            )
        for i, g in enumerate(self.grid_exercises):
            skill_id = f"grid_{g.perspective.ptype.value}_{i}"
            self.progress[skill_id] = SkillProgress(
                skill_id=skill_id,
                level=DrawingLevel.LEVEL_3_PERSPECTIVE,
                category="grid"
            )
        
        # Level 4 skills
        for i, scene in enumerate(self.construction_scenes):
            skill_id = f"construction_{scene.scene_type.value}_{i}"
            self.progress[skill_id] = SkillProgress(
                skill_id=skill_id,
                level=DrawingLevel.LEVEL_4_CONSTRUCTION,
                category=scene.scene_type.value
            )
    
    def get_next_unmastered(self, level: Optional[DrawingLevel] = None) -> Optional[SkillProgress]:
        """Get next unmastered skill, optionally filtered by level."""
        candidates = [
            p for p in self.progress.values()
            if not p.mastered and (level is None or p.level == level)
        ]
        if not candidates:
            return None
        
        # Sort by level, then by attempts (least attempted first)
        candidates.sort(key=lambda p: (p.level.value, p.attempts))
        return candidates[0]
    
    def record_attempt(self, skill_id: str, score: float, metrics: Dict):
        """Record an attempt for a skill."""
        if skill_id in self.progress:
            p = self.progress[skill_id]
            p.attempts += 1
            if score > 0.7:  # Success threshold
                p.successes += 1
            p.best_score = max(p.best_score, score)
            p.avg_score = ((p.avg_score * (p.attempts - 1)) + score) / p.attempts
            p.last_attempt_metrics = metrics
            
            # Mastery criteria
            if p.attempts >= 5 and p.avg_score >= 0.8 and p.best_score >= 0.85:
                p.mastered = True
    
    def get_level_completion(self, level: DrawingLevel) -> float:
        """Get completion percentage for a level (0-1)."""
        level_skills = [p for p in self.progress.values() if p.level == level]
        if not level_skills:
            return 1.0
        mastered = sum(1 for p in level_skills if p.mastered)
        return mastered / len(level_skills)
    
    def get_overall_completion(self) -> float:
        """Overall curriculum completion."""
        if not self.progress:
            return 0.0
        return sum(1 for p in self.progress.values() if p.mastered) / len(self.progress)
    
    def to_json(self) -> str:
        """Serialize curriculum state."""
        data = {
            'progress': {
                k: {
                    'skill_id': v.skill_id,
                    'level': v.level.value,
                    'category': v.category,
                    'attempts': v.attempts,
                    'successes': v.successes,
                    'best_score': v.best_score,
                    'avg_score': v.avg_score,
                    'mastered': v.mastered,
                    'last_attempt_metrics': v.last_attempt_metrics
                } for k, v in self.progress.items()
            }
        }
        return json.dumps(data, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'DrawingCurriculum':
        """Deserialize curriculum state."""
        curriculum = cls()
        data = json.loads(json_str)
        for k, v in data.get('progress', {}).items():
            curriculum.progress[k] = SkillProgress(
                skill_id=v['skill_id'],
                level=DrawingLevel(v['level']),
                category=v['category'],
                attempts=v['attempts'],
                successes=v['successes'],
                best_score=v['best_score'],
                avg_score=v['avg_score'],
                mastered=v['mastered'],
                last_attempt_metrics=v.get('last_attempt_metrics')
            )
        return curriculum


def get_all_strokes_for_skill(curriculum: DrawingCurriculum, skill_id: str) -> List[Stroke]:
    """Get all strokes needed to practice a specific skill."""
    # Parse skill_id to find the exercise
    parts = skill_id.split('_')
    if not parts:
        return []
    
    level_prefix = parts[0]
    
    if level_prefix == 'line':
        # Find matching line exercise
        orientation = '_'.join(parts[1:-1])
        idx = int(parts[-1])
        if 0 <= idx < len(curriculum.line_exercises):
            ex = LineControlExercise()
            stroke, _ = ex.get_all_strokes()[idx]
            return [stroke]
    
    elif level_prefix == 'primitive':
        prim_type = '_'.join(parts[1:-1])
        idx = int(parts[-1])
        if 0 <= idx < len(curriculum.primitive_exercises):
            params = curriculum.primitive_exercises[idx]
            return get_primitive_strokes(params)
    
    elif level_prefix == 'wireframe':
        wire_type = '_'.join(parts[1:-1])
        idx = int(parts[-1])
        if 0 <= idx < len(curriculum.wireframe_exercises):
            params = curriculum.wireframe_exercises[idx]
            return get_wireframe_strokes(params)
    
    elif level_prefix == 'perspective':
        # Horizon line + VPs
        ptype = '_'.join(parts[1:-1])
        idx = int(parts[-1])
        if 0 <= idx < len(curriculum.perspective_setups):
            p = curriculum.perspective_setups[idx]
            strokes = [get_horizon_line(p)]
            if p.vp1:
                # VP markers (small crosses)
                strokes.append(Stroke(
                    (p.vp1[0]-10, p.vp1[1]), (p.vp1[0]+10, p.vp1[1]), (255,0,0), 2
                ))
                strokes.append(Stroke(
                    (p.vp1[0], p.vp1[1]-10), (p.vp1[0], p.vp1[1]+10), (255,0,0), 2
                ))
            if p.vp2:
                strokes.append(Stroke(
                    (p.vp2[0]-10, p.vp2[1]), (p.vp2[0]+10, p.vp2[1]), (0,255,0), 2
                ))
                strokes.append(Stroke(
                    (p.vp2[0], p.vp2[1]-10), (p.vp2[0], p.vp2[1]+10), (0,255,0), 2
                ))
            return strokes
    
    elif level_prefix == 'grid':
        idx = int(parts[-1])
        if 0 <= idx < len(curriculum.grid_exercises):
            return get_ground_grid_strokes(curriculum.grid_exercises[idx])
    
    elif level_prefix == 'construction':
        scene_type = '_'.join(parts[1:-1])
        idx = int(parts[-1])
        if 0 <= idx < len(curriculum.construction_scenes):
            scene = curriculum.construction_scenes[idx]
            return render_scene(scene)
    
    return []


def get_horizon_line(perspective: PerspectiveSetup) -> Stroke:
    """Horizon line stroke."""
    w, _ = perspective.canvas_size
    return Stroke((0, perspective.horizon_y), (w, perspective.horizon_y), (200, 200, 200), 1)


# ============================================================
# SkillDAG Integration Manifest (Fragment)
# ============================================================

DRAWING_FUNDAMENTALS_SKILLS = [
    # Level 0: Line Control (no prerequisites)
    {"id": "line_horizontal", "name": "Horizontal Line", "level": 0,
     "prerequisites": [], "category": "motor_control"},
    {"id": "line_vertical", "name": "Vertical Line", "level": 0,
     "prerequisites": [], "category": "motor_control"},
    {"id": "line_diagonal_45", "name": "Diagonal 45°", "level": 0,
     "prerequisites": [], "category": "motor_control"},
    {"id": "line_diagonal_135", "name": "Diagonal 135°", "level": 0,
     "prerequisites": [], "category": "motor_control"},
    {"id": "pressure_fade_in", "name": "Pressure Fade In", "level": 0,
     "prerequisites": ["line_horizontal"], "category": "pressure_control"},
    {"id": "pressure_fade_out", "name": "Pressure Fade Out", "level": 0,
     "prerequisites": ["line_horizontal"], "category": "pressure_control"},
    {"id": "pressure_wave", "name": "Pressure Wave", "level": 0,
     "prerequisites": ["pressure_fade_in", "pressure_fade_out"], "category": "pressure_control"},
    
    # Level 1: 2D Primitives (require line skills)
    {"id": "prim_cross", "name": "Cross (+)", "level": 1,
     "prerequisites": ["line_horizontal", "line_vertical"], "category": "primitives"},
    {"id": "prim_square", "name": "Square", "level": 1,
     "prerequisites": ["line_horizontal", "line_vertical"], "category": "primitives"},
    {"id": "prim_rectangle", "name": "Rectangle", "level": 1,
     "prerequisites": ["prim_square"], "category": "primitives"},
    {"id": "prim_x_mark", "name": "X Mark (×)", "level": 1,
     "prerequisites": ["line_diagonal_45", "line_diagonal_135"], "category": "primitives"},
    {"id": "prim_diamond", "name": "Diamond", "level": 1,
     "prerequisites": ["prim_x_mark"], "category": "primitives"},
    {"id": "prim_equilateral_triangle", "name": "Equilateral Triangle", "level": 1,
     "prerequisites": ["line_diagonal_45"], "category": "primitives"},
    {"id": "prim_right_triangle", "name": "Right Triangle", "level": 1,
     "prerequisites": ["line_horizontal", "line_vertical", "line_diagonal_45"], "category": "primitives"},
    {"id": "prim_hexagon", "name": "Hexagon", "level": 1,
     "prerequisites": ["prim_equilateral_triangle"], "category": "primitives"},
    {"id": "prim_octagon", "name": "Octagon", "level": 1,
     "prerequisites": ["prim_square", "prim_diamond"], "category": "primitives"},
    {"id": "prim_circle", "name": "Circle", "level": 1,
     "prerequisites": ["pressure_wave"], "category": "primitives"},
    
    # Level 2: 3D Wireframes (require 2D primitives)
    {"id": "wire_cube_iso", "name": "Cube (Isometric)", "level": 2,
     "prerequisites": ["prim_square", "line_diagonal_45"], "category": "wireframe"},
    {"id": "wire_box_iso", "name": "Rectangular Box (Isometric)", "level": 2,
     "prerequisites": ["wire_cube_iso", "prim_rectangle"], "category": "wireframe"},
    {"id": "wire_cube_1pt", "name": "Cube (1pt Perspective)", "level": 2,
     "prerequisites": ["wire_cube_iso", "perspective_1pt"], "category": "wireframe"},
    {"id": "wire_cube_2pt", "name": "Cube (2pt Perspective)", "level": 2,
     "prerequisites": ["wire_cube_1pt", "perspective_2pt"], "category": "wireframe"},
    {"id": "wire_box_2pt", "name": "Box (2pt Perspective)", "level": 2,
     "prerequisites": ["wire_cube_2pt", "wire_box_iso"], "category": "wireframe"},
    {"id": "wire_pyramid_2pt", "name": "Square Pyramid (2pt)", "level": 2,
     "prerequisites": ["wire_cube_2pt", "prim_equilateral_triangle"], "category": "wireframe"},
    {"id": "wire_prism_2pt", "name": "Triangular Prism (2pt)", "level": 2,
     "prerequisites": ["wire_cube_2pt", "prim_equilateral_triangle"], "category": "wireframe"},
    {"id": "wire_cylinder_2pt", "name": "Cylinder (2pt Wire)", "level": 2,
     "prerequisites": ["wire_cube_2pt", "prim_circle", "perspective_ellipse"], "category": "wireframe"},
    {"id": "wire_cone_2pt", "name": "Cone (2pt Wire)", "level": 2,
     "prerequisites": ["wire_cube_2pt", "prim_equilateral_triangle"], "category": "wireframe"},
    
    # Level 3: Perspective (require wireframes)
    {"id": "perspective_1pt", "name": "1-Point Perspective Setup", "level": 3,
     "prerequisites": ["wire_cube_iso"], "category": "perspective"},
    {"id": "perspective_2pt", "name": "2-Point Perspective Setup", "level": 3,
     "prerequisites": ["perspective_1pt"], "category": "perspective"},
    {"id": "perspective_3pt", "name": "3-Point Perspective Setup", "level": 3,
     "prerequisites": ["perspective_2pt"], "category": "perspective"},
    {"id": "perspective_ellipse", "name": "Ellipse in Perspective", "level": 3,
     "prerequisites": ["perspective_2pt", "prim_circle"], "category": "perspective"},
    {"id": "perspective_grid_ground", "name": "Ground Grid Construction", "level": 3,
     "prerequisites": ["perspective_2pt"], "category": "grid"},
    {"id": "perspective_grid_vertical", "name": "Vertical Grid (Wall)", "level": 3,
     "prerequisites": ["perspective_grid_ground"], "category": "grid"},
    {"id": "perspective_measuring", "name": "Measuring Points", "level": 3,
     "prerequisites": ["perspective_grid_ground"], "category": "measurement"},
    {"id": "perspective_shadow", "name": "Shadow Construction", "level": 3,
     "prerequisites": ["perspective_2pt", "wire_cube_2pt"], "category": "lighting"},
    
    # Level 4: Construction (require all perspective)
    {"id": "construct_still_life", "name": "Still Life Composition", "level": 4,
     "prerequisites": ["wire_cube_2pt", "wire_cylinder_2pt", "prim_circle",
                      "perspective_grid_ground", "perspective_shadow"], "category": "scene"},
    {"id": "construct_interior", "name": "Interior Corner", "level": 4,
     "prerequisites": ["construct_still_life", "perspective_grid_vertical",
                      "perspective_measuring"], "category": "scene"},
    {"id": "construct_exterior", "name": "Building Exterior", "level": 4,
     "prerequisites": ["construct_still_life", "wire_pyramid_2pt",
                      "perspective_shadow"], "category": "scene"},
    
    # Transfer skills (connect to writing/painting)
    {"id": "transfer_line_to_stroke", "name": "Line Control → Writing Strokes", "level": 0,
     "prerequisites": ["line_horizontal", "line_vertical", "line_diagonal_45"], "category": "transfer"},
    {"id": "transfer_prim_to_letter", "name": "Primitives → Letter Forms", "level": 1,
     "prerequisites": ["prim_square", "prim_circle", "prim_equilateral_triangle",
                      "prim_cross", "prim_x_mark"], "category": "transfer"},
    {"id": "transfer_wire_to_shape", "name": "Wireframes → Painting Shapes", "level": 2,
     "prerequisites": ["wire_cube_iso", "wire_cylinder_2pt", "wire_cone_2pt"], "category": "transfer"},
]