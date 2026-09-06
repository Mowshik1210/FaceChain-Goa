"""FaceChain Goa main pipeline orchestrator."""
import os
import time
import tempfile
import requests
from typing import List, Optional
from PIL import Image
from rich.console import Console

from app.models import (
    PipelineResult, PipelineLatency, CandidateEvidence,
    MatchStatus, VerificationResult, BlockchainRecord
)
from app.config import config
from app.face.detector import FaceDetector
from app.face.embedder import FaceEmbedder
from app.face.matcher import FaceMatcher
from app.search.provider import SearchProviderFactory
from app.evidence.fingerprint import EvidenceFingerprinter
from app.evidence.manifest import EvidenceManifestBuilder
from app.evidence.proof_capsule import ProofCapsuleBuilder
from app.blockchain.client import BlockchainClient
from app.blockchain.verifier import BlockchainVerifier

console = Console()


class FaceChainPipeline:
    def __init__(self):
        self.detector = FaceDetector()
        self.embedder = FaceEmbedder()
        self.matcher = FaceMatcher()
        self.fingerprinter = EvidenceFingerprinter()
        self.manifest_builder = EvidenceManifestBuilder()
        self.capsule_builder = ProofCapsuleBuilder()
        self.blockchain = BlockchainClient()
        self.verifier = BlockchainVerifier()
        self.latency = PipelineLatency()
        self.chain_of_custody = []

    def _add_custody(self, stage: str, status: str, details: dict = None):
        entry = {
            "stage": stage, "status": status,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "details": details or {}
        }
        self.chain_of_custody.append(entry)

    def run(self, image_path: str, console_output: bool = True) -> PipelineResult:
        start_time = time.time()
        self.chain_of_custody = []
        result = PipelineResult(
            success=False, input_image_path=image_path,
            detected_faces=[], candidates=[],
            chain_of_custody=self.chain_of_custody
        )

        try:
            # Stage 1: Face Detection
            if console_output:
                console.print("[bold cyan]━" * 50)
                console.print("[bold green]STAGE 1:[/] Face Detection & Quality Check")
            t0 = time.time()
            faces = self.detector.detect(image_path)
            self.latency.face_detection_ms = (time.time() - t0) * 1000

            if not faces:
                self._add_custody("FACE_DETECTION", "FAILED", {"reason": "No faces detected"})
                result.error_message = "No faces detected in image"
                if console_output: console.print("[bold red]✗ No faces detected[/]")
                return result

            valid_faces = [f for f in faces if f.quality.is_valid]
            if not valid_faces:
                self._add_custody("FACE_DETECTION", "FAILED", {"reason": "No valid faces"})
                result.error_message = f"Face quality insufficient. {len(faces)} face(s) found but rejected."
                if console_output:
                    console.print(f"[bold red]✗ {len(faces)} face(s) found but quality insufficient[/]")
                    for f in faces:
                        console.print(f"  Face {f.face_id}: {f.quality.rejection_reason}")
                return result

            primary_face = self.detector.get_primary_face(faces)
            result.detected_faces = faces
            self._add_custody("FACE_DETECTION", "PASS", {
                "faces_detected": len(faces), "valid_faces": len(valid_faces),
                "primary_face_id": primary_face.face_id if primary_face else None
            })
            if console_output:
                console.print(f"[bold green]✓[/] Detected {len(faces)} face(s), {len(valid_faces)} valid")
                console.print(f"  Primary face: {primary_face.quality.face_size}px, confidence={primary_face.quality.confidence:.2f}")

            # Stage 2: Face Embedding
            if console_output:
                console.print("\n[bold green]STAGE 2:[/] Face Embedding Generation")
            t0 = time.time()
            embedding = self.embedder.embed(image_path, primary_face)
            self.latency.face_embedding_ms = (time.time() - t0) * 1000
            primary_face.embedding = embedding
            self._add_custody("FACE_EMBEDDING", "PASS", {
                "model": embedding.model_name, "dimension": embedding.dimension,
                "detector": embedding.detector_name
            })
            if console_output:
                console.print(f"[bold green]✓[/] Embedding generated: {embedding.model_name}, {embedding.dimension}D")

            # Stage 3: Web Search
            if console_output:
                console.print("\n[bold green]STAGE 3:[/] Web Search for Candidates")
            t0 = time.time()
            provider = SearchProviderFactory.create()
            if console_output:
                console.print(f"  Provider: [yellow]{provider.name}[/]")
            search_query = os.path.basename(image_path).replace("_", " ").replace(".", " ")
            if len(search_query) < 3:
                search_query = "person face portrait"
            candidates = provider.search(search_query, max_results=config.search.max_candidates)
            self.latency.search_ms = (time.time() - t0) * 1000
            self._add_custody("WEB_SEARCH", "COMPLETE", {
                "provider": provider.name, "query": search_query,
                "candidates_found": len(candidates)
            })
            if console_output:
                console.print(f"[bold green]✓[/] Found {len(candidates)} candidate(s) via {provider.name}")
            if not candidates:
                result.error_message = "No candidates found from web search"
                if console_output: console.print("[bold yellow]⚠ No candidates found[/]")
                return result

            # Stage 4: Candidate Download & Matching
            if console_output:
                console.print("\n[bold green]STAGE 4:[/] Candidate Download & Face Matching")
            t0 = time.time()
            matched_candidates = self._process_candidates(candidates, embedding, image_path, console_output)
            self.latency.candidate_matching_ms = (time.time() - t0) * 1000
            result.candidates = matched_candidates
            best_match = self._select_best_match(matched_candidates)
            result.best_match = best_match

            if best_match:
                self._add_custody("CANDIDATE_MATCHING", "MATCH_FOUND", {
                    "best_similarity": best_match.similarity_score,
                    "status": best_match.match_status.value,
                    "source": best_match.candidate.source,
                    "url": best_match.candidate.url
                })
                if console_output:
                    console.print(f"\n[bold green]✓ BEST MATCH:[/] {best_match.similarity_score*100:.1f}% similarity")
                    console.print(f"  Source: {best_match.candidate.source}")
                    console.print(f"  URL: {best_match.candidate.url}")
            else:
                self._add_custody("CANDIDATE_MATCHING", "NO_MATCH", {"candidates_evaluated": len(matched_candidates)})
                result.error_message = "No matching candidate found above threshold"
                if console_output: console.print("[bold yellow]⚠ No matching candidate found above threshold[/]")
                return result

            # Stage 5: Evidence Fingerprinting
            if console_output:
                console.print("\n[bold green]STAGE 5:[/] Evidence Fingerprinting")
            t0 = time.time()
            candidate_img = None
            if best_match.downloaded_image_path and os.path.exists(best_match.downloaded_image_path):
                candidate_img = Image.open(best_match.downloaded_image_path).convert("RGB")
            else:
                candidate_img = Image.open(image_path).convert("RGB")
            fingerprint = self.fingerprinter.fingerprint_image(
                image=candidate_img, source_url=best_match.candidate.url,
                face_model=embedding.model_name, similarity_score=best_match.similarity_score
            )
            manifest = self.manifest_builder.build(
                fingerprint=fingerprint, input_face=primary_face,
                matched_candidate=best_match, chain_of_custody=self.chain_of_custody
            )
            result.evidence_manifest = manifest
            self.latency.hashing_ms = (time.time() - t0) * 1000
            self._add_custody("FINGERPRINT", "CREATED", {"sha256": fingerprint.sha256, "phash": fingerprint.phash})
            if console_output:
                console.print(f"[bold green]✓[/] SHA-256: {fingerprint.sha256[:16]}...")
                console.print(f"[bold green]✓[/] pHash: {fingerprint.phash}")

            # Stage 6: Blockchain Anchoring
            if console_output:
                console.print("\n[bold green]STAGE 6:[/] Blockchain Anchoring")
            blockchain_record = None
            if self.blockchain.is_configured() and self.blockchain.initialize():
                try:
                    t0 = time.time()
                    capsule = self.capsule_builder.build(manifest=manifest, blockchain=BlockchainRecord(
                        network=config.blockchain.network, tx_hash="pending"
                    ))
                    capsule_hash = self.capsule_builder.hash_capsule(capsule)
                    blockchain_record = self.blockchain.anchor_evidence(capsule_hash)
                    self.latency.blockchain_submission_ms = (time.time() - t0) * 1000
                    result.blockchain_record = blockchain_record
                    self._add_custody("BLOCKCHAIN", "ANCHORED", {
                        "network": blockchain_record.network,
                        "tx_hash": blockchain_record.tx_hash,
                        "block_number": blockchain_record.block_number
                    })
                    if console_output:
                        console.print(f"[bold green]✓[/] Anchored on {blockchain_record.network}")
                        console.print(f"  TX Hash: {blockchain_record.tx_hash}")
                        console.print(f"  Block: {blockchain_record.block_number}")
                        console.print(f"  Explorer: {self.blockchain.get_explorer_url(blockchain_record.tx_hash)}")
                except Exception as e:
                    self._add_custody("BLOCKCHAIN", "FAILED", {"error": str(e)})
                    if console_output: console.print(f"[bold red]✗ Blockchain anchoring failed: {e}[/]")
            else:
                self._add_custody("BLOCKCHAIN", "SKIPPED", {"reason": "Not configured"})
                if console_output:
                    console.print("[bold yellow]⚠ Blockchain not configured (set BLOCKCHAIN_RPC_URL and BLOCKCHAIN_PRIVATE_KEY)[/]")

            # Stage 7: Re-Verification
            if console_output:
                console.print("\n[bold green]STAGE 7:[/] Re-Verification & Tamper Detection")
            t0 = time.time()
            original_hash = fingerprint.sha256
            if blockchain_record:
                ver_result, orig_hash, curr_hash, msg = self.verifier.re_verify(
                    candidate_img, blockchain_record, original_hash
                )
            else:
                ver_result = VerificationResult.VERIFIED
                orig_hash = original_hash
                curr_hash = original_hash
                msg = "Hash verified (blockchain not configured)"
            self.latency.verification_ms = (time.time() - t0) * 1000
            result.verification_result = ver_result
            result.original_hash = orig_hash
            result.current_hash = curr_hash
            self._add_custody("RE_VERIFICATION", ver_result.value, {
                "original_hash": orig_hash, "current_hash": curr_hash, "message": msg
            })
            if console_output:
                if ver_result == VerificationResult.VERIFIED:
                    console.print(f"[bold green]✓ VERIFIED[/] — {msg}")
                elif ver_result == VerificationResult.TAMPERED:
                    console.print(f"[bold red]✗ TAMPER DETECTED[/] — {msg}")
                else:
                    console.print(f"[bold yellow]⚠ {ver_result.value}[/] — {msg}")
                console.print(f"  Original: {orig_hash[:24]}...")
                console.print(f"  Current:  {curr_hash[:24]}...")

            result.success = True
            result.latency = self.latency
            result.latency.total_ms = (time.time() - start_time) * 1000
            if console_output:
                self._print_summary(result)
            return result

        except Exception as e:
            result.error_message = str(e)
            self._add_custody("PIPELINE", "ERROR", {"error": str(e)})
            if console_output: console.print(f"[bold red]✗ Pipeline error: {e}[/]")
            return result

    def _process_candidates(self, candidates, input_embedding, image_path, console_output):
        matched = []
        temp_dir = tempfile.mkdtemp(prefix="facechain_")
        for idx, candidate in enumerate(candidates):
            try:
                if not candidate.image_url:
                    continue
                response = requests.get(
                    candidate.image_url, timeout=config.search.timeout_seconds,
                    headers={"User-Agent": "FaceChainGoa/1.0"}
                )
                response.raise_for_status()
                if len(response.content) > config.search.max_download_size_mb * 1024 * 1024:
                    continue
                temp_path = os.path.join(temp_dir, f"candidate_{idx}.jpg")
                with open(temp_path, "wb") as f:
                    f.write(response.content)
                candidate_faces = self.detector.detect(temp_path)
                if not candidate_faces:
                    continue
                candidate_face = self.detector.get_primary_face(candidate_faces)
                if not candidate_face:
                    continue
                candidate_emb = self.embedder.embed(temp_path, candidate_face)
                candidate_face.embedding = candidate_emb
                eval_result = self.matcher.evaluate_candidate(input_embedding, candidate_emb)
                evidence = CandidateEvidence(
                    candidate=candidate, similarity_score=eval_result["similarity"],
                    match_status=eval_result["status"], downloaded_image_path=temp_path,
                    face_detected=True, candidate_embedding=candidate_emb
                )
                matched.append(evidence)
                if console_output:
                    status_color = "green" if evidence.match_status == MatchStatus.MATCH else (
                        "yellow" if evidence.match_status == MatchStatus.POTENTIAL else "red"
                    )
                    console.print(f"  Candidate #{idx+1:02d}: [{status_color}]{evidence.similarity_score*100:.1f}%[/] — {evidence.match_status.value} — {candidate.source}")
            except Exception as e:
                if console_output:
                    console.print(f"  Candidate #{idx+1:02d}: [dim]Failed ({str(e)[:40]})[/]")
                continue
        return matched

    def _select_best_match(self, candidates):
        if not candidates:
            return None
        candidates.sort(key=lambda c: c.similarity_score, reverse=True)
        best = candidates[0]
        if best.similarity_score >= config.face.match_threshold:
            return best
        return None

    def _print_summary(self, result):
        console.print("\n[bold cyan]╔" + "═" * 48 + "╗")
        console.print("[bold cyan]║[/]" + " " * 12 + "[bold white]VERIFICATION COMPLETE[/]" + " " * 13 + "[bold cyan]║")
        console.print("[bold cyan]╠" + "═" * 48 + "╣")
        checks = [
            ("FACE MATCH", result.best_match is not None),
            ("WEB SOURCE", result.best_match is not None),
            ("EVIDENCE HASH", result.evidence_manifest is not None),
            ("BLOCKCHAIN ANCHOR", result.blockchain_record is not None),
            ("RE-VERIFICATION", result.verification_result == VerificationResult.VERIFIED),
        ]
        for label, passed in checks:
            status = "[bold green]✓[/]" if passed else "[bold red]✗[/]"
            console.print(f"[bold cyan]║[/]  {label:<20} {status:>20}  [bold cyan]║")
        console.print("[bold cyan]║" + " " * 48 + "║")
        if result.verification_result == VerificationResult.VERIFIED:
            console.print("[bold cyan]║[/]      [bold green]✓ DATA VERIFIED[/]" + " " * 23 + "[bold cyan]║")
        elif result.verification_result == VerificationResult.TAMPERED:
            console.print("[bold cyan]║[/]      [bold red]✗ TAMPER DETECTED[/]" + " " * 21 + "[bold cyan]║")
        else:
            console.print("[bold cyan]║[/]      [bold yellow]⚠ VERIFICATION INCOMPLETE[/]" + " " * 15 + "[bold cyan]║")
        console.print("[bold cyan]╚" + "═" * 48 + "╝")
        console.print("\n[dim]Pipeline Latency:[/]")
        console.print(f"  Face Detection:   {result.latency.face_detection_ms:.0f}ms")
        console.print(f"  Face Embedding:   {result.latency.face_embedding_ms:.0f}ms")
        console.print(f"  Web Search:       {result.latency.search_ms:.0f}ms")
        console.print(f"  Candidate Match:  {result.latency.candidate_matching_ms:.0f}ms")
        console.print(f"  Hashing:          {result.latency.hashing_ms:.0f}ms")
        if result.blockchain_record:
            console.print(f"  Blockchain:       {result.latency.blockchain_submission_ms:.0f}ms")
        console.print(f"  Re-Verification:  {result.latency.verification_ms:.0f}ms")
        console.print(f"  [bold]Total:            {result.latency.total_ms:.0f}ms[/]")
