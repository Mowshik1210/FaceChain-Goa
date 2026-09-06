"""Shared data models for FaceChain Goa."""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
import numpy as np


class PipelineStage(Enum):
    """Pipeline execution stages."""
    INIT = "initialization"
    FACE_DETECTION = "face_detection"
    FACE_EMBEDDING = "face_embedding"
    SEARCH = "web_search"
    CANDIDATE_DOWNLOAD = "candidate_download"
    CANDIDATE_MATCHING = "candidate_matching"
    EVIDENCE_FINGERPRINT = "evidence_fingerprint"
    BLOCKCHAIN_ANCHOR = "blockchain_anchor"
    RE_VERIFICATION = "re_verification"
    COMPLETE = "complete"


class MatchStatus(Enum):
    """Candidate match status."""
    REJECTED = "REJECTED"
    POTENTIAL = "POTENTIAL MATCH"
    MATCH = "MATCH"


class VerificationResult(Enum):
    """Final verification result."""
    VERIFIED = "VERIFIED"
    TAMPERED = "TAMPER DETECTED"
    FAILED = "VERIFICATION FAILED"
    PENDING = "PENDING"


@dataclass
class BoundingBox:
    """Face bounding box."""
    x: int
    y: int
    width: int
    height: int

    def to_tuple(self) -> tuple:
        return (self.x, self.y, self.x + self.width, self.y + self.height)


@dataclass
class FaceQuality:
    """Face quality metrics."""
    confidence: float
    face_size: int
    sharpness: float
    brightness: float
    is_valid: bool
    rejection_reason: Optional[str] = None


@dataclass
class FaceEmbedding:
    """Face embedding result."""
    embedding: np.ndarray
    model_name: str
    detector_name: str
    dimension: int

    def __post_init__(self):
        if isinstance(self.embedding, list):
            self.embedding = np.array(self.embedding)
        self.dimension = len(self.embedding)


@dataclass
class DetectedFace:
    """Detected face with metadata."""
    bbox: BoundingBox
    quality: FaceQuality
    embedding: Optional[FaceEmbedding] = None
    face_id: int = 0


@dataclass
class SearchCandidate:
    """Web search candidate."""
    url: str
    source: str
    image_url: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CandidateEvidence:
    """Evidence for a matched candidate."""
    candidate: SearchCandidate
    similarity_score: float
    match_status: MatchStatus
    downloaded_image_path: Optional[str] = None
    face_detected: bool = False
    candidate_embedding: Optional[FaceEmbedding] = None


@dataclass
class EvidenceFingerprint:
    """Cryptographic fingerprint of evidence."""
    sha256: str
    phash: str
    source_url: str
    content_type: str
    retrieved_at: str
    face_model: str
    similarity_score: float
    verification_version: str = "1.0"


@dataclass
class EvidenceManifest:
    """Complete evidence manifest."""
    fingerprint: EvidenceFingerprint
    input_face: DetectedFace
    matched_candidate: CandidateEvidence
    chain_of_custody: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class BlockchainRecord:
    """Blockchain anchoring record."""
    network: str
    tx_hash: str
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    timestamp: Optional[int] = None
    contract_address: Optional[str] = None
    evidence_hash: Optional[str] = None


@dataclass
class ProofCapsule:
    """Compact proof capsule."""
    project: str
    version: str
    source: Dict[str, Any]
    fingerprint: Dict[str, str]
    match: Dict[str, float]
    blockchain: Dict[str, Any]
    timestamp: str


@dataclass
class PipelineLatency:
    """Pipeline stage latencies."""
    face_detection_ms: float = 0.0
    face_embedding_ms: float = 0.0
    search_ms: float = 0.0
    candidate_download_ms: float = 0.0
    candidate_matching_ms: float = 0.0
    hashing_ms: float = 0.0
    blockchain_submission_ms: float = 0.0
    blockchain_confirmation_ms: float = 0.0
    verification_ms: float = 0.0
    total_ms: float = 0.0


@dataclass
class PipelineResult:
    """Complete pipeline result."""
    success: bool
    input_image_path: str
    detected_faces: List[DetectedFace]
    candidates: List[CandidateEvidence]
    best_match: Optional[CandidateEvidence] = None
    evidence_manifest: Optional[EvidenceManifest] = None
    blockchain_record: Optional[BlockchainRecord] = None
    verification_result: VerificationResult = VerificationResult.PENDING
    original_hash: Optional[str] = None
    current_hash: Optional[str] = None
    latency: PipelineLatency = field(default_factory=PipelineLatency)
    error_message: Optional[str] = None
    chain_of_custody: List[Dict[str, Any]] = field(default_factory=list)
