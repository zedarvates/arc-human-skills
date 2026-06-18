"""3D Wireframe Primitives - Level 2: Cube, Box, Pyramid, Prism, Cylinder."""
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from enum import Enum
import math
import numpy as np

from arc_human_skills.paint_automation import Stroke
from arc_human_skills.drawing_fundamentals.primitives_2d import PrimitiveQualityMetrics


class Wireframe3DType(Enum):
    CUBE = "cube"
    RECTANGULAR_BOX = "rectangular_box"      # Box with different W/D/H
    SQUARE_PYRAMID = "square_pyramid"         # Pyramid on square base
    TRIANGULAR_PRISM = "triangular_prism"     # Prism with triangle base
    CYLINDER_WIRE = "cylinder_wire"           # Two ellipses + sides
    CONE_WIRE = "cone_wire"                   # Ellipse base + apex


@dataclass
class Wireframe3DParams:
    """Parameters for a 3D wireframe primitive."""
    wire_type: Wireframe3DType
    center: Tuple[int, int]      # Center of base on canvas
    width: float                 # X extent
    depth: float                 # Z extent (into screen)
    height: float                # Y extent (vertical)
    rotation_y_deg: float = 0.0  # Rotation around vertical axis
    perspective: str = "2pt"     # "1pt", "2pt", "3pt", "iso" (isometric)
    vp1: Optional[Tuple[int, int]] = None  # Vanishing point 1
    vp2: Optional[Tuple[int, int]] = None  # Vanishing point 2
    vp3: Optional[Tuple[int, int]] = None  # Vanishing point 3 (for 3pt)
    horizon_y: int = 300         # Horizon line Y
    thickness: int = 2
    show_hidden: bool = False    # Draw hidden lines (dashed)


@dataclass
class WireframeQualityMetrics:
    """Quality metrics for 3D wireframe."""
    # Edge metrics
    edge_metrics: List  # LineQualityMetrics per visible edge
    
    # Perspective coherence
    vp_convergence_errors: List[float]  # How well edges converge to VPs
    horizon_alignment_error: float      # Vertical edges alignment
    
    # Proportions
    proportion_errors_pct: Dict[str, float]  # Width:Depth:Height ratios
    
    # Structural
    vertex_closure_errors: List[float]  # Gap at each vertex
    hidden_line_consistency: float      # If show_hidden, consistency
    
    # Overall
    composite_score: float


def get_3d_vertices(params: Wireframe3DParams) -> Dict[str, Tuple[float, float, float]]:
    """Get 3D vertices in object space (before projection)."""
    cx, cy = params.center
    w, d, h = params.width, params.depth, params.height
    
    # Object space: center at origin, base on XZ plane, Y up
    if params.wire_type == Wireframe3DType.CUBE:
        s = w  # width = depth = height for cube
        return {
            # Base (Y=0)
            'A': (-s/2, 0, -s/2), 'B': (s/2, 0, -s/2),
            'C': (s/2, 0, s/2),   'D': (-s/2, 0, s/2),
            # Top (Y=h)
            'E': (-s/2, h, -s/2), 'F': (s/2, h, -s/2),
            'G': (s/2, h, s/2),   'H': (-s/2, h, s/2),
        }
    
    elif params.wire_type == Wireframe3DType.RECTANGULAR_BOX:
        return {
            # Base
            'A': (-w/2, 0, -d/2), 'B': (w/2, 0, -d/2),
            'C': (w/2, 0, d/2),   'D': (-w/2, 0, d/2),
            # Top
            'E': (-w/2, h, -d/2), 'F': (w/2, h, -d/2),
            'G': (w/2, h, d/2),   'H': (-w/2, h, d/2),
        }
    
    elif params.wire_type == Wireframe3DType.SQUARE_PYRAMID:
        # Base square + apex
        base_vertices = {
            'A': (-w/2, 0, -w/2), 'B': (w/2, 0, -w/2),
            'C': (w/2, 0, w/2),   'D': (-w/2, 0, w/2),
        }
        base_vertices['P'] = (0, h, 0)  # Apex above center
        return base_vertices
    
    elif params.wire_type == Wireframe3DType.TRIANGULAR_PRISM:
        # Equilateral triangle base
        tri_h = w * math.sqrt(3) / 2
        base = {
            'A': (-w/2, 0, -tri_h/3), 'B': (w/2, 0, -tri_h/3),
            'C': (0, 0, 2*tri_h/3),
        }
        top = {f'{k}′': (x, h, z) for k, (x, y, z) in base.items()}
        return {**base, **top}
    
    elif params.wire_type == Wireframe3DType.CYLINDER_WIRE:
        # Approximate with 16-gon top/bottom
        n = 16
        r = w / 2
        vertices = {}
        for i in range(n):
            angle = 2 * math.pi * i / n
            x, z = r * math.cos(angle), r * math.sin(angle)
            vertices[f'B{i}'] = (x, 0, z)
            vertices[f'T{i}'] = (x, h, z)
        return vertices
    
    elif params.wire_type == Wireframe3DType.CONE_WIRE:
        # Circle base + apex
        n = 16
        r = w / 2
        vertices = {}
        for i in range(n):
            angle = 2 * math.pi * i / n
            x, z = r * math.cos(angle), r * math.sin(angle)
            vertices[f'B{i}'] = (x, 0, z)
        vertices['P'] = (0, h, 0)
        return vertices
    
    return {}


def get_wireframe_edges(params: Wireframe3DParams) -> List[Tuple[str, str]]:
    """Get edge connections for wireframe type."""
    if params.wire_type in [Wireframe3DType.CUBE, Wireframe3DType.RECTANGULAR_BOX]:
        return [
            # Base
            ('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A'),
            # Top
            ('E', 'F'), ('F', 'G'), ('G', 'H'), ('H', 'E'),
            # Verticals
            ('A', 'E'), ('B', 'F'), ('C', 'G'), ('D', 'H'),
        ]
    
    elif params.wire_type == Wireframe3DType.SQUARE_PYRAMID:
        return [
            # Base
            ('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A'),
            # Sides to apex
            ('A', 'P'), ('B', 'P'), ('C', 'P'), ('D', 'P'),
        ]
    
    elif params.wire_type == Wireframe3DType.TRIANGULAR_PRISM:
        return [
            # Bottom triangle
            ('A', 'B'), ('B', 'C'), ('C', 'A'),
            # Top triangle
            ('A′', 'B′'), ('B′', 'C′'), ('C′', 'A′'),
            # Verticals
            ('A', 'A′'), ('B', 'B′'), ('C', 'C′'),
        ]
    
    elif params.wire_type == Wireframe3DType.CYLINDER_WIRE:
        n = 16
        edges = []
        # Bottom polygon
        for i in range(n):
            edges.append((f'B{i}', f'B{(i+1)%n}'))
        # Top polygon
        for i in range(n):
            edges.append((f'T{i}', f'T{(i+1)%n}'))
        # Verticals
        for i in range(n):
            edges.append((f'B{i}', f'T{i}'))
        return edges
    
    elif params.wire_type == Wireframe3DType.CONE_WIRE:
        n = 16
        edges = []
        # Base polygon
        for i in range(n):
            edges.append((f'B{i}', f'B{(i+1)%n}'))
        # Sides to apex
        for i in range(n):
            edges.append((f'B{i}', 'P'))
        return edges
    
    return []


def project_3d_to_2d(
    vertices_3d: Dict[str, Tuple[float, float, float]],
    params: Wireframe3DParams
) -> Dict[str, Tuple[int, int]]:
    """Project 3D vertices to 2D canvas coordinates using perspective."""
    cx, cy = params.center
    horizon = params.horizon_y
    vp1 = params.vp1
    vp2 = params.vp2
    vp3 = params.vp3
    
    # Rotation around Y axis
    rot = math.radians(params.rotation_y_deg)
    cos_r, sin_r = math.cos(rot), math.sin(rot)
    
    projected = {}
    
    for name, (x, y, z) in vertices_3d.items():
        # Rotate
        xr = x * cos_r - z * sin_r
        zr = x * sin_r + z * cos_r
        yr = y
        
        if params.perspective == "iso":
            # Isometric projection
            # X→right, Z→up-left, Y→up
            px = cx + xr * 0.707 - zr * 0.707
            py = cy - yr - (xr + zr) * 0.353
            projected[name] = (int(px), int(py))
        
        elif params.perspective == "1pt":
            # 1-point: Z lines converge to center VP, X horizontal, Y vertical
            if vp1 is None:
                vp1 = (cx, horizon)
            
            # Distance from camera (assume camera at Z = -dist)
            dist = 800
            scale = dist / (dist + zr)
            
            px = cx + xr * scale
            py = cy - yr * scale
            
            # Z lines converge to VP
            if abs(zr) > 1:
                vpx, vpy = vp1
                # Line from point to VP
                t = 0.3  # How far toward VP
                px = int(px + (vpx - px) * t)
                py = int(py + (vpy - py) * t)
            projected[name] = (int(px), int(py))
        
        elif params.perspective == "2pt":
            # 2-point: X and Z lines converge to two VPs on horizon
            if vp1 is None:
                vp1 = (cx - 300, horizon)
            if vp2 is None:
                vp2 = (cx + 300, horizon)
            
            # Simple 2pt: project to both VPs
            dist = 800
            scale = dist / (dist + zr)
            
            # X dimension → VP1, Z dimension → VP2
            # This is simplified; real 2pt needs proper projection matrix
            px = cx + xr * scale
            py = cy - yr * scale
            
            # Bias toward VPs based on angle
            if xr > 0:
                px = int(px + (vp2[0] - px) * 0.15)
            else:
                px = int(px + (vp1[0] - px) * 0.15)
            
            projected[name] = (int(px), int(py))
        
        elif params.perspective == "3pt":
            # 3-point: add zenith/nadir VP for verticals
            # Simplified: use 2pt + vertical convergence
            if vp1 is None:
                vp1 = (cx - 300, horizon)
            if vp2 is None:
                vp2 = (cx + 300, horizon)
            if vp3 is None:
                vp3 = (cx, horizon - 400)  # Zenith
            
            projected[name] = project_3d_to_2d({name: (xr, yr, zr)}, 
                Wireframe3DParams(
                    wire_type=params.wire_type, center=params.center,
                    width=params.width, depth=params.depth, height=params.height,
                    rotation_y_deg=0, perspective="2pt", vp1=vp1, vp2=vp2, horizon_y=horizon
                ))[name]
            
            # Bias verticals toward VP3
            py = projected[name][1]
            py = int(py + (vp3[1] - py) * 0.1)
            projected[name] = (projected[name][0], py)
        
        else:
            # Default: orthographic
            projected[name] = (cx + int(xr), cy - int(yr))
    
    return projected


def get_wireframe_strokes(params: Wireframe3DParams) -> List[Stroke]:
    """Generate 2D strokes for a 3D wireframe."""
    vertices_3d = get_3d_vertices(params)
    vertices_2d = project_3d_to_2d(vertices_3d, params)
    edges = get_wireframe_edges(params)
    
    strokes = []
    for start_name, end_name in edges:
        if start_name in vertices_2d and end_name in vertices_2d:
            p1 = vertices_2d[start_name]
            p2 = vertices_2d[end_name]
            
            # Check if hidden (only for perspective modes, not isometric)
            is_hidden = False
            if params.perspective != "iso":
                is_hidden = _is_edge_hidden(start_name, end_name, vertices_3d, params)
            
            if is_hidden and not params.show_hidden:
                continue  # Skip hidden lines unless requested
            
            strokes.append(Stroke(
                start=p1, end=p2,
                color=(128, 128, 128) if is_hidden else (0, 0, 0),
                thickness=params.thickness if not is_hidden else max(1, params.thickness - 1)
            ))
    
    return strokes


def _is_edge_hidden(
    start: str, end: str,
    vertices_3d: Dict[str, Tuple[float, float, float]],
    params: Wireframe3DParams
) -> bool:
    """Simple hidden line detection (back-face culling)."""
    # For simple cases, use vertex order / normal
    if params.wire_type in [Wireframe3DType.CUBE, Wireframe3DType.RECTANGULAR_BOX]:
        # Hidden if both vertices are on back face (negative Z after rotation)
        rot = math.radians(params.rotation_y_deg)
        cos_r, sin_r = math.cos(rot), math.sin(rot)
        
        def get_zr(v):
            x, y, z = v
            return x * sin_r + z * cos_r
        
        zr1 = get_zr(vertices_3d[start])
        zr2 = get_zr(vertices_3d[end])
        
        # Both far back = hidden
        return zr1 < -params.depth * 0.3 and zr2 < -params.depth * 0.3
    
    # Default: not hidden
    return False


# Standard curriculum for Level 2
WIREFRAME_3D_CURRICULUM = [
    # Phase 1: Isometric (no perspective complexity)
    Wireframe3DParams(Wireframe3DType.CUBE, (400, 350), 100, 100, 100, 
                      perspective="iso", rotation_y_deg=30),
    Wireframe3DParams(Wireframe3DType.RECTANGULAR_BOX, (400, 350), 140, 80, 100,
                      perspective="iso", rotation_y_deg=30),
    
    # Phase 2: 1-point perspective
    Wireframe3DParams(Wireframe3DType.CUBE, (400, 400), 100, 100, 100,
                      perspective="1pt", horizon_y=300, vp1=(400, 300)),
    
    # Phase 3: 2-point perspective
    Wireframe3DParams(Wireframe3DType.CUBE, (400, 400), 100, 100, 100,
                      perspective="2pt", horizon_y=300, vp1=(100, 300), vp2=(700, 300),
                      rotation_y_deg=30),
    Wireframe3DParams(Wireframe3DType.RECTANGULAR_BOX, (400, 400), 140, 80, 100,
                      perspective="2pt", horizon_y=300, vp1=(100, 300), vp2=(700, 300),
                      rotation_y_deg=30),
    
    # Phase 4: Other primitives in 2pt
    Wireframe3DParams(Wireframe3DType.SQUARE_PYRAMID, (400, 450), 120, 120, 140,
                      perspective="2pt", horizon_y=300, vp1=(100, 300), vp2=(700, 300),
                      rotation_y_deg=30),
    Wireframe3DParams(Wireframe3DType.TRIANGULAR_PRISM, (400, 350), 100, 100, 100,
                      perspective="2pt", horizon_y=300, vp1=(100, 300), vp2=(700, 300),
                      rotation_y_deg=30),
    
    # Phase 5: Curved wireframes
    Wireframe3DParams(Wireframe3DType.CYLINDER_WIRE, (400, 350), 80, 80, 120,
                      perspective="2pt", horizon_y=300, vp1=(100, 300), vp2=(700, 300)),
    Wireframe3DParams(Wireframe3DType.CONE_WIRE, (400, 400), 100, 100, 140,
                      perspective="2pt", horizon_y=300, vp1=(100, 300), vp2=(700, 300)),
]