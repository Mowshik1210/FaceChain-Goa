"""FaceChain Goa — FastAPI Backend

HH GOA 2026 — Task 3 Integration API
Provides a non-blocking start endpoint, real-time SSE progress, and a result endpoint.
"""
import asyncio
import json
import os
import tempfile
import uuid
from contextlib import asynccontextmanager
from queue import Queue
from threading import Thread
from typing import Optional, Dict, Any

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from app.pipeline import FaceChainPipeline
from app.models import VerificationResult
from app.config import config
from app.blockchain.client import BlockchainClient


_DEFAULT_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

_cors_env = os.getenv("CORS_ORIGINS", "")
CORS_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip()] if _cors_env else _DEFAULT_ORIGINS


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(config.temp_dir, exist_ok=True)
    yield


app = FastAPI(
    title="FaceChain Goa API",
    description="Face Identification & Blockchain Verification",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


ALLOWED_CONTENT_TYPES = {
    "image/jpeg", "image/jpg", "image/png", "image/webp", "image/bmp"
}
MAX_FILE_SIZE = 10 * 1024 * 1024


class VerifyResponse(BaseModel):
    success: bool
    runId: str
    face: dict
    discovery: dict
    match: Optional[dict]
    fingerprint: Optional[dict]
    blockchain: dict
    verification: dict
    timing: dict
    error: Optional[str] = None
    stage: Optional[str] = None


# run_id -> {queue, result, done, temp_path}
runs: Dict[str, Dict[str, Any]] = {}


def _build_response(result, run_id: str) -> dict:
    primary = result.detected_faces[0] if result.detected_faces else None
    face_data = {
        "detected": len(result.detected_faces) > 0,
        "quality": "PASS" if (primary and primary.quality.is_valid) else "FAIL",
        "embeddingCreated": primary is not None and primary.embedding is not None,
        "count": len(result.detected_faces),
        "model": primary.embedding.model_name if primary and primary.embedding else None,
        "detector": primary.embedding.detector_name if primary and primary.embedding else None,
    }

    custody_search = next(
        (c for c in result.chain_of_custody if c.get("stage") == "WEB_SEARCH"), {}
    )
    discovery_data = {
        "provider": custody_search.get("details", {}).get("provider", "unknown"),
        "query": custody_search.get("details", {}).get("query", ""),
        "resultsFound": custody_search.get("details", {}).get("candidates_found", 0),
        "status": "complete" if custody_search else "failed",
    }

    match_data = None
    if result.best_match:
        best_candidate = result.best_match.candidate
        candidate_data = []
        for rank, evidence in enumerate(result.candidates, start=1):
            candidate = evidence.candidate
            candidate_data.append({
                "rank": rank,
                "source": candidate.source,
                "title": candidate.title or "",
                "similarity": round(evidence.similarity_score, 4),
                "status": evidence.match_status.value,
                "url": candidate.url,
                "imageUrl": candidate.image_url or "",
                "error": None,
            })

        match_data = {
            "found": True,
            "similarity": round(result.best_match.similarity_score, 4),
            "sourceUrl": best_candidate.url,
            "title": best_candidate.title or "",
            "snippet": best_candidate.description or "",
            "imageUrl": best_candidate.image_url or "",
            "timestamp": best_candidate.timestamp or "",
            "status": result.best_match.match_status.value,
            "source": best_candidate.source,
            "candidates": candidate_data,
        }

    fingerprint_data = None
    if result.evidence_manifest and result.evidence_manifest.fingerprint:
        fp = result.evidence_manifest.fingerprint
        fingerprint_data = {
            "sha256": fp.sha256,
            "pHash": fp.phash,
            "retrievedAt": fp.retrieved_at,
            "faceModel": fp.face_model,
            "similarity": fp.similarity_score,
        }

    if result.blockchain_record:
        bc = result.blockchain_record
        blockchain_data = {
            "network": bc.network,
            "transactionHash": bc.tx_hash,
            "blockNumber": bc.block_number,
            "confirmed": True,
            "explorerUrl": BlockchainClient().get_explorer_url(bc.tx_hash),
            "status": "CONFIRMED",
            "evidenceHash": bc.evidence_hash,
        }
    else:
        blockchain_data = {
            "confirmed": False,
            "status": "NOT_CONFIGURED",
            "network": config.blockchain.network,
        }

    verified_on_chain = (
        result.verification_result == VerificationResult.VERIFIED
        and result.blockchain_record is not None
    )
    verification_data = {
        "status": result.verification_result.value,
        "originalHash": result.original_hash,
        "currentHash": result.current_hash,
        "hashMatch": bool(
            result.original_hash
            and result.current_hash
            and result.original_hash == result.current_hash
        ),
        "verifiedOnChain": verified_on_chain,
    }

    timing_data = {
        "totalMs": round(result.latency.total_ms, 2),
        "faceDetectionMs": round(result.latency.face_detection_ms, 2),
        "faceEmbeddingMs": round(result.latency.face_embedding_ms, 2),
        "searchMs": round(result.latency.search_ms, 2),
        "candidateMatchingMs": round(result.latency.candidate_matching_ms, 2),
        "hashingMs": round(result.latency.hashing_ms, 2),
        "blockchainMs": round(result.latency.blockchain_submission_ms, 2),
        "verificationMs": round(result.latency.verification_ms, 2),
    }

    return {
        "success": result.success,
        "runId": run_id,
        "face": face_data,
        "discovery": discovery_data,
        "match": match_data,
        "fingerprint": fingerprint_data,
        "blockchain": blockchain_data,
        "verification": verification_data,
        "timing": timing_data,
        "error": result.error_message,
        "stage": None,
    }


def _failure_stage(result) -> str:
    if not result.detected_faces:
        return "face"
    if not result.candidates:
        return "discovery"
    if not result.best_match:
        return "match"
    return "pipeline"


def _build_error_response(error: str, stage: str, run_id: str) -> dict:
    return {
        "success": False,
        "runId": run_id,
        "face": {"detected": False, "quality": "FAIL", "embeddingCreated": False, "count": 0},
        "discovery": {"provider": "none", "query": "", "resultsFound": 0, "status": "failed"},
        "match": None,
        "fingerprint": None,
        "blockchain": {"confirmed": False, "status": "NOT_CONFIGURED", "network": config.blockchain.network},
        "verification": {"status": "UNVERIFIED", "verifiedOnChain": False},
        "timing": {"totalMs": 0},
        "error": error,
        "stage": stage,
    }


def _emit_finished(state: Dict[str, Any], result_data: dict):
    state["result"] = result_data
    state["done"] = True
    state["queue"].put({
        "stage": 7,
        "name": "Pipeline",
        "status": "finished",
        "message": "Verification pipeline completed",
        "timestamp": __import__("time").time(),
        "data": {
            "success": result_data.get("success", False),
            "runId": result_data.get("runId"),
        },
    })


def _pipeline_worker(run_id: str, temp_path: str):
    state = runs[run_id]

    def send_progress(event):
        # queue.Queue is thread-safe; this callback is called from this worker.
        state["queue"].put(event)

    try:
        pipeline = FaceChainPipeline(progress_callback=send_progress)
        result = pipeline.run(temp_path, console_output=True)
        if result.success:
            response_data = _build_response(result, run_id)
        else:
            response_data = _build_error_response(
                result.error_message or "Pipeline failed",
                _failure_stage(result),
                run_id,
            )
        _emit_finished(state, response_data)
    except Exception:
        response_data = _build_error_response(
            "Internal verification error",
            "pipeline",
            run_id,
        )
        _emit_finished(state, response_data)
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        state["temp_path"] = None


async def _validate_and_save(image: UploadFile) -> str:
    content_type = image.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {content_type}. Allowed: JPEG, PNG, WEBP, BMP",
        )

    contents = await image.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Max 10MB.")

    suffix = os.path.splitext(image.filename or ".jpg")[1] or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=config.temp_dir) as tmp:
        tmp.write(contents)
        return tmp.name


@app.post("/api/verify/start")
async def verify_start(image: UploadFile = File(...)):
    temp_path = await _validate_and_save(image)
    run_id = str(uuid.uuid4())
    runs[run_id] = {
        "queue": Queue(),
        "result": None,
        "done": False,
        "temp_path": temp_path,
    }

    worker = Thread(
        target=_pipeline_worker,
        args=(run_id, temp_path),
        daemon=True,
        name=f"facechain-{run_id[:8]}",
    )
    worker.start()

    return {"runId": run_id, "status": "started"}


@app.get("/api/verify/events/{run_id}")
async def verify_events(run_id: str):
    state = runs.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Verification run not found")

    async def event_stream():
        while True:
            event = await asyncio.to_thread(state["queue"].get)
            yield f"data: {json.dumps(event, default=str)}\n\n"
            if event.get("status") == "finished":
                break

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/verify/result/{run_id}")
async def verify_result(run_id: str):
    state = runs.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Verification run not found")
    if not state["done"]:
        return {"status": "running", "runId": run_id}
    return JSONResponse(content=state["result"])


# Backward-compatible endpoint. It does not stream; new UI uses /start + SSE.
@app.post("/api/verify")
async def verify(image: UploadFile = File(...)):
    temp_path = await _validate_and_save(image)
    run_id = str(uuid.uuid4())
    runs[run_id] = {
        "queue": Queue(),
        "result": None,
        "done": False,
        "temp_path": temp_path,
    }
    _pipeline_worker(run_id, temp_path)
    return JSONResponse(content=runs[run_id]["result"])


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("api:app", host=host, port=port, reload=True)
