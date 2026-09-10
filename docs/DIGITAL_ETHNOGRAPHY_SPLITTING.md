# Feed screen-recording splitting for digital ethnography

`laclaugpt-split` is a small, project-neutral preprocessing tool for TikTok and
Instagram feed screen recordings. It proposes post boundaries from two visible
signals:

1. change in the platform's identity/text region;
2. vertical optical flow consistent with a feed scroll.

Nearby candidates are merged, a configurable guard interval trims the scrolling
transition, and short fragments are omitted. Every boundary retains its two
scores and the effective configuration in `splitting-manifest.json`.

This is descriptive preprocessing, not discourse analysis. Researchers should
inspect the clips and manifest before treating them as analytical documents.
The detector does not infer authorship, political affiliation, ideology, affect,
populism, or any other theoretical category.

## Installation

FFmpeg must be available on `PATH`. Install the optional Python dependencies:

```bash
python -m pip install -e ".[splitting]"
```

## Usage

Inspect proposed boundaries without writing clips:

```bash
laclaugpt-split recording.mp4 --platform tiktok -o split-output --dry-run
```

Write clips and a provenance manifest:

```bash
laclaugpt-split recording.mp4 --platform instagram -o split-output
```

The defaults are deliberately transparent rather than universally optimal.
For a new device layout, validate them on a hand-coded sample and tune
`--identity-threshold`, `--flow-threshold`, `--sample-fps`, `--minimum-gap`,
`--minimum-clip`, and `--transition-guard`. Platform regions are fractional, so
they scale with resolution; custom layouts can use the Python API and supply
`SplitConfig(identity_roi=(x1, y1, x2, y2))`.

The minimal public implementation intentionally excludes OCR, ASR, LLM calls,
project-specific file naming, political metadata, databases, cluster paths, and
automatic feedback into Context Memory.
