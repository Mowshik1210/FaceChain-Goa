"""Evidence fingerprinting with SHA-256 and perceptual hash."""
import hashlib
import io
import time
from typing import Union
from PIL import Image
import imagehash
from app.models import EvidenceFingerprint


class EvidenceFingerprinter:
    def __init__(self):
        self.version = "1.0"

    def sha256(self, data: Union[bytes, str, Image.Image]) -> str:
        if isinstance(data, Image.Image):
            buf = io.BytesIO()
            data.save(buf, format="PNG")
            data = buf.getvalue()
        elif isinstance(data, str):
            data = data.encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    def perceptual_hash(self, image: Image.Image) -> str:
        return str(imagehash.phash(image))

    def fingerprint_image(self, image: Image.Image, source_url: str,
                         face_model: str, similarity_score: float) -> EvidenceFingerprint:
        sha = self.sha256(image)
        phash = self.perceptual_hash(image)
        return EvidenceFingerprint(
            sha256=sha, phash=phash, source_url=source_url,
            content_type="image/jpeg",
            retrieved_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            face_model=face_model, similarity_score=similarity_score,
            verification_version=self.version
        )

    def hash_text(self, text: str) -> str:
        normalized = " ".join(text.lower().split())
        return self.sha256(normalized)
