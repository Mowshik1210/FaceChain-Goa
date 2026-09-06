"""Face detection and quality assessment."""
import os
import cv2
import numpy as np
from deepface import DeepFace

from app.models import DetectedFace, BoundingBox, FaceQuality
from app.config import config


class FaceDetector:
    def __init__(self):
        self.detector_backend = config.face.detector
        self.min_face_size = config.face.min_face_size
        self.min_confidence = config.face.min_confidence
        self.min_sharpness = config.face.min_sharpness

    def detect(self, image_path: str) -> list:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        try:
            faces = DeepFace.extract_faces(
                img_path=image_path,
                detector_backend=self.detector_backend,
                enforce_detection=False,
                align=True
            )
        except Exception as e:
            raise RuntimeError(f"Face detection failed: {e}")

        detected_faces = []
        for idx, face_data in enumerate(faces):
            if not isinstance(face_data, dict):
                continue
            facial_area = face_data.get("facial_area", {})
            confidence = face_data.get("confidence", 0.0)
            x = facial_area.get("x", 0)
            y = facial_area.get("y", 0)
            w = facial_area.get("w", 0)
            h = facial_area.get("h", 0)
            bbox = BoundingBox(x=x, y=y, width=w, height=h)
            face_img = img_rgb[y:y+h, x:x+w]
            quality = self._assess_quality(face_img, confidence)
            face = DetectedFace(bbox=bbox, quality=quality, face_id=idx)
            detected_faces.append(face)
        return detected_faces

    def _assess_quality(self, face_img, confidence):
        if face_img.size == 0:
            return FaceQuality(0.0, 0, 0.0, 0.0, False, "Empty face region")
        face_size = min(face_img.shape[:2])
        gray = cv2.cvtColor(face_img, cv2.COLOR_RGB2GRAY)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        brightness = float(np.mean(gray))
        is_valid = True
        reasons = []
        if face_size < self.min_face_size:
            is_valid = False
            reasons.append(f"Face too small ({face_size}px)")
        if confidence < self.min_confidence:
            is_valid = False
            reasons.append(f"Low confidence ({confidence:.2f})")
        if sharpness < self.min_sharpness:
            is_valid = False
            reasons.append(f"Too blurry ({sharpness:.1f})")
        if brightness < 20 or brightness > 250:
            is_valid = False
            reasons.append(f"Poor lighting ({brightness:.1f})")
        return FaceQuality(
            confidence=float(confidence), face_size=int(face_size),
            sharpness=float(sharpness), brightness=brightness,
            is_valid=is_valid,
            rejection_reason="; ".join(reasons) if reasons else None
        )

    def get_primary_face(self, faces):
        if not faces:
            return None
        valid_faces = [f for f in faces if f.quality.is_valid]
        if not valid_faces:
            return None
        valid_faces.sort(key=lambda f: f.quality.confidence * f.quality.face_size, reverse=True)
        return valid_faces[0]
