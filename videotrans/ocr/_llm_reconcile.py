# -*- coding: utf-8 -*-
"""LLM step for Hybrid recognition: reconcile Whisper (audio) and OCR (on-screen) text.

Uses the existing prompt in prompts/srt/hybrid_reconcile.txt. The prompt also asks for
translation; here the target language is set to the source language so the pipeline's
own translation stage is not repeated.
"""
import re
from pathlib import Path
from typing import Dict, List

from videotrans.configure.config import ROOT_DIR
from videotrans.ocr._reconciler import format_hybrid_prompt_block

PROMPT_PATH = Path(ROOT_DIR) / "videotrans" / "prompts" / "srt" / "hybrid_reconcile.txt"
SOURCE_LANG_PHRASE = "the same language as Audio_ASR"
SYSTEM_INSTRUCTION = "You are a top-tier Subtitle Reconciliation Engine."


def build_prompt(template: str, aligned: List[Dict]) -> str:
    body = template.replace("{lang}", SOURCE_LANG_PHRASE).replace("{lang_prompt}", "")
    return f"{body}\n\n<INPUT>\n{format_hybrid_prompt_block(aligned, '', '')}</INPUT>\n"


def parse_reconciled(text: str, expected: int) -> List[str]:
    """Return one reconciled text per input block, in input order.

    Raises ValueError when the response does not contain exactly the expected indices.
    """
    without_think = re.sub(r"<think>.*?</think>", "", text or "", flags=re.I | re.S)
    match = re.search(r"<TRANSLATE_TEXT>(.*?)(?:</TRANSLATE_TEXT>|$)", without_think, re.S | re.I)
    if not match:
        raise ValueError("LLM response has no <TRANSLATE_TEXT> block")
    body = re.sub(r"```[a-zA-Z]*", "", match.group(1)).strip()

    texts: Dict[int, str] = {}
    for block in re.split(r"\n\s*\n", body):
        lines = [line.strip() for line in block.strip().splitlines() if line.strip()]
        if len(lines) < 3 or not lines[0].isdigit():
            continue
        texts[int(lines[0])] = " ".join(lines[2:])

    if sorted(texts) != list(range(1, expected + 1)):
        raise ValueError(f"LLM returned blocks {sorted(texts)}, expected 1..{expected}")
    return [texts[i] for i in range(1, expected + 1)]


JUDGE_INSTRUCTION = """You compare an original speech transcript (A) with a proposed edit (B) of the same subtitle line.
Answer OK if B keeps the same meaning as A. Spelling, punctuation, capitalisation and removing filler words are allowed.
Answer CHANGED if B changes any fact, word meaning, name, number, or adds or drops content.
Output exactly one line per item in the form "<index> OK" or "<index> CHANGED", wrapped in <JUDGE> tags. No other text."""


def build_judge_prompt(pairs: List[tuple]) -> str:
    """pairs: list of (original_text, proposed_text), numbered from 1."""
    items = "\n".join(f"[{i}]\nA: {a}\nB: {b}" for i, (a, b) in enumerate(pairs, start=1))
    return f"{JUDGE_INSTRUCTION}\n\n<INPUT>\n{items}\n</INPUT>\n"


def parse_judge(text: str, expected: int) -> List[bool]:
    """Return True (meaning kept) or False (changed) per item. Raises when any index is missing."""
    without_think = re.sub(r"<think>.*?</think>", "", text or "", flags=re.I | re.S)
    verdicts: Dict[int, bool] = {}
    for match in re.finditer(r"^\s*\[?(\d+)\]?[\s:.)-]+(OK|CHANGED)\b", without_think, re.M | re.I):
        verdicts[int(match.group(1))] = match.group(2).upper() == "OK"
    if sorted(verdicts) != list(range(1, expected + 1)):
        raise ValueError(f"judge returned items {sorted(verdicts)}, expected 1..{expected}")
    return [verdicts[i] for i in range(1, expected + 1)]


def revert_changed(aligned: List[Dict], texts: List[str], kept: List[bool]) -> List[str]:
    """Use the Whisper text for every block the judge marked as changed."""
    return [
        text if ok else (item.get("whisper_text") or text)
        for item, text, ok in zip(aligned, texts, kept)
    ]


def judge_with_gemini(pairs: List[tuple], api_key: str, model: str) -> List[bool]:
    """Ask Gemini whether each proposed edit keeps the original meaning."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=120_000))
    try:
        response = client.models.generate_content(
            model=model,
            contents=build_judge_prompt(pairs),
            config=types.GenerateContentConfig(system_instruction="You are a strict bilingual meaning checker."),
        )
    finally:
        client.close()
    return parse_judge(response.text, expected=len(pairs))


MIN_LENGTH_RATIO = 0.6


def _capitalized_names(text: str) -> List[str]:
    """Capitalised words that are not the first word (likely proper nouns)."""
    words = re.findall(r"\S+", text or "")
    return [re.sub(r"[^\w]", "", w) for w in words[1:] if w[:1].isupper() and len(re.sub(r"[^\w]", "", w)) >= 2]


def guard_reconciled(aligned: List[Dict], texts: List[str]) -> List[str]:
    """Keep the LLM text only when it does not shorten or rename the Whisper text.

    Falls back to the Whisper text for a block when the LLM output is much shorter, or when a
    proper noun present in the Whisper text is missing from the LLM output.
    """
    result = []
    for item, llm_text in zip(aligned, texts):
        whisper_text = (item.get("whisper_text") or "").strip()
        if not whisper_text:
            result.append(llm_text)
            continue
        too_short = len(llm_text) < MIN_LENGTH_RATIO * len(whisper_text)
        names_lost = any(name not in llm_text for name in _capitalized_names(whisper_text))
        result.append(whisper_text if (too_short or names_lost) else llm_text)
    return result


def reconcile_with_gemini(aligned: List[Dict], api_key: str, model: str) -> List[str]:
    """Call Gemini once for the whole aligned list. Raises on API or parse errors."""
    from google import genai
    from google.genai import types

    template = PROMPT_PATH.read_text(encoding="utf-8")
    prompt = build_prompt(template, aligned)
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=120_000))
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
        )
    finally:
        client.close()
    texts = guard_reconciled(aligned, parse_reconciled(response.text, expected=len(aligned)))

    # Semantic check: only blocks that differ from the Whisper text need a judgement.
    changed = [
        i for i, (item, text) in enumerate(zip(aligned, texts))
        if (item.get("whisper_text") or "").strip() and text.strip() != item["whisper_text"].strip()
    ]
    if not changed:
        return texts
    verdicts = judge_with_gemini(
        [(aligned[i]["whisper_text"], texts[i]) for i in changed], api_key, model)
    kept = [True] * len(aligned)
    for i, ok in zip(changed, verdicts):
        kept[i] = ok
    return revert_changed(aligned, texts, kept)
