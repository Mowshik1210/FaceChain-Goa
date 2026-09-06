"""Proof capsule generation."""
import time
import json
import hashlib
from typing import Dict, Any
from app.models import ProofCapsule, EvidenceManifest, BlockchainRecord


class ProofCapsuleBuilder:
    def build(self, manifest: EvidenceManifest, blockchain: BlockchainRecord) -> ProofCapsule:
        return ProofCapsule(
            project="FaceChain Goa", version="1.0",
            source={
                "domain": manifest.matched_candidate.candidate.source,
                "url": manifest.matched_candidate.candidate.url
            },
            fingerprint={
                "sha256": manifest.fingerprint.sha256,
                "phash": manifest.fingerprint.phash
            },
            match={"similarity": manifest.matched_candidate.similarity_score},
            blockchain={
                "network": blockchain.network,
                "tx_hash": blockchain.tx_hash,
                "block_number": blockchain.block_number,
                "contract_address": blockchain.contract_address
            },
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )

    def to_dict(self, capsule: ProofCapsule) -> Dict[str, Any]:
        return {
            "project": capsule.project, "version": capsule.version,
            "source": capsule.source, "fingerprint": capsule.fingerprint,
            "match": capsule.match, "blockchain": capsule.blockchain,
            "timestamp": capsule.timestamp
        }

    def to_json(self, capsule: ProofCapsule, indent: int = 2) -> str:
        return json.dumps(self.to_dict(capsule), indent=indent)

    def hash_capsule(self, capsule: ProofCapsule) -> str:
        data = json.dumps(self.to_dict(capsule), sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()
