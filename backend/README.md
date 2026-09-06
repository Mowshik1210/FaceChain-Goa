# FaceChain Goa

> **DISCOVER &bull; FINGERPRINT &bull; VERIFY**

HH GOA 2026 — Task 3: Face Identification & Blockchain Verification

## What It Does

FaceChain Goa is a privacy-conscious **Face Provenance & Verification Engine** that:

1. Detects and encodes a face from an input image
2. Genuinely searches public web/social content
3. Compares candidate images using face embeddings
4. Creates a cryptographic evidence fingerprint (SHA-256 + pHash)
5. Anchors the fingerprint on Ethereum Sepolia blockchain
6. Independently re-verifies evidence integrity against the on-chain record

**Critical:** The system does NOT claim certain identity. It reports "visual face match confidence" and "evidence quality."

## Architecture

```
INPUT IMAGE
    &darr;
FACE DETECTION + QUALITY GATE
    &darr;
FACE EMBEDDING (DeepFace/Facenet512)
    &darr;
GENUINE WEB SEARCH (DuckDuckGo / SerpAPI)
    &darr;
CANDIDATE DOWNLOAD & MATCHING
    &darr;
EVIDENCE FINGERPRINT (SHA-256 + pHash)
    &darr;
BLOCKCHAIN ANCHOR (Sepolia Testnet)
    &darr;
RE-VERIFICATION & TAMPER DETECTION
    &darr;
VERIFIED / TAMPERED
```

## Tech Stack

- **Face Recognition:** DeepFace (RetinaFace detector + Facenet512)
- **Search:** DuckDuckGo (free) / SerpAPI Google Lens (reverse image)
- **Blockchain:** Ethereum Sepolia, Web3.py, Solidity smart contract
- **Hashing:** SHA-256, perceptual hash (imagehash)
- **CLI:** Rich + Typer terminal UI

## Setup

```bash
# 1. Clone and enter directory
cd facechain-goa

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your values
```

## Environment Variables

```bash
# Face Recognition
FACE_MODEL=Facenet512
FACE_DETECTOR=retinaface
MATCH_THRESHOLD=0.65

# Search (duckduckgo | serpapi)
SEARCH_PROVIDER=duckduckgo
SEARCH_API_KEY=           # Required only for SerpAPI

# Blockchain (Sepolia)
BLOCKCHAIN_NETWORK=sepolia
BLOCKCHAIN_RPC_URL=https://rpc.sepolia.org
BLOCKCHAIN_PRIVATE_KEY=   # Your Sepolia testnet private key
BLOCKCHAIN_CONTRACT_ADDRESS=  # Optional: deployed contract address
```

## Running

```bash
# Demo mode (creates and processes a test image)
python main.py --demo

# Process your own authorized image
python main.py --image path/to/your/image.jpg

# Tamper detection demonstration
python main.py --tamper-demo
```

## Blockchain Used

- **Network:** Ethereum Sepolia Testnet
- **Contract:** `FaceChainEvidence.sol` with `anchorEvidence()` and `verifyEvidence()`
- **Explorer:** Transaction hashes link dynamically to `sepolia.etherscan.io`

## Verification Example

When successful, the terminal displays:

```
╔══════════════════════════════════════════════════╗
║          VERIFICATION COMPLETE                   ║
╠══════════════════════════════════════════════════╣
║  FACE MATCH              ✓                       ║
║  WEB SOURCE              ✓                       ║
║  EVIDENCE HASH           ✓                       ║
║  BLOCKCHAIN ANCHOR       ✓                       ║
║  RE-VERIFICATION         ✓                       ║
║                                                  ║
║       ✓ DATA VERIFIED                            ║
╚══════════════════════════════════════════════════╝
```

## Testing

```bash
pytest tests/
```

## Known Limitations

1. **Search Provider:** DuckDuckGo is keyword-based; reverse image search requires SerpAPI key
2. **Face Matching:** Similarity scores indicate visual resemblance, NOT legal identity proof
3. **Blockchain:** Requires Sepolia ETH (obtainable from faucets) and valid RPC endpoint
4. **Rate Limits:** Free search providers may rate-limit heavy usage
5. **Public Content Only:** The system is designed for authorized/public content only

## Privacy & Responsible Use

- Do not process images of private individuals without consent
- Do not bypass CAPTCHAs, authentication, or platform security
- Raw face embeddings are not stored permanently
- Temporary candidate images are deleted after processing
- No personal names or identity claims are output

## Future Improvements

- Multi-face cluster analysis
- Additional search providers (Bing, Brave)
- IPFS integration for decentralized storage
- Mobile-optimized embedding models
