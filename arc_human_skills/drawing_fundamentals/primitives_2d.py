"""2D Primitives - Level 1: Square, Circle, Triangle, Cross, X, Diamond, Hexagon."""
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum
import math
import numpy as np
import cv2

from arc_human_skills.paint_automation import Stroke
from arc_human_skills.drawing_fundamentals.line_control import (
    LineOrientation, LineQualityMetrics, evaluate_line_drawing
)


class Primitive2DType(Enum):
    SQUARE = "square"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    EQUILATERAL_TRIANGLE = "equilateral_triangle"
    RIGHT_TRIANGLE = "right_triangle"
    CROSS = "cross"           # + shape
    X_MARK = "x_mark"         # × shape
    DIAMOND = "diamond"       # ◊ rotated square
    HEXAGON = "hexagon"
    OCTAGON = "octagon"


@dataclass
class Primitive2DParams:
    """Parameters for drawing a 2D primitive."""
    prim_type: Primitive2DType
    center: Tuple[int, int]
    size: float  # Primary size (side length for square, radius for circle, etc.)
    size_secondary: Optional[float] = None  # For rectangle: height
    rotation_deg: float = 0.0
    thickness: int = 2
    
    # Quality thresholds for evaluation
    angle_tolerance_deg: float = 3.0
    length_tolerance_pct: float = 5.0
    closure_tolerance_px: float = 5.0
    symmetry_tolerance_px: float = 5.0


@dataclass
class PrimitiveQualityMetrics:
    """Quality metrics for a 2D primitive."""
    # Per-edge metrics
    edge_metrics: List[LineQualityMetrics]
    
    # Global shape metrics
    closure_gap_px: float  # Distance between start and end
    angle_errors_deg: List[float]  # Deviation from ideal angles
    length_errors_pct: List[float]  # Deviation from ideal side lengths
    
    # Symmetry
    bilateral_symmetry_score: float  # 0-1
    radial_symmetry_score: float  # 0-1 (for regular polygons)
    
    # Overall
    is_closed: bool
    composite_score: float  # 0-1


def get_primitive_strokes(params: Primitive2DParams) -> List[Stroke]:
    """Generate strokes for a 2D primitive."""
    cx, cy = params.center
    s = params.size
    s2 = params.size_secondary if params.size_secondary else s
    rot = math.radians(params.rotation_deg)
    t = params.thickness
    
    def rotate(x: float, y: float) -> Tuple[int, int]:
        xr = x * math.cos(rot) - y * math.sin(rot)
        yr = x * math.sin(rot) + y * math.cos(rot)
        return (cx + int(xr), cy + int(yr))
    
    strokes = []
    
    if params.prim_type == Primitive2DType.SQUARE:
        # 4 corners: (-s,-s), (s,-s), (s,s), (-s,s)
        corners = [rotate(-s, -s), rotate(s, -s), rotate(s, s), rotate(-s, s)]
        for i in range(4):
            strokes.append(Stroke(corners[i], corners[(i+1)%4], (0,0,0), t))
    
    elif params.prim_type == Primitive2DType.RECTANGLE:
        # width=s, height=s2
        corners = [rotate(-s, -s2), rotate(s, -s2), rotate(s, s2), rotate(-s, s2)]
        for i in range(4):
            strokes.append(Stroke(corners[i], corners[(i+1)%4], (0,0,0), t))
    
    elif params.prim_type == Primitive2DType.CIRCLE:
        # Approximate with 16 segments
        n_segments = 16
        for i in range(n_segments):
            a1 = 2 * math.pi * i / n_segments
            a2 = 2 * math.pi * (i + 1) / n_segments
            p1 = rotate(s * math.cos(a1), s * math.sin(a1))
            p2 = rotate(s * math.cos(a2), s * math.sin(a2))
            strokes.append(Stroke(p1, p2, (0,0,0), t))
    
    elif params.prim_type == Primitive2DType.EQUILATERAL_TRIANGLE:
        # Height = s * sqrt(3)
        h = s * math.sqrt(3)
        # Top vertex, bottom-left, bottom-right
        corners = [rotate(0, -h*2/3), rotate(-s, h/3), rotate(s, h/3)]
        for i in range(3):
            strokes.append(Stroke(corners[i], corners[(i+1)%3], (0,0,0), t))
    
    elif params.prim_type == Primitive2DType.RIGHT_TRIANGLE:
        # Right angle at bottom-left
        corners = [rotate(-s, s), rotate(-s, -s), rotate(s, -s)]
        for i in range(3):
            strokes.append(Stroke(corners[i], corners[(i+1)%3], (0,0,0), t))
    
    elif params.prim_type == Primitive2DType.CROSS:
        # Vertical + horizontal
        v_len = s * 1.5
        h_len = s * 1.5
        strokes.append(Stroke(rotate(0, -v_len), rotate(0, v_len), (0,0,0), t))
        strokes.append(Stroke(rotate(-h_len, 0), rotate(h_len, 0), (0,0,0), t))
    
    elif params.prim_type == Primitive2DType.X_MARK:
        # Two diagonals
        d = s * 1.4
        strokes.append(Stroke(rotate(-d, -d), rotate(d, d), (0,0,0), t))
        strokes.append(Stroke(rotate(-d, d), rotate(d, -d), (0,0,0), t))
    
    elif params.prim_type == Primitive2DType.DIAMOND:
        # Rotated square 45 degrees
        corners = [rotate(0, -s), rotate(s, 0), rotate(0, s), rotate(-s, 0)]
        for i in range(4):
            strokes.append(Stroke(corners[i], corners[(i+1)%4], (0,0,0), t))
    
    elif params.prim_type == Primitive2DType.HEXAGON:
        n = 6
        for i in range(n):
            a1 = 2 * math.pi * i / n - math.pi / 2  # Flat top
            a2 = 2 * math.pi * (i + 1) / n - math.pi / 2
            p1 = rotate(s * math.cos(a1), s * math.sin(a1))
            p2 = rotate(s * math.cos(a2), s * math.sin(a2))
            strokes.append(Stroke(p1, p2, (0,0,0), t))
    
    elif params.prim_type == Primitive2DType.OCTAGON:
        n = 8
        for i in range(n):
            a1 = 2 * math.pi * i / n
            a2 = 2 * math.pi * (i + 1) / n
            p1 = rotate(s * math.cos(a1), s * math.sin(a1))
            p2 = rotate(s * math.cos(a2), s * math.sin(a2))
            strokes.append(Stroke(p1, p2, (0,0,0), t))
    
    return strokes


def get_ideal_vertices(params: Primitive2DParams) -> List[Tuple[float, float]]:
    """Get ideal vertex positions for a primitive (for evaluation)."""
    cx, cy = params.center
    s = params.size
    s2 = params.size_secondary if params.size_secondary else s
    rot = math.radians(params.rotation_deg)
    
    def rotate(x: float, y: float) -> Tuple[float, float]:
        xr = x * math.cos(rot) - y * math.sin(rot)
        yr = x * math.sin(rot) + y * math.cos(rot)
        return (cx + xr, cy + yr)
    
    if params.prim_type in [Primitive2DType.SQUARE, Primitive2DType.DIAMOND]:
        if params.prim_type == Primitive2DType.DIAMOND:
            return [rotate(0, -s), rotate(s, 0), rotate(0, s), rotate(-s, 0)]
        return [rotate(-s, -s), rotate(s, -s), rotate(s, s), rotate(-s, s)]
    
    elif params.prim_type == Primitive2DType.RECTANGLE:
        return [rotate(-s, -s2), rotate(s, -s2), rotate(s, s2), rotate(-s, s2)]
    
    elif params.prim_type == Primitive2DType.EQUILATERAL_TRIANGLE:
        h = s * math.sqrt(3)
        return [rotate(0, -h*2/3), rotate(-s, h/3), rotate(s, h/3)]
    
    elif params.prim_type == Primitive2DType.RIGHT_TRIANGLE:
        return [rotate(-s, s), rotate(-s, -s), rotate(s, -s)]
    
    elif params.prim_type == Primitive2DType.CROSS:
        # Return endpoints of both lines
        v = s * 1.5
        h = s * 1.5
        return [rotate(0, -v), rotate(0, v), rotate(-h, 0), rotate(h, 0)]
    
    elif params.prim_type == Primitive2DType.X_MARK:
        d = s * 1.4
        return [rotate(-d, -d), rotate(d, d), rotate(-d, d), rotate(d, -d)]
    
    elif params.prim_type == Primitive2DType.HEXAGON:
        n = 6
        return [rotate(s * math.cos(2*math.pi*i/n - math.pi/2), 
                       s * math.sin(2*math.pi*i/n - math.pi/2)) for i in range(n)]
    
    elif params.prim_type == Primitive2DType.OCTAGON:
        n = 8
        return [rotate(s * math.cos(2*math.pi*i/n), 
                       s * math.sin(2*math.pi*i/n)) for i in range(n)]
    
    elif params.prim_type == Primitive2DType.CIRCLE:
        # Return 16 sample points
        n = 16
        return [rotate(s * math.cos(2*math.pi*i/n), s * math.sin(2*math.pi*i/n)) for i in range(n)]
    
    return []


def evaluate_primitive_2d(
    drawn_pixels_by_stroke: List[List[Tuple[int, int]]],
    params: Primitive2DParams
) -> PrimitiveQualityMetrics:
    """
    Evaluate a drawn 2D primitive.
    drawn_pixels_by_stroke: list of pixel lists, one per stroke
    """
    ideal_vertices = get_ideal_vertices(params)
    n_edges = len(ideal_vertices)
    
    if n_edges == 0:
        return PrimitiveQualityMetrics(
            edge_metrics=[],
            closure_gap_px=999, angle_errors_deg=[], length_errors_pct=[],
            bilateral_symmetry_score=0, radial_symmetry_score=0,
            is_closed=False, composite_score=0
        )
    
    edge_metrics = []
    angle_errors = []
    length_errors = []
    
    # Evaluate each edge (stroke)
    for i, drawn_pixels in enumerate(drawn_pixels_by_stroke):
        if len(drawn_pixels) < 2:
            # Create dummy metric for missing stroke
            edge_metrics.append(LineQualityMetrics(
                start_error_px=999, end_error_px=999,
                max_deviation_px=999, rmse_deviation_px=999, straightness_score=0,
                target_angle_rad=0, actual_angle_rad=0, angle_error_deg=999,
                mean_thickness=0, thickness_std=0, thickness_consistency=0,
                target_length=0, actual_length=0, length_error_pct=100,
                composite_score=0
            ))
            angle_errors.append(999)
            length_errors.append(100)
            continue
        
        # Determine target for this edge
        start_ideal = ideal_vertices[i]
        end_ideal = ideal_vertices[(i + 1) % n_edges]
        
        target_vec = np.array(end_ideal) - np.array(start_ideal)
        target_length = np.linalg.norm(target_vec)
        target_angle = math.atan2(target_vec[1], target_vec[0])
        
        # Create dummy params for line evaluation
        from arc_human_skills.drawing_fundamentals.line_control import LineControlParams, LineOrientation
        dummy_params = LineControlParams(
            orientation=LineOrientation.FREE,
            start=(int(start_ideal[0]), int(start_ideal[1])),
            length=int(target_length),
            target_thickness=params.thickness
        )
        
        metrics = evaluate_line_drawing(drawn_pixels, dummy_params)
        
        # Override with actual target angle/length
        metrics.target_angle_rad = target_angle
        metrics.target_length = float(target_length)
        metrics.angle_error_deg = float(abs(metrics.actual_angle_rad - target_angle))
        metrics.angle_error_deg = min(metrics.angle_error_deg, 2*math.pi - metrics.angle_error_deg)
        metrics.angle_error_deg = math.degrees(metrics.angle_error_deg)
        
        edge_metrics.append(metrics)
        angle_errors.append(metrics.angle_error_deg)
        length_errors.append(metrics.length_error_pct)
    
    # Closure gap (last point to first point)
    if drawn_pixels_by_stroke and drawn_pixels_by_stroke[0] and drawn_pixels_by_stroke[-1]:
        first_pt = np.array(drawn_pixels_by_stroke[0][0])
        last_pt = np.array(drawn_pixels_by_stroke[-1][-1])
        closure_gap = float(np.linalg.norm(last_pt - first_pt))
        is_closed = closure_gap <= params.closure_tolerance_px
    else:
        closure_gap = 999
        is_closed = False
    
    # Symmetry scores (simplified)
    bilateral_symmetry = _compute_bilateral_symmetry(drawn_pixels_by_stroke, params)
    radial_symmetry = _compute_radial_symmetry(drawn_pixels_by_stroke, params)
    
    # Composite score
    valid_edges = [m for m in edge_metrics if m.composite_score > 0]
    if valid_edges:
        avg_edge_score = np.mean([m.composite_score for m in valid_edges])
        closure_score = max(0, 1 - closure_gap / 20.0)
        angle_score = max(0, 1 - np.mean([e for e in angle_errors if e < 999]) / 15.0) if angle_errors else 0
        length_score = max(0, 1 - np.mean([e for e in length_errors if e < 100]) / 20.0) if length_errors else 0
        
        composite = (
            0.4 * avg_edge_score +
            0.2 * closure_score +
            0.2 * angle_score +
            0.1 * length_score +
            0.1 * bilateral_symmetry
        )
    else:
        composite = 0.0
    
    return PrimitiveQualityMetrics(
        edge_metrics=edge_metrics,
        closure_gap_px=closure_gap,
        angle_errors_deg=angle_errors,
        length_errors_pct=length_errors,
        bilateral_symmetry_score=bilateral_symmetry,
        radial_symmetry_score=radial_symmetry,
        is_closed=is_closed,
        composite_score=composite
    )


def _compute_bilateral_symmetry(
    drawn_pixels_by_stroke: List[List[Tuple[int, int]]],
    params: Primitive2DParams
) -> float:
    """Compute bilateral symmetry score (0-1)."""
    # Simplified: check if opposite edges have similar lengths
    if len(drawn_pixels_by_stroke) < 4:
        return 1.0
    
    try:
        lengths = []
        for pixels in drawn_pixels_by_stroke:
            if len(pixels) >= 2:
                pts = np.array(pixels)
                length = np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1))
                lengths.append(length)
        
        if len(lengths) < 4:
            return 1.0
        
        # Compare opposite edges
        n = len(lengths)
        diffs = []
        for i in range(n // 2):
            diffs.append(abs(lengths[i] - lengths[i + n//2]) / max(lengths[i], lengths[i + n//2]))
        
        return float(1.0 - np.mean(diffs))
    except:
        return 0.5


def _compute_radial_symmetry(
    drawn_pixels_by_stroke: List[List[Tuple[int, int]]],
    params: Primitive2DParams
) -> float:
    """Compute radial symmetry score for regular polygons (0-1)."""
    if params.prim_type not in [
        Primitive2DType.SQUARE, Primitive2DType.EQUILATERAL_TRIANGLE,
        Primitive2DType.DIAMOND, Primitive2DType.HEXAGON, Primitive2DType.OCTAGON,
        Primitive2DType.CIRCLE
    ]:
        return 1.0  # Not applicable
    
    try:
        # Check if all edges have similar length and angles
        lengths = []
        angles = []
        
        for pixels in drawn_pixels_by_stroke:
            if len(pixels) >= 2:
                pts = np.array(pixels)
                # Length
                length = np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1))
                lengths.append(length)
                # Angle (first to last)
                vec = pts[-1] - pts[0]
                angles.append(math.atan2(vec[1], vec[0]))
        
        if len(lengths) < 3:
            return 1.0
        
        # Coefficient of variation for lengths
        len_cv = np.std(lengths) / max(np.mean(lengths), 1)
        # Angle regularity
        angle_cv = np.std(angles) / max(np.mean(np.abs(angles)), 0.01)
        
        return float(max(0, 1 - (len_cv + angle_cv) / 2))
    except:
        return 0.5


# Standard exercise sequences for Level 1
PRIMITIVE_2D_CURRICULUM = [
    # Phase 1: Orthogonal forms
    Primitive2DParams(Primitive2DType.CROSS, (400, 300), 80),           # + (easiest - 2 strokes)
    Primitive2DParams(Primitive2DType.SQUARE, (400, 300), 100),          # □
    Primitive2DParams(Primitive2DType.RECTANGLE, (400, 300), 120, 80),   # ▭
    
    # Phase 2: Diagonal forms
    Primitive2DParams(Primitive2DType.X_MARK, (400, 300), 80),           # ×
    Primitive2DParams(Primitive2DType.DIAMOND, (400, 300), 100),         # ◊
    Primitive2DParams(Primitive2DType.EQUILATERAL_TRIANGLE, (400, 300), 100),  # △
    Primitive2DParams(Primitive2DType.RIGHT_TRIANGLE, (400, 300), 100),  # ◤
    
    # Phase 3: Regular polygons
    Primitive2DParams(Primitive2DType.HEXAGON, (400, 300), 80),          # ⬡
    Primitive2DParams(Primitive2DType.OCTAGON, (400, 300), 80),          # ⬢
    
    # Phase 4: Circle (curved)
    Primitive2DParams(Primitive2DType.CIRCLE, (400, 300), 80),           # ○
]