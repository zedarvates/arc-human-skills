"""arc-human-skills: ARC-AGI-3 Human-like skills acquisition."""
from .config import load_config, Config, PaintConfig, VideoConfig, EvaluationConfig, QdrantConfig, LearningTrackConfig

__version__ = "0.1.0"
__all__ = [
    "load_config",
    "Config",
    "PaintConfig",
    "VideoConfig",
    "EvaluationConfig",
    "QdrantConfig",
    "LearningTrackConfig",
]