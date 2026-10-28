"""Regression tests: merged Whisper segments keep per-line OCR text; OCR noise is dropped."""

from videotrans.task.taskcfg import SrtItem
from videotrans.ocr._reconciler import align_and_reconcile_transcripts


def _item(text, start_ms, end_ms, line=1):
    return SrtItem(
        text=text,
        start_time=start_ms,
        end_time=end_ms,
        startraw=start_ms,
        endraw=end_ms,
        line=line,
        time=f"{start_ms} --> {end_ms}",
    )


class TestMergedWhisperSegment:
    def test_segment_spanning_two_ocr_lines_is_split_per_line(self):
        whisper = [_item("hello world  second line", 0, 3820)]
        ocr = [_item("Hello world", 0, 3360), _item("Second line", 3360, 4360)]

        out = align_and_reconcile_transcripts(whisper, ocr)

        assert [it["ocr_text"] for it in out] == ["Hello world", "Second line"]
        assert all(it["whisper_text"] == "" for it in out)
        assert [it["line"] for it in out] == [1, 2]
        assert [it["start_time"] for it in out] == [0, 3360]

    def test_single_ocr_line_keeps_whisper_text_with_ocr_context(self):
        whisper = [_item("hello world", 0, 3000)]
        ocr = [_item("Hello world", 0, 2900)]

        out = align_and_reconcile_transcripts(whisper, ocr)

        assert len(out) == 1
        assert out[0]["whisper_text"] == "hello world"
        assert out[0]["ocr_text"] == "Hello world"

    def test_one_ocr_line_overlapping_two_segments_keeps_both_whisper_entries(self):
        # A single OCR line matches each segment on its own, so the normal path applies.
        whisper = [_item("first part", 0, 2000), _item("second part", 2000, 4000)]
        ocr = [_item("First part Second part", 0, 4000)]

        out = align_and_reconcile_transcripts(whisper, ocr)

        assert len(out) == 2
        assert [it["whisper_text"] for it in out] == ["first part", "second part"]
        assert all(it["ocr_text"] == "First part Second part" for it in out)


class TestOcrNoiseFilter:
    def test_single_character_ocr_items_are_dropped(self):
        whisper = []
        ocr = [_item("C", 0, 500), _item("Hello world", 600, 2000)]

        out = align_and_reconcile_transcripts(whisper, ocr)

        assert [it["ocr_text"] for it in out] == ["Hello world"]

    def test_single_character_ocr_does_not_add_to_whisper_entry(self):
        whisper = [_item("hello world", 0, 2000)]
        ocr = [_item("x", 0, 1900)]

        out = align_and_reconcile_transcripts(whisper, ocr)

        assert len(out) == 1
        assert out[0]["ocr_text"] == ""

    def test_all_noise_ocr_falls_back_to_whisper_only(self):
        whisper = [_item("hello", 0, 1000)]
        ocr = [_item("-", 0, 1000)]

        out = align_and_reconcile_transcripts(whisper, ocr)

        assert out[0]["whisper_text"] == "hello"
        assert out[0]["ocr_text"] == ""
