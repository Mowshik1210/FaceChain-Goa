/* FaceChain Goa — live forensic pipeline UI */
import { useMemo, useRef, useState } from "react";
import { verifyImageWithProgress, VerificationResponse, ProgressEvent } from "../lib/verificationApi";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Check,
  ChevronRight,
  Clipboard,
  FileImage,
  Fingerprint,
  Link2,
  Menu,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
  Zap,
} from "lucide-react";
import { toast } from "sonner";

function SectionLabel({ index, children }: { index: string; children: string }) {
  return <div className="section-label"><span>{index}</span><span>{children}</span></div>;
}

function StatusPill({ children, tone = "muted" }: { children: React.ReactNode; tone?: "muted" | "yellow" | "pink" | "green" }) {
  return <span className={`status-pill status-${tone}`}><span className="status-dot" />{children}</span>;
}

const truncateHash = (hash?: string, head = 8, tail = 6) => {
  if (!hash) return "—";
  if (hash.length <= head + tail + 3) return hash;
  return `${hash.slice(0, head)}...${hash.slice(-tail)}`;
};

const formatPercent = (value?: number | null) => {
  if (value === undefined || value === null) return "—";
  const pct = value <= 1 ? value * 100 : value;
  return `${pct.toFixed(1)}%`;
};

const formatMs = (value?: number) => {
  if (value === undefined || value === null) return "—";
  if (value < 1000) return `${value.toFixed(0)} ms`;
  return `${(value / 1000).toFixed(2)} s`;
};

const stageNames: Record<number, string> = {
  1: "Face Detection & Quality Check",
  2: "Face Embedding Generation",
  3: "Web Search & Discovery",
  4: "Candidate Download & Face Matching",
  5: "Evidence Fingerprinting",
  6: "Blockchain Anchoring",
  7: "Re-Verification & Tamper Detection",
};

const stageIcons: Record<number, React.ReactNode> = {
  1: <Fingerprint size={19} strokeWidth={1.5} />,
  2: <Sparkles size={19} strokeWidth={1.5} />,
  3: <Sparkles size={19} strokeWidth={1.5} />,
  4: <ShieldCheck size={19} strokeWidth={1.5} />,
  5: <FileImage size={19} strokeWidth={1.5} />,
  6: <Link2 size={19} strokeWidth={1.5} />,
  7: <Check size={19} strokeWidth={1.5} />,
};

export default function Home() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [liveStages, setLiveStages] = useState<Record<number, ProgressEvent>>({});
  const [liveCandidates, setLiveCandidates] = useState<any[]>([]);
  const [result, setResult] = useState<VerificationResponse | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const fileMeta = useMemo(() => file ? `${(file.size / 1024).toFixed(1)} KB · ${file.type || "image"}` : null, [file]);

  const acceptFile = (next?: File) => {
    if (!next) return;
    if (!next.type.startsWith("image/")) {
      toast.error("Please choose a JPG, PNG, or WEBP image.");
      return;
    }
    if (next.size > 10 * 1024 * 1024) {
      toast.error("Image is larger than the 10 MB limit.");
      return;
    }
    if (preview) URL.revokeObjectURL(preview);
    setFile(next);
    setPreview(URL.createObjectURL(next));
    setResult(null);
    setLiveStages({});
    setLiveCandidates([]);
    toast.success("Image staged. Ready for backend verification.");
  };

  const clearFile = () => {
    if (preview) URL.revokeObjectURL(preview);
    setFile(null);
    setPreview(null);
    setResult(null);
    setLiveStages({});
    setLiveCandidates([]);
  };

  const copyToClipboard = async (text?: string, label = "Hash") => {
    if (!text) return;
    await navigator.clipboard.writeText(text);
    toast.success(`${label} copied to clipboard.`);
  };

  const handleProgress = (event: ProgressEvent) => {
    setLiveStages(prev => ({ ...prev, [event.stage]: event }));

    if (event.stage === 4 && event.status === "candidate" && event.data?.rank) {
      setLiveCandidates(prev => {
        const candidate = {
          rank: event.data?.rank,
          source: event.data?.source || "Unknown source",
          title: event.data?.title || "",
          similarity: event.data?.similarity,
          status: event.data?.status || "PROCESSING",
          url: event.data?.url || "",
          imageUrl: event.data?.imageUrl || "",
          error: event.data?.error || null,
        };
        const index = prev.findIndex(item => item.rank === candidate.rank);
        const next = [...prev];
        if (index >= 0) next[index] = { ...next[index], ...candidate };
        else next.push(candidate);
        return next.sort((a, b) => a.rank - b.rank);
      });
    }
  };

  const startScan = async () => {
    if (!file) {
      toast.error("Add a face image before starting a scan.");
      document.querySelector("#scan")?.scrollIntoView({ behavior: "smooth" });
      return;
    }
    if (isVerifying) return;

    setIsVerifying(true);
    setResult(null);
    setLiveStages({});
    setLiveCandidates([]);
    toast.info("Live verification pipeline initiated...");

    try {
      const data = await verifyImageWithProgress(file, handleProgress);
      setResult(data);
      if (data.success === false || data.error) toast.error(data.error || "Verification pipeline reported an issue.");
      else toast.success("Verification pipeline completed successfully.");
    } catch (error) {
      console.error("FaceChain verification error:", error);
      toast.error(error instanceof Error ? error.message : "Verification failed. Check backend connection.");
    } finally {
      setIsVerifying(false);
    }
  };

  const faceDetectedCount = useMemo(() => {
    if (typeof result?.face?.count === "number") return result.face.count;
    const live = liveStages[1]?.data?.faces;
    if (typeof live === "number") return live;
    if (result?.face?.detected === true) return 1;
    return 0;
  }, [result, liveStages]);

  const discoveredSource = (result?.match as any)?.source || "Source unavailable";
  const discoveredUrl = (result?.match as any)?.sourceUrl || "";
  const candidateCount = (result?.discovery as any)?.resultsFound ?? liveStages[3]?.data?.resultsFound ?? 0;
  const isBlockchainConfigured = Boolean(result?.blockchain?.confirmed || result?.blockchain?.anchored === true || result?.blockchain?.transactionHash || result?.blockchain?.tx_hash);

  const getStageStatus = (stage: number) => {
    const live = liveStages[stage];
    if (live?.status === "running") return "running";
    if (live?.status === "completed" || live?.status === "pending") return live.status;
    if (live?.status === "failed") return "failed";
    if (result) {
      if (stage === 1) return faceDetectedCount > 0 ? "completed" : "failed";
      if (stage === 2) return result.face?.embeddingCreated ? "completed" : "waiting";
      if (stage === 3) return result.discovery?.status === "complete" ? "completed" : "failed";
      if (stage === 4) return result.match ? "completed" : "failed";
      if (stage === 5) return result.fingerprint?.sha256 ? "completed" : "waiting";
      if (stage === 6) return isBlockchainConfigured ? "completed" : "pending";
      if (stage === 7) return result.verification?.status === "VERIFIED" ? "completed" : result.verification?.status === "TAMPERED" ? "failed" : "pending";
    }
    return "waiting";
  };

  const stageMessage = (stage: number) => {
    const live = liveStages[stage];
    if (live?.message) return live.message;
    if (stage === 1) return result?.face ? `${faceDetectedCount} face(s) · quality ${result.face.quality || "—"}` : "Awaiting image";
    if (stage === 2) return result?.face?.model ? `${result.face.model} embedding created` : "Awaiting embedding";
    if (stage === 3) return result?.discovery ? `${result.discovery.provider || "Search"} · ${candidateCount} result(s)` : "Awaiting web discovery";
    if (stage === 4) return result?.match ? `Best visual match ${formatPercent(result.match.similarity)}` : "Awaiting candidate matching";
    if (stage === 5) return result?.fingerprint?.sha256 ? `SHA-256 ${truncateHash(result.fingerprint.sha256)} · pHash ${truncateHash(result.fingerprint.pHash || result.fingerprint.phash)}` : "Awaiting fingerprints";
    if (stage === 6) return isBlockchainConfigured ? `Anchored on ${result?.blockchain?.network || "network"}` : "Blockchain anchoring unavailable";
    if (stage === 7) return result?.verification?.status ? `${result.verification.status} · ${result.verification.hashMatch ? "hash match" : "hash check pending"}` : "Awaiting re-verification";
    return "Waiting";
  };

  const statusTone = (status: string): "muted" | "yellow" | "pink" | "green" => status === "completed" ? "green" : status === "failed" ? "pink" : status === "running" ? "yellow" : status === "pending" ? "yellow" : "muted";
  const statusLabel = (status: string) => status === "completed" ? "✓ Complete" : status === "failed" ? "✕ Failed" : status === "running" ? "Live" : status === "pending" ? "Pending" : "Waiting";

  return (
    <div className="site-shell">
      <header className="topbar">
        <a className="brand-lockup" href="#top" aria-label="FaceChain Goa home">
          <img src="/assets/facechain-goa-mark.webp" alt="" className="brand-mark" />
          <span><b>FACECHAIN</b><em>GOA</em></span>
        </a>
        <div className="topbar-meta"><span>TASK 03</span><span className="meta-divider" /><span>HH GOA 2026</span></div>
        <button className="menu-toggle" onClick={() => setMenuOpen(v => !v)} aria-expanded={menuOpen} aria-label="Toggle navigation"><Menu size={20} /></button>
        <nav className={menuOpen ? "nav-links nav-open" : "nav-links"} aria-label="Primary navigation">
          <a href="#scan" onClick={() => setMenuOpen(false)}>Scan</a>
          <a href="#evidence" onClick={() => setMenuOpen(false)}>Evidence</a>
          <a href="#verification" onClick={() => setMenuOpen(false)}>Verification</a>
          <a href="#about" onClick={() => setMenuOpen(false)}>About</a>
          <button className="nav-cta" onClick={startScan} disabled={isVerifying}>{isVerifying ? "Verifying..." : "Start verification"} <ArrowUpRight size={15} /></button>
        </nav>
      </header>

      <main id="top">
        <section className="hero-section">
          <div className="hero-visual" role="img" aria-label="Coastal Goa horizon with a forensic fingerprint motif" />
          <div className="hero-copy">
            <div className="eyebrow"><span className="eyebrow-line" />Privacy-conscious provenance engine</div>
            <h1><span>FACECHAIN</span><strong>GOA</strong></h1>
            <p className="hero-tagline">DISCOVER.<br />FINGERPRINT.<br /><i>VERIFY.</i></p>
            <p className="hero-description">From a face in an image to a tamper-evident evidence trail. Real search, matching, hashing, blockchain, and verification — surfaced live as the backend executes.</p>
            <div className="hero-actions">
              <button className="button button-yellow" onClick={() => document.querySelector("#scan")?.scrollIntoView({ behavior: "smooth" })}>Start a scan <ArrowDownRight size={17} /></button>
              <a className="text-link" href="#how-it-works">View live pipeline <ArrowUpRight size={15} /></a>
            </div>
          </div>
          <div className="hero-stamp"><span>HH</span><b>03</b><small>PROVENANCE<br />LAB / GOA</small></div>
          <div className="hero-caption">15°29′N 73°49′E <span /> FIELD NOTE 01 / DIGITAL EVIDENCE</div>
        </section>

        <section className="manifesto-band">
          <p>Every discovery deserves<br /><em>a chain of custody.</em></p>
          <div className="manifesto-note"><span>01 — WHY IT MATTERS</span><p>Digital evidence can be copied, cropped, and changed. FaceChain Goa keeps the path from source to proof visible.</p></div>
        </section>

        <section className="scan-section" id="scan">
          <div className="section-intro">
            <SectionLabel index="01" children="The scan desk" />
            <h2>Put the<br /><em>evidence</em> in.</h2>
            <p>Upload a source image. The backend then runs seven real stages. This UI does not invent scores, sources, hashes, or blockchain state.</p>
          </div>
          <div className="scan-workbench">
            <div className={`upload-zone ${isDragging ? "is-dragging" : ""} ${preview ? "has-file" : ""}`}
              onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={e => { e.preventDefault(); setIsDragging(false); acceptFile(e.dataTransfer.files?.[0]); }}>
              {preview ? <>
                <img src={preview} alt="Selected evidence preview" className="preview-image" />
                <div className="preview-overlay" />
                <div className="preview-meta"><StatusPill tone="yellow">Image staged</StatusPill><span>{fileMeta}</span></div>
                <button className="remove-file" onClick={clearFile} aria-label="Remove selected image"><X size={17} /></button>
              </> : <>
                <div className="upload-symbol"><Upload size={21} /></div>
                <h3>Drop face image</h3>
                <p>or <button className="inline-button" onClick={() => inputRef.current?.click()}>choose from device</button></p>
                <small>JPG · PNG · WEBP / MAX 10 MB</small>
                <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp,image/bmp" hidden onChange={e => acceptFile(e.target.files?.[0])} />
              </>}
            </div>
            <div className="scan-controls">
              <div className="control-row"><span>FACE DETECTED</span><StatusPill tone={faceDetectedCount ? "green" : isVerifying ? "yellow" : "muted"}>{isVerifying && !faceDetectedCount ? "Analyzing..." : faceDetectedCount ? `${faceDetectedCount} Detected` : "Awaiting backend"}</StatusPill></div>
              <div className="control-row"><span>FACE QUALITY</span><StatusPill tone={result?.face?.quality === "PASS" ? "green" : isVerifying ? "yellow" : "muted"}>{result?.face?.quality || (isVerifying ? "Measuring..." : "Not measured")}</StatusPill></div>
              <div className="control-row"><span>SEARCH PROVIDER</span><span className="control-value">{result?.discovery?.provider || liveStages[3]?.data?.provider || "Google Lens via SerpAPI"}</span></div>
              <button className="button button-green" onClick={startScan} disabled={isVerifying}>{isVerifying ? "Verification In Progress..." : "Start verification"}<Zap size={16} /></button>
              <p className="truth-note">Live events come directly from the FastAPI pipeline. No candidate, score, hash, transaction, or verification state is fabricated here.</p>
            </div>
          </div>
        </section>

        <section className="pipeline-section" id="how-it-works">
          <div className="pipeline-heading">
            <SectionLabel index="02" children="The live pipeline" />
            <h2>Seven stages.<br /><em>One evidence trail.</em></h2>
            <StatusPill tone={isVerifying ? "yellow" : result ? (result.verification?.status === "VERIFIED" ? "green" : "yellow") : "yellow"}>{isVerifying ? "Pipeline active" : result ? "Pipeline evaluated" : "Pipeline idle"}</StatusPill>
          </div>

          {result?.error && <div className="mb-6 p-4 rounded-lg border border-pink-500/40 bg-pink-950/20 text-pink-200 flex items-start gap-3"><AlertTriangle className="text-pink-400 shrink-0" size={18} /><div><b className="block text-sm uppercase tracking-wide text-pink-400">Verification incomplete</b><p className="text-xs mt-1">{result.error}</p></div></div>}

          <div className="pipeline-list">
            {Array.from({ length: 7 }, (_, i) => i + 1).map(stage => {
              const status = getStageStatus(stage);
              const live = liveStages[stage];
              const data = live?.data || {};
              return <div className="pipeline-stage" key={stage}>
                <div className="stage-number">{String(stage).padStart(2, "0")}</div>
                <div className="stage-icon">{stageIcons[stage]}</div>
                <div className="stage-copy">
                  <b>{stageNames[stage]}</b>
                  <span>{stageMessage(stage)}{data.timeMs !== undefined && <span className="block text-[11px] opacity-60 mt-1">Stage time: {formatMs(data.timeMs)}</span>}{stage === 3 && candidateCount > 0 && <span className="block text-[11px] opacity-60 mt-1">{candidateCount} web result(s) discovered</span>}{stage === 4 && liveCandidates.length > 0 && <span className="block text-[11px] opacity-60 mt-1">{liveCandidates.length} candidate event(s) received</span>}</span>
                </div>
                <StatusPill tone={statusTone(status)}>{statusLabel(status)}</StatusPill>
                <ChevronRight size={16} className="stage-chevron" />
              </div>;
            })}
          </div>

          {(isVerifying || liveCandidates.length > 0 || result?.match?.candidates?.length) && <div className="mt-8 p-5 rounded-xl border border-stone-800 bg-stone-950/70">
            <div className="flex items-center justify-between mb-4"><div><span className="text-xs font-mono tracking-widest text-yellow-400 uppercase">Stage 04 / Candidate ledger</span><p className="text-xs text-stone-500 mt-1">Every candidate event received from the real matching loop.</p></div><span className="text-xs font-mono text-stone-400">{Math.max(liveCandidates.length, result?.match?.candidates?.length || 0)} recorded</span></div>
            <div className="overflow-x-auto"><table className="w-full text-left text-xs font-mono"><thead><tr className="border-b border-stone-800 text-stone-500"><th className="py-2 pr-3">#</th><th className="py-2 pr-3">Source</th><th className="py-2 pr-3">Similarity</th><th className="py-2 pr-3">Status</th><th className="py-2">Link</th></tr></thead><tbody>
              {(liveCandidates.length ? liveCandidates : (result?.match?.candidates || [])).map((c: any) => <tr key={c.rank} className="border-b border-stone-900"><td className="py-3 pr-3 text-stone-500">{String(c.rank).padStart(2, "0")}</td><td className="py-3 pr-3 text-stone-200"><div>{c.source || "Unknown"}</div><div className="text-[10px] text-stone-600 max-w-[300px] truncate">{c.title || ""}</div></td><td className="py-3 pr-3">{formatPercent(c.similarity)}</td><td className="py-3 pr-3">{c.status === "MATCH" ? <StatusPill tone="green">MATCH</StatusPill> : c.status === "FAILED" ? <StatusPill tone="pink">FAILED</StatusPill> : <StatusPill tone="yellow">{c.status || "PROCESSING"}</StatusPill>}</td><td className="py-3">{c.url ? <a href={c.url} target="_blank" rel="noopener noreferrer" className="text-yellow-400 underline underline-offset-4">Open ↗</a> : "—"}</td></tr>)}
            </tbody></table></div>
          </div>}

          {result && <div className="mt-8 p-6 rounded-xl border border-yellow-500/30 bg-stone-900/90 text-stone-200">
            <div className="flex items-center justify-between pb-4 mb-4 border-b border-stone-800"><span className="text-xs font-mono tracking-widest text-yellow-400 uppercase">Verification summary</span><StatusPill tone={result.verification?.status === "VERIFIED" ? "green" : result.verification?.status === "PENDING" ? "yellow" : "pink"}>{result.verification?.status || "PENDING"}</StatusPill></div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 text-xs font-mono">
              <div><span className="text-stone-400 block mb-1">Visual Match</span><strong>{formatPercent(result.match?.similarity)}</strong></div>
              <div><span className="text-stone-400 block mb-1">Web Source</span><strong className="block">{discoveredSource}</strong>{discoveredUrl && <a href={discoveredUrl} target="_blank" rel="noopener noreferrer" className="text-yellow-400 underline underline-offset-4">Open discovered website ↗</a>}</div>
              <div><span className="text-stone-400 block mb-1">Evidence Hash</span><strong>{result.fingerprint?.sha256 ? truncateHash(result.fingerprint.sha256, 10, 8) : "Pending"}</strong></div>
              <div><span className="text-stone-400 block mb-1">Blockchain</span><strong>{isBlockchainConfigured ? "Anchored" : "Not configured"}</strong></div>
              <div><span className="text-stone-400 block mb-1">Total Time</span><strong>{formatMs(result.timing?.totalMs)}</strong></div>
            </div>
          </div>}

          {result?.timing && <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px] font-mono text-stone-500">
            <div>FACE {formatMs(result.timing.faceDetectionMs)}</div><div>EMBED {formatMs(result.timing.faceEmbeddingMs)}</div><div>SEARCH {formatMs(result.timing.searchMs)}</div><div>MATCH {formatMs(result.timing.candidateMatchingMs)}</div><div>HASH {formatMs(result.timing.hashingMs)}</div><div>CHAIN {formatMs(result.timing.blockchainMs)}</div><div>VERIFY {formatMs(result.timing.verificationMs)}</div><div>TOTAL {formatMs(result.timing.totalMs)}</div>
          </div>}
          <div className="pipeline-footer"><span>INPUT IMAGE</span><div className="footer-rule" /><span>REAL RESULT ONLY</span></div>
        </section>

        <section className="evidence-section" id="evidence">
          <div className="evidence-image" role="img" aria-label="Archival paper texture with fingerprint watermark" />
          <div className="evidence-copy">
            <SectionLabel index="03" children="Proof capsule" /><h2>Evidence<br /><em>has a texture.</em></h2>
            <p>The result is a record: source, timestamp, content fingerprint, and a clear account of what the system could and could not verify.</p>
            <div className="capsule-card">
              <div className="capsule-top"><span>FACECHAIN / EVIDENCE</span><StatusPill tone={result?.fingerprint?.sha256 ? "green" : "muted"}>{result?.fingerprint?.sha256 ? "Fingerprint ready" : "Awaiting result"}</StatusPill></div>
              <div className="hash-row"><span>SHA-256</span><code>{truncateHash(result?.fingerprint?.sha256 || "Not calculated", 12, 12)}</code></div>
              <div className="hash-row"><span>pHash</span><code>{truncateHash(result?.fingerprint?.pHash || result?.fingerprint?.phash || "Not calculated", 8, 8)}</code></div>
              <div className="hash-row"><span>Source</span><div className="flex flex-col items-end gap-1 text-right"><code>{result ? discoveredSource : "Awaiting discovery"}</code>{discoveredUrl && <a href={discoveredUrl} target="_blank" rel="noopener noreferrer" className="text-[11px] text-yellow-400 underline underline-offset-2">Open discovered website ↗</a>}</div></div>
              <div className="hash-row"><span>Retrieved</span><code>{result?.fingerprint?.retrievedAt ? new Date(result.fingerprint.retrievedAt).toLocaleString() : "Stage event pending"}</code></div>
              <button className="capsule-action" onClick={() => copyToClipboard(result?.fingerprint?.sha256, "SHA-256 fingerprint")}><Clipboard size={14} /> Copy hash</button>
            </div>
          </div>
        </section>

        <section className="chain-section">
          <div className="chain-copy"><SectionLabel index="04" children="Proof architecture" /><h2>Explain the<br /><em>chain in seconds.</em></h2><p>Evidence is fingerprinted before it is anchored. A transaction is only shown as confirmed when the real network response exists.</p><div className="chain-list"><div><span>01</span><b>Evidence</b><small>Source content</small></div><div><span>02</span><b>Hash</b><small>SHA-256 fingerprint</small></div><div><span>03</span><b>Block</b><small>Network record</small></div><div><span>04</span><b>Verify</b><small>Re-check current hash</small></div></div></div>
          <div className="chain-visual"><img src="/assets/facechain-goa-chain.webp" alt="Abstract chain of evidence illustration" /><div className="chain-status"><Link2 size={16} /><span>{isBlockchainConfigured ? `ANCHORED ON ${result?.blockchain?.network?.toUpperCase() || "SEPOLIA"}` : "BLOCKCHAIN NOT CONFIGURED"}</span></div></div>
        </section>

        <section className="verification-section" id="verification">
          <div className="verification-inner"><div className="verification-kicker"><span>05</span><span>Final state</span></div><div className="verification-mark"><ShieldCheck size={28} /><span>{result?.verification?.status?.toUpperCase() || "UNVERIFIED"}</span></div><h2>Proof is a<br /><em>state of evidence.</em></h2><p>Original hash, current hash, and real blockchain state meet here. Until then, uncertainty stays visible.</p><div className="verification-grid"><div><span>ORIGINAL HASH</span><b>{truncateHash(result?.verification?.originalHash || result?.verification?.original_hash || result?.fingerprint?.sha256, 10, 8)}</b></div><div><span>CURRENT HASH</span><b>{truncateHash(result?.verification?.currentHash || result?.verification?.current_hash || result?.fingerprint?.sha256, 10, 8)}</b></div><div><span>NETWORK</span><b>{result?.blockchain?.network?.toUpperCase() || "NOT CONFIGURED"}</b></div></div></div>
        </section>

        <section className="about-section" id="about"><div><SectionLabel index="06" children="About the system" /><h2>What / How / <em>Why</em></h2></div><div className="about-columns"><div><span>WHAT</span><p>Face detection, genuine web discovery, visual candidate matching, evidence fingerprinting, blockchain anchoring, and re-verification in one visible trail.</p></div><div><span>HOW</span><p>Face <b>→</b> Embed <b>→</b> Search <b>→</b> Match <b>→</b> Fingerprint <b>→</b> Blockchain <b>→</b> Verify</p></div><div><span>PRIVACY & RESPONSIBLE USE</span><p>Similarity is evidence, not absolute identity proof. Public-source discovery has provider limitations. Sensitive data should not be stored unnecessarily.</p></div></div></section>
      </main>

      <footer className="footer"><div className="brand-lockup"><img src="/assets/facechain-goa-mark.webp" alt="" className="brand-mark" /><span><b>FACECHAIN</b><em>GOA</em></span></div><span>DISCOVER. FINGERPRINT. VERIFY.</span><span>HH GOA 2026 / TASK 03</span></footer>
    </div>
  );
}
