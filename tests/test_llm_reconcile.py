"""Prompt building and response parsing for the Hybrid LLM reconcile step (no network)."""

import pytest

from videotrans.ocr._llm_reconcile import build_prompt, parse_reconciled, PROMPT_PATH

ALIGNED = [
    {"line": 1, "time": "00:00:00,000 --> 00:00:02,000", "whisper_text": "hello wrld",
     "ocr_text": "Hello world", "start_time": 0, "end_time": 2000, "startraw": "00:00:00,000", "endraw": "00:00:02,000"},
    {"line": 2, "time": "00:00:02,000 --> 00:00:04,000", "whisper_text": "second line",
     "ocr_text": "", "start_time": 2000, "end_time": 4000, "startraw": "00:00:02,000", "endraw": "00:00:04,000"},
]

RESPONSE = """<TRANSLATE_TEXT>
1
00:00:00,000 --> 00:00:02,000
Hello world

2
00:00:02,000 --> 00:00:04,000
Second line
</TRANSLATE_TEXT>"""


class TestBuildPrompt:
    def test_fills_language_placeholders_and_wraps_input(self):
        template = PROMPT_PATH.read_text(encoding="utf-8")
        prompt = build_prompt(template, ALIGNED)
        assert "{lang}" not in prompt and "{lang_prompt}" not in prompt
        assert "<INPUT>" in prompt and "</INPUT>" in prompt
        assert "Audio_ASR: hello wrld" in prompt
        assert "Video_OCR: Hello world" in prompt
        assert "[2]" in prompt


class TestParseReconciled:
    def test_returns_texts_in_index_order(self):
        assert parse_reconciled(RESPONSE, expected=2) == ["Hello world", "Second line"]

    def test_strips_think_block_and_code_fences(self):
        text = "<think>reasoning</think>\n```\n" + RESPONSE + "\n```"
        assert parse_reconciled(text, expected=2) == ["Hello world", "Second line"]

    def test_multiline_text_is_joined(self):
        text = "<TRANSLATE_TEXT>\n1\n00:00:00,000 --> 00:00:02,000\nHello\nworld\n\n2\n00:00:02,000 --> 00:00:04,000\nSecond\n</TRANSLATE_TEXT>"
        assert parse_reconciled(text, expected=2) == ["Hello world", "Second"]

    def test_missing_block_raises(self):
        with pytest.raises(ValueError):
            parse_reconciled(RESPONSE, expected=3)

    def test_extra_block_raises(self):
        with pytest.raises(ValueError):
            parse_reconciled(RESPONSE, expected=1)

    def test_no_tag_raises(self):
        with pytest.raises(ValueError):
            parse_reconciled("Hello world", expected=1)

    def test_empty_response_raises(self):
        with pytest.raises(ValueError):
            parse_reconciled("", expected=1)
