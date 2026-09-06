# TikTok Splitting 2.0 — speed/accuracy optimisation

## What went wrong in hungary-roihu-splitting (v1 splitting)

Symptoms (Tomi's report): "liian tarkka — naurettavan vähän videoita
läpi, ihan liian hidas."

Root causes identified in `splitting_base.py`:

1. **Full-scan OCR pass** (`FULL_SCAN_OCR`): OCR on every frame of the
   whole video. OCR is ~20-50 ms/frame → a 10-minute recording at 30 fps
   = 18,000 frames → **10-15 minutes of OCR per recording**, and any
   missed username frame fragmented runs.
2. **Cascade of 5 detectors, all must agree**: silence + scene +
   avatar + OCR + content-shift, each with its own thresholds; a
   conservative gate anywhere drops the clip. The thresholds were set
   "aggressively low for maximum sensitivity" but then the *final
   acceptance* still required multiple signals — sensitivity at the
   detection layer, selectivity at the fusion layer. Result: few clips.
3. **Ollama/Whisper fallback for uncertain cases** — minutes per video.
4. **Per-frame Python loops** — no frame skipping, no downscaling.

## v2 strategy: cheap-first, decisive-middle, expensive-last

**Tier 1 (cheap, whole video):**
- Decode at *stride 3* (every 3rd frame) downscaled to 540×960.
- Hash-based username-region change detection (pHash on the username
  ROI): cuts are where the hash distance jumps. ~2 ms/frame.
- Silence detection (auditok) runs in parallel for gap trimming.
- **Cost:** ~30 s for a 10-min recording.

**Tier 2 (verification, only at candidate boundaries):**
- At each *candidate* boundary only (typically 20-100 per recording):
  OCR the username ROI on 5 frames around the candidate.
  - Username changed → accept as cut, extract identity. (~250 ms/candidate)
  - No text in ROI → candidate is a "no-username gap" → drop segment
    (this is what removes the scroll transitions).
- Total: ~1-3 min per recording. This is where the accuracy lives.

**Tier 3 (expensive fallback, rare):**
- Only when Tier 2 has no candidates at all (e.g. no visible username
  the whole recording): scene detection (PySceneDetect, adaptive) +
  avatar-region check, and only for the first N candidates the Ollama
  visual check. Bounded: max 20 Ollama calls per recording (config).

**Fusion change (the decisive fix):** v1 required *consensus*;
v2 uses **username-identity as the primary signal with scene/avatar as
verification**, and drops the requirement that all detectors agree. A
cut is accepted if: (a) username ROI changes with confidence ≥ 0.5
(OCR text hash), OR (b) scene boundary + avatar change. Everything else
is noise. This recovers the clips v1 dropped while keeping precision
because identity-change is ground truth, not a heuristic.

## Expected results

- Speed: ~10× faster end-to-end (no full-scan OCR, no unbounded LLM).
- Yield: username-identity cutting recovers the clips v1's fusion
  gate dropped; no-username stretches still trimmed.
- Accuracy: identity-based cuts are exact where v1 was approximate;
  the fuzzy cases shrink to Tier 3 where they are handled explicitly.

## Tunable knobs (config)

```
stride: 3                  # decode stride for Tier 1
downscale: 540x960
username_hash_threshold: 10  # Hamming distance for "username changed"
ocr_verify_frames: 5       # frames OCR'd per candidate in Tier 2
ocr_confidence: 0.55
max_ollama_calls: 20       # hard cap per recording
silence_vad: auditok
```

## Files

- `splitting2/tiktok_splitter.py` — TikTok implementation (ROIs from
  v1's `tiktok_splitting.py` reused: avatar (630,1370)-(700,1450),
  text (10,1100)-(600,1450) at 1080×1920, fraction-based)
- `splitting2/base.py` — tiered pipeline (ported from
  `hungary-roihu-splitting/splitting_base.py`, simplified)
- CLI: `python -m splitting2.base video.mp4 --platform tiktok`