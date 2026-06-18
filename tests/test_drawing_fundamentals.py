"""Tests for drawing fundamentals modules."""
import pytest
import math
from arc_human_skills.drawing_fundamentals import (
    # Line control
    LineControlExercise, LineControlParams, LineOrientation, LineQualityMetrics,
    evaluate_line_drawing,
    # Primitives 2D
    Primitive2DType, Primitive2DParams, PrimitiveQualityMetrics,
    get_primitive_strokes, evaluate_primitive_2d, PRIMITIVE_2D_CURRICULUM,
    # Wireframe 3D
    Wireframe3DType, Wireframe3DParams, get_wireframe_strokes, WIREFRAME_3D_CURRICULUM,
    # Perspective
    PerspectiveType, PerspectiveSetup, GridParams, get_ground_grid_strokes,
    PERSPECTIVE_CURRICULUM, GRID_EXERCISES,
    # Construction
    ConstructionType, SceneParams, render_scene, get_construction_curriculum,
    # Curriculum
    DrawingLevel, SkillProgress, DrawingCurriculum, DRAWING_FUNDAMENTALS_SKILLS,
    get_all_strokes_for_skill,
)


class TestLineControl:
    """Tests for Level 0: Line control."""
    
    def test_standard_exercises_exist(self):
        """Should have standard line exercises."""
        ex = LineControlExercise()
        assert len(ex.exercises) >= 8  # At least H, V, 4 diagonals
        
        orientations = [p.orientation for p in ex.exercises]
        assert LineOrientation.HORIZONTAL in orientations
        assert LineOrientation.VERTICAL in orientations
        assert LineOrientation.DIAGONAL_45 in orientations
        assert LineOrientation.DIAGONAL_135 in orientations
    
    def test_get_stroke_for_exercise(self):
        """Should generate correct strokes for exercises."""
        ex = LineControlExercise()
        for params in ex.exercises[:4]:  # Test first 4
            stroke = ex.get_stroke_for_exercise(params)
            assert isinstance(stroke.start, tuple)
            assert isinstance(stroke.end, tuple)
            assert stroke.thickness == params.target_thickness
    
    def test_evaluate_perfect_line(self):
        """Perfect line should score 1.0."""
        params = LineControlParams(
            LineOrientation.HORIZONTAL, (100, 300), 400
        )
        # Perfect line pixels
        drawn = [(100 + i, 300) for i in range(401)]
        
        metrics = evaluate_line_drawing(drawn, params)
        
        assert metrics.composite_score > 0.95
        assert metrics.angle_error_deg < 1.0
        assert metrics.length_error_pct < 1.0
        assert metrics.straightness_score > 0.99
    
    def test_evaluate_noisy_line(self):
        """Noisy line should have lower score."""
        params = LineControlParams(
            LineOrientation.HORIZONTAL, (100, 300), 400
        )
        # Wavy line with significant deviation
        drawn = [(100 + i, 300 + int(15 * math.sin(i * 0.2))) for i in range(401)]
        
        metrics = evaluate_line_drawing(drawn, params)
        
        assert metrics.composite_score < 0.85
        assert metrics.rmse_deviation_px > 8.0
        assert metrics.straightness_score < 0.9
    
    def test_evaluate_wrong_angle(self):
        """Line at wrong angle should have high angle error."""
        params = LineControlParams(LineOrientation.HORIZONTAL, (100, 300), 400)
        # Vertical line instead of horizontal
        drawn = [(100, 300 - i) for i in range(401)]
        
        metrics = evaluate_line_drawing(drawn, params)
        
        assert metrics.angle_error_deg > 80  # ~90° off


class TestPrimitives2D:
    """Tests for Level 1: 2D primitives."""
    
    def test_all_primitive_types_have_strokes(self):
        """Each primitive type should generate strokes."""
        for prim_type in Primitive2DType:
            params = Primitive2DParams(prim_type, (400, 300), 100)
            strokes = get_primitive_strokes(params)
            assert len(strokes) > 0
    
    def test_square_has_4_strokes(self):
        """Square should have 4 edges."""
        params = Primitive2DParams(Primitive2DType.SQUARE, (400, 300), 100)
        strokes = get_primitive_strokes(params)
        assert len(strokes) == 4
    
    def test_cross_has_2_strokes(self):
        """Cross should have 2 strokes."""
        params = Primitive2DParams(Primitive2DType.CROSS, (400, 300), 80)
        strokes = get_primitive_strokes(params)
        assert len(strokes) == 2
    
    def test_hexagon_has_6_strokes(self):
        """Hexagon should have 6 strokes."""
        params = Primitive2DParams(Primitive2DType.HEXAGON, (400, 300), 80)
        strokes = get_primitive_strokes(params)
        assert len(strokes) == 6
    
    def test_circle_approximation(self):
        """Circle should have many segments."""
        params = Primitive2DParams(Primitive2DType.CIRCLE, (400, 300), 80)
        strokes = get_primitive_strokes(params)
        assert len(strokes) == 16  # 16 segments
    
    def test_evaluate_square_perfect(self):
        """Perfect square should score high."""
        params = Primitive2DParams(Primitive2DType.SQUARE, (400, 300), 100)
        strokes = get_primitive_strokes(params)
        
        # Extract perfect pixels from each stroke
        drawn_by_stroke = []
        for stroke in strokes:
            # Simple interpolation
            x1, y1 = stroke.start
            x2, y2 = stroke.end
            n = max(abs(x2-x1), abs(y2-y1)) + 1
            drawn = [
                (int(x1 + (x2-x1)*i/n), int(y1 + (y2-y1)*i/n))
                for i in range(n)
            ]
            drawn_by_stroke.append(drawn)
        
        metrics = evaluate_primitive_2d(drawn_by_stroke, params)
        
        assert metrics.composite_score > 0.75
        assert metrics.is_closed
        assert metrics.closure_gap_px < 5.0
    
    def test_curriculum_order(self):
        """Curriculum should progress from simple to complex."""
        # Cross (2 strokes) -> Square (4) -> Triangle (3) -> Hexagon (6) -> Circle (16)
        types_in_order = [p.prim_type for p in PRIMITIVE_2D_CURRICULUM]
        
        assert types_in_order[0] == Primitive2DType.CROSS  # Simplest
        assert types_in_order[1] == Primitive2DType.SQUARE
        assert Primitive2DType.CIRCLE in types_in_order[-2:]  # Last (hardest)


class TestWireframe3D:
    """Tests for Level 2: 3D wireframes."""
    
    def test_cube_vertices(self):
        """Cube should have 8 vertices."""
        params = Wireframe3DParams(
            Wireframe3DType.CUBE, (400, 300), 100, 100, 100, perspective="iso"
        )
        # Import the internal function
        from arc_human_skills.drawing_fundamentals.wireframe_3d import get_3d_vertices
        vertices = get_3d_vertices(params)
        assert len(vertices) == 8
        for k in ['A','B','C','D','E','F','G','H']:
            assert k in vertices
    
    def test_pyramid_vertices(self):
        """Square pyramid should have 5 vertices."""
        params = Wireframe3DParams(
            Wireframe3DType.SQUARE_PYRAMID, (400, 300), 100, 100, 100, perspective="iso"
        )
        from arc_human_skills.drawing_fundamentals.wireframe_3d import get_3d_vertices
        vertices = get_3d_vertices(params)
        assert len(vertices) == 5
        assert 'P' in vertices  # Apex
    
    def test_isometric_projection(self):
        """Isometric projection should work."""
        params = Wireframe3DParams(
            Wireframe3DType.CUBE, (400, 350), 100, 100, 100,
            perspective="iso", rotation_y_deg=30
        )
        strokes = get_wireframe_strokes(params)
        assert len(strokes) == 12  # 12 edges of cube
    
    def test_2pt_perspective_projection(self):
        """2-point perspective should produce strokes."""
        params = Wireframe3DParams(
            Wireframe3DType.CUBE, (400, 400), 100, 100, 100,
            perspective="2pt", vp1=(100, 300), vp2=(700, 300),
            horizon_y=300, rotation_y_deg=30
        )
        strokes = get_wireframe_strokes(params)
        assert len(strokes) > 0
    
    def test_curriculum_progression(self):
        """Wireframe curriculum should progress isometric -> 1pt -> 2pt."""
        types = [p.wire_type for p in WIREFRAME_3D_CURRICULUM]
        perspectives = [p.perspective for p in WIREFRAME_3D_CURRICULUM]
        
        # First should be iso
        assert perspectives[0] == "iso"
        # Should have 2pt later
        assert "2pt" in perspectives


class TestPerspective:
    """Tests for Level 3: Perspective construction."""
    
    def test_1pt_setup(self):
        """1-point perspective setup."""
        p = PerspectiveSetup(PerspectiveType.ONE_POINT, horizon_y=300, vp1=(400, 300))
        assert p.vp1 == (400, 300)
        assert p.vp2 is None
    
    def test_2pt_setup(self):
        """2-point perspective setup."""
        p = PerspectiveSetup(
            PerspectiveType.TWO_POINT, horizon_y=300,
            vp1=(100, 300), vp2=(700, 300)
        )
        assert p.vp1 == (100, 300)
        assert p.vp2 == (700, 300)
    
    def test_ground_grid_2pt(self):
        """2pt ground grid should generate strokes."""
        p = PerspectiveSetup(
            PerspectiveType.TWO_POINT, horizon_y=300,
            vp1=(100, 300), vp2=(700, 300), canvas_size=(800, 600)
        )
        grid = GridParams(p, spacing=50, divisions=8)
        strokes = get_ground_grid_strokes(grid)
        assert len(strokes) > 20  # Many grid lines
    
    def test_horizon_line(self):
        """Horizon line spans canvas."""
        from arc_human_skills.drawing_fundamentals.curriculum import get_horizon_line
        p = PerspectiveSetup(PerspectiveType.ONE_POINT, horizon_y=300, canvas_size=(800, 600))
        stroke = get_horizon_line(p)
        assert stroke.start == (0, 300)
        assert stroke.end == (800, 300)


class TestConstruction:
    """Tests for Level 4: Scene construction."""
    
    def test_still_life_creation(self):
        """Should create still life scene."""
        p = PerspectiveSetup(
            PerspectiveType.TWO_POINT, horizon_y=300,
            vp1=(100, 300), vp2=(700, 300), canvas_size=(800, 600)
        )
        scene = get_construction_curriculum()[0]  # First is still life
        assert scene.scene_type == ConstructionType.STILL_LIFE_SIMPLE
        assert len(scene.objects) >= 3
    
    def test_render_scene_produces_strokes(self):
        """Scene rendering should produce strokes."""
        p = PerspectiveSetup(
            PerspectiveType.TWO_POINT, horizon_y=300,
            vp1=(100, 300), vp2=(700, 300), canvas_size=(800, 600)
        )
        scene = get_construction_curriculum()[0]
        strokes = render_scene(scene)
        assert len(strokes) > 10
    
    def test_objects_have_z_order(self):
        """Objects should have z_order for layering."""
        p = PerspectiveSetup(
            PerspectiveType.TWO_POINT, horizon_y=300,
            vp1=(100, 300), vp2=(700, 300), canvas_size=(800, 600)
        )
        scene = get_construction_curriculum()[0]
        for obj in scene.objects:
            assert hasattr(obj, 'z_order')


class TestCurriculum:
    """Tests for curriculum orchestration."""
    
    def test_drawing_levels_defined(self):
        """All 5 levels should exist."""
        assert DrawingLevel.LEVEL_0_LINE_CONTROL.value == 0
        assert DrawingLevel.LEVEL_1_PRIMITIVES_2D.value == 1
        assert DrawingLevel.LEVEL_2_WIREFRAME_3D.value == 2
        assert DrawingLevel.LEVEL_3_PERSPECTIVE.value == 3
        assert DrawingLevel.LEVEL_4_CONSTRUCTION.value == 4
    
    def test_curriculum_initialization(self):
        """Curriculum should initialize all exercises."""
        curr = DrawingCurriculum()
        
        assert len(curr.line_exercises) > 0
        assert len(curr.primitive_exercises) > 0
        assert len(curr.wireframe_exercises) > 0
        assert len(curr.perspective_setups) > 0
        assert len(curr.grid_exercises) > 0
        assert len(curr.construction_scenes) > 0
        
        # Should have progress for all (approx 39 skills)
        assert len(curr.progress) >= 35
    
    def test_get_next_unmastered(self):
        """Should return first unmastered skill."""
        curr = DrawingCurriculum()
        next_skill = curr.get_next_unmastered()
        
        assert next_skill is not None
        assert not next_skill.mastered
        # Should be level 0 (line control) first
        assert next_skill.level == DrawingLevel.LEVEL_0_LINE_CONTROL
    
    def test_record_attempt(self):
        """Recording attempts should update progress."""
        curr = DrawingCurriculum()
        skill_id = list(curr.progress.keys())[0]
        
        curr.record_attempt(skill_id, 0.9, {"test": "data"})
        
        p = curr.progress[skill_id]
        assert p.attempts == 1
        assert p.successes == 1
        assert p.best_score == 0.9
        assert p.avg_score == 0.9
    
    def test_mastery_criteria(self):
        """Mastery should be granted after 5 attempts avg >= 0.8."""
        curr = DrawingCurriculum()
        skill_id = list(curr.progress.keys())[0]
        
        # 5 good attempts
        for _ in range(5):
            curr.record_attempt(skill_id, 0.85, {})
        
        p = curr.progress[skill_id]
        assert p.mastered
        assert p.attempts == 5
    
    def test_level_completion(self):
        """Level completion calculation."""
        curr = DrawingCurriculum()
        
        # No skills mastered initially
        assert curr.get_level_completion(DrawingLevel.LEVEL_0_LINE_CONTROL) == 0.0
        assert curr.get_overall_completion() == 0.0
    
    def test_skill_dag_manifest(self):
        """SkillDAG manifest should have proper structure."""
        for skill in DRAWING_FUNDAMENTALS_SKILLS:
            assert 'id' in skill
            assert 'name' in skill
            assert 'level' in skill
            assert 'prerequisites' in skill
            assert 'category' in skill
            assert 0 <= skill['level'] <= 4
            # Prerequisites should be strings
            for prereq in skill['prerequisites']:
                assert isinstance(prereq, str)
    
    def test_transfer_skills_exist(self):
        """Should have transfer skills connecting to writing/painting."""
        transfer_skills = [s for s in DRAWING_FUNDAMENTALS_SKILLS if s['category'] == 'transfer']
        assert len(transfer_skills) >= 3
        
        transfer_ids = [s['id'] for s in transfer_skills]
        assert 'transfer_line_to_stroke' in transfer_ids
        assert 'transfer_prim_to_letter' in transfer_ids
        assert 'transfer_wire_to_shape' in transfer_ids
    
    def test_prerequisite_chain(self):
        """Prerequisites should form valid DAG (no cycles)."""
        # Build graph
        graph = {s['id']: s['prerequisites'] for s in DRAWING_FUNDAMENTALS_SKILLS}
        
        # Simple cycle detection (DFS)
        visited = set()
        rec_stack = set()
        
        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False
        
        for node in graph:
            if node not in visited:
                assert not has_cycle(node), f"Cycle detected involving {node}"


class TestIntegration:
    """Integration tests across levels."""
    
    def test_get_strokes_for_skill(self):
        """Should get strokes for any skill ID."""
        curr = DrawingCurriculum()
        
        # Level 0
        strokes = get_all_strokes_for_skill(curr, "line_horizontal_0")
        assert len(strokes) == 1
        
        # Level 1
        strokes = get_all_strokes_for_skill(curr, "primitive_square_1")
        assert len(strokes) == 4
        
        # Level 2
        strokes = get_all_strokes_for_skill(curr, "wireframe_cube_iso_0")
        assert len(strokes) > 0
        
        # Level 3
        strokes = get_all_strokes_for_skill(curr, "perspective_1pt_0")
        assert len(strokes) >= 1  # Horizon line
        
        # Level 4 (may be empty if not enough scenes)
        scene_skills = [s for s in curr.progress if s.startswith("construction_")]
        if scene_skills:
            strokes = get_all_strokes_for_skill(curr, scene_skills[0])
            assert len(strokes) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])