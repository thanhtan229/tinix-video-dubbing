# -*- coding: utf-8 -*-
"""LLM step for Hybrid recognition: minimal corrections to Whisper text using OCR evidence.

The model proposes "original phrase -> replacement" pairs. Each pair is applied only when the
original phrase occurs exactly once in the Whisper text. A second call judges whether the
changed blocks keep the original meaning; changed blocks that fail fall back to Whisper text.
"""
import re
from pathlib import Path
from typing import Dict, List, Tuple

from videotrans.configure.config import ROOT_DIR, logger
from videotrans.ocr._reconciler import format_hybrid_prompt_block

EDIT_PROMPT_PATH = Path(ROOT_DIR) / "videotrans" / "prompts" / "srt" / "hybrid_edit.txt"
SYSTEM_INSTRUCTION = "You are a careful subtitle correction engine. You output only the requested edit lines."
JUDGE_INSTRUCTION = """You compare an original speech transcript (A) with a proposed edit (B) of the same subtitle line.
Answer OK if B keeps the same meaning as A. Spelling, punctuation, capitalisation and removing filler words are allowed.
Answer CHANGED if B changes any fact, word meaning, name, number, or adds or drops content.
Output exactly one line per item in the form "<index> OK" or "<index> CHANGED", wrapped in <JUDGE> tags. No other text."""
MIN_LENGTH_RATIO = 0.6


def build_edit_prompt(template: str, aligned: List[Dict]) -> str:
    return f"{template}\n\n<INPUT>\n{format_hybrid_prompt_block(aligned, '', '')}</INPUT>\n"


def parse_edits(text: str) -> List[Tuple[int, str, str]]:
    """Return (block_index, original, replacement) triples from the <EDITS> block.

    An empty result is valid (no changes needed). Malformed lines are skipped.
    """
    without_think = re.sub(r"<think>.*?</think>", "", text or "", flags=re.I | re.S)
    match = re.search(r"<EDITS>(.*?)(?:</EDITS>|$)", without_think, re.S | re.I)
    if not match:
        raise ValueError("LLM response has no <EDITS> block")
    body = re.sub(r"```[a-zA-Z]*", "", match.group(1))
    edits = []
    for line in body.splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 3 or not parts[0].isdigit() or not parts[1]:
            continue
        edits.append((int(parts[0]), parts[1], parts[2]))
    return edits


def apply_edits(aligned: List[Dict], edits: List[Tuple[int, str, str]]) -> Tuple[List[str], int, int]:
    """Apply edits to the Whisper text of each block.

    An edit is applied only when its original phrase occurs exactly once in the current text.
    Returns (texts, applied_count, skipped_count).
    """
    texts = [(item.get("whisper_text") or "") for item in aligned]
    applied = skipped = 0
    for index, original, replacement in edits:
        if not (1 <= index <= len(aligned)) or original == replacement:
            skipped += 1
            continue
        text = texts[index - 1]
        if text.count(original) == 1:
            texts[index - 1] = text.replace(original, replacement)
            applied += 1
        else:
            skipped += 1
    return texts, applied, skipped


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


def _capitalized_names(text: str) -> List[str]:
    """Capitalised words that are not the first word (likely proper nouns)."""
    words = re.findall(r"\S+", text or "")
    return [re.sub(r"[^\w]", "", w) for w in words[1:] if w[:1].isupper() and len(re.sub(r"[^\w]", "", w)) >= 2]


def guard_reconciled(aligned: List[Dict], texts: List[str]) -> List[str]:
    """Safety net: fall back to Whisper text when a block is much shorter or loses a proper noun."""
    result = []
    for item, text in zip(aligned, texts):
        whisper_text = (item.get("whisper_text") or "").strip()
        if not whisper_text:
            result.append(text)
            continue
        too_short = len(text) < MIN_LENGTH_RATIO * len(whisper_text)
        names_lost = any(name not in text for name in _capitalized_names(whisper_text))
        result.append(whisper_text if (too_short or names_lost) else text)
    return result


def _gemini_client(api_key: str):
    from google import genai
    from google.genai import types

    return genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=120_000)), types


def judge_with_gemini(pairs: List[tuple], api_key: str, model: str) -> List[bool]:
    """Ask Gemini whether each proposed edit keeps the original meaning."""
    client, types = _gemini_client(api_key)
    try:
        response = client.models.generate_content(
            model=model,
            contents=build_judge_prompt(pairs),
            config=types.GenerateContentConfig(system_instruction="You are a strict bilingual meaning checker."),
        )
    finally:
        client.close()
    return parse_judge(response.text, expected=len(pairs))


def reconcile_with_gemini(aligned: List[Dict], api_key: str, model: str) -> List[str]:
    """Propose minimal edits with Gemini, apply them, then check meaning. Raises on API or parse errors."""
    client, types = _gemini_client(api_key)
    try:
        response = client.models.generate_content(
            model=model,
            contents=build_edit_prompt(EDIT_PROMPT_PATH.read_text(encoding="utf-8"), aligned),
            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
        )
    finally:
        client.close()

    edits = parse_edits(response.text)
    texts, applied, skipped = apply_edits(aligned, edits)
    logger.info(f"[hybrid-llm] proposed={len(edits)} applied={applied} skipped={skipped}")
    texts = guard_reconciled(aligned, texts)

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
    logger.info(f"[hybrid-llm] judge kept={sum(verdicts)} reverted={len(verdicts) - sum(verdicts)}")
    return revert_changed(aligned, texts, kept)
