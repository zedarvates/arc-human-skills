"""Line control fundamentals - Level 0: Pure motor control."""
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum
import math
import numpy as np

from arc_human_skills.paint_automation import Stroke


class LineOrientation(Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    DIAGONAL_45 = "diagonal_45"      # ↗
    DIAGONAL_135 = "diagonal_135"    # ↖
    DIAGONAL_M45 = "diagonal_m45"    # ↘
    DIAGONAL_M135 = "diagonal_m135"  # ↙
    FREE = "free"


@dataclass
class LineControlParams:
    """Parameters for a line drawing exercise."""
    orientation: LineOrientation
    start: Tuple[int, int]
    length: int
    target_thickness: int = 2
    pressure_profile: str = "constant"  # constant, fade_in, fade_out, wave
    speed: float = 1.0  # relative speed factor


@dataclass
class LineQualityMetrics:
    """Geometric quality metrics for a drawn line."""
    # Endpoint accuracy
    start_error_px: float
    end_error_px: float
    
    # Straightness
    max_deviation_px: float
    rmse_deviation_px: float
    straightness_score: float  # 0-1, 1 = perfectly straight
    
    # Angle accuracy
    target_angle_rad: float
    actual_angle_rad: float
    angle_error_deg: float
    
    # Thickness consistency
    mean_thickness: float
    thickness_std: float
    thickness_consistency: float  # 0-1
    
    # Length accuracy
    target_length: float
    actual_length: float
    length_error_pct: float
    
    # Overall
    composite_score: float  # 0-1 weighted combination


class LineControlExercise:
    """Generates and evaluates line control exercises."""
    
    # Standard exercise set for Level 0
    STANDARD_EXERCISES = [
        # Horizontal lines (left-to-right, right-to-left)
        LineControlParams(LineOrientation.HORIZONTAL, (100, 300), 400, 2, "constant"),
        LineControlParams(LineOrientation.HORIZONTAL, (500, 300), 400, 2, "constant"),
        
        # Vertical lines (top-to-bottom, bottom-to-top)
        LineControlParams(LineOrientation.VERTICAL, (400, 100), 400, 2, "constant"),
        LineControlParams(LineOrientation.VERTICAL, (400, 500), 400, 2, "constant"),
        
        # Diagonals (8 directions)
        LineControlParams(LineOrientation.DIAGONAL_45, (100, 500), 400, 2, "constant"),
        LineControlParams(LineOrientation.DIAGONAL_135, (500, 500), 400, 2, "constant"),
        LineControlParams(LineOrientation.DIAGONAL_M45, (100, 100), 400, 2, "constant"),
        LineControlParams(LineOrientation.DIAGONAL_M135, (500, 100), 400, 2, "constant"),
        
        # Pressure control
        LineControlParams(LineOrientation.HORIZONTAL, (100, 200), 400, 2, "fade_in"),
        LineControlParams(LineOrientation.HORIZONTAL, (100, 400), 400, 2, "fade_out"),
        LineControlParams(LineOrientation.HORIZONTAL, (100, 250), 400, 2, "wave"),
    ]
    
    def __init__(self, canvas_size: Tuple[int, int] = (800, 600)):
        self.canvas_size = canvas_size
        self.exercises = self.STANDARD_EXERCISES.copy()
    
    def add_custom_exercise(self, params: LineControlParams):
        self.exercises.append(params)
    
    def get_stroke_for_exercise(self, params: LineControlParams) -> Stroke:
        """Convert exercise params to a Stroke for Paint automation."""
        x, y = params.start
        length = params.length
        
        if params.orientation == LineOrientation.HORIZONTAL:
            end = (x + length, y)
            target_angle = 0.0
        elif params.orientation == LineOrientation.VERTICAL:
            end = (x, y - length)  # Paint: y increases downward
            target_angle = -math.pi / 2
        elif params.orientation == LineOrientation.DIAGONAL_45:
            end = (x + length, y - length)
            target_angle = -math.pi / 4
        elif params.orientation == LineOrientation.DIAGONAL_135:
            end = (x - length, y - length)
            target_angle = -3 * math.pi / 4
        elif params.orientation == LineOrientation.DIAGONAL_M45:
            end = (x + length, y + length)
            target_angle = math.pi / 4
        elif params.orientation == LineOrientation.DIAGONAL_M135:
            end = (x - length, y + length)
            target_angle = 3 * math.pi / 4
        else:
            end = (x + length, y)
            target_angle = 0.0
        
        return Stroke(
            start=params.start,
            end=end,
            color=(0, 0, 0),
            thickness=params.target_thickness
        )
    
    def get_all_strokes(self) -> List[Tuple[Stroke, LineControlParams]]:
        return [(self.get_stroke_for_exercise(p), p) for p in self.exercises]


def evaluate_line_drawing(
    drawn_pixels: List[Tuple[int, int]],  # List of (x, y) points from canvas
    params: LineControlParams
) -> LineQualityMetrics:
    """
    Evaluate a drawn line against exercise parameters.
    drawn_pixels: ordered list of pixel coordinates from stroke capture
    """
    if len(drawn_pixels) < 2:
        return LineQualityMetrics(
            start_error_px=999, end_error_px=999,
            max_deviation_px=999, rmse_deviation_px=999, straightness_score=0.0,
            target_angle_rad=0, actual_angle_rad=0, angle_error_deg=999,
            mean_thickness=0, thickness_std=999, thickness_consistency=0.0,
            target_length=params.length, actual_length=0, length_error_pct=100,
            composite_score=0.0
        )
    
    points = np.array(drawn_pixels, dtype=np.float32)
    
    # Target line
    start_pt = np.array(params.start, dtype=np.float32)
    target_stroke = LineControlExercise().get_stroke_for_exercise(params)
    end_target = np.array(target_stroke.end, dtype=np.float32)
    target_vec = end_target - start_pt
    target_length = np.linalg.norm(target_vec)
    target_angle = math.atan2(target_vec[1], target_vec[0])
    
    # Actual endpoints
    actual_start = points[0]
    actual_end = points[-1]
    actual_vec = actual_end - actual_start
    actual_length = np.linalg.norm(actual_vec)
    actual_angle = math.atan2(actual_vec[1], actual_vec[0])
    
    # Endpoint errors
    start_error = np.linalg.norm(actual_start - start_pt)
    end_error = np.linalg.norm(actual_end - end_target)
    
    # Straightness: distance from ideal line
    if target_length > 0:
        # Project each point onto target line, measure perpendicular distance
        target_unit = target_vec / target_length
        deviations = []
        for pt in points:
            vec_from_start = pt - start_pt
            proj_length = np.dot(vec_from_start, target_unit)
            proj_point = start_pt + target_unit * proj_length
            deviation = np.linalg.norm(pt - proj_point)
            deviations.append(deviation)
        
        max_dev = float(max(deviations))
        rmse_dev = float(np.sqrt(np.mean(np.array(deviations) ** 2)))
        straightness = float(1.0 / (1.0 + rmse_dev / max(1.0, target_length * 0.1)))
    else:
        max_dev = rmse_dev = 999
        straightness = 0.0
    
    # Angle error
    angle_diff = abs(actual_angle - target_angle)
    angle_diff = min(angle_diff, 2 * math.pi - angle_diff)  # Normalize
    angle_error_deg = float(math.degrees(angle_diff))
    
    # Length error
    length_error_pct = float(abs(actual_length - target_length) / max(1, target_length) * 100)
    
    # Thickness estimation (from point density if available)
    # Simplified: assume constant for now
    mean_thickness = params.target_thickness
    thickness_std = 0.0
    thickness_consistency = 1.0
    
    # Composite score (weighted)
    weights = {
        'endpoint': 0.25,
        'straightness': 0.35,
        'angle': 0.25,
        'length': 0.15
    }
    
    endpoint_score = max(0, 1 - (start_error + end_error) / 20.0)
    straightness_score = straightness
    angle_score = max(0, 1 - angle_error_deg / 15.0)
    length_score = max(0, 1 - length_error_pct / 20.0)
    
    composite = (
        weights['endpoint'] * endpoint_score +
        weights['straightness'] * straightness_score +
        weights['angle'] * angle_score +
        weights['length'] * length_score
    )
    
    return LineQualityMetrics(
        start_error_px=float(start_error),
        end_error_px=float(end_error),
        max_deviation_px=max_dev,
        rmse_deviation_px=rmse_dev,
        straightness_score=straightness,
        target_angle_rad=target_angle,
        actual_angle_rad=actual_angle,
        angle_error_deg=angle_error_deg,
        mean_thickness=mean_thickness,
        thickness_std=thickness_std,
        thickness_consistency=thickness_consistency,
        target_length=float(target_length),
        actual_length=float(actual_length),
        length_error_pct=length_error_pct,
        composite_score=composite
    )


def extract_stroke_pixels(canvas_before: np.ndarray, canvas_after: np.ndarray, 
                          expected_region: Tuple[int, int, int, int]) -> List[Tuple[int, int]]:
    """
    Extract drawn stroke pixels by differencing canvas before/after.
    expected_region: (x1, y1, x2, y2) region where stroke was drawn
    """
    x1, y1, x2, y2 = expected_region
    if x2 <= x1 or y2 <= y1:
        return []
    
    roi_before = canvas_before[y1:y2, x1:x2]
    roi_after = canvas_after[y1:y2, x1:x2]
    
    # Detect changed pixels (darker = drawn)
    if len(roi_before.shape) == 3:
        diff = cv2.absdiff(
            cv2.cvtColor(roi_before, cv2.COLOR_BGR2GRAY),
            cv2.cvtColor(roi_after, cv2.COLOR_BGR2GRAY)
        )
    else:
        diff = cv2.absdiff(roi_before, roi_after)
    
    _, mask = cv2.threshold(diff, 10, 255, cv2.THRESH_BINARY)
    
    # Get ordered points (skeletonize or simple contour)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return []
    
    # Use largest contour
    largest = max(contours, key=cv2.contourArea)
    points = largest.reshape(-1, 2)
    
    # Offset back to canvas coordinates
    points[:, 0] += x1
    points[:, 1] += y1
    
    # Sort by distance from expected start
    start_pt = np.array([x1, y1])
    dists = np.linalg.norm(points - start_pt, axis=1)
    points = points[np.argsort(dists)]
    
    return [(int(x), int(y)) for x, y in points]


# Need cv2 import
import cv2