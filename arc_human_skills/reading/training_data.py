"""Letter training data generation for reading track."""
import os
import time
import subprocess
import requests
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

from arc_human_skills.config import load_config

@dataclass
class LetterSample:
    letter: str
    image: np.ndarray  # 64x64 grayscale
    font_name: str
    font_size: int
    style: str  # regular, bold, italic, handwritten

class LetterTrainingGenerator:
    """Generates letter training images in multiple fonts/styles for recognition training."""
    
    # Common Windows fonts that should be available
    FONTS = [
        ("Arial", "regular"),
        ("Arial", "bold"),
        ("Arial", "italic"),
        ("Times New Roman", "regular"),
        ("Times New Roman", "bold"),
        ("Courier New", "regular"),
        ("Courier New", "bold"),
        ("Consolas", "regular"),
        ("Calibri", "regular"),
        ("Calibri", "bold"),
    ]
    
    def __init__(self, config=None):
        self.config = config or load_config()
        self.output_dir = Path(self.config.storage_root) / "training" / "letters"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.qdrant_url = self.config.qdrant.url
        self.collection = self.config.qdrant.collections["letters"]
        self.vision_model = self.config.evaluation.vision_model
        self.localai_url = self.config.evaluation.localai_url
    
    def _get_font_path(self, font_name: str, style: str) -> Optional[str]:
        """Get font file path for given font and style."""
        import os
        fonts_dir = "C:/Windows/Fonts"
        style_map = {
            "regular": "",
            "bold": "bd",
            "italic": "i",
            "bold_italic": "bi",
        }
        suffix = style_map.get(style, "")
        
        # Common font filenames
        candidates = [
            f"{font_name}{suffix}.ttf",
            f"{font_name.replace(' ', '')}{suffix}.ttf",
        ]
        
        for cand in candidates:
            path = os.path.join(fonts_dir, cand)
            if os.path.exists(path):
                return path
        
        # Fallback: try to find any matching font
        for f in os.listdir(fonts_dir):
            if font_name.lower().replace(" ", "") in f.lower() and f.endswith(".ttf"):
                return os.path.join(fonts_dir, f)
        
        return None
    
    def generate_letter(self, letter: str, count: int = 10, size: int = 64) -> list[np.ndarray]:
        """Generate letter images in multiple font styles."""
        if len(letter) != 1 or not letter.isalpha():
            raise ValueError("Letter must be a single alphabetic character")
        
        letter = letter.upper()
        images = []
        
        for font_name, style in self.FONTS:
            if len(images) >= count:
                break
            
            font_path = self._get_font_path(font_name, style)
            if not font_path:
                continue
            
            try:
                # Create image
                img = Image.new('L', (size, size), 255)  # White background
                draw = ImageDraw.Draw(img)
                
                # Load font
                font = ImageFont.truetype(font_path, size - 8)  # Leave margin
                
                # Center the letter
                bbox = draw.textbbox((0, 0), letter, font=font)
                w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                x = (size - w) // 2
                y = (size - h) // 2
                
                # Draw letter in black
                draw.text((x, y), letter, font=font, fill=0)
                
                # Convert to numpy
                arr = np.array(img, dtype=np.uint8)
                images.append(arr)
                
            except Exception as e:
                print(f"Failed to generate {letter} with {font_name} {style}: {e}")
                continue
        
        # If not enough, duplicate with noise
        while len(images) < count and images:
            base = images[np.random.randint(0, len(images))]
            noise = np.random.normal(0, 5, base.shape).astype(np.int16)
            noisy = np.clip(base.astype(np.int16) + noise, 0, 255).astype(np.uint8)
            images.append(noisy)
        
        return images[:count]
    
    def _get_embedding(self, image: np.ndarray) -> list[float]:
        """Get vision embedding for image via LocalAI."""
        # Save temp image
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            temp_path = f.name
        cv2.imwrite(temp_path, image)
        
        try:
            # LocalAI embeddings endpoint (would need vision embeddings model)
            # For now, use a simple feature vector
            # TODO: Use actual vision embedding model
            features = self._extract_simple_features(image)
            return features
        finally:
            os.unlink(temp_path)
    
    def _extract_simple_features(self, image: np.ndarray) -> list[float]:
        """Extract simple handcrafted features for letter recognition."""
        # Resize to 32x32 for consistency
        small = cv2.resize(image, (32, 32))
        
        # Normalize
        norm = small.astype(np.float32) / 255.0
        
        # Flatten + basic moments
        flat = norm.flatten()
        
        # Hu moments for shape invariance
        moments = cv2.moments(small)
        hu = cv2.HuMoments(moments).flatten()
        
        # Combine
        features = np.concatenate([flat[::4], hu])  # Downsample + moments
        return features.tolist()
    
    def generate_and_store(self, letter: str, count: int = 10):
        """Generate letter samples and store in Qdrant."""
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct, VectorParams, Distance
        
        client = QdrantClient(url=self.qdrant_url)
        
        # Create collection if not exists
        try:
            client.get_collection(self.collection)
        except:
            # Determine vector size from sample
            sample_images = self.generate_letter(letter, 1)
            if sample_images:
                sample_embedding = self._get_embedding(sample_images[0])
                vec_size = len(sample_embedding)
                client.create_collection(
                    collection_name=self.collection,
                    vectors_config=VectorParams(size=vec_size, distance=Distance.COSINE)
                )
        
        # Generate and store
        images = self.generate_letter(letter, count)
        points = []
        
        for i, img in enumerate(images):
            embedding = self._get_embedding(img)
            point = PointStruct(
                id=hash(f"{letter}_{i}_{time.time()}") % (2**63),
                vector=embedding,
                payload={
                    "letter": letter,
                    "font_index": i,
                    "image_shape": img.shape,
                }
            )
            points.append(point)
        
        if points:
            client.upsert(collection_name=self.collection, points=points)
        
        return len(points)

    def generate_alphabet(self, count_per_letter: int = 5):
        """Generate training data for all letters A-Z."""
        import time
        total = 0
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            n = self.generate_and_store(letter, count_per_letter)
            total += n
            print(f"Generated {n} samples for {letter}")
        print(f"Total: {total} samples stored in Qdrant")
        return total