from __future__ import annotations

import pytest

from laclaugpt.splitting import Boundary, SplitConfig, plan_clips


def test_plan_clips_trims_transitions_and_drops_short_segments() -> None:
    config = SplitConfig(minimum_clip_seconds=3.0, transition_guard_seconds=0.25)
    boundaries = [Boundary(5.0, 0.3, 0.02, 0.9), Boundary(6.5, 0.3, 0.02, 0.9)]
    clips = plan_clips(12.0, boundaries, config)
    assert [(clip.start, clip.end) for clip in clips] == [(0.0, 4.75), (6.75, 12.0)]
    assert [clip.sequence for clip in clips] == [1, 2]


def test_invalid_platform_is_explicit() -> None:
    with pytest.raises(ValueError, match="unsupported platform"):
        SplitConfig(platform="unknown").roi()


def test_visual_metrics_detect_changed_shifted_region() -> None:
    np = pytest.importorskip("numpy")
    pytest.importorskip("cv2")
    from laclaugpt.splitting.core import identity_change, vertical_flow

    before = np.zeros((200, 100, 3), dtype=np.uint8)
    after = before.copy()
    before[120:170, 5:70] = 255
    after[100:150, 5:70] = 255
    roi = (0.0, 0.45, 0.8, 0.9)
    assert identity_change(before, after, roi) > 0.1
    assert vertical_flow(before, after) > 0.01
