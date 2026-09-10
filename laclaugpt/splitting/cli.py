"""Command-line interface for the minimal feed splitter."""
from __future__ import annotations

import argparse
import json

from .core import SplitConfig, split_video


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        prog="laclaugpt-split",
        description="Split TikTok/Instagram feed screen recordings into candidate post clips.",
    )
    command.add_argument("video")
    command.add_argument("--output", "-o", required=True)
    command.add_argument("--platform", choices=("tiktok", "instagram"), default="tiktok")
    command.add_argument("--sample-fps", type=float, default=2.0)
    command.add_argument("--identity-threshold", type=float, default=0.18)
    command.add_argument("--flow-threshold", type=float, default=0.01)
    command.add_argument("--minimum-gap", type=float, default=1.0)
    command.add_argument("--minimum-clip", type=float, default=3.0)
    command.add_argument("--transition-guard", type=float, default=0.25)
    command.add_argument("--dry-run", action="store_true")
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    config = SplitConfig(
        platform=args.platform,
        sample_fps=args.sample_fps,
        identity_change_threshold=args.identity_threshold,
        vertical_flow_threshold=args.flow_threshold,
        minimum_boundary_gap=args.minimum_gap,
        minimum_clip_seconds=args.minimum_clip,
        transition_guard_seconds=args.transition_guard,
        dry_run=args.dry_run,
    )
    print(json.dumps(split_video(args.video, args.output, config),
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
