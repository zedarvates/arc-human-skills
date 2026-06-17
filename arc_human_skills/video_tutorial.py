"""Video tutorial processing: download, transcribe, extract frames."""
import subprocess
import requests
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import cv2

from arc_human_skills.config import load_config, VideoConfig

@dataclass
class Tutorial:
    url: str
    title: str
    track: str  # reading, writing, painting
    description: str = ""
    duration: int = 0
    video_path: Optional[Path] = None
    audio_path: Optional[Path] = None
    transcript: str = ""
    key_frames: list[Path] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

@dataclass
class DownloadResult:
    video_path: Path
    audio_path: Path
    duration: float

class VideoTutorialProcessor:
    """Handles tutorial video download, transcription, frame extraction."""
    
    def __init__(self, config: VideoConfig = None):
        self.config = config or load_config().video
        self.download_dir = Path(self.config.download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
    
    def download(self, tutorial: Tutorial) -> DownloadResult:
        """Download video and extract audio using yt-dlp."""
        # Sanitize filename
        safe_title = "".join(c for c in tutorial.title if c.isalnum() or c in " -_")[:100]
        video_file = self.download_dir / f"{safe_title}.mp4"
        audio_file = self.download_dir / f"{safe_title}.wav"
        
        # Download video (best quality <= 720p to save space)
        cmd = [
            "yt-dlp",
            "-f", "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "-o", str(video_file),
            tutorial.url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"yt-dlp failed: {result.stderr}")
        
        # Extract audio as WAV (for Whisper)
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_file),
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1",
            str(audio_file)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr}")
        
        # Get duration
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_file)
        ]
        dur_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        duration = float(dur_result.stdout.strip()) if dur_result.stdout.strip() else 0
        
        tutorial.video_path = video_file
        tutorial.audio_path = audio_file
        tutorial.duration = duration
        
        return DownloadResult(video_path=video_file, audio_path=audio_file, duration=duration)
    
    def transcribe(self, audio_path: str | Path) -> str:
        """Transcribe audio using LocalAI Whisper."""
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio not found: {audio_path}")
        
        # LocalAI /v1/audio/transcriptions endpoint
        url = f"{self.config.localai_url}/v1/audio/transcriptions"
        with open(audio_path, "rb") as f:
            files = {"file": (audio_path.name, f, "audio/wav")}
            data = {"model": self.config.whisper_model, "language": "en"}
            response = requests.post(url, files=files, data=data, timeout=300)
        
        if response.status_code != 200:
            raise RuntimeError(f"Whisper failed: {response.text}")
        
        result = response.json()
        return result.get("text", "")
    
    def extract_key_frames(self, video_path: str | Path, max_frames: int = 10) -> list[Path]:
        """Extract key frames at scene changes using OpenCV."""
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")
        
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")
        
        frames_dir = self.download_dir / "frames" / video_path.stem
        frames_dir.mkdir(parents=True, exist_ok=True)
        
        prev_frame = None
        key_frames = []
        frame_count = 0
        
        while len(key_frames) < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)
            
            if prev_frame is not None:
                # Compute difference
                diff = cv2.absdiff(prev_frame, gray)
                _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
                change_ratio = cv2.countNonZero(thresh) / (gray.shape[0] * gray.shape[1])
                
                # Scene change threshold
                if change_ratio > 0.15:  # 15% pixel change
                    frame_file = frames_dir / f"keyframe_{len(key_frames):03d}.png"
                    cv2.imwrite(str(frame_file), frame)
                    key_frames.append(frame_file)
            
            prev_frame = gray
            frame_count += 1
            
            # Also sample every N frames as fallback
            if frame_count % 300 == 0 and len(key_frames) < max_frames:
                frame_file = frames_dir / f"sample_{len(key_frames):03d}.png"
                cv2.imwrite(str(frame_file), frame)
                key_frames.append(frame_file)
        
        cap.release()
        return key_frames
    
    def process_tutorial(self, tutorial: Tutorial) -> Tutorial:
        """Full pipeline: download -> transcribe -> extract frames."""
        self.download(tutorial)
        tutorial.transcript = self.transcribe(tutorial.audio_path)
        tutorial.key_frames = self.extract_key_frames(tutorial.video_path)
        return tutorial