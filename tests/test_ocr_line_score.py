"""OCR line confidence filter used by the subtitle extractor."""

from videotrans.ocr._rapidocr import MIN_LINE_SCORE, filter_ocr_lines


def _line(text, score):
    return [[[0, 0], [1, 0], [1, 1], [0, 1]], text, score]


class TestOverlayTokens:
    def test_overlay_fragments_are_removed_from_subtitle_line(self):
        result = [_line("and works 2MA380 IMA to help", 0.95)]
        assert filter_ocr_lines(result) == "and works to help"

    def test_unit_and_number_fragments_are_removed(self):
        result = [_line("run 90m 2x MIN", 0.95)]
        assert filter_ocr_lines(result) == "run"

    def test_real_words_and_acronyms_are_kept(self):
        result = [_line("I use AI on the Secure VM 24/7", 0.95)]
        assert filter_ocr_lines(result) == "I use AI on the Secure VM 24/7"

    def test_merged_subtitle_word_with_digits_is_kept(self):
        result = [_line("andworks24/7tohelpyou achieve", 0.95)]
        assert filter_ocr_lines(result) == "andworks24/7tohelpyou achieve"

    def test_line_of_only_overlay_is_dropped(self):
        result = [_line("IMA 2MA380", 0.95), _line("Hello", 0.95)]
        assert filter_ocr_lines(result) == "Hello"


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
