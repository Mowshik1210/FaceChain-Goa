"""FaceChain Goa main pipeline orchestrator."""
import os
import time
import tempfile
import requests
from typing import Optional, Callable, Dict, Any
from PIL import Image
from rich.console import Console

from app.models import PipelineResult, PipelineLatency, CandidateEvidence, MatchStatus, VerificationResult
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
    def __init__(self, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
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
        self.progress_callback = progress_callback

    def _add_custody(self, stage: str, status: str, details: Optional[dict] = None):
        self.chain_of_custody.append({
            "stage": stage,
            "status": status,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "details": details or {},
        })

    def _emit_progress(
        self,
        stage: int,
        name: str,
        status: str,
        message: str = "",
        data: Optional[Dict[str, Any]] = None,
    ):
        event = {
            "stage": stage,
            "name": name,
            "status": status,
            "message": message,
            "timestamp": time.time(),
            "data": data or {},
        }
        if self.progress_callback:
            try:
                self.progress_callback(event)
            except Exception:
                # UI progress must never break the actual verification pipeline.
                pass

    def run(self, image_path: str, console_output: bool = True) -> PipelineResult:
        start_time = time.time()
        self.chain_of_custody = []
        result = PipelineResult(
            success=False,
            input_image_path=image_path,
            detected_faces=[],
            candidates=[],
            chain_of_custody=self.chain_of_custody,
        )

        try:
            # ──────────────────────────────────────────────────────────────
            # STAGE 1 — Face Detection & Quality
            # ──────────────────────────────────────────────────────────────
            self._emit_progress(1, "Face Detection & Quality Check", "running", "Detecting faces and checking image quality...")
            if console_output:
                console.print("[bold cyan]━" * 50)
                console.print("[bold green]STAGE 1:[/] Face Detection & Quality Check")

            t0 = time.time()
            faces = self.detector.detect(image_path)
            self.latency.face_detection_ms = (time.time() - t0) * 1000

            valid_faces = [f for f in faces if f.quality.is_valid]
            self._emit_progress(
                1,
                "Face Detection & Quality Check",
                "completed" if valid_faces else "failed",
                f"Detected {len(faces)} face(s), {len(valid_faces)} valid",
                {
                    "faces": len(faces),
                    "validFaces": len(valid_faces),
                    "timeMs": round(self.latency.face_detection_ms, 2),
                },
            )

            if not faces:
                self._add_custody("FACE_DETECTION", "FAILED", {"reason": "No faces detected"})
                result.error_message = "No faces detected in image"
                if console_output:
                    console.print("[bold red]✗ No faces detected[/]")
                return self._finish_early(result, start_time)

            if not valid_faces:
                self._add_custody("FACE_DETECTION", "FAILED", {"reason": "No valid faces"})
                result.error_message = f"Face quality insufficient. {len(faces)} face(s) found but rejected."
                if console_output:
                    console.print(f"[bold red]✗ {len(faces)} face(s) found but quality insufficient[/]")
                return self._finish_early(result, start_time)

            primary_face = self.detector.get_primary_face(faces)
            if not primary_face:
                result.error_message = "Could not select a primary face"
                return self._finish_early(result, start_time)

            result.detected_faces = faces
            self._add_custody("FACE_DETECTION", "PASS", {
                "faces_detected": len(faces),
                "valid_faces": len(valid_faces),
                "primary_face_id": primary_face.face_id,
            })
            if console_output:
                console.print(f"[bold green]✓[/] Detected {len(faces)} face(s), {len(valid_faces)} valid")
                console.print(f"  Primary face: {primary_face.quality.face_size}px, confidence={primary_face.quality.confidence:.2f}")

            # ──────────────────────────────────────────────────────────────
            # STAGE 2 — Embedding
            # ──────────────────────────────────────────────────────────────
            self._emit_progress(2, "Face Embedding Generation", "running", "Generating facial embedding...")
            if console_output:
                console.print("\n[bold green]STAGE 2:[/] Face Embedding Generation")

            t0 = time.time()
            embedding = self.embedder.embed(image_path, primary_face)
            self.latency.face_embedding_ms = (time.time() - t0) * 1000
            primary_face.embedding = embedding

            self._add_custody("FACE_EMBEDDING", "PASS", {
                "model": embedding.model_name,
                "dimension": embedding.dimension,
                "detector": embedding.detector_name,
            })
            self._emit_progress(
                2,
                "Face Embedding Generation",
                "completed",
                f"Embedding generated: {embedding.model_name}, {embedding.dimension}D",
                {
                    "model": embedding.model_name,
                    "dimension": embedding.dimension,
                    "timeMs": round(self.latency.face_embedding_ms, 2),
                },
            )
            if console_output:
                console.print(f"[bold green]✓[/] Embedding generated: {embedding.model_name}, {embedding.dimension}D")

            # ──────────────────────────────────────────────────────────────
            # STAGE 3 — Web Search
            # ──────────────────────────────────────────────────────────────
            self._emit_progress(3, "Web Search & Discovery", "running", "Searching the web for visual matches...")
            if console_output:
                console.print("\n[bold green]STAGE 3:[/] Web Search for Candidates")
            t0 = time.time()
            provider = SearchProviderFactory.create()
            if console_output:
                console.print(f"  Provider: [yellow]{provider.name}[/]")

            if config.search.provider.lower() == "serpapi":
                search_query = image_path
            else:
                search_query = os.path.basename(image_path).replace("_", " ").replace(".", " ")
            if len(search_query) < 3:
                search_query = "person face portrait"

            candidates = provider.search(search_query, max_results=config.search.max_candidates)
            self.latency.search_ms = (time.time() - t0) * 1000
            self._add_custody("WEB_SEARCH", "COMPLETE", {
                "provider": provider.name,
                "query": search_query,
                "candidates_found": len(candidates),
            })
            self._emit_progress(
                3,
                "Web Search & Discovery",
                "completed" if candidates else "failed",
                f"Found {len(candidates)} candidate(s)",
                {
                    "provider": provider.name,
                    "resultsFound": len(candidates),
                    "timeMs": round(self.latency.search_ms, 2),
                },
            )
            if console_output:
                console.print(f"[bold green]✓[/] Found {len(candidates)} candidate(s) via {provider.name}")
            if not candidates:
                result.error_message = "No candidates found from web search"
                return self._finish_early(result, start_time)

            # ──────────────────────────────────────────────────────────────
            # STAGE 4 — Candidate matching
            # ──────────────────────────────────────────────────────────────
            self._emit_progress(4, "Candidate Download & Face Matching", "running", f"Analyzing {len(candidates)} visual candidates...", {"totalCandidates": len(candidates)})
            if console_output:
                console.print("\n[bold green]STAGE 4:[/] Candidate Download & Face Matching")
            t0 = time.time()
            matched_candidates = self._process_candidates(candidates, embedding, image_path, console_output)
            self.latency.candidate_matching_ms = (time.time() - t0) * 1000
            result.candidates = matched_candidates

            best_match = self._select_best_match(matched_candidates)
            result.best_match = best_match
            self._emit_progress(
                4,
                "Candidate Download & Face Matching",
                "completed" if best_match else "failed",
                f"Evaluated {len(candidates)} candidate(s); {len(matched_candidates)} produced matchable faces",
                {
                    "candidatesFound": len(candidates),
                    "candidatesEvaluated": len(matched_candidates),
                    "bestSimilarity": round(best_match.similarity_score, 4) if best_match else None,
                    "timeMs": round(self.latency.candidate_matching_ms, 2),
                },
            )

            if best_match:
                self._add_custody("CANDIDATE_MATCHING", "MATCH_FOUND", {
                    "best_similarity": best_match.similarity_score,
                    "status": best_match.match_status.value,
                    "source": best_match.candidate.source,
                    "url": best_match.candidate.url,
                })
                if console_output:
                    console.print(f"\n[bold green]✓ BEST MATCH:[/] {best_match.similarity_score * 100:.1f}% similarity")
                    console.print(f"  Source: {best_match.candidate.source}")
                    console.print(f"  URL: {best_match.candidate.url}")
            else:
                self._add_custody("CANDIDATE_MATCHING", "NO_MATCH", {"candidates_evaluated": len(matched_candidates)})
                result.error_message = "No matching candidate found above threshold"
                if console_output:
                    console.print("[bold yellow]⚠ No matching candidate found above threshold[/]")
                return self._finish_early(result, start_time)

            # ──────────────────────────────────────────────────────────────
            # STAGE 5 — Fingerprint
            # ──────────────────────────────────────────────────────────────
            self._emit_progress(5, "Evidence Fingerprinting", "running", "Generating cryptographic evidence fingerprints...")
            if console_output:
                console.print("\n[bold green]STAGE 5:[/] Evidence Fingerprinting")
            t0 = time.time()
            if best_match.downloaded_image_path and os.path.exists(best_match.downloaded_image_path):
                candidate_img = Image.open(best_match.downloaded_image_path).convert("RGB")
            else:
                candidate_img = Image.open(image_path).convert("RGB")

            fingerprint = self.fingerprinter.fingerprint_image(
                image=candidate_img,
                source_url=best_match.candidate.url,
                face_model=embedding.model_name,
                similarity_score=best_match.similarity_score,
            )
            manifest = self.manifest_builder.build(
                fingerprint=fingerprint,
                input_face=primary_face,
                matched_candidate=best_match,
                chain_of_custody=self.chain_of_custody,
            )
            result.evidence_manifest = manifest
            self.latency.hashing_ms = (time.time() - t0) * 1000
            self._add_custody("FINGERPRINT", "CREATED", {"sha256": fingerprint.sha256, "phash": fingerprint.phash})
            self._emit_progress(
                5,
                "Evidence Fingerprinting",
                "completed",
                "SHA-256 and pHash generated",
                {"sha256": fingerprint.sha256, "pHash": fingerprint.phash, "timeMs": round(self.latency.hashing_ms, 2)},
            )
            if console_output:
                console.print(f"[bold green]✓[/] SHA-256: {fingerprint.sha256[:16]}...")
                console.print(f"[bold green]✓[/] pHash: {fingerprint.phash}")

            # ──────────────────────────────────────────────────────────────
            # STAGE 6 — Blockchain
            # ──────────────────────────────────────────────────────────────
            self._emit_progress(6, "Blockchain Anchoring", "running", "Checking blockchain configuration...")
            if console_output:
                console.print("\n[bold green]STAGE 6:[/] Blockchain Anchoring")

            blockchain_record = None
            blockchain_error = None
            if self.blockchain.is_configured() and self.blockchain.initialize():
                try:
                    t0 = time.time()
                    blockchain_record = self.blockchain.anchor_evidence(fingerprint.sha256)
                    self.latency.blockchain_submission_ms = (time.time() - t0) * 1000
                    result.blockchain_record = blockchain_record
                    self._add_custody("BLOCKCHAIN", "ANCHORED", {
                        "network": blockchain_record.network,
                        "tx_hash": blockchain_record.tx_hash,
                        "block_number": blockchain_record.block_number,
                    })
                    if console_output:
                        console.print(f"[bold green]✓[/] Anchored on {blockchain_record.network}")
                        console.print(f"  TX Hash: {blockchain_record.tx_hash}")
                        console.print(f"  Block: {blockchain_record.block_number}")
                        console.print(f"  Explorer: {self.blockchain.get_explorer_url(blockchain_record.tx_hash)}")
                except Exception as exc:
                    blockchain_error = str(exc)
                    self._add_custody("BLOCKCHAIN", "FAILED", {"error": blockchain_error})
                    if console_output:
                        console.print(f"[bold red]✗ Blockchain anchoring failed: {blockchain_error}[/]")
            else:
                self._add_custody("BLOCKCHAIN", "SKIPPED", {"reason": "Not configured"})
                if console_output:
                    console.print("[bold yellow]⚠ Blockchain not configured (set BLOCKCHAIN_RPC_URL and BLOCKCHAIN_PRIVATE_KEY)[/]")

            self._emit_progress(
                6,
                "Blockchain Anchoring",
                "completed" if blockchain_record else "pending",
                f"Evidence anchored on {blockchain_record.network}" if blockchain_record else (blockchain_error or "Blockchain anchoring unavailable"),
                {
                    "configured": blockchain_record is not None,
                    "network": blockchain_record.network if blockchain_record else config.blockchain.network,
                    "txHash": blockchain_record.tx_hash if blockchain_record else None,
                    "blockNumber": blockchain_record.block_number if blockchain_record else None,
                    "timeMs": round(self.latency.blockchain_submission_ms, 2),
                },
            )

            # ──────────────────────────────────────────────────────────────
            # STAGE 7 — Re-verification
            # ──────────────────────────────────────────────────────────────
            self._emit_progress(7, "Re-Verification & Tamper Detection", "running", "Re-verifying evidence integrity...")
            if console_output:
                console.print("\n[bold green]STAGE 7:[/] Re-Verification & Tamper Detection")
            t0 = time.time()
            original_hash = fingerprint.sha256

            if blockchain_record:
                ver_result, orig_hash, curr_hash, msg = self.verifier.re_verify(candidate_img, blockchain_record, original_hash)
            else:
                current_hash = self.fingerprinter.sha256(candidate_img)
                if current_hash == original_hash:
                    ver_result = VerificationResult.PENDING
                    orig_hash = original_hash
                    curr_hash = current_hash
                    msg = "Hash matches locally. Blockchain anchoring unavailable — verification pending."
                else:
                    ver_result = VerificationResult.TAMPERED
                    orig_hash = original_hash
                    curr_hash = current_hash
                    msg = "Hash mismatch detected."

            self.latency.verification_ms = (time.time() - t0) * 1000
            result.verification_result = ver_result
            result.original_hash = orig_hash
            result.current_hash = curr_hash
            self._add_custody("RE_VERIFICATION", ver_result.value, {
                "original_hash": orig_hash,
                "current_hash": curr_hash,
                "message": msg,
            })
            self._emit_progress(
                7,
                "Re-Verification & Tamper Detection",
                "completed",
                msg,
                {
                    "status": ver_result.value,
                    "originalHash": orig_hash,
                    "currentHash": curr_hash,
                    "hashMatch": orig_hash == curr_hash,
                    "verifiedOnChain": ver_result == VerificationResult.VERIFIED,
                    "timeMs": round(self.latency.verification_ms, 2),
                },
            )

            if console_output:
                if ver_result == VerificationResult.VERIFIED:
                    console.print(f"[bold green]✓ VERIFIED[/] — {msg}")
                elif ver_result == VerificationResult.TAMPERED:
                    console.print(f"[bold red]✗ TAMPER DETECTED[/] — {msg}")
                elif ver_result == VerificationResult.PENDING:
                    console.print(f"[bold yellow]⏳ PENDING[/] — {msg}")
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

        except Exception as exc:
            result.error_message = str(exc)
            result.latency = self.latency
            result.latency.total_ms = (time.time() - start_time) * 1000
            self._add_custody("PIPELINE", "ERROR", {"error": str(exc)})
            self._emit_progress(0, "Pipeline", "failed", str(exc), {"timeMs": round(result.latency.total_ms, 2)})
            if console_output:
                console.print(f"[bold red]✗ Pipeline error: {exc}[/]")
            return result

    def _finish_early(self, result: PipelineResult, start_time: float) -> PipelineResult:
        result.success = False
        result.latency = self.latency
        result.latency.total_ms = (time.time() - start_time) * 1000
        return result

    def _process_candidates(self, candidates, input_embedding, image_path, console_output):
        matched = []
        temp_dir = tempfile.mkdtemp(prefix="facechain_")

        for idx, candidate in enumerate(candidates):
            rank = idx + 1
            base_data = {
                "rank": rank,
                "source": candidate.source,
                "title": candidate.title or "",
                "url": candidate.url,
            }
            try:
                if not candidate.image_url:
                    self._emit_progress(4, "Candidate Download & Face Matching", "candidate", f"Candidate #{rank:02d}: no image URL", {**base_data, "status": "FAILED", "error": "No image URL"})
                    continue

                response = requests.get(
                    candidate.image_url,
                    timeout=config.search.timeout_seconds,
                    headers={"User-Agent": "FaceChainGoa/1.0"},
                )
                response.raise_for_status()
                if len(response.content) > config.search.max_download_size_mb * 1024 * 1024:
                    self._emit_progress(4, "Candidate Download & Face Matching", "candidate", f"Candidate #{rank:02d}: image too large", {**base_data, "status": "FAILED", "error": "Image exceeds download limit"})
                    continue

                temp_path = os.path.join(temp_dir, f"candidate_{idx}.jpg")
                with open(temp_path, "wb") as f:
                    f.write(response.content)

                candidate_faces = self.detector.detect(temp_path)
                if not candidate_faces:
                    self._emit_progress(4, "Candidate Download & Face Matching", "candidate", f"Candidate #{rank:02d}: no face detected", {**base_data, "status": "REJECTED", "similarity": 0})
                    continue

                candidate_face = self.detector.get_primary_face(candidate_faces)
                if not candidate_face:
                    self._emit_progress(4, "Candidate Download & Face Matching", "candidate", f"Candidate #{rank:02d}: no primary face", {**base_data, "status": "REJECTED", "similarity": 0})
                    continue

                candidate_emb = self.embedder.embed(temp_path, candidate_face)
                candidate_face.embedding = candidate_emb
                eval_result = self.matcher.evaluate_candidate(input_embedding, candidate_emb)
                evidence = CandidateEvidence(
                    candidate=candidate,
                    similarity_score=eval_result["similarity"],
                    match_status=eval_result["status"],
                    downloaded_image_path=temp_path,
                    face_detected=True,
                    candidate_embedding=candidate_emb,
                )
                matched.append(evidence)

                similarity = round(evidence.similarity_score, 4)
                status = evidence.match_status.value
                self._emit_progress(
                    4,
                    "Candidate Download & Face Matching",
                    "candidate",
                    f"Candidate #{rank:02d}: {similarity * 100:.1f}% — {status}",
                    {**base_data, "similarity": similarity, "status": status, "imageUrl": candidate.image_url},
                )

                if console_output:
                    status_color = "green" if evidence.match_status == MatchStatus.MATCH else ("yellow" if evidence.match_status == MatchStatus.POTENTIAL else "red")
                    console.print(f"  Candidate #{rank:02d}: [{status_color}]{similarity * 100:.1f}%[/] — {status} — {candidate.source}")

            except Exception as exc:
                error = str(exc)[:120]
                self._emit_progress(
                    4,
                    "Candidate Download & Face Matching",
                    "candidate",
                    f"Candidate #{rank:02d}: failed",
                    {**base_data, "similarity": None, "status": "FAILED", "error": error},
                )
                if console_output:
                    console.print(f"  Candidate #{rank:02d}: [dim]Failed ({error[:60]})[/]")

        return matched

    def _select_best_match(self, candidates):
        if not candidates:
            return None
        candidates.sort(key=lambda c: c.similarity_score, reverse=True)
        best = candidates[0]
        return best if best.similarity_score >= config.face.match_threshold else None

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
        elif result.verification_result == VerificationResult.PENDING:
            console.print("[bold cyan]║[/]      [bold yellow]⏳ VERIFICATION PENDING[/]" + " " * 16 + "[bold cyan]║")
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
