export interface FaceData {
  detected?: boolean | number;
  count?: number;
  faces_detected?: number;
  quality?: string;
  embeddingCreated?: boolean;
  embedding?: string | boolean;
  model?: string;
  detector?: string;
  status?: string;
}

export interface DiscoveryCandidate {
  source?: string;
  title?: string;
  url?: string;
  similarity?: number;
}

export interface DiscoveryData {
  provider?: string;
  search_provider?: string;
  candidates_found?: number;
  candidates?: DiscoveryCandidate[] | number;
  resultsFound?: number;
  source?: string;
  status?: string;
}

export interface MatchCandidate {
  rank?: number;
  source?: string;
  title?: string;
  similarity?: number;
  status?: string;
  url?: string;
  imageUrl?: string;
  error?: string | null;
}

export interface MatchData {
  found?: boolean;
  similarity?: number;
  similarity_score?: number;
  score?: number;
  status?: string;
  source?: string;
  candidate?: string;
  url?: string;
  candidate_url?: string;
  sourceUrl?: string;
  title?: string;
  snippet?: string;
  imageUrl?: string;
  candidates?: MatchCandidate[];
}

export interface FingerprintData {
  sha256?: string;
  pHash?: string;
  phash?: string;
  status?: string;
  retrievedAt?: string;
  faceModel?: string;
  similarity?: number;
}

export interface BlockchainData {
  confirmed?: boolean;
  anchored?: boolean | string;
  status?: string;
  network?: string;
  tx_hash?: string;
  transactionHash?: string;
  transaction_hash?: string;
  block_number?: number | string;
  blockNumber?: number | string;
  block?: number | string;
  explorer_url?: string;
  explorerUrl?: string;
  explorer_link?: string;
  evidenceHash?: string;
}

export interface VerificationData {
  status?: "VERIFIED" | "PENDING" | "TAMPERED" | "INCOMPLETE" | "FAILED" | string;
  message?: string;
  reason?: string;
  originalHash?: string;
  currentHash?: string;
  original_hash?: string;
  current_hash?: string;
  hashMatch?: boolean;
  verifiedOnChain?: boolean;
}

export interface VerificationResponse {
  success?: boolean;
  runId?: string;
  face?: FaceData;
  discovery?: DiscoveryData;
  match?: MatchData | null;
  fingerprint?: FingerprintData | null;
  blockchain?: BlockchainData;
  verification?: VerificationData;
  timing?: Record<string, number>;
  error?: string | null;
  stage?: string | null;
}

export interface ProgressEvent {
  stage: number;
  name: string;
  status: "running" | "candidate" | "completed" | "failed" | "pending" | "finished" | string;
  message: string;
  timestamp?: number;
  data?: Record<string, any>;
}

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function readJson(response: Response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(
      data?.detail ||
      data?.error ||
      `Request failed with status ${response.status}`
    );
  }
  return data;
}

/**
 * Starts the pipeline immediately, then listens to the backend SSE stream.
 * The backend runs the heavy pipeline in a worker thread, so the browser gets
 * genuine stage-by-stage progress instead of waiting several minutes.
 */
export async function verifyImageWithProgress(
  file: File,
  onProgress: (event: ProgressEvent) => void
): Promise<VerificationResponse> {
  const formData = new FormData();
  formData.append("image", file);

  const startResponse = await fetch(`${API_BASE_URL}/api/verify/start`, {
    method: "POST",
    body: formData,
  });

  const startData = await readJson(startResponse);
  const runId = startData?.runId;

  if (!runId) {
    throw new Error("Backend did not return a verification run ID.");
  }

  return new Promise<VerificationResponse>((resolve, reject) => {
    const eventSource = new EventSource(
      `${API_BASE_URL}/api/verify/events/${encodeURIComponent(runId)}`
    );
    let finished = false;

    const cleanup = () => eventSource.close();

    eventSource.onmessage = async (message) => {
      try {
        const event = JSON.parse(message.data) as ProgressEvent;
        onProgress(event);

        if (event.status === "finished") {
          finished = true;
          cleanup();

          const resultResponse = await fetch(
            `${API_BASE_URL}/api/verify/result/${encodeURIComponent(runId)}`
          );
          const result = await readJson(resultResponse);
          resolve(result as VerificationResponse);
        }
      } catch (error) {
        cleanup();
        reject(error instanceof Error ? error : new Error("Invalid backend event."));
      }
    };

    eventSource.onerror = () => {
      if (finished) return;
      cleanup();
      reject(
        new Error(
          "Live verification connection was lost. Make sure the FastAPI backend is running."
        )
      );
    };
  });
}

/** Compatibility helper for any older frontend code. */
export async function verifyImage(file: File): Promise<VerificationResponse> {
  return verifyImageWithProgress(file, () => undefined);
}
