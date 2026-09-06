"""Face embedding generation."""
import numpy as np
from deepface import DeepFace
from app.models import FaceEmbedding
from app.config import config


class FaceEmbedder:
    def __init__(self):
        self.model_name = config.face.model
        self.detector_backend = config.face.detector

    def embed(self, image_path: str, face=None) -> FaceEmbedding:
        try:
            reps = DeepFace.represent(
                img_path=image_path,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=False,
                align=True
            )
        except Exception as e:
            raise RuntimeError(f"Embedding generation failed: {e}")
        if not reps:
            raise ValueError("No face representation generated")
        embedding = reps[0]["embedding"]
        return FaceEmbedding(
            embedding=np.array(embedding),
            model_name=self.model_name,
            detector_name=self.detector_backend,
            dimension=len(embedding)
        )
