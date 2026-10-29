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
    return parse_reconciled(response.text, expected=len(aligned))
