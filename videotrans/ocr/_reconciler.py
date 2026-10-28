# -*- coding: utf-8 -*-
from typing import List, Dict, Tuple, Optional
from videotrans.task.taskcfg import SrtItem
from videotrans.util.tools import ms_to_time_string


def time_to_ms(time_str: str) -> int:
    """Convert 'HH:MM:SS,mmm' or 'HH:MM:SS.mmm' to milliseconds."""
    if not time_str:
        return 0
    time_str = str(time_str).strip().replace(',', '.')
    parts = time_str.split(':')
    if len(parts) == 3:
        h, m, s = parts
        return int(float(h) * 3600000 + float(m) * 60000 + float(s) * 1000)
    elif len(parts) == 2:
        m, s = parts
        return int(float(m) * 60000 + float(s) * 1000)
    try:
        return int(float(time_str) * 1000)
    except ValueError:
        return 0


def _value_to_ms(value) -> int:
    """Numeric values are already milliseconds; strings are 'HH:MM:SS,mmm' timestamps."""
    if isinstance(value, (int, float)):
        return int(value)
    return time_to_ms(value)


def get_item_ms(item: SrtItem) -> Tuple[int, int]:
    """Extract start and end time in milliseconds from SrtItem."""
    if item.startraw not in (None, '') and item.endraw not in (None, ''):
        return _value_to_ms(item.startraw), _value_to_ms(item.endraw)
    return _value_to_ms(item.start_time), _value_to_ms(item.end_time)


def align_and_reconcile_transcripts(
    whisper_items: List[SrtItem],
    ocr_items: List[SrtItem]
) -> List[Dict]:
    """
    Align Whisper audio transcript with OCR visual transcript based on time overlap.
    Returns aligned pairs suitable for LLM cross-referencing and error correction.
    """
    if not whisper_items and not ocr_items:
        return []

    # If only one source is present, fallback gracefully
    if not ocr_items:
        return [
            {
                "line": it.line,
                "time": it.time,
                "start_time": it.start_time,
                "end_time": it.end_time,
                "whisper_text": it.text,
                "ocr_text": "",
                "startraw": it.startraw,
                "endraw": it.endraw
            }
            for it in whisper_items
        ]

    if not whisper_items:
        return [
            {
                "line": it.line,
                "time": it.time,
                "start_time": it.start_time,
                "end_time": it.end_time,
                "whisper_text": "",
                "ocr_text": it.text,
                "startraw": it.startraw,
                "endraw": it.endraw
            }
            for it in ocr_items
        ]

    aligned_pairs = []

    for w_idx, w_item in enumerate(whisper_items, start=1):
        w_start, w_end = get_item_ms(w_item)
        matching_ocr_texts = []

        for o_item in ocr_items:
            o_start, o_end = get_item_ms(o_item)
            # Calculate time overlap
            overlap = max(0, min(w_end, o_end) - max(w_start, o_start))
            if overlap > 0 or (abs(w_start - o_start) < 600 and abs(w_end - o_end) < 600):
                matching_ocr_texts.append(o_item.text)

        ocr_combined = " ".join(matching_ocr_texts).strip()

        aligned_pairs.append({
            "line": w_idx,
            "time": w_item.time,
            "start_time": w_item.start_time,
            "end_time": w_item.end_time,
            "whisper_text": w_item.text,
            "ocr_text": ocr_combined,
            "startraw": w_item.startraw,
            "endraw": w_item.endraw
        })

    return aligned_pairs


def format_hybrid_prompt_block(aligned_items: List[Dict], source_lang: str, target_lang: str) -> str:
    """Format aligned items into structured input for the LLM hybrid prompt."""
    lines = []
    for it in aligned_items:
        lines.append(f"[{it['line']}]")
        lines.append(f"Audio_ASR: {it['whisper_text']}")
        lines.append(f"Video_OCR: {it['ocr_text']}")
        lines.append(f"Time: {it['time']}")
        lines.append("")
    return "\n".join(lines)
