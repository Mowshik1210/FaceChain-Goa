"""Tests for FaceChain Goa pipeline."""
import os
import tempfile
import numpy as np
from PIL import Image
import pytest

from app.face.detector import FaceDetector
from app.face.embedder import FaceEmbedder
from app.face.matcher import FaceMatcher
from app.evidence.fingerprint import EvidenceFingerprinter
from app.blockchain.verifier import BlockchainVerifier
from app.models import VerificationResult, FaceEmbedding


@pytest.fixture
def sample_image():
    """Create a temporary test image."""
    img = Image.new("RGB", (400, 400), color=(200, 200, 200))
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    img.save(tmp.name)
    yield tmp.name
    os.unlink(tmp.name)


def test_face_detector_initialization():
    detector = FaceDetector()
    assert detector.detector_backend is not None


def test_face_embedder_initialization():
    embedder = FaceEmbedder()
    assert embedder.model_name is not None


def test_matcher_similarity():
    matcher = FaceMatcher()
    emb1 = FaceEmbedding(embedding=np.random.rand(512), model_name="test", detector_name="test", dimension=512)
    emb2 = FaceEmbedding(embedding=np.random.rand(512), model_name="test", detector_name="test", dimension=512)
    sim = matcher.compute_similarity(emb1, emb2)
    assert 0.0 <= sim <= 1.0


def test_fingerprint_consistency():
    fp = EvidenceFingerprinter()
    img = Image.new("RGB", (100, 100), color="red")
    h1 = fp.sha256(img)
    h2 = fp.sha256(img)
    assert h1 == h2
    assert len(h1) == 64


def test_tamper_detection():
    verifier = BlockchainVerifier()
    fp = EvidenceFingerprinter()
    img = Image.new("RGB", (100, 100), color="blue")
    original_hash = fp.sha256(img)
    tampered = verifier.simulate_tamper(img)
    tampered_hash = fp.sha256(tampered)
    assert original_hash != tampered_hash


def test_proof_capsule_hashing():
    from app.evidence.proof_capsule import ProofCapsuleBuilder
    from app.models import ProofCapsule, EvidenceManifest, BlockchainRecord, EvidenceFingerprint, DetectedFace, FaceQuality, BoundingBox, CandidateEvidence, SearchCandidate
    builder = ProofCapsuleBuilder()
    face = DetectedFace(bbox=BoundingBox(0,0,100,100), quality=FaceQuality(0.9, 100, 50, 128, True), face_id=0)
    candidate = CandidateEvidence(
        candidate=SearchCandidate(url="http://example.com", source="example.com"),
        similarity_score=0.95, match_status="MATCH"
    )
    fingerprint = EvidenceFingerprint(
        sha256="abc123", phash="def456", source_url="http://example.com",
        content_type="image/jpeg", retrieved_at="2024-01-01T00:00:00Z",
        face_model="Facenet512", similarity_score=0.95
    )
    manifest = EvidenceManifest(fingerprint=fingerprint, input_face=face, matched_candidate=candidate)
    blockchain = BlockchainRecord(network="sepolia", tx_hash="0x123")
    capsule = builder.build(manifest, blockchain)
    h = builder.hash_capsule(capsule)
    assert len(h) == 64
