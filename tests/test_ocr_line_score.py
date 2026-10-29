"""OCR line confidence filter used by the subtitle extractor."""

from videotrans.ocr._rapidocr import MIN_LINE_SCORE, filter_ocr_lines


def _line(text, score):
    return [[[0, 0], [1, 0], [1, 1], [0, 1]], text, score]


class TestFilterOcrLines:
    def test_keeps_high_confidence_subtitle_lines_in_order(self):
        result = [_line("Hello world", 0.97), _line("second line", 0.92)]
        assert filter_ocr_lines(result) == "Hello world second line"

    def test_drops_low_confidence_overlay_text(self):
        result = [_line("Hello world", 0.97), _line("SIMA HObE", 0.62)]
        assert filter_ocr_lines(result) == "Hello world"

    def test_threshold_is_inclusive(self):
        result = [_line("edge", MIN_LINE_SCORE)]
        assert filter_ocr_lines(result) == "edge"

    def test_empty_and_whitespace_lines_are_skipped(self):
        result = [_line("   ", 0.99), _line("ok", 0.9)]
        assert filter_ocr_lines(result) == "ok"

    def test_no_result_returns_empty_string(self):
        assert filter_ocr_lines(None) == ""
        assert filter_ocr_lines([]) == ""
