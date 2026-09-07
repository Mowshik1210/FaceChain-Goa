<div align="center">

# 🟢 FaceChain Goa

### DISCOVER • FINGERPRINT • VERIFY

**A privacy-conscious Face Provenance & Verification Engine, anchored on-chain.**

Built for **HH Goa 2026 — Task 3: Face Identification & Blockchain Verification**

[![Made with Python](https://img.shields.io/badge/Python-3.10%2B-2ecc71?style=for-the-badge&logo=python&logoColor=white)](#)
[![Blockchain](https://img.shields.io/badge/Ethereum-Sepolia-14532d?style=for-the-badge&logo=ethereum&logoColor=white)](#)
[![Frontend](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-1b5e20?style=for-the-badge&logo=react&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-MIT-00c853?style=for-the-badge)](#)

<img src="https://img.shields.io/badge/status-hackathon%20build-2ecc71?style=flat-square" alt="status"/>
<img src="https://img.shields.io/badge/live-face--chain--goa.vercel.app-1b5e20?style=flat-square" alt="live"/>

</div>

<br/>

<div align="center">

```
╔══════════════════════════════════════════════════╗
║          VERIFICATION COMPLETE                   ║
╠══════════════════════════════════════════════════╣
║  FACE MATCH              ✓                       ║
║  WEB SOURCE               ✓                       ║
║  EVIDENCE HASH             ✓                       ║
║  BLOCKCHAIN ANCHOR           ✓                       ║
║  RE-VERIFICATION               ✓                       ║
║                                                  ║
║       ✓ DATA VERIFIED                            ║
╚══════════════════════════════════════════════════╝
```

</div>

<br/>

## 📖 Table of Contents

- [What It Does](#-what-it-does)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Quick Start (Two-Terminal Setup)](#-quick-start-two-terminal-setup)
- [Environment Variables](#-environment-variables)
- [Running the CLI Engine](#-running-the-cli-engine)
- [Blockchain Layer](#-blockchain-layer)
- [Testing](#-testing)
- [Known Limitations](#-known-limitations)
- [Privacy & Responsible Use](#-privacy--responsible-use)
- [Roadmap](#-roadmap)
- [Team](#-team)

<br/>

## 🟢 What It Does

FaceChain Goa is a **Face Provenance & Verification Engine** designed with privacy at its core. Given a single input image, it:

1. 🧠 Detects and encodes a face from the input image
2. 🔎 Genuinely searches public web/social content for matches
3. 🪞 Compares candidate images using face embeddings
4. 🔐 Creates a cryptographic evidence fingerprint (`SHA-256` + `pHash`)
5. ⛓️ Anchors the fingerprint on the **Ethereum Sepolia** blockchain
6. ♻️ Independently re-verifies evidence integrity against the on-chain record

> ⚠️ **Important:** The system never claims certain identity. It only reports **visual face match confidence** and **evidence quality** — never a legal identity assertion.

<br/>

## 🏗️ Architecture

```
                    INPUT IMAGE
                         │
                         ▼
          FACE DETECTION + QUALITY GATE
                         │
                         ▼
          FACE EMBEDDING (DeepFace / Facenet512)
                         │
                         ▼
          GENUINE WEB SEARCH (DuckDuckGo / SerpAPI)
                         │
                         ▼
          CANDIDATE DOWNLOAD & MATCHING
                         │
                         ▼
          EVIDENCE FINGERPRINT (SHA-256 + pHash)
                         │
                         ▼
          BLOCKCHAIN ANCHOR (Sepolia Testnet)
                         │
                         ▼
          RE-VERIFICATION & TAMPER DETECTION
                         │
                         ▼
              ✅ VERIFIED  /  ⚠️ TAMPERED
```

<br/>

## 🧩 Tech Stack

| Layer | Technology |
|---|---|
| 🖼️ **Face Recognition** | DeepFace — RetinaFace detector + Facenet512 |
| 🔍 **Search** | DuckDuckGo (free) / SerpAPI Google Lens (reverse image) |
| ⛓️ **Blockchain** | Ethereum Sepolia · Web3.py · Solidity smart contract |
| 🧬 **Hashing** | SHA-256 + perceptual hash (`imagehash`) |
| 💻 **CLI** | Rich + Typer terminal UI |
| 🎨 **Frontend** | React + Vite + TailwindCSS + Radix UI |
| 🌐 **Web Server** | Express (Node.js) |

<br/>

## 🚀 Quick Start (Two-Terminal Setup)

This project runs as **two independent processes** — start the backend first, then the frontend, each in its own terminal.

### 🖥️ Terminal 1 — Backend

```bash
# 1. Move into the backend directory
cd backend

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# edit .env with your keys and RPC values

# 5. Start the backend server
python main.py
```

### 💻 Terminal 2 — Frontend

```bash
# 1. From the project root, install dependencies
npm install
# or: pnpm install

# 2. Start the dev server
npm run dev
```

> 🟢 Once both terminals are running, open the frontend URL printed in Terminal 2 — it will connect to the backend automatically.

<br/>

## 🔑 Environment Variables

```env
# Face Recognition
FACE_MODEL=Facenet512
FACE_DETECTOR=retinaface
MATCH_THRESHOLD=0.65

# Search (duckduckgo | serpapi)
SEARCH_PROVIDER=duckduckgo
SEARCH_API_KEY=                # Required only for SerpAPI

# Blockchain (Sepolia)
BLOCKCHAIN_NETWORK=sepolia
BLOCKCHAIN_RPC_URL=https://rpc.sepolia.org
BLOCKCHAIN_PRIVATE_KEY=        # Your Sepolia testnet private key
BLOCKCHAIN_CONTRACT_ADDRESS=   # Optional: deployed contract address
```

<br/>

## ⚙️ Running the CLI Engine

The core verification engine can also be run standalone from the project root:

```bash
# Demo mode — creates and processes a test image
python main.py --demo

# Process your own authorized image
python main.py --image path/to/your/image.jpg

# Tamper detection demonstration
python main.py --tamper-demo
```

<br/>

## ⛓️ Blockchain Layer

| | |
|---|---|
| **Network** | Ethereum Sepolia Testnet |
| **Contract** | `FaceChainEvidence.sol` — `anchorEvidence()` & `verifyEvidence()` |
| **Explorer** | Transaction hashes link dynamically to [sepolia.etherscan.io](https://sepolia.etherscan.io) |

<br/>

## 🧪 Testing

```bash
pytest tests/
```

<br/>

## ⚠️ Known Limitations

- 🔎 **Search Provider** — DuckDuckGo is keyword-based; reverse image search requires a SerpAPI key
- 🎯 **Face Matching** — similarity scores indicate visual resemblance, **not** legal identity proof
- ⛽ **Blockchain** — requires Sepolia ETH (via faucets) and a valid RPC endpoint
- 🚦 **Rate Limits** — free search providers may throttle heavy usage
- 🌍 **Public Content Only** — designed strictly for authorized/public content

<br/>

## 🔐 Privacy & Responsible Use

- 🚫 Do not process images of private individuals without consent
- 🚫 Do not bypass CAPTCHAs, authentication, or platform security
- 🗑️ Raw face embeddings are **not** stored permanently
- 🗑️ Temporary candidate images are deleted after processing
- 🙅 No personal names or identity claims are ever output

<br/>

## 🛣️ Roadmap

- [ ] Multi-face cluster analysis
- [ ] Additional search providers (Bing, Brave)
- [ ] IPFS integration for decentralized storage
- [ ] Mobile-optimized embedding models

<br/>

## 👥 Team

**Neural Coders** — built for HH Goa 2026, Task 3

<br/>

<div align="center">

**⭐ If you like this project, give it a star! ⭐**

Made with 🟢 and ☕ for Hacker House Goa 2026

</div>
