"""
Hailo-8 Vision Evaluator for ARC Human Skills
Secondary evaluator using Hailo-8 NPU on EUREKAI (192.168.1.47:8767).
- YOLOv8m: detect UI elements, drawing components
- OCR: extract text from drawings/screenshots
- Classification: identify shapes, letters, primitives

Falls back gracefully if Hailo-8 is unavailable → geometric-only evaluation.
"""
import json, os, base64, io, logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import urllib.request, urllib.error, urllib.parse

logger = logging.getLogger(__name__)

HAILO_URL = os.environ.get("HAILO_API_URL", "http://192.168.1.47:8767")
CONFIDENCE_THRESHOLD = float(os.environ.get("HAILO_CONFIDENCE", 0.5))

# ── Data Types ────────────────────────────────────────────────

@dataclass
class Detection:
    """YOLOv8 detection result"""
    label: str
    confidence: float
    x: float
    y: float
    width: float
    height: float

@dataclass
class OcrResult:
    """OCR extracted text"""
    text: str
    confidence: float

@dataclass
class EvaluationResult:
    """Combined evaluation from Hailo-8"""
    score: float                # 0-1 composite
    details: Dict[str, Any]    # raw response
    hailo_available: bool      # whether Hailo was used
    error: Optional[str] = None

# ── API Calls ─────────────────────────────────────────────────

def _api_post(endpoint: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    """Send POST request to Hailo-8 API"""
    url = f"{HAILO_URL}{endpoint}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data,
        headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        logger.warning(f"Hailo HTTP {e.code}: {e.read().decode()[:100]}")
        return None
    except Exception as e:
        logger.warning(f"Hailo request failed: {e}")
        return None

def check_available() -> bool:
    """Quick check if Hailo-8 API is responsive"""
    try:
        resp = urllib.request.urlopen(f"{HAILO_URL}/health", timeout=3)
        return resp.status == 200
    except:
        return False

# ── Drawing Evaluation ────────────────────────────────────────

def evaluate_drawing(image_path: str) -> EvaluationResult:
    """
    Evaluate a drawing using Hailo-8 vision.
    Uses OCR to check if text/shape labels are correct and
    detection to verify drawing components.
    """
    hailo_ok = check_available()
    if not hailo_ok:
        return EvaluationResult(
            score=0.0, details={}, hailo_available=False,
            error="Hailo-8 unavailable (fallback to geometric)"
        )
    
    path = Path(image_path)
    if not path.exists():
        return EvaluationResult(
            score=0.0, details={}, hailo_available=True,
            error=f"File not found: {image_path}"
        )
    
    # Detect objects in the drawing
    detections = _api_post("/vision/detect", {
        "image_path": str(path.resolve())
    })
    
    # OCR to verify text
    ocr_result = _api_post("/vision/ocr", {
        "image_path": str(path.resolve())
    })
    
    # Classify the drawing
    classify_result = _api_post("/vision/classify", {
        "image_path": str(path.resolve())
    })
    
    details = {
        "detections": detections,
        "ocr": ocr_result,
        "classification": classify_result,
    }
    
    # Compute composite score
    score = _compute_score(detections, ocr_result, classify_result)
    
    return EvaluationResult(
        score=score,
        details=details,
        hailo_available=True,
    )

def evaluate_stroke(image_path: str, expected_label: str) -> EvaluationResult:
    """
    Evaluate a single stroke drawing against expected label.
    Uses Hailo-8 classification to check if the drawing matches
    the expected primitive/shape.
    """
    result = evaluate_drawing(image_path)
    if not result.hailo_available or result.error:
        return result
    
    # Check if detected objects match expected
    detections = result.details.get("detections", {})
    detected_labels = []
    if detections and "detections" in detections:
        detected_labels = [d.get("label", "").lower()
                          for d in detections["detections"]]
    
    expected = expected_label.lower()
    match = expected in detected_labels
    confidence = 0.0
    if match and detections:
        for d in detections.get("detections", []):
            if d.get("label", "").lower() == expected:
                confidence = max(confidence, d.get("confidence", 0))
    
    result.score = confidence if match else 0.0
    result.details["expected"] = expected_label
    result.details["detected"] = detected_labels
    result.details["match"] = match
    
    return result

def _compute_score(detections: Optional[dict],
                   ocr: Optional[dict],
                   classification: Optional[dict]) -> float:
    """Compute composite 0-1 score from all Hailo-8 outputs"""
    scores = []
    
    if detections and "detections" in detections:
        avg_conf = sum(d.get("confidence", 0) for d in detections["detections"])
        count = len(detections["detections"])
        if count > 0:
            scores.append(avg_conf / count)
    
    if ocr and "text" in ocr:
        # OCR has text → at least 0.5 for having content
        text_conf = ocr.get("confidence", 0.5)
        scores.append(text_conf if text_conf > 0 else 0.5)
    
    if classification and "predictions" in classification:
        avg_pred = sum(p.get("confidence", 0) for p in classification["predictions"])
        pred_count = len(classification["predictions"])
        if pred_count > 0:
            scores.append(avg_pred / pred_count)
    
    if not scores:
        return 0.0
    
    return sum(scores) / len(scores)

def evaluate_via_hailo(image_path: str, task_type: str = "stroke",
                       expected: Optional[str] = None) -> EvaluationResult:
    """
    Unified entry point for Hailo-8 evaluation.
    
    Args:
        image_path: Path to the screenshot/image
        task_type: "stroke" | "primitive" | "letter" | "wireframe" | "painting"
        expected: Expected label (e.g. "square", "A", "cube")
    """
    if task_type in ("stroke", "primitive"):
        return evaluate_stroke(image_path, expected or "unknown")
    elif task_type == "letter":
        return evaluate_stroke(image_path, expected or "letter")
    else:
        return evaluate_drawing(image_path)

# ── Integration Hook ─────────────────────────────────────────

def integrate_with_trainer(trainer_instance) -> None:
    """
    Patch a trainer instance to use Hailo-8 as secondary evaluator.
    Call this after creating the trainer:
        trainer = Trainer(...)
        integrate_with_trainer(trainer)
    
    The trainer will then use Hailo-8 alongside geometric metrics.
    """
    original_evaluate = getattr(trainer_instance, '_evaluate_drawing', None)
    
    async def patched_evaluate(skill_id, image_path, **kwargs):
        # Run original geometric evaluation
        geo_score = 0.0
        if original_evaluate:
            geo_result = await original_evaluate(skill_id, image_path, **kwargs)
            if hasattr(geo_result, 'score'):
                geo_score = geo_result.score
            elif isinstance(geo_result, (int, float)):
                geo_score = geo_result
        
        # Run Hailo-8 visual evaluation
        hailo_result = evaluate_drawing(image_path)
        
        # Combine: weighted average (60% geometric, 40% visual)
        if hailo_result.hailo_available and not hailo_result.error:
            combined = (geo_score * 0.6) + (hailo_result.score * 0.4)
            logger.info(f"Hailo evaluation: geo={geo_score:.2f}, "
                       f"hailo={hailo_result.score:.2f}, combined={combined:.2f}")
            return combined
        
        return geo_score
    
    trainer_instance._evaluate_drawing = patched_evaluate
    logger.info("Hailo-8 evaluator integrated with trainer")
