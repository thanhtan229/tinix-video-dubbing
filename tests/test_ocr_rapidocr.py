"""Regression tests for OCR span aggregation output, ROI change detection, and timing boundaries."""

import numpy as np
import cv2
import pytest
from videotrans.ocr._rapidocr import VideoSubtitleExtractor, roi_changed, string_similarity
from videotrans.util.tools import ms_to_time_string
from videotrans.util._srt_parse import get_srt_from_list, srt_str_to_listdict


def _extractor():
    # Skip __init__ so the RapidOCR model is not loaded; aggregation needs only settings.
    ex = VideoSubtitleExtractor.__new__(VideoSubtitleExtractor)
    ex.min_subtitle_duration_ms = 300
    ex.max_gap_merge_ms = 400
    ex.similarity_threshold = 0.80
    return ex


class TestAggregateEventsOutput:
    def test_start_and_end_time_are_milliseconds_and_raw_are_srt_clock_strings(self):
        # Regression: start_time/end_time must remain integer ms for numeric arithmetic,
        # while startraw/endraw must be formatted SRT clock strings ("HH:MM:SS,mmm").
        events = [(0, "Hello world"), (250, "Hello world"), (500, "Hello world"),
                  (750, "Hello world"), (1000, "")]
        items = _extractor()._aggregate_events(events, frame_step_ms=250)
        assert len(items) == 1
        assert isinstance(items[0].start_time, int)
        assert isinstance(items[0].end_time, int)
        assert items[0].start_time == 0
        assert items[0].end_time == 1000
        assert items[0].startraw == "00:00:00,000"
        assert items[0].endraw == "00:00:01,000"
        assert items[0].time == "00:00:00,000 --> 00:00:01,000"

    def test_time_string_is_still_provided_for_display(self):
        events = [(0, "Line"), (500, "Line"), (1000, "")]
        items = _extractor()._aggregate_events(events, frame_step_ms=250)
        assert " --> " in items[0].time

    def test_nonzero_start_srt_roundtrip(self):
        # Verify a nonzero start round-trips through the project SRT serializer and parser,
        # preserving text and numeric integer millisecond times as well as SRT clock strings.
        events = [
            (1500, "First subtitle line"),
            (1750, "First subtitle line"),
            (2000, "First subtitle line"),
            (2250, ""),
            (3000, "Second subtitle line"),
            (3250, "Second subtitle line"),
            (3500, ""),
        ]
        items = _extractor()._aggregate_events(events, frame_step_ms=250)
        assert len(items) == 2

        assert isinstance(items[0].start_time, int)
        assert isinstance(items[0].end_time, int)
        assert items[0].start_time == 1500
        assert items[0].end_time == 2250
        assert items[0].startraw == "00:00:01,500"
        assert items[0].endraw == "00:00:02,250"
        assert items[0].time == "00:00:01,500 --> 00:00:02,250"

        assert isinstance(items[1].start_time, int)
        assert isinstance(items[1].end_time, int)
        assert items[1].start_time == 3000
        assert items[1].end_time == 3500
        assert items[1].startraw == "00:00:03,000"
        assert items[1].endraw == "00:00:03,500"

        # Round-trip through project SRT serializer and parser
        srt_text = get_srt_from_list(items)
        parsed_items = srt_str_to_listdict(srt_text)

        assert len(parsed_items) == 2
        for orig, parsed in zip(items, parsed_items):
            assert parsed.text == orig.text
            assert parsed.start_time == orig.start_time
            assert parsed.end_time == orig.end_time
            assert isinstance(parsed.start_time, int)
            assert isinstance(parsed.end_time, int)
            assert parsed.startraw == orig.startraw
            assert parsed.endraw == orig.endraw


class TestRoiChangeDetection:
    def test_identical_crops_are_unchanged(self):
        a = np.zeros((20, 50, 3), dtype=np.uint8)
        assert roi_changed(a, a.copy()) is False

    def test_different_text_region_is_changed(self):
        a = np.zeros((20, 50, 3), dtype=np.uint8)
        b = np.full((20, 50, 3), 255, dtype=np.uint8)
        assert roi_changed(a, b) is True

    def test_first_frame_and_shape_change_are_changed(self):
        a = np.zeros((20, 50, 3), dtype=np.uint8)
        assert roi_changed(None, a) is True
        assert roi_changed(a, np.zeros((10, 50, 3), dtype=np.uint8)) is True

    def test_empty_rois_handled_safely(self):
        empty0 = np.zeros((0, 0, 3), dtype=np.uint8)
        empty_w = np.zeros((0, 100, 3), dtype=np.uint8)
        empty_h = np.zeros((100, 0, 3), dtype=np.uint8)
        normal = np.zeros((100, 200, 3), dtype=np.uint8)

        # Empty vs empty should not trigger change
        assert roi_changed(empty0, empty0) is False
        assert roi_changed(empty0, empty_w) is False
        assert roi_changed(empty_w, empty_h) is False
        # None vs empty
        assert roi_changed(None, empty0) is False
        assert roi_changed(empty0, None) is False
        # Empty vs non-empty
        assert roi_changed(empty0, normal) is True
        assert roi_changed(normal, empty0) is True

    def test_sparse_glyph_change_empty_to_short_word(self):
        # A large subtitle ROI where global mean pixel difference is tiny (< 3.0),
        # but localized glyph pixels changed significantly.
        roi_empty = np.zeros((120, 800, 3), dtype=np.uint8)
        roi_short = roi_empty.copy()
        cv2.putText(roi_short, "Hi", (380, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

        # Confirm the global mean is below the legacy 3.0 threshold to verify the test is meaningful
        mean_diff = float(cv2.absdiff(roi_empty, roi_short).mean())
        assert mean_diff < 3.0

        # Must detect the sparse glyph change
        assert roi_changed(roi_empty, roi_short) is True
        assert roi_changed(roi_short, roi_empty) is True
        assert roi_changed(roi_short, roi_short.copy()) is False

    def test_sparse_glyph_change_one_line_to_another(self):
        # Transition from one subtitle line to another on a large ROI
        roi_line1 = np.zeros((120, 800, 3), dtype=np.uint8)
        cv2.putText(roi_line1, "First subtitle line", (150, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        roi_line2 = np.zeros((120, 800, 3), dtype=np.uint8)
        cv2.putText(roi_line2, "Second subtitle line", (150, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        assert roi_changed(roi_line1, roi_line2) is True
        assert roi_changed(roi_line2, roi_line1) is True
        assert roi_changed(roi_line1, roi_line1.copy()) is False


class TestVideoExtractorIntegration:
    def test_run_calls_ocr_once_for_static_subtitle_and_ends_at_clip_duration(self, tmp_path):
        # 10fps clip of 20 frames (2000ms duration) sampled at 4fps.
        # Verified that OCR runs once for static text and ends at exactly 2000ms.
        video = str(tmp_path / "static.avi")
        writer = cv2.VideoWriter(video, cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (320, 240))
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        for _ in range(20):  # 2 seconds at 10 fps
            writer.write(frame)
        writer.release()

        calls = []
        def fake_ocr(roi):
            calls.append(roi.shape)
            return [[None, "Static text", 0.9]], None

        ex = VideoSubtitleExtractor.__new__(VideoSubtitleExtractor)
        ex.video_path = video
        ex.crop_box = (0.75, 0.96, 0.05, 0.95)
        ex.sample_fps = 4.0
        ex.similarity_threshold = 0.80
        ex.min_subtitle_duration_ms = 300
        ex.max_gap_merge_ms = 400
        ex.callback = None
        ex.ocr = fake_ocr

        items = ex.run()
        assert len(calls) == 1
        assert len(items) == 1
        assert items[0].text == "Static text"
        assert items[0].start_time == 0
        assert items[0].end_time == 2000
        assert items[0].startraw == "00:00:00,000"
        assert items[0].endraw == "00:00:02,000"

    def test_run_multi_segment_video_transitions(self, tmp_path):
        # Short multi-segment video: empty -> first text -> second text -> empty.
        # Verifies that OCR runs only on transitions and both subtitle spans/timing are emitted.
        # 40 frames at 10fps (4.0 seconds total):
        # - frames 0..9 (0.0s - 1.0s): empty
        # - frames 10..19 (1.0s - 2.0s): "Hello world"
        # - frames 20..29 (2.0s - 3.0s): "Second subtitle"
        # - frames 30..39 (3.0s - 4.0s): empty
        video = str(tmp_path / "multi_segment.avi")
        writer = cv2.VideoWriter(video, cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (320, 240))

        frame_empty = np.zeros((240, 320, 3), dtype=np.uint8)

        frame_first = np.zeros((240, 320, 3), dtype=np.uint8)
        # Subtitle area y in [0.75*240, 0.96*240] = [180, 230], x in [0.05*320, 0.95*320] = [16, 304]
        cv2.putText(frame_first, "Hello world", (30, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        frame_second = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.putText(frame_second, "Second subtitle", (30, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        for _ in range(10):
            writer.write(frame_empty)
        for _ in range(10):
            writer.write(frame_first)
        for _ in range(10):
            writer.write(frame_second)
        for _ in range(10):
            writer.write(frame_empty)
        writer.release()

        # Reference crops for fake OCR classifier
        roi_first_ref = frame_first[180:230, 16:304]
        roi_second_ref = frame_second[180:230, 16:304]

        ocr_calls = []
        def fake_ocr(roi):
            ocr_calls.append(roi.copy())
            if roi.mean() < 1.0:
                return [], None
            d1 = float(cv2.absdiff(roi, roi_first_ref).mean())
            d2 = float(cv2.absdiff(roi, roi_second_ref).mean())
            if d1 < d2:
                return [[None, "Hello world", 0.98]], None
            else:
                return [[None, "Second subtitle", 0.98]], None

        ex = VideoSubtitleExtractor.__new__(VideoSubtitleExtractor)
        ex.video_path = video
        ex.crop_box = (0.75, 0.96, 0.05, 0.95)
        ex.sample_fps = 4.0
        ex.similarity_threshold = 0.80
        ex.min_subtitle_duration_ms = 300
        ex.max_gap_merge_ms = 400
        ex.callback = None
        ex.ocr = fake_ocr

        items = ex.run()

        # Sampled at 4fps with orig 10fps -> step is 2 frames -> 20 frames sampled total.
        # OCR should only run on transitions:
        # 1. frame 0 (initial empty)
        # 2. frame 10 (transition empty -> first text)
        # 3. frame 20 (transition first text -> second text)
        # 4. frame 30 (transition second text -> empty)
        assert len(ocr_calls) == 4

        # Both spans emitted with correct timing
        assert len(items) == 2

        assert items[0].text == "Hello world"
        assert items[0].start_time == 1000
        assert items[0].end_time == 2000
        assert items[0].startraw == "00:00:01,000"
        assert items[0].endraw == "00:00:02,000"

        assert items[1].text == "Second subtitle"
        assert items[1].start_time == 2000
        assert items[1].end_time == 3000
        assert items[1].startraw == "00:00:02,000"
        assert items[1].endraw == "00:00:03,000"


class TestBoundaries:
    def test_min_duration_boundary_below_is_discarded(self):
        ex = _extractor()
        ex.min_subtitle_duration_ms = 300
        events = [(0, "Short")]
        # duration = 299 < 300 -> filtered out
        items = ex._aggregate_events(events, frame_step_ms=299)
        assert len(items) == 0

    def test_min_duration_boundary_exact_is_kept(self):
        ex = _extractor()
        ex.min_subtitle_duration_ms = 300
        events = [(0, "Exact")]
        # duration = 300 == 300 -> kept
        items = ex._aggregate_events(events, frame_step_ms=300)
        assert len(items) == 1
        assert items[0].start_time == 0
        assert items[0].end_time == 300

    def test_min_duration_boundary_above_is_kept(self):
        ex = _extractor()
        ex.min_subtitle_duration_ms = 300
        events = [(0, "Above")]
        # duration = 301 > 300 -> kept
        items = ex._aggregate_events(events, frame_step_ms=301)
        assert len(items) == 1
        assert items[0].start_time == 0
        assert items[0].end_time == 301

    def test_max_gap_merge_boundary_exact_is_merged(self):
        ex = _extractor()
        ex.min_subtitle_duration_ms = 300
        ex.max_gap_merge_ms = 400
        ex.similarity_threshold = 0.80

        # Span 1: 0..500. Span 2 starts at 900 -> gap = 900 - 500 = 400 (== max_gap_merge_ms)
        events = [
            (0, "Line"), (250, "Line"), (500, ""),
            (900, "Line"), (1150, "Line"), (1400, "")
        ]
        items = ex._aggregate_events(events, frame_step_ms=250)
        assert len(items) == 1
        assert items[0].start_time == 0
        assert items[0].end_time == 1400

    def test_max_gap_merge_boundary_exceeded_by_one_is_not_merged(self):
        ex = _extractor()
        ex.min_subtitle_duration_ms = 300
        ex.max_gap_merge_ms = 400
        ex.similarity_threshold = 0.80

        # Span 1: 0..500. Span 2 starts at 901 -> gap = 901 - 500 = 401 (> max_gap_merge_ms)
        events = [
            (0, "Line"), (250, "Line"), (500, ""),
            (901, "Line"), (1151, "Line"), (1401, "")
        ]
        items = ex._aggregate_events(events, frame_step_ms=250)
        assert len(items) == 2
        assert items[0].start_time == 0
        assert items[0].end_time == 500
        assert items[1].start_time == 901
        assert items[1].end_time == 1401

    def test_max_gap_merge_boundary_below_by_one_is_merged(self):
        ex = _extractor()
        ex.min_subtitle_duration_ms = 300
        ex.max_gap_merge_ms = 400
        ex.similarity_threshold = 0.80

        # Span 1: 0..500. Span 2 starts at 899 -> gap = 899 - 500 = 399 (< max_gap_merge_ms)
        events = [
            (0, "Line"), (250, "Line"), (500, ""),
            (899, "Line"), (1149, "Line"), (1399, "")
        ]
        items = ex._aggregate_events(events, frame_step_ms=250)
        assert len(items) == 1
        assert items[0].start_time == 0
        assert items[0].end_time == 1399

    def test_similarity_threshold_boundary_stream(self):
        ex = _extractor()
        ex.similarity_threshold = 0.80

        # "12345" vs "1234x" has similarity exactly 0.80 (>= threshold -> merges)
        assert string_similarity("12345", "1234x") == 0.80
        events_equal = [(0, "12345"), (250, "1234x"), (500, "")]
        items_equal = ex._aggregate_events(events_equal, frame_step_ms=250)
        assert len(items_equal) == 1
        assert items_equal[0].start_time == 0
        assert items_equal[0].end_time == 500

        # "12345" vs "123xx" has similarity 0.60 (< threshold -> does not merge)
        assert string_similarity("12345", "123xx") == 0.60
        events_below = [(0, "12345"), (300, "123xx"), (600, "")]
        items_below = ex._aggregate_events(events_below, frame_step_ms=300)
        assert len(items_below) == 2
        assert items_below[0].text == "12345"
        assert items_below[0].start_time == 0
        assert items_below[0].end_time == 300
        assert items_below[1].text == "123xx"
        assert items_below[1].start_time == 300
        assert items_below[1].end_time == 600

    def test_similarity_threshold_boundary_gap_merge(self):
        ex = _extractor()
        ex.similarity_threshold = 0.80
        ex.max_gap_merge_ms = 400

        # Gap = 200ms (<= 400ms). Sim == 0.80 -> merges across gap
        events_equal = [
            (0, "12345"), (250, "12345"), (500, ""),
            (700, "1234x"), (950, "1234x"), (1200, "")
        ]
        items_equal = ex._aggregate_events(events_equal, frame_step_ms=250)
        assert len(items_equal) == 1
        assert items_equal[0].start_time == 0
        assert items_equal[0].end_time == 1200

        # Gap = 200ms (<= 400ms). Sim == 0.60 (< 0.80) -> does not merge across gap
        events_below = [
            (0, "12345"), (250, "12345"), (500, ""),
            (700, "123xx"), (950, "123xx"), (1200, "")
        ]
        items_below = ex._aggregate_events(events_below, frame_step_ms=250)
        assert len(items_below) == 2
        assert items_below[0].text == "12345"
        assert items_below[1].text == "123xx"

    def test_clip_duration_cap_prevents_exceeding_duration(self):
        ex = _extractor()
        ex.min_subtitle_duration_ms = 300
        # Clip duration known to be 2000ms
        events = [(1600, "Ending subtitle"), (1800, "Ending subtitle")]
        # Without cap, 1800 + 300 would be 2100ms.
        # With clip_duration_ms=2000, end_time is capped at 2000ms.
        # Duration is 2000 - 1600 = 400ms >= 300ms min duration.
        items = ex._aggregate_events(events, frame_step_ms=300, clip_duration_ms=2000)
        assert len(items) == 1
        assert items[0].start_time == 1600
        assert items[0].end_time == 2000
        assert items[0].startraw == "00:00:01,600"
        assert items[0].endraw == "00:00:02,000"
