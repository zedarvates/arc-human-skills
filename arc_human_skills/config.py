"""Configuration loader for arc-human-skills."""
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

@dataclass
class PaintConfig:
    exe_path: str
    canvas_size: tuple[int, int]
    default_color: tuple[int, int, int]
    brush_size: int

@dataclass
class VideoConfig:
    download_dir: str
    whisper_model: str
    localai_url: str

@dataclass
class EvaluationConfig:
    vision_model: str
    localai_url: str
    similarity_threshold: float

@dataclass
class QdrantConfig:
    url: str
    collections: dict[str, str]

@dataclass
class LearningTrackConfig:
    enabled: bool
    priority: int
    practice_per_session: int

@dataclass
class Config:
    storage_root: str
    paint: PaintConfig
    video: VideoConfig
    evaluation: EvaluationConfig
    qdrant: QdrantConfig
    learning_tracks: dict[str, LearningTrackConfig]

def load_config(path: str | Path = None) -> Config:
    if path is None:
        path = Path(__file__).parent.parent / "config.yaml"
    with open(path) as f:
        data = yaml.safe_load(f)
    d = data.get("arc_human_skills", {})
    return Config(
        storage_root=d["storage_root"],
        paint=PaintConfig(**d["paint"]),
        video=VideoConfig(**d["video"]),
        evaluation=EvaluationConfig(**d["evaluation"]),
        qdrant=QdrantConfig(**d["qdrant"]),
        learning_tracks={k: LearningTrackConfig(**v) for k, v in d["learning_tracks"].items()},
    )