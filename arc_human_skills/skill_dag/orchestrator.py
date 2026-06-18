"""SkillDAG loader and orchestrator for ARC-AGI-3 human skills."""
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from collections import defaultdict
from enum import Enum

@dataclass
class Skill:
    """Atomic skill in the DAG."""
    id: str
    name: str
    domain: str  # reading, writing, painting, transfer
    category: str
    description: str
    prerequisites: List[str] = field(default_factory=list)
    strokes: List[List[int]] = field(default_factory=list)  # For stroke skills
    composition: List[dict] = field(default_factory=list)  # For letter skills
    difficulty: int = 1
    practice_reps: int = 5
    colors: List[str] = field(default_factory=list)
    technique: str = ""
    target_letter: str = ""
    training_samples: int = 0
    word_list: List[str] = field(default_factory=list)
    model: str = ""
    evaluation_metric: str = "accuracy"
    enables: List[str] = field(default_factory=list)
    # Extra fields from manifest
    reading_link: str = ""
    offset: List[int] = field(default_factory=list)

@dataclass
class SkillProgress:
    """Track progress on a skill."""
    skill_id: str
    attempts: int = 0
    successes: int = 0
    avg_score: float = 0.0
    last_practiced: float = 0.0
    mastered: bool = False
    
    @property
    def success_rate(self) -> float:
        return self.successes / max(1, self.attempts)

class SkillDAGOrchestrator:
    """Orchestrates skill practice following the DAG dependencies."""
    
    def __init__(self, manifest_path: str | Path):
        self.manifest_path = Path(manifest_path)
        self.skills: Dict[str, Skill] = {}
        self.progress: Dict[str, SkillProgress] = {}
        self._load_manifest()
        self._build_dependency_graph()
    
    def _load_manifest(self):
        """Load skills from YAML manifest."""
        with open(self.manifest_path) as f:
            data = yaml.safe_load(f)
        
        for skill_data in data.get("skills", []):
            skill = Skill(**skill_data)
            self.skills[skill.id] = skill
            self.progress[skill.id] = SkillProgress(skill_id=skill.id)
    
    def _build_dependency_graph(self):
        """Build adjacency lists for topological sorting."""
        self.dependents = defaultdict(list)  # skill -> skills that depend on it
        self.in_degree = defaultdict(int)    # skill -> number of prerequisites
        
        for skill in self.skills.values():
            for prereq in skill.prerequisites:
                self.dependents[prereq].append(skill.id)
                self.in_degree[skill.id] += 1
            
            # Ensure all skills have entries
            if skill.id not in self.in_degree:
                self.in_degree[skill.id] = 0
    
    def get_ready_skills(self, domain: str = None) -> List[Skill]:
        """Get skills whose prerequisites are met (mastered)."""
        ready = []
        for skill in self.skills.values():
            if domain and skill.domain != domain:
                continue
            if self._prerequisites_met(skill.id):
                ready.append(skill)
        return ready
    
    def _prerequisites_met(self, skill_id: str) -> bool:
        """Check if all prerequisites are mastered."""
        skill = self.skills.get(skill_id)
        if not skill:
            return False
        for prereq in skill.prerequisites:
            prereq_progress = self.progress.get(prereq)
            if not prereq_progress or not prereq_progress.mastered:
                return False
        return True
    
    def get_practice_order(self, domain: str = None) -> List[Skill]:
        """Get topological order for practice (respects dependencies)."""
        # Kahn's algorithm for topological sort
        in_degree = self.in_degree.copy()
        queue = [sid for sid, deg in in_degree.items() if deg == 0]
        
        if domain:
            queue = [sid for sid in queue if self.skills[sid].domain == domain]
        
        order = []
        while queue:
            # Prioritize by difficulty (easier first) then by ID
            queue.sort(key=lambda sid: (self.skills[sid].difficulty, sid))
            current = queue.pop(0)
            order.append(self.skills[current])
            
            if domain and self.skills[current].domain != domain:
                continue
            
            for dependent in self.dependents[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        return order
    
    def record_attempt(self, skill_id: str, success: bool, score: float = 0.0):
        """Record a practice attempt."""
        import time
        progress = self.progress.get(skill_id)
        if not progress:
            return
        
        progress.attempts += 1
        if success:
            progress.successes += 1
        progress.avg_score = (progress.avg_score * (progress.attempts - 1) + score) / progress.attempts
        progress.last_practiced = time.time()
        
        # Check for mastery (configurable threshold)
        if progress.attempts >= 5 and progress.success_rate >= 0.8 and progress.avg_score >= 0.75:
            progress.mastered = True
    
    def get_skill_status(self, skill_id: str) -> dict:
        """Get detailed status for a skill."""
        skill = self.skills.get(skill_id)
        progress = self.progress.get(skill_id)
        if not skill or not progress:
            return {"error": "Skill not found"}
        
        prereqs_met = all(self.progress.get(p, SkillProgress(p)).mastered for p in skill.prerequisites)
        
        return {
            "skill_id": skill_id,
            "name": skill.name,
            "domain": skill.domain,
            "category": skill.category,
            "difficulty": skill.difficulty,
            "mastered": progress.mastered,
            "attempts": progress.attempts,
            "success_rate": progress.success_rate,
            "avg_score": progress.avg_score,
            "prerequisites_met": prereqs_met,
            "prerequisites": skill.prerequisites,
        }
    
    def get_domain_summary(self, domain: str) -> dict:
        """Get progress summary for a domain."""
        domain_skills = [s for s in self.skills.values() if s.domain == domain]
        total = len(domain_skills)
        mastered = sum(1 for s in domain_skills if self.progress[s.id].mastered)
        in_progress = sum(1 for s in domain_skills if self.progress[s.id].attempts > 0 and not self.progress[s.id].mastered)
        
        return {
            "domain": domain,
            "total_skills": total,
            "mastered": mastered,
            "in_progress": in_progress,
            "not_started": total - mastered - in_progress,
            "mastery_percentage": mastered / max(1, total) * 100,
        }
    
    def recommend_next_skills(self, domain: str = None, limit: int = 5) -> List[Skill]:
        """Recommend next skills to practice based on readiness and progress."""
        ready = self.get_ready_skills(domain)
        
        # Prioritize: not started > in progress > mastered (for review)
        def priority(skill):
            prog = self.progress[skill.id]
            if prog.mastered:
                return 2  # Review
            elif prog.attempts > 0:
                return 0  # In progress
            else:
                return 1  # Not started
        
        ready.sort(key=lambda s: (priority(s), s.difficulty, s.id))
        return ready[:limit]


def create_session_plan(orchestrator: SkillDAGOrchestrator, 
                        domain: str, 
                        max_skills: int = 5) -> List[dict]:
    """Create a practice session plan for a domain."""
    recommendations = orchestrator.recommend_next_skills(domain, max_skills)
    
    plan = []
    for skill in recommendations:
        plan.append({
            "skill_id": skill.id,
            "name": skill.name,
            "description": skill.description,
            "practice_reps": skill.practice_reps,
            "difficulty": skill.difficulty,
            "prerequisites": skill.prerequisites,
        })
    
    return plan