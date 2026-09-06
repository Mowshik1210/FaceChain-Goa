# FaceChain Goa UI Direction

## Three initial directions

### Theme Name: Monsoon Archive
Very Brief Intro: A tactile editorial system that treats every verification as a piece of coastal evidence: paper, ink, stamps, and a precise forensic trail. Goa is present through horizon light, palm silhouettes, and warm pigment rather than tourist clichés.
Probability: 0.074

### Theme Name: Signal Coast
Very Brief Intro: A sharper technical direction built around dark green fields, high-contrast yellow signals, and a restrained network diagram language. It makes the pipeline feel fast and legible for a live hackathon demo.
Probability: 0.021

### Theme Name: Sunlit Ledger
Very Brief Intro: An airy museum-catalog approach with off-white space, soft archival photography, thin rules, and confident typography. The product feels like a trusted public record rather than a conventional SaaS tool.
Probability: 0.089

## Chosen Approach: Monsoon Archive

### Design Movement
Contemporary editorial brutalism with archival print cues and coastal South Asian color logic. The interface should feel like a field notebook from a digital investigator: expressive in its composition, exact in its evidence language.

### Core Principles
1. **Proof before polish.** Every result is labeled as backend-derived, pending, unavailable, or failed; the UI never implies a success that the system has not returned.
2. **Editorial rhythm.** Use offset columns, oversized numerals, thin rules, and purposeful whitespace instead of a centered SaaS dashboard grid.
3. **Tactile seriousness.** Cream paper, deep Goa green, charcoal ink, and small registration marks provide warmth while technical data remains crisp and readable.
4. **Fast path to the scan.** The landing statement earns attention, then the upload workspace is immediately reachable with obvious next actions.

### Color Philosophy
Deep Goa green is the grounding color: it signals trust, vegetation, and the depth of the coastal horizon. Warm turmeric yellow is reserved for active signals and confirmed progression, so it reads as energy rather than decoration. Cream/off-white creates the archival paper field. Charcoal carries the technical copy. Controlled coral pink is used only for warnings, stamps, and moments that need emotional emphasis; it must never become a generic accent gradient.

### Layout Paradigm
A split editorial canvas: navigation and metadata hug a narrow left rail on large screens while the main content moves through asymmetric bands. The scanner is a framed workbench, not a floating card. Evidence and verification sections alternate cream and green fields, with technical details aligned to rules and timestamps. On mobile, the rail collapses into a compact top bar and the pipeline becomes a vertical evidence spine.

### Signature Elements
- A small fingerprint-sun mark and compact wordmark with a yellow registration tick.
- Thin yellow evidence rules, numbered pipeline stages, and archival label chips.
- A “Proof Capsule” motif: a paper-like evidence panel with hash rows, custody events, and a stamped status.

### Interaction Philosophy
Interactions should feel like handling evidence: deliberate, clear, and reversible. Upload is a visible handoff, not a hidden input. Buttons use language that describes the action. Hover states underline or shift a rule; active states confirm with a small physical press. Backend truth is surfaced in plain language, and unavailable capability is shown as an honest status rather than disabled mystery.

### Animation
Use 180–280ms ease-out transitions for controls and a staggered 40ms reveal for pipeline stages. When a scan runs, animate only the active stage rule and a small signal traveling between nodes. Hash creation can use a short masked-to-visible reveal; blockchain confirmation can use a single yellow pulse through the chain. Verification success gets one stamped-in moment, not a looping celebration. Gentle palm or grain movement is allowed only in the hero and respects `prefers-reduced-motion`.

### Typography System
Use **DM Sans** for interface copy and **Space Grotesk** for display numerals and headlines. Headlines are uppercase with tight tracking and a slightly compressed line-height. Body copy is 15–17px with generous line-height. Metadata uses 11–12px uppercase labels with wide tracking. The word “GOA” can be oversized and italicized sparingly to create the editorial anchor.

### Brand Essence
FaceChain Goa is a privacy-conscious provenance engine for investigators, creators, and judges who need to move from a discovered face to a tamper-evident proof trail. Personality: **exact, coastal, uncompromising**.

### Brand Voice
Headlines are declarative and compact. CTAs are verbs. Microcopy explains uncertainty without hedging or hype.

Example lines:
- “From face to proof.”
- “No match is still a result. Keep the trail honest.”

### Wordmark & Logo
The mark is a fingerprint whorl intersected by a rising sun and one broken chain link. The wordmark is set in a custom-styled uppercase lockup with a yellow registration tick between FACECHAIN and GOA; it should not rely on a default unmodified font treatment.

### Signature Brand Color
**Monsoon Green — #0B3B32.** It is darker and more botanical than standard product greens, allowing cream type and turmeric signals to feel unmistakably tied to Goa rather than generic fintech.

## Implementation Guardrails

The supplied terminal project remains the source of truth. This frontend prototype will use explicit empty, pending, failed, and success states and will not invent candidates, hashes, timings, transaction IDs, or verification claims. The UI will be prepared for a future API adapter, while the static experience remains honest about backend availability. No backend or server logic in the supplied source archive is modified in this frontend project.

## Style Decisions

- Favor a split editorial canvas over centered dashboard geometry.
- Use generated imagery only for the hero and atmospheric proof sections; keep the technical evidence UI deterministic and readable.
- Keep coral pink rare and meaningful: warnings, tamper states, and proof stamps only.
- Never use a purple gradient, fake metrics, fake candidates, or placeholder blockchain success.
- Make mobile a vertical evidence trail rather than a shrunk desktop layout.

## Asset URLs

- Hero: `/assets/facechain-goa-hero.webp`
- Proof paper: `/assets/facechain-goa-passport.webp`
- Chain illustration: `/assets/facechain-goa-chain.webp`
- Brand mark: `/assets/facechain-goa-mark.webp`
