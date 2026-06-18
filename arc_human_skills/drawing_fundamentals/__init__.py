"""Drawing Fundamentals package for ARC-AGI-3 human skills."""

from .line_control import (
    LineControlExercise,
    LineControlParams,
    LineOrientation,
    LineQualityMetrics,
    evaluate_line_drawing,
    extract_stroke_pixels,
)

from .primitives_2d import (
    Primitive2DType,
    Primitive2DParams,
    PrimitiveQualityMetrics,
    get_primitive_strokes,
    evaluate_primitive_2d,
    PRIMITIVE_2D_CURRICULUM,
)

from .wireframe_3d import (
    Wireframe3DType,
    Wireframe3DParams,
    WireframeQualityMetrics,
    get_wireframe_strokes,
    WIREFRAME_3D_CURRICULUM,
)

from .perspective import (
    PerspectiveType,
    PerspectiveSetup,
    GridParams,
    get_ground_grid_strokes,
    get_ellipse_in_perspective,
    get_shadow_strokes,
    PERSPECTIVE_CURRICULUM,
    GRID_EXERCISES,
)

from .construction import (
    ConstructionType,
    ConstructionObject,
    SceneParams,
    render_scene,
    get_construction_curriculum,
)

from .curriculum import (
    DrawingLevel,
    SkillProgress,
    DrawingCurriculum,
    get_all_strokes_for_skill,
    DRAWING_FUNDAMENTALS_SKILLS,
)

__all__ = [
    # Line control
    "LineControlExercise",
    "LineControlParams",
    "LineOrientation",
    "LineQualityMetrics",
    "evaluate_line_drawing",
    "extract_stroke_pixels",
    
    # 2D primitives
    "Primitive2DType",
    "Primitive2DParams",
    "PrimitiveQualityMetrics",
    "get_primitive_strokes",
    "evaluate_primitive_2d",
    "PRIMITIVE_2D_CURRICULUM",
    
    # 3D wireframes
    "Wireframe3DType",
    "Wireframe3DParams",
    "WireframeQualityMetrics",
    "get_wireframe_strokes",
    "WIREFRAME_3D_CURRICULUM",
    
    # Perspective
    "PerspectiveType",
    "PerspectiveSetup",
    "GridParams",
    "get_ground_grid_strokes",
    "get_ellipse_in_perspective",
    "get_shadow_strokes",
    "PERSPECTIVE_CURRICULUM",
    "GRID_EXERCISES",
    
    # Construction
    "ConstructionType",
    "ConstructionObject",
    "SceneParams",
    "render_scene",
    "get_construction_curriculum",
    
    # Curriculum orchestration
    "DrawingLevel",
    "SkillProgress",
    "DrawingCurriculum",
    "get_all_strokes_for_skill",
    "DRAWING_FUNDAMENTALS_SKILLS",
]