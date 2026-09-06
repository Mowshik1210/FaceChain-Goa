"""Blockchain re-verification and tamper detection."""
from typing import Tuple, Optional
from PIL import Image
from app.models import BlockchainRecord, VerificationResult
from app.blockchain.client import BlockchainClient
from app.evidence.fingerprint import EvidenceFingerprinter


class BlockchainVerifier:
    def __init__(self):
        self.fingerprinter = EvidenceFingerprinter()
        self.client = BlockchainClient()

    def re_verify(self, image, blockchain_record, original_hash):
        current_hash = self.fingerprinter.sha256(image)
        if current_hash != original_hash:
            return (VerificationResult.TAMPERED, original_hash, current_hash,
                    "Hash mismatch - content has been modified")
        if self.client.is_configured() and self.client.initialize():
            exists, details = self.client.verify_on_chain(original_hash)
            if exists:
                return (VerificationResult.VERIFIED, original_hash, current_hash,
                        "Hash matches and blockchain record confirmed")
            return (VerificationResult.FAILED, original_hash, current_hash,
                    "Hash matches but no on-chain record found")
        return (VerificationResult.VERIFIED, original_hash, current_hash,
                "Hash matches (blockchain client not configured for on-chain verification)")

    def simulate_tamper(self, image: Image.Image) -> Image.Image:
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Brightness(image)
        return enhancer.enhance(1.1)
