"""Hybrid LLM step: edit prompt, edit parsing and application, guard and meaning check (no network)."""

import pytest

from videotrans.ocr._llm_reconcile import (
    EDIT_PROMPT_PATH,
    apply_edits,
    build_edit_prompt,
    build_judge_prompt,
    guard_reconciled,
    parse_edits,
    parse_judge,
    revert_changed,
)


def _aligned(*whisper_texts):
    return [
        {"line": i + 1, "time": f"00:00:{i:02d},000 --> 00:00:{i + 1:02d},000", "whisper_text": w,
         "ocr_text": "", "start_time": i * 1000, "end_time": (i + 1) * 1000,
         "startraw": f"00:00:{i:02d},000", "endraw": f"00:00:{i + 1:02d},000"}
        for i, w in enumerate(whisper_texts)
    ]


class TestBuildEditPrompt:
    def test_prompt_contains_rules_and_wrapped_input(self):
        prompt = build_edit_prompt(EDIT_PROMPT_PATH.read_text(encoding="utf-8"), _aligned("tất pin gì"))
        assert "# RULES" in prompt
        assert "<EDITS>" in prompt
        assert "<INPUT>" in prompt and "</INPUT>" in prompt
        assert "Audio_ASR: tất pin gì" in prompt


class TestParseEdits:
    def test_parses_index_original_replacement(self):
        text = "<EDITS>\n3 | tất pin | topping\n</EDITS>"
        assert parse_edits(text) == [(3, "tất pin", "topping")]

    def test_empty_edits_is_valid(self):
        assert parse_edits("<EDITS>\n</EDITS>") == []

    def test_skips_malformed_lines(self):
        text = "<EDITS>\nnot an edit\n2 | | empty original\n1 | soi | nước sôi\n</EDITS>"
        assert parse_edits(text) == [(1, "soi", "nước sôi")]

    def test_strips_think_and_fences(self):
        text = "<think>x</think>\n```\n<EDITS>\n1 | a | b\n</EDITS>\n```"
        assert parse_edits(text) == [(1, "a", "b")]

    def test_missing_tag_raises(self):
        with pytest.raises(ValueError):
            parse_edits("1 | a | b")


class TestApplyEdits:
    def test_applies_unique_phrase(self):
        texts, applied, skipped = apply_edits(_aligned("tất pin gì"), [(1, "tất pin", "topping")])
        assert texts == ["topping gì"] and (applied, skipped) == (1, 0)

    def test_skips_phrase_that_is_not_present(self):
        texts, applied, skipped = apply_edits(_aligned("hello"), [(1, "world", "earth")])
        assert texts == ["hello"] and (applied, skipped) == (0, 1)

    def test_skips_ambiguous_phrase(self):
        texts, applied, skipped = apply_edits(_aligned("ớt ớt"), [(1, "ớt", "tươi")])
        assert texts == ["ớt ớt"] and (applied, skipped) == (0, 1)

    def test_skips_out_of_range_index(self):
        texts, applied, skipped = apply_edits(_aligned("hello"), [(5, "hello", "hi")])
        assert texts == ["hello"] and (applied, skipped) == (0, 1)

    def test_skips_no_op_edit(self):
        texts, applied, skipped = apply_edits(_aligned("hello"), [(1, "hello", "hello")])
        assert texts == ["hello"] and (applied, skipped) == (0, 1)

    def test_sequential_edits_on_same_block(self):
        texts, applied, _ = apply_edits(_aligned("soi vô nợ"), [(1, "soi", "nước sôi"), (1, "nợ", "nở")])
        assert texts == ["nước sôi vô nở"] and applied == 2


class TestGuard:
    def test_similar_length_text_is_kept(self):
        assert guard_reconciled(_aligned("tôi cho một muỗng"), ["Tôi cho một muỗng."]) == ["Tôi cho một muỗng."]

    def test_much_shorter_text_falls_back(self):
        whisper = "Công thức Nhi sẽ để trên mạng hình Muối tôi đang xài là muối ngọc yến á"
        assert guard_reconciled(_aligned(whisper), ["Công thức tôi sẽ để trên màn hình."]) == [whisper]

    def test_lost_proper_noun_falls_back(self):
        whisper = "Mì hôm nay Nhi ăn là mì gấu đỏ quốc dân rồi ha"
        assert guard_reconciled(_aligned(whisper), ["Mì hôm nay tôi ăn là mì Gấu Đỏ quốc dân."]) == [whisper]

    def test_first_word_capital_is_not_a_proper_noun(self):
        whisper = "Công thức này áp dụng cho mọi loại mì"
        llm = "Công thức này áp dụng cho mọi loại mì."
        assert guard_reconciled(_aligned(whisper), [llm]) == [llm]

    def test_empty_whisper_keeps_text(self):
        assert guard_reconciled(_aligned(""), ["Hello world"]) == ["Hello world"]


class TestJudge:
    def test_prompt_lists_original_and_proposed_pairs(self):
        prompt = build_judge_prompt([("soi vô", "nước sôi vô")])
        assert "<INPUT>" in prompt and "[1]" in prompt
        assert "A: soi vô" in prompt and "B: nước sôi vô" in prompt

    def test_parses_ok_and_changed(self):
        assert parse_judge("<JUDGE>\n1 OK\n2 CHANGED\n</JUDGE>", expected=2) == [True, False]

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
        assert revert_changed(aligned, ["nước sôi vô", "nở."], [False, True]) == ["soi vô", "nở."]
