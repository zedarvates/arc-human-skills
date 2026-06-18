"""Tests for SkillDAG orchestrator."""
import pytest
import tempfile
import yaml
from arc_human_skills.skill_dag.orchestrator import SkillDAGOrchestrator, Skill, create_session_plan

# Minimal test manifest
TEST_MANIFEST = {
    "skills": [
        {
            "id": "stroke_vertical",
            "name": "Vertical Stroke",
            "domain": "writing",
            "category": "fundamental",
            "description": "Basic vertical line",
            "prerequisites": [],
            "difficulty": 1,
            "practice_reps": 10
        },
        {
            "id": "stroke_horizontal",
            "name": "Horizontal Stroke",
            "domain": "writing",
            "category": "fundamental",
            "description": "Basic horizontal line",
            "prerequisites": [],
            "difficulty": 1,
            "practice_reps": 10
        },
        {
            "id": "letter_T",
            "name": "Letter T",
            "domain": "writing",
            "category": "letter",
            "description": "Horizontal + vertical",
            "prerequisites": ["stroke_vertical", "stroke_horizontal"],
            "difficulty": 2,
            "practice_reps": 5
        },
        {
            "id": "shape_square",
            "name": "Square",
            "domain": "painting",
            "category": "shape",
            "description": "Four lines",
            "prerequisites": ["stroke_vertical", "stroke_horizontal"],
            "difficulty": 1,
            "practice_reps": 5
        },
        {
            "id": "transfer_strokes",
            "name": "Strokes to Shapes",
            "domain": "transfer",
            "category": "cross_domain",
            "description": "Apply strokes to shapes",
            "prerequisites": ["stroke_vertical", "stroke_horizontal"],
            "enables": ["shape_square", "letter_T"],
            "difficulty": 2,
            "practice_reps": 5
        }
    ]
}

@pytest.fixture
def orchestrator():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(TEST_MANIFEST, f)
        temp_path = f.name
    
    orch = SkillDAGOrchestrator(temp_path)
    yield orch
    
    import os
    os.unlink(temp_path)

def test_load_manifest(orchestrator):
    """Should load all skills from manifest."""
    assert len(orchestrator.skills) == 5
    assert "stroke_vertical" in orchestrator.skills
    assert "letter_T" in orchestrator.skills
    assert "transfer_strokes" in orchestrator.skills

def test_prerequisites_met(orchestrator):
    """Should correctly check prerequisites."""
    # No prerequisites met initially
    assert not orchestrator._prerequisites_met("letter_T")
    
    # Mark prerequisites as mastered
    orchestrator.progress["stroke_vertical"].mastered = True
    orchestrator.progress["stroke_horizontal"].mastered = True
    
    # Now letter_T prerequisites met
    assert orchestrator._prerequisites_met("letter_T")

def test_get_ready_skills(orchestrator):
    """Should return skills with met prerequisites."""
    ready = orchestrator.get_ready_skills("writing")
    # stroke_vertical and stroke_horizontal have no prereqs
    assert len(ready) == 2
    assert all(s.domain == "writing" for s in ready)

def test_get_practice_order(orchestrator):
    """Should return topological order."""
    order = orchestrator.get_practice_order("writing")
    skill_ids = [s.id for s in order]
    
    # Prerequisites should come before dependents
    assert skill_ids.index("stroke_vertical") < skill_ids.index("letter_T")
    assert skill_ids.index("stroke_horizontal") < skill_ids.index("letter_T")

def test_record_attempt(orchestrator):
    """Should record attempts and track mastery."""
    orchestrator.record_attempt("stroke_vertical", True, 0.9)
    orchestrator.record_attempt("stroke_vertical", True, 0.8)
    orchestrator.record_attempt("stroke_vertical", False, 0.5)
    orchestrator.record_attempt("stroke_vertical", True, 0.85)
    orchestrator.record_attempt("stroke_vertical", True, 0.9)
    
    progress = orchestrator.progress["stroke_vertical"]
    assert progress.attempts == 5
    assert progress.successes == 4
    assert progress.success_rate == 0.8
    # Not mastered yet (avg_score might be < 0.75)

def test_get_skill_status(orchestrator):
    """Should return detailed skill status."""
    status = orchestrator.get_skill_status("letter_T")
    
    assert status["skill_id"] == "letter_T"
    assert status["name"] == "Letter T"
    assert status["domain"] == "writing"
    assert status["prerequisites"] == ["stroke_vertical", "stroke_horizontal"]
    # Prereqs not met initially
    assert status["prerequisites_met"] == False

def test_get_domain_summary(orchestrator):
    """Should summarize domain progress."""
    writing_summary = orchestrator.get_domain_summary("writing")
    
    assert writing_summary["domain"] == "writing"
    assert writing_summary["total_skills"] == 3  # stroke_vertical, stroke_horizontal, letter_T
    assert writing_summary["mastered"] == 0

def test_recommend_next_skills(orchestrator):
    """Should recommend ready skills prioritized by progress."""
    recommendations = orchestrator.recommend_next_skills("writing", limit=3)
    
    # Should recommend fundamentals first (no prereqs)
    assert len(recommendations) <= 3
    assert all(s.category == "fundamental" for s in recommendations)

def test_create_session_plan(orchestrator):
    """Should create practice session plan."""
    plan = create_session_plan(orchestrator, "writing", max_skills=3)
    
    assert len(plan) <= 3
    for item in plan:
        assert "skill_id" in item
        assert "name" in item
        assert "practice_reps" in item
        assert "difficulty" in item

def test_transfer_skill_enables(orchestrator):
    """Transfer skills should list what they enable."""
    transfer = orchestrator.skills["transfer_strokes"]
    assert "shape_square" in transfer.enables
    assert "letter_T" in transfer.enables