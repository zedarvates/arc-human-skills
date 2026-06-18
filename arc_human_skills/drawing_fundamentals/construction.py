"""Construction - Level 4: Combining primitives into complex forms (still life, scenes)."""
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
from enum import Enum
import math
import numpy as np

from arc_human_skills.paint_automation import Stroke
from arc_human_skills.drawing_fundamentals.primitives_2d import (
    Primitive2DType, Primitive2DParams, get_primitive_strokes
)
from arc_human_skills.drawing_fundamentals.wireframe_3d import (
    Wireframe3DType, Wireframe3DParams, get_wireframe_strokes
)
from arc_human_skills.drawing_fundamentals.perspective import (
    PerspectiveSetup, PerspectiveType, GridParams, get_ground_grid_strokes
)


class ConstructionType(Enum):
    """Types of constructed scenes."""
    STILL_LIFE_SIMPLE = "still_life_simple"      # 3-5 objects on table
    STILL_LIFE_COMPLEX = "still_life_complex"    # 7+ objects, overlapping
    INTERIOR_CORNER = "interior_corner"          # Room corner with furniture
    EXTERIOR_BUILDING = "exterior_building"      # Building with windows/doors
    URBAN_STREET = "urban_street"                # Street with buildings
    NATURE_SCENE = "nature_scene"                # Trees, rocks, terrain


@dataclass
class ConstructionObject:
    """An object in a constructed scene."""
    name: str
    obj_type: str  # "primitive_2d", "wireframe_3d"
    params: object  # Primitive2DParams or Wireframe3DParams
    position_3d: Tuple[float, float, float] = (0, 0, 0)  # World position
    rotation_y_deg: float = 0.0
    color: Tuple[int, int, int] = (0, 0, 0)
    z_order: int = 0  # Drawing order (back to front)


@dataclass
class SceneParams:
    """Complete scene construction parameters."""
    scene_type: ConstructionType
    perspective: PerspectiveSetup
    objects: List[ConstructionObject]
    ground_grid: Optional[GridParams] = None
    lighting: Optional[Dict] = None  # Light direction, intensity


# ============================================================
# PREDEFINED SCENES (Curriculum)
# ============================================================

def create_still_life_simple(perspective: PerspectiveSetup) -> SceneParams:
    """Simple still life: box, sphere, cylinder on table."""
    objects = [
        # Table (large flat box)
        ConstructionObject(
            name="table",
            obj_type="wireframe_3d",
            params=Wireframe3DParams(
                Wireframe3DType.RECTANGULAR_BOX, (400, 450), 300, 200, 30,
                perspective=perspective.ptype.value, vp1=perspective.vp1,
                vp2=perspective.vp2, horizon_y=perspective.horizon_y
            ),
            position_3d=(0, -15, 0),  # Below center
            color=(100, 80, 60)
        ),
        
        # Cube on table
        ConstructionObject(
            name="cube",
            obj_type="wireframe_3d",
            params=Wireframe3DParams(
                Wireframe3DType.CUBE, (250, 350), 80, 80, 80,
                perspective=perspective.ptype.value, vp1=perspective.vp1,
                vp2=perspective.vp2, horizon_y=perspective.horizon_y,
                rotation_y_deg=30
            ),
            position_3d=(-80, 40, -50),
            color=(0, 0, 0)
        ),
        
        # Cylinder (wireframe)
        ConstructionObject(
            name="cylinder",
            obj_type="wireframe_3d",
            params=Wireframe3DParams(
                Wireframe3DType.CYLINDER_WIRE, (400, 350), 60, 60, 100,
                perspective=perspective.ptype.value, vp1=perspective.vp1,
                vp2=perspective.vp2, horizon_y=perspective.horizon_y
            ),
            position_3d=(0, 50, 0),
            color=(0, 0, 0)
        ),
        
        # Sphere (as circle in perspective)
        ConstructionObject(
            name="sphere",
            obj_type="primitive_2d",
            params=Primitive2DParams(
                Primitive2DType.CIRCLE, (550, 320), 50,
                rotation_deg=0, thickness=2
            ),
            position_3d=(80, 50, 30),
            color=(0, 0, 0)
        ),
    ]
    
    return SceneParams(
        scene_type=ConstructionType.STILL_LIFE_SIMPLE,
        perspective=perspective,
        objects=objects,
        ground_grid=GridParams(perspective, spacing=40, divisions=10)
    )


def create_interior_corner(perspective: PerspectiveSetup) -> SceneParams:
    """Interior room corner with furniture."""
    # 2-point perspective for room
    vp1 = perspective.vp1 or (100, perspective.horizon_y)
    vp2 = perspective.vp2 or (700, perspective.horizon_y)
    
    objects = [
        # Floor grid (large)
        ConstructionObject(
            name="floor_grid",
            obj_type="grid",
            params=GridParams(
                PerspectiveSetup(PerspectiveType.TWO_POINT, perspective.horizon_y,
                                vp1=vp1, vp2=vp2),
                spacing=50, divisions=12, extent=600
            ),
            position_3d=(0, 0, 0),
            color=(128, 128, 128),
            z_order=-10
        ),
        
        # Back wall (large rectangle in perspective)
        ConstructionObject(
            name="back_wall",
            obj_type="primitive_2d",
            params=Primitive2DParams(
                Primitive2DType.RECTANGLE, (400, 200), 300, 200,
                thickness=3
            ),
            position_3d=(0, 100, -300),
            color=(180, 180, 200),
            z_order=-5
        ),
        
        # Box on floor (cube)
        ConstructionObject(
            name="cube_box",
            obj_type="wireframe_3d",
            params=Wireframe3DParams(
                Wireframe3DType.CUBE, (200, 450), 100, 100, 100,
                perspective="2pt", vp1=vp1, vp2=vp2,
                horizon_y=perspective.horizon_y, rotation_y_deg=20
            ),
            position_3d=(-120, 50, -80),
            color=(0, 0, 0),
            z_order=0
        ),
        
        # Tall box (rectangular box)
        ConstructionObject(
            name="tall_box",
            obj_type="wireframe_3d",
            params=Wireframe3DParams(
                Wireframe3DType.RECTANGULAR_BOX, (600, 400), 80, 100, 180,
                perspective="2pt", vp1=vp1, vp2=vp2,
                horizon_y=perspective.horizon_y, rotation_y_deg=-15
            ),
            position_3d=(100, 90, 50),
            color=(0, 0, 0),
            z_order=0
        ),
        
        # Window on back wall
        ConstructionObject(
            name="window",
            obj_type="primitive_2d",
            params=Primitive2DParams(
                Primitive2DType.RECTANGLE, (400, 150), 150, 100,
                thickness=2
            ),
            position_3d=(0, 150, -300),
            color=(100, 150, 200),
            z_order=-4
        ),
    ]
    
    return SceneParams(
        scene_type=ConstructionType.INTERIOR_CORNER,
        perspective=perspective,
        objects=objects
    )


def create_exterior_building(perspective: PerspectiveSetup) -> SceneParams:
    """Simple building exterior with windows/door."""
    vp1 = perspective.vp1 or (100, perspective.horizon_y)
    vp2 = perspective.vp2 or (700, perspective.horizon_y)
    
    objects = [
        # Ground
        ConstructionObject(
            name="ground",
            obj_type="grid",
            params=GridParams(
                PerspectiveSetup(PerspectiveType.TWO_POINT, perspective.horizon_y,
                                vp1=vp1, vp2=vp2),
                spacing=60, divisions=10
            ),
            color=(100, 100, 90)
        ),
        
        # Main building block
        ConstructionObject(
            name="building_main",
            obj_type="wireframe_3d",
            params=Wireframe3DParams(
                Wireframe3DType.RECTANGULAR_BOX, (400, 400), 200, 120, 180,
                perspective="2pt", vp1=vp1, vp2=vp2,
                horizon_y=perspective.horizon_y, rotation_y_deg=30
            ),
            position_3d=(0, 90, 0),
            color=(80, 80, 80)
        ),
        
        # Roof (pyramid on top)
        ConstructionObject(
            name="roof",
            obj_type="wireframe_3d",
            params=Wireframe3DParams(
                Wireframe3DType.SQUARE_PYRAMID, (400, 280), 210, 210, 80,
                perspective="2pt", vp1=vp1, vp2=vp2,
                horizon_y=perspective.horizon_y, rotation_y_deg=30
            ),
            position_3d=(0, 180, 0),
            color=(120, 60, 60)
        ),
        
        # Door
        ConstructionObject(
            name="door",
            obj_type="primitive_2d",
            params=Primitive2DParams(
                Primitive2DType.RECTANGLE, (400, 470), 50, 90,
                thickness=3
            ),
            position_3d=(0, -55, 70),
            color=(60, 40, 20)
        ),
        
        # Windows (row)
        ConstructionObject(
            name="window_1",
            obj_type="primitive_2d",
            params=Primitive2DParams(
                Primitive2DType.RECTANGLE, (300, 350), 50, 60,
                thickness=2
            ),
            position_3d=(-80, 50, 70),
            color=(150, 200, 250)
        ),
        ConstructionObject(
            name="window_2",
            obj_type="primitive_2d",
            params=Primitive2DParams(
                Primitive2DType.RECTANGLE, (500, 350), 50, 60,
                thickness=2
            ),
            position_3d=(80, 50, 70),
            color=(150, 200, 250)
        ),
    ]
    
    return SceneParams(
        scene_type=ConstructionType.EXTERIOR_BUILDING,
        perspective=perspective,
        objects=objects
    )


# ============================================================
# SCENE RENDERING
# ============================================================

def render_scene(scene: SceneParams) -> List[Stroke]:
    """Render all objects in a scene to strokes (back-to-front order)."""
    all_strokes = []
    
    # Sort objects by z_order (back first)
    sorted_objects = sorted(scene.objects, key=lambda o: o.z_order)
    
    for obj in sorted_objects:
        strokes = []
        
        if obj.obj_type == "primitive_2d":
            p = obj.params
            if isinstance(p, Primitive2DParams):
                # Override color/thickness if specified
                original_color = (0, 0, 0)
                p_copy = Primitive2DParams(
                    p.prim_type, p.center, p.size, p.size_secondary,
                    p.rotation_deg, p.thickness
                )
                strokes = get_primitive_strokes(p_copy)
                # Apply object color
                for s in strokes:
                    s.color = obj.color
        
        elif obj.obj_type == "wireframe_3d":
            w = obj.params
            if isinstance(w, Wireframe3DParams):
                # Update perspective params from scene
                w_copy = Wireframe3DParams(
                    w.wire_type, w.center, w.width, w.depth, w.height,
                    w.rotation_y_deg, w.perspective, w.vp1, w.vp2,
                    w.vp3, w.horizon_y, w.thickness, w.show_hidden
                )
                strokes = get_wireframe_strokes(w_copy)
                for s in strokes:
                    if s.color == (0, 0, 0):
                        s.color = obj.color
        
        elif obj.obj_type == "grid":
            g = obj.params
            if isinstance(g, GridParams):
                g_copy = GridParams(
                    g.perspective, g.plane, g.spacing, g.extent,
                    g.divisions, obj.color, g.color_minor
                )
                strokes = get_ground_grid_strokes(g_copy)
        
        all_strokes.extend(strokes)
    
    return all_strokes


# ============================================================
# CURRICULUM: Ordered scenes for training
# ============================================================

def get_construction_curriculum() -> List[SceneParams]:
    """Get ordered list of construction exercises."""
    results = []
    
    # 1. 2pt perspective setup
    persp_2pt = PerspectiveSetup(
        PerspectiveType.TWO_POINT, horizon_y=300,
        vp1=(100, 300), vp2=(700, 300), canvas_size=(800, 600)
    )
    
    # 2. 1pt perspective setup
    persp_1pt = PerspectiveSetup(
        PerspectiveType.ONE_POINT, horizon_y=300,
        vp1=(400, 300), canvas_size=(800, 600)
    )
    
    # Simple still life (easiest - isolated objects)
    results.append(create_still_life_simple(persp_2pt))
    
    # Interior corner (room understanding)
    results.append(create_interior_corner(persp_2pt))
    
    # Exterior building (architectural)
    results.append(create_exterior_building(persp_2pt))
    
    # 1pt corridor/hallway
    corridor_persp = PerspectiveSetup(
        PerspectiveType.ONE_POINT, horizon_y=300,
        vp1=(400, 300), canvas_size=(800, 600)
    )
    
    return results