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


from videotrans.ocr._llm_reconcile import guard_reconciled


def _aligned_one(whisper_text):
    return [{"whisper_text": whisper_text, "ocr_text": ""}]


class TestGuardReconciled:
    def test_similar_length_llm_text_is_kept(self):
        assert guard_reconciled(_aligned_one("tôi cho một muỗng đường"), ["Tôi cho một muỗng đường."]) == ["Tôi cho một muỗng đường."]

    def test_much_shorter_llm_text_falls_back_to_whisper(self):
        whisper = "Công thức Nhi sẽ để trên mạng hình Muối tôi đang xài là muối ngọc yến á"
        assert guard_reconciled(_aligned_one(whisper), ["Công thức tôi sẽ để trên màn hình."]) == [whisper]

    def test_lost_proper_noun_falls_back_to_whisper(self):
        whisper = "Mì hôm nay Nhi ăn là mì gấu đỏ quốc dân"
        assert guard_reconciled(_aligned_one(whisper), ["Mì hôm nay tôi ăn là mì Gấu Đỏ quốc dân."]) == [whisper]

    def test_first_word_capital_is_not_a_proper_noun(self):
        whisper = "Công thức này áp dụng cho mọi loại mì"
        llm = "Công thức này áp dụng cho mọi loại mì."
        assert guard_reconciled(_aligned_one(whisper), [llm]) == [llm]

    def test_empty_whisper_text_keeps_llm_text(self):
        assert guard_reconciled(_aligned_one(""), ["Hello world"]) == ["Hello world"]


from videotrans.ocr._llm_reconcile import build_judge_prompt, parse_judge, revert_changed


class TestJudge:
    def test_prompt_lists_original_and_proposed_pairs(self):
        prompt = build_judge_prompt([("soi vô", "nước sôi vô")])
        assert "<INPUT>" in prompt and "[1]" in prompt
        assert "A: soi vô" in prompt and "B: nước sôi vô" in prompt

    def test_parses_ok_and_changed(self):
        text = "<JUDGE>\n1 OK\n2 CHANGED\n</JUDGE>"
        assert parse_judge(text, expected=2) == [True, False]

    def test_accepts_bracket_and_colon_formats(self):
        assert parse_judge("[1]: OK\n2) changed", expected=2) == [True, False]

    def test_missing_index_raises(self):
        with pytest.raises(ValueError):
            parse_judge("1 OK", expected=2)

    def test_empty_response_raises(self):
        with pytest.raises(ValueError):
            parse_judge("", expected=1)

    def test_revert_uses_whisper_text_only_for_changed_blocks(self):
        aligned = [{"whisper_text": "soi vô"}, {"whisper_text": "nợ"}]
        out = revert_changed(aligned, ["nước sôi vô", "nở."], [False, True])
        assert out == ["soi vô", "nở."]
