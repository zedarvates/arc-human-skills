"""Tests for benchmark and trainer."""
import pytest
import json
import tempfile
from pathlib import Path
from arc_human_skills.benchmark import BenchmarkRunner, BenchmarkResult, TaskStatus
from arc_human_skills.trainer import HumanSkillsTrainer, TrainingConfig

def test_benchmark_result():
    """BenchmarkResult should store all fields."""
    result = BenchmarkResult(
        task_id="test_001",
        status=TaskStatus.PASSED,
        score=0.85,
        details={"key": "value"},
        duration_sec=1.5
    )
    assert result.task_id == "test_001"
    assert result.status == TaskStatus.PASSED
    assert result.score == 0.85
    assert result.details["key"] == "value"

def test_training_config():
    """TrainingConfig should have sensible defaults."""
    config = TrainingConfig()
    assert config.session_duration_min == 30
    assert config.max_sessions == 0
    assert "writing" in config.domains_per_session
    assert "reading" in config.domains_per_session
    assert "painting" in config.domains_per_session

def test_trainer_init():
    """Trainer should initialize with config."""
    config = TrainingConfig(headless=True, max_sessions=1)
    trainer = HumanSkillsTrainer(config)
    assert trainer.config.headless == True
    assert trainer.config.max_sessions == 1
    assert trainer.running == False

def test_skill_dag_integration(trainer):
    """Trainer should have access to skill DAG."""
    assert trainer.skill_dag is not None
    assert len(trainer.skill_dag.skills) > 0

def test_session_plan_generation():
    """Should generate session plans from skill DAG."""
    from arc_human_skills.skill_dag.orchestrator import SkillDAGOrchestrator, create_session_plan
    
    # Use the actual manifest
    manifest_path = Path(__file__).parent.parent / "arc_human_skills" / "skill_dag" / "manifest.yaml"
    if manifest_path.exists():
        dag = SkillDAGOrchestrator(manifest_path)
        plan = create_session_plan(dag, "writing", max_skills=3)
        assert len(plan) <= 3
        for item in plan:
            assert "skill_id" in item
            assert "name" in item
            assert "practice_reps" in item

def test_benchmark_task_format():
    """Benchmark tasks should have valid structure."""
    tasks_file = Path(__file__).parent.parent / "arc_human_skills" / "eval_tasks" / "arc_tasks.json"
    if tasks_file.exists():
        with open(tasks_file) as f:
            tasks = json.load(f)
        
        assert len(tasks) > 0
        for task in tasks:
            assert "task_id" in task
            assert "domain" in task
            assert "type" in task
            assert "description" in task
            assert "input" in task
            assert "expected_output" in task
            assert "evaluation" in task
            assert "difficulty" in task
            
            # Check domain values
            assert task["domain"] in ["reading", "writing", "painting", "transfer", "integrated"]
            
            # Check difficulty range
            assert 1 <= task["difficulty"] <= 4