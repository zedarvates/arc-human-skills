"""Perspective Construction - Level 3: Horizon, VPs, Grids, Ellipses, Shadows."""
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum
import math
import numpy as np

from arc_human_skills.paint_automation import Stroke
from arc_human_skills.drawing_fundamentals.wireframe_3d import Wireframe3DParams


class PerspectiveType(Enum):
    ONE_POINT = "1pt"
    TWO_POINT = "2pt"
    THREE_POINT = "3pt"
    ISOMETRIC = "iso"
    CURVILINEAR = "curvilinear"  # 4/5 point (fisheye/panoramic)


@dataclass
class PerspectiveSetup:
    """Complete perspective setup for a drawing."""
    ptype: PerspectiveType
    horizon_y: int                    # Horizon line Y position
    vp1: Optional[Tuple[int, int]] = None   # Primary VP
    vp2: Optional[Tuple[int, int]] = None   # Secondary VP
    vp3: Optional[Tuple[int, int]] = None   # Tertiary VP (zenith/nadir)
    station_point_dist: float = 800   # Camera distance
    cone_of_vision_deg: float = 60    # 60° typical
    canvas_size: Tuple[int, int] = (800, 600)
    
    def get_vp_positions(self) -> List[Tuple[int, int]]:
        """Get all VP positions."""
        vps = []
        if self.vp1: vps.append(self.vp1)
        if self.vp2: vps.append(self.vp2)
        if self.vp3: vps.append(self.vp3)
        return vps


@dataclass
class GridParams:
    """Parameters for perspective grid."""
    perspective: PerspectiveSetup
    plane: str = "ground"      # "ground", "vertical", "sloped"
    spacing: float = 50        # World units between grid lines
    extent: float = 400        # How far grid extends
    divisions: int = 8         # Number of divisions
    color_major: Tuple[int, int, int] = (0, 0, 0)
    color_minor: Tuple[int, int, int] = (128, 128, 128)


def get_horizon_line(perspective: PerspectiveSetup) -> Stroke:
    """Get horizon line stroke."""
    w, _ = perspective.canvas_size
    return Stroke((0, perspective.horizon_y), (w, perspective.horizon_y), (200, 200, 200), 1)


def get_ground_grid_strokes(params: GridParams) -> List[Stroke]:
    """Generate 2-point perspective ground grid strokes."""
    strokes = []
    p = params.perspective
    vp1, vp2 = p.vp1, p.vp2
    
    if not vp1 or not vp2:
        return strokes
    
    canvas_h = p.canvas_size[1]
    horizon = p.horizon_y
    
    # Ground plane: lines from station point to VPs
    # Station point typically at bottom center
    sp_x = p.canvas_size[0] // 2
    sp_y = canvas_h  # Bottom of canvas
    
    # Transverse lines (parallel to picture plane) → converge to VPs
    # These are the "depth" lines
    for i in range(params.divisions + 1):
        # Interpolate along bottom edge
        t = i / params.divisions
        bottom_x = p.canvas_size[0] * t
        
        # Line from bottom point to VP1 (left depth lines)
        strokes.append(Stroke(
            (int(bottom_x), sp_y), vp1, params.color_minor, 1
        ))
        # Line from bottom point to VP2 (right depth lines)
        strokes.append(Stroke(
            (int(bottom_x), sp_y), vp2, params.color_minor, 1
        ))
    
    # Longitudinal lines (receding) → horizontal in 1pt, but in 2pt they're
    # curves or lines connecting corresponding points on left/right edges
    # Simplified: draw horizontal lines at calculated Y positions
    for i in range(1, params.divisions):
        # Perspective spacing: lines get closer toward horizon
        # Using similar triangles
        t = i / params.divisions
        # Distance from horizon (in perspective)
        y = int(sp_y - (sp_y - horizon) * math.sqrt(t))  # sqrt for perspective compression
        
        # Line across at this Y
        # Find intersections with left/right boundaries
        # Left boundary: line from SP to VP1
        # Right boundary: line from SP to VP2
        left_x = _intersect_horizontal_with_vp_line(y, sp_x, sp_y, vp1)
        right_x = _intersect_horizontal_with_vp_line(y, sp_x, sp_y, vp2)
        
        if left_x < right_x:
            color = params.color_major if i % 2 == 0 else params.color_minor
            strokes.append(Stroke(
                (left_x, y), (right_x, y), color, 1 if i % 2 == 0 else 1
            ))
    
    return strokes


def _intersect_horizontal_with_vp_line(y: int, sp_x: int, sp_y: int, vp: Tuple[int, int]) -> int:
    """Find X intersection of horizontal line Y with line from station point to VP."""
    vpx, vpy = vp
    if vpy == sp_y:
        return sp_x
    t = (y - sp_y) / (vpy - sp_y)
    return int(sp_x + t * (vpx - sp_x))


def get_vertical_grid_strokes(params: GridParams) -> List[Stroke]:
    """Generate vertical plane grid (e.g., wall)."""
    strokes = []
    p = params.perspective
    
    if params.plane != "vertical":
        return strokes
    
    # Vertical plane uses same VPs but lines go up from ground
    # Similar to ground grid but vertical
    return strokes


def get_ellipse_in_perspective(
    center_3d: Tuple[float, float, float],
    radius_x: float, radius_z: float,
    perspective: PerspectiveSetup,
    rotation_y_deg: float = 0.0,
    segments: int = 32
) -> List[Stroke]:
    """
    Generate ellipse strokes for a circle in perspective.
    A circle in 3D becomes an ellipse in 2D perspective.
    """
    # This is complex - simplified version using affine approximation
    # For proper implementation, need full projection matrix
    strokes = []
    
    # Project center
    cx = perspective.canvas_size[0] // 2 + int(center_3d[0])
    cy = perspective.horizon_y - int(center_3d[1])
    
    # Ellipse axes depend on orientation
    if perspective.ptype == PerspectiveType.ONE_POINT:
        # Circle on ground: ellipse with minor axis vertical
        # Major axis = radius_x * scale, minor = radius_z * scale * cos(angle)
        scale = perspective.station_point_dist / (perspective.station_point_dist + center_3d[2])
        rx = radius_x * scale
        ry = radius_z * scale * 0.5  # Foreshortening
        
        for i in range(segments):
            a1 = 2 * math.pi * i / segments
            a2 = 2 * math.pi * (i + 1) / segments
            x1 = cx + rx * math.cos(a1)
            y1 = cy + ry * math.sin(a1)
            x2 = cx + rx * math.cos(a2)
            y2 = cy + ry * math.sin(a2)
            strokes.append(Stroke((int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 0), 2))
    
    return strokes


def get_shadow_strokes(
    object_vertices_3d: dict,
    light_dir_3d: Tuple[float, float, float],
    ground_y: float,
    perspective: PerspectiveSetup
) -> List[Stroke]:
    """
    Cast shadow of 3D object onto ground plane.
    light_dir_3d: normalized direction FROM light TO object (e.g., (1, -1, 1) for top-right)
    """
    strokes = []
    
    # Normalize light direction
    lx, ly, lz = light_dir_3d
    length = math.sqrt(lx*lx + ly*ly + lz*lz)
    lx, ly, lz = lx/length, ly/length, lz/length
    
    # For each vertex, project shadow onto ground plane Y=0
    shadow_vertices = {}
    for name, (x, y, z) in object_vertices_3d.items():
        if y <= ground_y:
            continue  # Already on/below ground
        
        # Ray from vertex in light direction: V + t * L
        # Intersect with ground plane: y + t * ly = ground_y
        t = (ground_y - y) / ly
        if t > 0:
            sx = x + t * lx
            sz = z + t * lz
            shadow_vertices[name] = (sx, ground_y, sz)
    
    # Project shadow vertices to 2D
    # Simplified: just project as flat shapes
    from arc_human_skills.drawing_fundamentals.wireframe_3d import project_3d_to_2d
    projected = project_3d_to_2d(shadow_vertices, Wireframe3DParams(
        wire_type=list(object_vertices_3d.keys())[0] if object_vertices_3d else "cube",
        center=(perspective.canvas_size[0]//2, perspective.horizon_y),
        width=100, depth=100, height=100,
        perspective=perspective.ptype.value,
        vp1=perspective.vp1, vp2=perspective.vp2, vp3=perspective.vp3,
        horizon_y=perspective.horizon_y
    ))
    
    # Draw shadow as filled polygon (simplified as outline)
    # Get convex hull of shadow points
    pts = list(projected.values())
    if len(pts) >= 3:
        # Simple convex hull (Graham scan)
        hull = _convex_hull(pts)
        for i in range(len(hull)):
            p1 = hull[i]
            p2 = hull[(i+1) % len(hull)]
            strokes.append(Stroke(p1, p2, (64, 64, 64), 2))
    
    return strokes


def _convex_hull(points: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Graham scan convex hull."""
    if len(points) <= 3:
        return points
    
    # Find bottom-most point
    start = min(points, key=lambda p: (p[1], p[0]))
    
    # Sort by polar angle
    def angle(p):
        return math.atan2(p[1] - start[1], p[0] - start[0])
    
    sorted_pts = sorted([p for p in points if p != start], key=angle)
    
    hull = [start]
    for pt in sorted_pts:
        while len(hull) >= 2:
            p1, p2 = hull[-2], hull[-1]
            # Cross product
            cross = (p2[0] - p1[0]) * (pt[1] - p2[1]) - (p2[1] - p1[1]) * (pt[0] - p2[0])
            if cross <= 0:  # Not a left turn
                hull.pop()
            else:
                break
        hull.append(pt)
    
    return hull


def get_measuring_points(
    perspective: PerspectiveSetup,
    reference_height: float = 100
) -> List[Stroke]:
    """
    Get measuring points for consistent vertical scaling.
    In 2pt perspective, vertical scale changes with depth.
    """
    strokes = []
    
    if perspective.ptype != PerspectiveType.TWO_POINT:
        return strokes
    
    # Measuring line method: vertical line at picture plane intersection
    # Height at different depths calculated via similar triangles
    # Simplified: draw measuring line at center
    cx = perspective.canvas_size[0] // 2
    
    strokes.append(Stroke(
        (cx, perspective.horizon_y + 200),  # Base reference
        (cx, perspective.horizon_y - 200),  # Top reference
        (200, 100, 100), 1
    ))
    
    return strokes


# Standard exercises for Level 3
PERSPECTIVE_CURRICULUM = [
    # 1. Horizon line + single VP setup
    PerspectiveSetup(
        PerspectiveType.ONE_POINT, horizon_y=300,
        vp1=(400, 300), canvas_size=(800, 600)
    ),
    
    # 2. Two VPs on horizon
    PerspectiveSetup(
        PerspectiveType.TWO_POINT, horizon_y=300,
        vp1=(100, 300), vp2=(700, 300), canvas_size=(800, 600)
    ),
    
    # 3. Three-point (zenith)
    PerspectiveSetup(
        PerspectiveType.THREE_POINT, horizon_y=300,
        vp1=(100, 300), vp2=(700, 300), vp3=(400, -100),
        canvas_size=(800, 600)
    ),
    
    # 4. Isometric (no VPs)
    PerspectiveSetup(
        PerspectiveType.ISOMETRIC, horizon_y=300,
        canvas_size=(800, 600)
    ),
]

# Grid exercises
GRID_EXERCISES = [
    GridParams(PERSPECTIVE_CURRICULUM[1], spacing=50, divisions=8),  # 2pt ground grid
    GridParams(PERSPECTIVE_CURRICULUM[0], spacing=50, divisions=6),  # 1pt ground grid
]