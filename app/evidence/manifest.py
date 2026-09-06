"""Evidence manifest generation."""
import time
import json
from typing import Dict, Any, List
from app.models import EvidenceManifest, EvidenceFingerprint, DetectedFace, CandidateEvidence


class EvidenceManifestBuilder:
    def build(self, fingerprint, input_face, matched_candidate, chain_of_custody=None):
        return EvidenceManifest(
            fingerprint=fingerprint, input_face=input_face,
            matched_candidate=matched_candidate,
            chain_of_custody=chain_of_custody or []
        )

    def to_dict(self, manifest: EvidenceManifest) -> Dict[str, Any]:
        return {
            "fingerprint": {
                "sha256": manifest.fingerprint.sha256,
                "phash": manifest.fingerprint.phash,
                "source_url": manifest.fingerprint.source_url,
                "content_type": manifest.fingerprint.content_type,
                "retrieved_at": manifest.fingerprint.retrieved_at,
                "face_model": manifest.fingerprint.face_model,
                "similarity_score": manifest.fingerprint.similarity_score,
                "verification_version": manifest.fingerprint.verification_version
            },
            "input_face": {
                "face_id": manifest.input_face.face_id,
                "bbox": {
                    "x": manifest.input_face.bbox.x, "y": manifest.input_face.bbox.y,
                    "width": manifest.input_face.bbox.width, "height": manifest.input_face.bbox.height
                },
                "quality": {
                    "confidence": manifest.input_face.quality.confidence,
                    "face_size": manifest.input_face.quality.face_size,
                    "sharpness": manifest.input_face.quality.sharpness,
                    "brightness": manifest.input_face.quality.brightness,
                    "is_valid": manifest.input_face.quality.is_valid
                }
            },
            "matched_candidate": {
                "source": manifest.matched_candidate.candidate.source,
                "url": manifest.matched_candidate.candidate.url,
                "similarity_score": manifest.matched_candidate.similarity_score,
                "match_status": manifest.matched_candidate.match_status.value,
                "face_detected": manifest.matched_candidate.face_detected
            },
            "chain_of_custody": manifest.chain_of_custody,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

    def to_json(self, manifest: EvidenceManifest, indent: int = 2) -> str:
        return json.dumps(self.to_dict(manifest), indent=indent)
