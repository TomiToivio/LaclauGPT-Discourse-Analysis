"""Visual feed-transition detection without research-project-specific metadata.

The detector samples a screen recording, proposes boundaries when the stable
identity/text region changes, and verifies candidates with vertical optical
flow. It produces transparent scores and never performs discourse analysis.
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator


PLATFORM_ROIS = {
    # Fractions (x1, y1, x2, y2). Override in SplitConfig for other layouts.
    "tiktok": (0.01, 0.57, 0.56, 0.76),
    "instagram": (0.00, 0.75, 0.70, 0.90),
}


@dataclass(frozen=True)
class SplitConfig:
    platform: str = "tiktok"
    sample_fps: float = 2.0
    identity_change_threshold: float = 0.18
    vertical_flow_threshold: float = 0.01
    minimum_boundary_gap: float = 1.0
    minimum_clip_seconds: float = 3.0
    transition_guard_seconds: float = 0.25
    identity_roi: tuple[float, float, float, float] | None = None
    dry_run: bool = False

    def roi(self) -> tuple[float, float, float, float]:
        try:
            return self.identity_roi or PLATFORM_ROIS[self.platform.casefold()]
        except KeyError as exc:
            raise ValueError(f"unsupported platform: {self.platform}") from exc


@dataclass(frozen=True)
class Boundary:
    timestamp: float
    identity_change: float
    vertical_flow: float
    confidence: float
    method: str = "identity-change+vertical-flow"


@dataclass(frozen=True)
class Clip:
    sequence: int
    start: float
    end: float
    duration: float
    output: str = ""


def _cv2_numpy():
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            "video splitting requires the optional 'splitting' dependencies"
        ) from exc
    return cv2, np


def _crop(frame, roi):
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = roi
    left, right = round(x1 * width), round(x2 * width)
    top, bottom = round(y1 * height), round(y2 * height)
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise ValueError(f"invalid fractional ROI {roi} for {width}x{height} frame")
    return frame[top:bottom, left:right]


def identity_change(before, after, roi) -> float:
    """Return normalized mean absolute change inside the identity/text ROI."""
    cv2, np = _cv2_numpy()
    a = cv2.cvtColor(_crop(before, roi), cv2.COLOR_BGR2GRAY)
    b = cv2.cvtColor(_crop(after, roi), cv2.COLOR_BGR2GRAY)
    b = cv2.resize(b, (a.shape[1], a.shape[0]))
    return float(np.mean(cv2.absdiff(a, b)) / 255.0)


def vertical_flow(before, after) -> float:
    """Return robust median absolute vertical flow, normalized by frame height."""
    cv2, np = _cv2_numpy()
    height = before.shape[0]
    scale = min(1.0, 480.0 / max(before.shape[:2]))
    size = (max(2, round(before.shape[1] * scale)), max(2, round(height * scale)))
    a = cv2.cvtColor(cv2.resize(before, size), cv2.COLOR_BGR2GRAY)
    b = cv2.cvtColor(cv2.resize(after, size), cv2.COLOR_BGR2GRAY)
    flow = cv2.calcOpticalFlowFarneback(a, b, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    return float(np.median(np.abs(flow[..., 1])) / max(1, size[1]))


def _sampled_frames(video: Path, sample_fps: float) -> tuple[float, Iterator[tuple[float, object]]]:
    cv2, _ = _cv2_numpy()
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise ValueError(f"cannot open video: {video}")
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    if not math.isfinite(fps) or fps <= 0 or frames <= 0:
        capture.release()
        raise ValueError(f"video has invalid duration metadata: {video}")
    duration = frames / fps
    step = max(1, round(fps / sample_fps))

    def iterator():
        index = 0
        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                if index % step == 0:
                    yield index / fps, frame
                index += 1
        finally:
            capture.release()
    return duration, iterator()


def detect_boundaries(video: str | Path, config: SplitConfig) -> tuple[float, list[Boundary]]:
    """Detect auditable candidate boundaries in one screen recording."""
    if config.sample_fps <= 0:
        raise ValueError("sample_fps must be positive")
    path = Path(video)
    duration, frames = _sampled_frames(path, config.sample_fps)
    previous = None
    candidates: list[Boundary] = []
    for timestamp, frame in frames:
        if previous is None:
            previous = (timestamp, frame)
            continue
        _before_time, before = previous
        identity = identity_change(before, frame, config.roi())
        flow = vertical_flow(before, frame)
        if (identity >= config.identity_change_threshold
                and flow >= config.vertical_flow_threshold):
            confidence = min(1.0, 0.5 * identity / config.identity_change_threshold
                             + 0.5 * flow / config.vertical_flow_threshold)
            candidate = Boundary(timestamp, identity, flow, confidence)
            if candidates and timestamp - candidates[-1].timestamp < config.minimum_boundary_gap:
                if candidate.confidence > candidates[-1].confidence:
                    candidates[-1] = candidate
            else:
                candidates.append(candidate)
        previous = (timestamp, frame)
    return duration, candidates


def plan_clips(duration: float, boundaries: list[Boundary], config: SplitConfig) -> list[Clip]:
    """Turn boundaries into non-overlapping clips while trimming scroll transitions."""
    if duration <= 0:
        raise ValueError("duration must be positive")
    points = [0.0] + [b.timestamp for b in boundaries if 0 < b.timestamp < duration] + [duration]
    points = sorted(set(points))
    clips = []
    for index, (left, right) in enumerate(zip(points, points[1:]), start=1):
        start = left + (config.transition_guard_seconds if left > 0 else 0)
        end = right - (config.transition_guard_seconds if right < duration else 0)
        if end - start >= config.minimum_clip_seconds:
            clips.append(Clip(len(clips) + 1, round(start, 3), round(end, 3),
                              round(end - start, 3)))
    return clips


def _cut(source: Path, destination: Path, start: float, end: float) -> None:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is required to write clips")
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(source),
        "-map", "0", "-c", "copy", str(destination),
    ], check=True)


def split_video(video: str | Path, output_dir: str | Path,
                config: SplitConfig) -> dict:
    """Detect, optionally cut, and write a JSON provenance manifest."""
    source = Path(video).resolve()
    destination = Path(output_dir).resolve()
    duration, boundaries = detect_boundaries(source, config)
    planned = plan_clips(duration, boundaries, config)
    clips = []
    for clip in planned:
        output = destination / f"{source.stem}_{clip.sequence:04d}{source.suffix.lower()}"
        if not config.dry_run:
            _cut(source, output, clip.start, clip.end)
        clips.append(Clip(clip.sequence, clip.start, clip.end, clip.duration, str(output)))
    manifest = {
        "schema": "laclaugpt.feed-splitting/1.0",
        "source": str(source),
        "duration": round(duration, 3),
        "config": asdict(config),
        "boundaries": [asdict(item) for item in boundaries],
        "clips": [asdict(item) for item in clips],
        "interpretation_status": "descriptive preprocessing; verify clips before analysis",
    }
    if not config.dry_run:
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "splitting-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
