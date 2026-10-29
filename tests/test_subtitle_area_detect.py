"""Automatic source-subtitle area: pick the persistent text band, ignore overlays and noise."""

from videotrans.ocr._rapidocr import pick_subtitle_band, _has_subtitle_text


def test_picks_the_persistent_band_and_ignores_overlay():
    frames = []
    for i in range(100):
        boxes = [(0.745, 0.775, 0.2, 0.8)] if i < 80 else []
        if i < 30:
            boxes.append((0.90, 0.92, 0.1, 0.5))
        frames.append(boxes)
    ymin, ymax, xmin, xmax = pick_subtitle_band(frames)
    assert 0.73 <= ymin <= 0.75 and 0.77 <= ymax <= 0.79
    assert ymax < 0.85  # overlay band is excluded


def test_returns_none_when_no_band_is_persistent():
    assert pick_subtitle_band([[] for _ in range(10)]) is None


def test_returns_none_when_band_is_rare():
    frames = [[(0.5, 0.52, 0.1, 0.9)] if i % 10 == 0 else [] for i in range(100)]
    assert pick_subtitle_band(frames, min_share=0.2) is None


def test_subtitle_text_filter_rejects_overlay_fragments():
    assert _has_subtitle_text("your relationships")
    assert not _has_subtitle_text("SIMA 2MA380")  # mixed-case fragments such as HObE are a known gap
