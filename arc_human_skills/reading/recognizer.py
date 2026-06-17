"""Letter recognition for reading track - evaluates hand-drawn letters from Paint."""
import base64
import tempfile
import os
import requests
import numpy as np
import cv2
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
from PIL import Image

from arc_human_skills.config import load_config
from arc_human_skills.paint_automation import PaintController, Stroke, IS_WINDOWS, PYAUTOGUI_AVAILABLE

@dataclass
class RecognitionResult:
    predicted_letter: str
    confidence: float
    all_scores: dict[str, float]
    is_correct: bool = False

class LetterRecognizer:
    """Recognizes hand-drawn letters using LocalAI vision model."""
    
    def __init__(self, config=None):
        self.config = config or load_config()
        self.vision_model = self.config.evaluation.vision_model
        self.localai_url = self.config.evaluation.localai_url
        self.similarity_threshold = self.config.evaluation.similarity_threshold
        self.qdrant_url = self.config.qdrant.url
        self.collection = self.config.qdrant.collections["letters"]
    
    def _image_to_base64(self, image: np.ndarray) -> str:
        """Convert numpy image to base64 string."""
        _, buffer = cv2.imencode('.png', image)
        return base64.b64encode(buffer).decode('utf-8')
    
    def recognize_from_paint(self, paint_ctrl: PaintController, target_letter: str) -> RecognitionResult:
        """Capture Paint canvas and recognize the drawn letter."""
        # Capture canvas
        canvas_img = paint_ctrl.screenshot()
        
        # Preprocess: crop to content, resize to standard size
        processed = self._preprocess_canvas(canvas_img)
        
        # Recognize via vision model
        return self.recognize_image(processed, target_letter)
    
    def recognize_image(self, image: np.ndarray, target_letter: str = "") -> RecognitionResult:
        """Recognize letter from preprocessed image using LocalAI vision."""
        # Convert to base64
        b64_image = self._image_to_base64(image)
        
        # Prepare prompt for vision model
        prompt = self._build_recognition_prompt(target_letter)
        
        # Call LocalAI vision endpoint
        url = f"{self.localai_url}/v1/chat/completions"
        payload = {
            "model": self.vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}}
                    ]
                }
            ],
            "max_tokens": 100,
            "temperature": 0.1
        }
        
        try:
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code != 200:
                raise RuntimeError(f"Vision model error: {response.text}")
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            return self._parse_recognition_response(content, target_letter)
            
        except Exception as e:
            # Fallback: simple template matching with Qdrant stored templates
            return self._fallback_recognition(image, target_letter, str(e))
    
    def _build_recognition_prompt(self, target_letter: str = "") -> str:
        """Build prompt for vision model."""
        if target_letter:
            return f"""Analyze this hand-drawn letter image. The user was trying to draw the letter '{target_letter}'.
Return ONLY a JSON object with:
- "letter": the recognized letter (A-Z)
- "confidence": 0.0 to 1.0
- "reasoning": brief explanation

Example: {{"letter": "A", "confidence": 0.85, "reasoning": "Clear triangular shape with crossbar"}}"""
        else:
            return """Analyze this hand-drawn letter image. Identify which capital letter (A-Z) it represents.
Return ONLY a JSON object with:
- "letter": the recognized letter (A-Z)
- "confidence": 0.0 to 1.0
- "reasoning": brief explanation

Example: {"letter": "A", "confidence": 0.85, "reasoning": "Clear triangular shape with crossbar"}"""
    
    def _parse_recognition_response(self, content: str, target_letter: str) -> RecognitionResult:
        """Parse vision model response."""
        import json
        import re
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if not json_match:
            return RecognitionResult(
                predicted_letter="?",
                confidence=0.0,
                all_scores={},
                is_correct=False
            )
        
        try:
            data = json.loads(json_match.group())
            predicted = data.get("letter", "?").upper()
            confidence = float(data.get("confidence", 0.0))
            
            return RecognitionResult(
                predicted_letter=predicted,
                confidence=confidence,
                all_scores={predicted: confidence},
                is_correct=(predicted == target_letter.upper()) if target_letter else False
            )
        except:
            return RecognitionResult(
                predicted_letter="?",
                confidence=0.0,
                all_scores={},
                is_correct=False
            )
    
    def _preprocess_canvas(self, canvas: np.ndarray) -> np.ndarray:
        """Preprocess canvas: crop to content, resize to 224x224 for vision model."""
        # Convert to grayscale if needed
        if len(canvas.shape) == 3:
            gray = cv2.cvtColor(canvas, cv2.COLOR_BGR2GRAY)
        else:
            gray = canvas
        
        # Invert (white background -> black, black ink -> white)
        inverted = 255 - gray
        
        # Find bounding box of non-white content
        coords = cv2.findNonZero(inverted)
        if coords is not None:
            x, y, w, h = cv2.boundingRect(coords)
            # Add padding
            pad = 10
            x = max(0, x - pad)
            y = max(0, y - pad)
            w = min(gray.shape[1] - x, w + 2*pad)
            h = min(gray.shape[0] - y, h + 2*pad)
            cropped = inverted[y:y+h, x:x+w]
        else:
            cropped = inverted
        
        # Resize to 224x224 maintaining aspect ratio, pad with black
        target_size = 224
        h, w = cropped.shape
        scale = target_size / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(cropped, (new_w, new_h))
        
        # Pad to square
        canvas_square = np.zeros((target_size, target_size), dtype=np.uint8)
        y_offset = (target_size - new_h) // 2
        x_offset = (target_size - new_w) // 2
        canvas_square[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
        
        # Convert to 3-channel for vision model
        return cv2.cvtColor(canvas_square, cv2.COLOR_GRAY2BGR)
    
    def _fallback_recognition(self, image: np.ndarray, target_letter: str, error: str) -> RecognitionResult:
        """Fallback: compare with Qdrant stored templates using simple features."""
        from qdrant_client import QdrantClient
        from arc_human_skills.reading.training_data import LetterTrainingGenerator
        
        try:
            # Extract simple features
            gen = LetterTrainingGenerator(self.config)
            query_features = gen._extract_simple_features(image)
            
            # Search Qdrant
            client = QdrantClient(url=self.qdrant_url)
            results = client.search(
                collection_name=self.collection,
                query_vector=query_features,
                limit=5
            )
            
            if results:
                best = results[0]
                predicted = best.payload.get("letter", "?")
                confidence = best.score
                return RecognitionResult(
                    predicted_letter=predicted,
                    confidence=confidence,
                    all_scores={r.payload.get("letter", "?"): r.score for r in results},
                    is_correct=(predicted == target_letter.upper()) if target_letter else False
                )
        except Exception as e2:
            pass
        
        return RecognitionResult(
            predicted_letter="?",
            confidence=0.0,
            all_scores={},
            is_correct=False
        )
    
    def evaluate_stroke_sequence(self, paint_ctrl: PaintController, strokes: List[Stroke], target_letter: str) -> RecognitionResult:
        """Draw stroke sequence then recognize."""
        for stroke in strokes:
            paint_ctrl.draw_stroke(stroke)
        return self.recognize_from_paint(paint_ctrl, target_letter)


class ReadingPracticeSession:
    """Manages a reading practice session: tutorial -> practice -> evaluation."""
    
    def __init__(self, config=None):
        self.config = config or load_config()
        self.recognizer = LetterRecognizer(self.config)
        self.practice_per_session = self.config.learning_tracks["reading"].practice_per_session
        self.tutorial_processor = None  # Lazy init
    
    def _get_tutorial_processor(self):
        if self.tutorial_processor is None:
            from arc_human_skills.video_tutorial import VideoTutorialProcessor
            self.tutorial_processor = VideoTutorialProcessor(self.config.video)
        return self.tutorial_processor
    
    def watch_tutorial(self, tutorial_url: str, title: str) -> str:
        """Download and transcribe a letter tutorial video."""
        from arc_human_skills.video_tutorial import Tutorial
        
        tutorial = Tutorial(
            url=tutorial_url,
            title=title,
            track="reading"
        )
        processor = self._get_tutorial_processor()
        processed = processor.process_tutorial(tutorial)
        return processed.transcript
    
    def practice_letter(self, paint_ctrl: PaintController, letter: str, repetitions: int = 3) -> List[RecognitionResult]:
        """Practice drawing a specific letter multiple times."""
        results = []
        
        for rep in range(repetitions):
            # Clear canvas (Ctrl+N for new)
            paint_ctrl.window.type_keys("^n")
            import time
            time.sleep(0.5)
            # Don't save dialog
            try:
                dialog = paint_ctrl.window.child_window(title="Paint")
                if dialog.exists():
                    dialog.child_window(title="Don't Save", control_type="Button").click()
            except:
                pass
            
            paint_ctrl.setup_canvas(800, 600)
            
            # For now, draw a simple template stroke pattern for the letter
            # TODO: Use learned stroke patterns from writing track
            strokes = self._get_letter_stroke_pattern(letter)
            result = self.recognizer.evaluate_stroke_sequence(paint_ctrl, strokes, letter)
            results.append(result)
            
            print(f"  Rep {rep+1}: Predicted '{result.predicted_letter}' (conf: {result.confidence:.2f}) {'✓' if result.is_correct else '✗'}")
        
        return results
    
    def _get_letter_stroke_pattern(self, letter: str) -> List[Stroke]:
        """Get basic stroke pattern for a letter (simplified - will be replaced by writing track)."""
        # Simple hardcoded patterns for basic letters
        # Center: (400, 300), size ~100px
        cx, cy = 400, 300
        s = 50
        
        patterns = {
            "A": [
                Stroke((cx-s, cy+s), (cx, cy-s)),      # Left diagonal
                Stroke((cx, cy-s), (cx+s, cy+s)),      # Right diagonal
                Stroke((cx-s//2, cy), (cx+s//2, cy)),  # Crossbar
            ],
            "B": [
                Stroke((cx-s, cy-s), (cx-s, cy+s)),    # Vertical
                Stroke((cx-s, cy-s), (cx, cy-s)),      # Top curve start
                Stroke((cx, cy-s), (cx+s//2, cy)),     # Top curve
                Stroke((cx-s, cy), (cx, cy)),          # Middle curve start
                Stroke((cx, cy), (cx+s//2, cy+s)),     # Bottom curve
            ],
            "C": [
                Stroke((cx+s//2, cy-s), (cx-s, cy-s)), # Top
                Stroke((cx-s, cy-s), (cx-s, cy+s)),    # Left
                Stroke((cx-s, cy+s), (cx+s//2, cy+s)), # Bottom
            ],
            # Add more as needed
        }
        
        return patterns.get(letter.upper(), [
            Stroke((cx-s, cy-s), (cx+s, cy+s)),  # Diagonal fallback
        ])
    
    def run_session(self, letters: List[str] = None) -> dict:
        """Run a full reading practice session."""
        if letters is None:
            letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")[:self.practice_per_session]
        
        if not IS_WINDOWS or not PYAUTOGUI_AVAILABLE:
            print("⚠️ Paint automation not available on this platform (Linux/WSL)")
            return {"status": "skipped", "reason": "Windows required"}
        
        paint = PaintController()
        paint.launch()
        
        try:
            session_results = {
                "letters_practiced": [],
                "total_attempts": 0,
                "correct": 0,
                "accuracy": 0.0
            }
            
            for letter in letters:
                print(f"\n📝 Practicing letter: {letter}")
                results = self.practice_letter(paint, letter, repetitions=3)
                
                session_results["letters_practiced"].append({
                    "letter": letter,
                    "attempts": [{"predicted": r.predicted_letter, "confidence": r.confidence, "correct": r.is_correct} for r in results]
                })
                
                for r in results:
                    session_results["total_attempts"] += 1
                    if r.is_correct:
                        session_results["correct"] += 1
            
            session_results["accuracy"] = session_results["correct"] / max(1, session_results["total_attempts"])
            return session_results
            
        finally:
            paint.close()