"""Gemini speech recognition: segment JSON parsing and word timing (no network)."""

import pytest

from videotrans.recognition._gemini import parse_segments, segments_to_words


class TestParseSegments:
    def test_parses_plain_json_array(self):
        text = '[{"start": 0, "end": 2.5, "text": "hello world"}]'
        assert parse_segments(text) == [{"start": 0.0, "end": 2.5, "text": "hello world"}]

    def test_strips_code_fence(self):
        text = '```json\n[{"start": 1, "end": 2, "text": "hi"}]\n```'
        assert parse_segments(text) == [{"start": 1.0, "end": 2.0, "text": "hi"}]

    def test_skips_empty_text_and_non_positive_duration(self):
        text = ('[{"start": 0, "end": 1, "text": "  "}, {"start": 2, "end": 2, "text": "x"},'
                ' {"start": 3, "end": 4, "text": "kept"}]')
        assert parse_segments(text) == [{"start": 3.0, "end": 4.0, "text": "kept"}]

    def test_empty_array_is_valid(self):
        assert parse_segments("[]") == []

    def test_non_array_raises(self):
        with pytest.raises(ValueError):
            parse_segments('{"start": 0}')

    def test_invalid_json_raises(self):
        with pytest.raises(Exception):
            parse_segments("not json")


class TestSegmentsToWords:
    def test_words_cover_segment_span_in_order(self):
        words = segments_to_words([{"start": 0.0, "end": 2.0, "text": "ab cde"}])
        assert [w["word"] for w in words] == ["ab", "cde"]
        assert words[0]["start"] == 0.0
        assert words[-1]["end"] == pytest.approx(2.0)
        assert words[0]["end"] == pytest.approx(words[1]["start"])

    def test_longer_words_get_longer_time(self):
        words = segments_to_words([{"start": 0.0, "end": 3.0, "text": "a bbbbbbbbb"}])
        assert (words[1]["end"] - words[1]["start"]) > (words[0]["end"] - words[0]["start"])

    def test_multiple_segments_keep_their_own_spans(self):
        segs = [{"start": 0.0, "end": 1.0, "text": "one"}, {"start": 5.0, "end": 6.0, "text": "two"}]
        words = segments_to_words(segs)
        assert words[0]["start"] == 0.0 and words[1]["start"] == 5.0
        assert words[1]["end"] == pytest.approx(6.0)

    def test_no_segments_gives_no_words(self):
        assert segments_to_words([]) == []
