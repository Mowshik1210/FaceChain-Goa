"""Face matching and similarity computation."""
import numpy as np
from scipy.spatial.distance import cosine
from app.models import FaceEmbedding, MatchStatus
from app.config import config


class FaceMatcher:
    def __init__(self):
        self.threshold = config.face.match_threshold

    def compute_similarity(self, emb1: FaceEmbedding, emb2: FaceEmbedding) -> float:
        v1 = emb1.embedding / np.linalg.norm(emb1.embedding)
        v2 = emb2.embedding / np.linalg.norm(emb2.embedding)
        sim = 1.0 - cosine(v1, v2)
        return float(np.clip(sim, 0.0, 1.0))

    def classify_match(self, similarity: float) -> MatchStatus:
        if similarity >= 0.80:
            return MatchStatus.MATCH
        elif similarity >= self.threshold:
            return MatchStatus.POTENTIAL
        else:
            return MatchStatus.REJECTED

    def evaluate_candidate(self, input_embedding, candidate_embedding):
        similarity = self.compute_similarity(input_embedding, candidate_embedding)
        status = self.classify_match(similarity)
        return {"similarity": similarity, "status": status, "is_match": status in (MatchStatus.MATCH, MatchStatus.POTENTIAL)}
