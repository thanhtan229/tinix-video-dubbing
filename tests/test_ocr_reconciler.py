"""Regression and behaviour tests for the Hybrid OCR/Whisper reconciler."""

from videotrans.task.taskcfg import SrtItem
from videotrans.ocr._reconciler import (
    time_to_ms,
    get_item_ms,
    align_and_reconcile_transcripts,
    format_hybrid_prompt_block,
)


def _item(text, start_ms, end_ms, line=1, startraw=None, endraw=None):
    return SrtItem(
        text=text,
        start_time=start_ms,
        end_time=end_ms,
        startraw=startraw if startraw is not None else start_ms,
        endraw=endraw if endraw is not None else end_ms,
        line=line,
        time=f"{start_ms} --> {end_ms}",
    )


class TestTimeToMs:
    def test_comma_separated_timestamp(self):
        assert time_to_ms("00:00:01,500") == 1500

    def test_dot_separated_timestamp_with_hours(self):
        assert time_to_ms("01:02:03.004") == 3723004

    def test_mm_ss_timestamp(self):
        assert time_to_ms("02:30") == 150000

    def test_plain_seconds(self):
        assert time_to_ms("2.5") == 2500

    def test_empty_and_invalid_return_zero(self):
        assert time_to_ms("") == 0
        assert time_to_ms("garbage") == 0


class TestGetItemMs:
    def test_numeric_raw_values_are_milliseconds(self):
        item = _item("a", 1000, 2000)
        assert get_item_ms(item) == (1000, 2000)

    def test_string_raw_values_from_whisper_are_parsed(self):
        # Whisper engines store startraw/endraw as 'HH:MM:SS,mmm' strings.
        item = _item("a", 1500, 3000, startraw="00:00:01,500", endraw="00:00:03,000")
        assert get_item_ms(item) == (1500, 3000)

    def test_numeric_start_time_without_raw_values(self):
        item = SrtItem(text="a", start_time=1200, end_time=2400, startraw="", endraw="")
        assert get_item_ms(item) == (1200, 2400)


class TestAlignAndReconcile:
    def test_both_sources_empty_returns_empty_list(self):
        assert align_and_reconcile_transcripts([], []) == []

    def test_whisper_only_has_empty_ocr_text(self):
        whisper = [_item("hello", 0, 1000)]
        pairs = align_and_reconcile_transcripts(whisper, [])
        assert len(pairs) == 1
        assert pairs[0]["whisper_text"] == "hello"
        assert pairs[0]["ocr_text"] == ""

    def test_ocr_only_has_empty_whisper_text(self):
        ocr = [_item("SUB", 0, 1000)]
        pairs = align_and_reconcile_transcripts([], ocr)
        assert pairs[0]["whisper_text"] == ""
        assert pairs[0]["ocr_text"] == "SUB"

    def test_overlapping_ocr_text_is_matched(self):
        whisper = [_item("hello there", 1000, 3000, line=1)]
        ocr = [_item("Xin chào", 1200, 2800)]
        pairs = align_and_reconcile_transcripts(whisper, ocr)
        assert pairs[0]["ocr_text"] == "Xin chào"

    def test_non_overlapping_ocr_text_is_excluded(self):
        whisper = [_item("hello", 0, 1000)]
        ocr = [_item("later subtitle", 5000, 6000)]
        pairs = align_and_reconcile_transcripts(whisper, ocr)
        assert pairs[0]["ocr_text"] == ""

    def test_hybrid_mode_accepts_whisper_string_timestamps(self):
        # Regression: Whisper items with 'HH:MM:SS,mmm' startraw used to raise ValueError.
        whisper = [_item("hello", 1500, 3000, startraw="00:00:01,500", endraw="00:00:03,000")]
        ocr = [_item("Xin chào", 1600, 2900)]
        pairs = align_and_reconcile_transcripts(whisper, ocr)
        assert pairs[0]["ocr_text"] == "Xin chào"


class TestFormatHybridPromptBlock:
    def test_formats_each_aligned_line(self):
        aligned = [{
            "line": 1,
            "time": "00:00:00,000 --> 00:00:01,000",
            "whisper_text": "hello",
            "ocr_text": "Xin chào",
        }]
        block = format_hybrid_prompt_block(aligned, "en", "vi")
        assert "[1]" in block
        assert "Audio_ASR: hello" in block
        assert "Video_OCR: Xin chào" in block
        assert "Time: 00:00:00,000 --> 00:00:01,000" in block
