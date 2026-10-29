# -*- coding: utf-8 -*-
import os
import re
import cv2
import time
from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Optional, Tuple, Callable
from videotrans.task.taskcfg import SrtItem
from videotrans.util.tools import ms_to_time_string


def time_to_ms(time_str: str) -> int:
    """Convert 'HH:MM:SS,mmm' or 'HH:MM:SS.mmm' to milliseconds."""
    if not time_str:
        return 0
    time_str = str(time_str).strip().replace(',', '.')
    parts = time_str.split(':')
    if len(parts) == 3:
        h, m, s = parts
        return int(float(h) * 3600000 + float(m) * 60000 + float(s) * 1000)
    elif len(parts) == 2:
        m, s = parts
        return int(float(m) * 60000 + float(s) * 1000)
    try:
        return int(float(time_str) * 1000)
    except ValueError:
        return 0

try:
    from rapidocr_onnxruntime import RapidOCR
except ImportError:
    RapidOCR = None

_OCR_INSTANCE = None

def get_ocr_instance():
    global _OCR_INSTANCE
    if _OCR_INSTANCE is None:
        if RapidOCR is None:
            raise RuntimeError("rapidocr_onnxruntime is not installed.")
        _OCR_INSTANCE = RapidOCR()
    return _OCR_INSTANCE


# RapidOCR line confidence below this is treated as on-screen noise. Measured on a real
# hardsubbed clip: keeps about 98% of subtitle lines and drops about 63% of overlay lines.
MIN_LINE_SCORE = 0.85


# Short acronyms that are real subtitle words and must not be treated as overlay noise.
_KEEP_ACRONYMS = {'AI', 'TV', 'US', 'UK', 'OK', 'PC', 'ID', 'USA', 'MMA', 'CEO', 'AM', 'PM', 'IT', 'ET', 'VM', 'II', 'III'}


def _is_overlay_token(token: str) -> bool:
    """Form-based check for on-screen overlay fragments such as 2MA380, 90m or IMA."""
    core = re.sub(r'^\W+|\W+$', '', token)
    if not core:
        return False
    # Digits mixed with letters, unless a run of 3+ lowercase letters shows a real word
    # (for example a merged subtitle word like "andworks24/7to").
    if re.search(r'\d', core) and re.search(r'[A-Za-z]', core) and not re.search(r'[a-z]{3,}', core):
        return True
    return core.isupper() and 2 <= len(core) <= 4 and core not in _KEEP_ACRONYMS


def filter_ocr_lines(ocr_result) -> str:
    """Join OCR line texts, skipping low-confidence lines and overlay fragments."""
    texts = []
    for box_info in ocr_result or []:
        if float(box_info[2]) < MIN_LINE_SCORE:
            continue
        words = [w for w in str(box_info[1]).split() if not _is_overlay_token(w)]
        if words:
            texts.append(" ".join(words))
    return " ".join(texts)


def string_similarity(s1: str, s2: str) -> float:
    """Compute string similarity ratio (0.0 to 1.0) ignoring spaces and punctuation."""
    clean1 = re.sub(r'[^\w]', '', s1.lower())
    clean2 = re.sub(r'[^\w]', '', s2.lower())
    if not clean1 and not clean2:
        return 1.0
    if not clean1 or not clean2:
        return 0.0
    return SequenceMatcher(None, clean1, clean2).ratio()


# Mean absolute pixel difference (0-255) below which two subtitle crops are treated as identical.
# Hardcoded subtitles stay still for seconds, so reusing the last OCR result is safe and avoids
# running the (slow) recognizer on every sampled frame.
ROI_UNCHANGED_THRESHOLD = 3.0
ROI_PIXEL_DIFF_THRESHOLD = 25.0
ROI_MIN_CHANGED_RATIO = 0.0005


def roi_changed(
    prev_roi,
    roi,
    threshold: float = ROI_UNCHANGED_THRESHOLD,
    pixel_diff_threshold: float = ROI_PIXEL_DIFF_THRESHOLD,
    min_pixel_ratio: float = ROI_MIN_CHANGED_RATIO,
) -> bool:
    if prev_roi is None:
        return roi is not None and getattr(roi, "size", 0) > 0
    if roi is None:
        return getattr(prev_roi, "size", 0) > 0

    prev_size = getattr(prev_roi, "size", 0)
    curr_size = getattr(roi, "size", 0)
    if prev_size == 0 and curr_size == 0:
        return False
    if prev_size == 0 or curr_size == 0:
        return True

    if prev_roi.shape != roi.shape:
        return True

    diff = cv2.absdiff(prev_roi, roi)
    if float(diff.mean()) > threshold:
        return True

    max_diff = diff.max(axis=-1) if diff.ndim >= 3 else diff
    num_changed = int((max_diff > pixel_diff_threshold).sum())
    total_pixels = max_diff.size
    if total_pixels > 0 and (num_changed / total_pixels) >= min_pixel_ratio:
        return True

    return False


class VideoSubtitleExtractor:
    """
    Video Subtitle Extractor using RapidOCR (ONNX).
    Extracts hardcoded subtitles from video frames into SRT items.
    """

    def __init__(
        self,
        video_path: str,
        crop_box: Tuple[float, float, float, float] = (0.75, 0.96, 0.05, 0.95),
        sample_fps: float = 4.0,
        similarity_threshold: float = 0.80,
        min_subtitle_duration_ms: int = 300,
        max_gap_merge_ms: int = 400,
        callback: Optional[Callable[[int, str], None]] = None
    ):
        self.video_path = video_path
        # crop_box: (ymin_ratio, ymax_ratio, xmin_ratio, xmax_ratio)
        self.crop_box = crop_box
        self.sample_fps = max(1.0, min(10.0, sample_fps))
        self.similarity_threshold = similarity_threshold
        self.min_subtitle_duration_ms = min_subtitle_duration_ms
        self.max_gap_merge_ms = max_gap_merge_ms
        self.callback = callback
        self.ocr = get_ocr_instance()
        self.clip_duration_ms: Optional[int] = None

    def run(self) -> List[SrtItem]:
        if not os.path.exists(self.video_path):
            raise FileNotFoundError(f"Video file not found: {self.video_path}")

        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open video file with OpenCV: {self.video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        orig_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration_sec = total_frames / orig_fps if orig_fps > 0 else 0
        clip_duration_ms = int(duration_sec * 1000) if duration_sec > 0 else None
        self.clip_duration_ms = clip_duration_ms

        # Calculate bounding box in pixels
        ymin_r, ymax_r, xmin_r, xmax_r = self.crop_box
        y1 = max(0, int(ymin_r * height))
        y2 = min(height, int(ymax_r * height))
        x1 = max(0, int(xmin_r * width))
        x2 = min(width, int(xmax_r * width))

        frame_step = max(1, int(orig_fps / self.sample_fps))
        frame_step_ms = max(1, int((frame_step / orig_fps) * 1000))
        current_frame_idx = 0

        raw_events = []  # List of (time_ms, text)
        prev_roi, prev_text = None, ""
        start_time = time.time()

        while True:
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_idx)
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            time_ms = int((current_frame_idx / orig_fps) * 1000)
            if clip_duration_ms is not None and clip_duration_ms > 0:
                time_ms = min(time_ms, clip_duration_ms)

            # Crop ROI
            roi = frame[y1:y2, x1:x2]

            # OCR inference (skipped while the subtitle crop is visually unchanged)
            if roi.size == 0:
                text = ""
                prev_roi, prev_text = roi, text
            elif roi_changed(prev_roi, roi):
                ocr_result, _ = self.ocr(roi)
                text = filter_ocr_lines(ocr_result)
                prev_roi, prev_text = roi, text
            else:
                text = prev_text

            raw_events.append((time_ms, text.strip()))

            if self.callback and total_frames > 0:
                percent = int((current_frame_idx / total_frames) * 100)
                self.callback(percent, f"OCR: {percent}% ({time_ms // 1000}s/{int(duration_sec)}s)")

            current_frame_idx += frame_step
            if current_frame_idx >= total_frames:
                break

        cap.release()

        # Aggregate raw frame events into continuous subtitle spans
        srt_items = self._aggregate_events(
            raw_events,
            frame_step_ms=frame_step_ms,
            clip_duration_ms=clip_duration_ms
        )
        return srt_items

    def _aggregate_events(
        self,
        events: List[Tuple[int, str]],
        frame_step_ms: int,
        clip_duration_ms: Optional[int] = None
    ) -> List[SrtItem]:
        if not events:
            return []

        if clip_duration_ms is None:
            clip_duration_ms = getattr(self, "clip_duration_ms", None)

        merged_spans = []  # List of dict(start_ms, end_ms, text)
        current_span = None

        for time_ms, text in events:
            if not text:
                if current_span:
                    merged_spans.append(current_span)
                    current_span = None
                continue

            span_end = time_ms + frame_step_ms
            if clip_duration_ms is not None and clip_duration_ms > 0:
                span_end = min(span_end, clip_duration_ms)

            if current_span is None:
                current_span = {
                    "start_ms": time_ms,
                    "end_ms": span_end,
                    "text": text
                }
            else:
                sim = string_similarity(current_span["text"], text)
                if sim >= self.similarity_threshold:
                    # Same subtitle, extend end time
                    current_span["end_ms"] = span_end
                    # Prefer longer text if similarity is high
                    if len(text) > len(current_span["text"]):
                        current_span["text"] = text
                else:
                    # Different subtitle, finish previous and start new
                    merged_spans.append(current_span)
                    current_span = {
                        "start_ms": time_ms,
                        "end_ms": span_end,
                        "text": text
                    }

        if current_span:
            merged_spans.append(current_span)

        # Post-processing: Merge close gaps and filter short durations
        filtered_spans = []
        for span in merged_spans:
            if clip_duration_ms is not None and clip_duration_ms > 0:
                span["end_ms"] = min(span["end_ms"], clip_duration_ms)
                span["start_ms"] = min(span["start_ms"], clip_duration_ms)

            duration = span["end_ms"] - span["start_ms"]
            if duration < self.min_subtitle_duration_ms:
                continue

            if filtered_spans:
                prev = filtered_spans[-1]
                gap = span["start_ms"] - prev["end_ms"]
                sim = string_similarity(prev["text"], span["text"])
                if gap <= self.max_gap_merge_ms and sim >= self.similarity_threshold:
                    prev["end_ms"] = span["end_ms"]
                    if clip_duration_ms is not None and clip_duration_ms > 0:
                        prev["end_ms"] = min(prev["end_ms"], clip_duration_ms)
                    continue

            filtered_spans.append(span)

        # Convert to SrtItem objects
        result_srt = []
        line_idx = 1
        for span in filtered_spans:
            start_ms = span["start_ms"]
            end_ms = span["end_ms"]
            if clip_duration_ms is not None and clip_duration_ms > 0:
                start_ms = min(start_ms, clip_duration_ms)
                end_ms = min(end_ms, clip_duration_ms)

            if end_ms <= start_ms:
                continue

            start_str = ms_to_time_string(ms=start_ms)
            end_str = ms_to_time_string(ms=end_ms)

            # start_time/end_time are integer milliseconds, matching the Whisper SrtItems that
            # downstream timing code (task/_rate.py, dubbing) does arithmetic on.
            # startraw/endraw are formatted SRT clock strings (HH:MM:SS,mmm).
            item = SrtItem(
                line=line_idx,
                time=f"{start_str} --> {end_str}",
                text=span["text"],
                start_time=int(start_ms),
                end_time=int(end_ms),
                startraw=start_str,
                endraw=end_str
            )
            result_srt.append(item)
            line_idx += 1

        return result_srt


def run_ocr_extraction(
    video_file: str,
    crop_box: Tuple[float, float, float, float] = (0.75, 0.96, 0.05, 0.95),
    callback: Optional[Callable[[int, str], None]] = None
) -> List[SrtItem]:
    """Top-level runner for OCR subtitle extraction."""
    extractor = VideoSubtitleExtractor(
        video_path=video_file,
        crop_box=crop_box,
        callback=callback
    )
    return extractor.run()
