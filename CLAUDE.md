# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

LaclauGPT is a political-science multimodal discourse-analysis pipeline. The open-source version here documents the scripts used to analyze TikTok (and Instagram) data collected around the 2024 European Parliament elections. The real collected data is not included (GDPR); the repo contains only the analysis pipeline scripts and the draft paper.

The scripts are designed to run as **batch jobs on CSC Puhti** (Finnish supercomputer) with **Ollama** serving local LLM models. They are not runnable as-is without that environment, the scraped CSV inputs, the video files in CSC Allas, and the Ollama models pulled.

## Running

There is no build step, test suite, or linter. The pipeline is a fixed sequence of scripts run in order:

1. `puhti_preprocess.py` — OpenCV keyframe extraction + EasyOCR + Whisper transcription
2. `puhti_frame.py` — per-frame multimodal analysis (`llama3.2-vision:11b`)
3. `puhti_summary.py` — combined summary analysis (`llama3.2-vision:11b`)
4. `puhti_postprocess.py` — structured JSON extraction of topics/entities/sentiment (`gemma3:27b`)
5. `puhti_populism.py` — Laclau/Palonen Formula of Populism analysis (`gemma3:27b`)

Each script iterates over a hardcoded list of country/language codes (e.g. `['fi', 'sv', 'pl', 'pt', 'de', 'es', 'hu', 'hr', 'fr', 'en']` — note the lists differ slightly between scripts, and `puhti_populism.py` adds `'bg'`).

Dependencies (not pinned anywhere): `pandas`, `ollama`, `opencv-python` (`cv2`), `easyocr`, `openai-whisper`, `deep-translator`, `pydantic`, `sqlite3` (stdlib). Models must be pulled via Ollama: `llama3.2-vision:11b` and `gemma3:27b`.

## Architecture

The pipeline is a linear **stage-by-stage CSV transformation** with a shared resumption pattern:

- **CSV handoff**: each stage reads `./csv/tiktok_<lang>.csv` (produced by the previous stage), adds its columns, and writes it back. `puhti_postprocess.py` and `puhti_populism.py` instead read/write `ep24_<country>.csv`.
- **SQLite caching per stage**: each script maintains its own database (`preprocess.db`, `frame.db`, `summary.db`, `formula_of_populism.db`) keyed by `(author_username, video_id)` or `video_file`. On every row, the script checks the DB first; if a record exists it reuses the cached result, otherwise it computes and inserts. This makes every stage **idempotent and resumable** — re-running picks up where it left off. Preserve this check-then-insert pattern when modifying any stage.
- **LLM calls**: all model calls go through `ollama.chat(...)` with a consistent `options` dict (`temperature: 0.0`, `num_predict: 2048`, etc.). System prompts are large, domain-specific, and embedded inline in each script. `puhti_postprocess.py` and `puhti_populism.py` use Pydantic models (`Sentiment`, `FormulaOfPopulism`) passed via `format=` to enforce structured JSON output, then validate with `model_validate_json`.
- **Logging**: each script configures a `RotatingFileHandler` writing to `./logs/<stage>.log` (postprocess and populism write to the working directory instead).

The theoretical layer: `puhti_summary.py` does the broad political analysis; `puhti_populism.py` re-analyzes that output through Laclau's chains of equivalence / antagonism and Palonen's Formula of Populism (`Us (Demand ≡ Demand) Affects + Frontier (Other ≡ Other) Affects`). The paper (`PAPER.md`) is a draft outline that situates this method and proposes extending it (persistent memory, grouping/comparison, visualizations, a research agent, Streamlit interface).

## Conventions specific to this repo

- Column-slot pattern: frames, OCR, and frame analyses are stored in fixed numbered columns (`ocr_1`..`ocr_6`, `frame_analysis_1`..`frame_analysis_6`) because at most 6 keyframes are extracted per video. New analysis dimensions that are per-frame should follow this numbering.
- Many paths are hardcoded relative to a working directory that contains `./csv/`, `./Allas/Scraper/TikTok/Videos/...`, `./Keyframes/`, `./database/`, and `./logs/`.