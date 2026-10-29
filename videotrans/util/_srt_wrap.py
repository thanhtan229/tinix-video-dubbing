# -*- coding: utf-8 -*-
import re
from typing import Tuple
from functools import lru_cache

from videotrans.configure import constants


def band_margin_v(area: Tuple[float, float, float, float], play_res_h: int = 288, font_size: int = 11) -> int:
    """Bottom margin (ASS units) that centres a one-line subtitle on a frame band (ymin, ymax, xmin, xmax)."""
    ymin, ymax = area[0], area[1]
    center = (ymin + ymax) / 2
    half_line = font_size * 1.2 / 2
    return max(0, int(round((1 - center) * play_res_h - half_line)))


def split_one_line(text: str, start_ms: int, end_ms: int, capacity: int, language: str = "en"):
    """Split one subtitle block into consecutive pieces that each fit on one line.

    Pieces share the block's time in proportion to their length, so each piece stays on screen
    for a sensible time. Returns a list of (start_ms, end_ms, text).
    """
    lines = [l.strip() for l in simple_wrap(text, capacity, language).split("\n") if l.strip()]
    if len(lines) <= 1:
        return [(int(start_ms), int(end_ms), lines[0] if lines else text.strip())]
    total = sum(len(l) for l in lines)
    span = end_ms - start_ms
    pieces = []
    cursor = float(start_ms)
    for i, line in enumerate(lines):
        duration = span * len(line) / total if i < len(lines) - 1 else end_ms - cursor
        pieces.append((int(cursor), int(cursor + duration), line))
        cursor += duration
    return pieces


def one_line_capacity(width: int, height: int, font_size: int = 11, play_res_h: int = 288,
                       fill: float = 0.9) -> int:
    """Characters that fit on one burned-in line.

    ASS font sizes are in units of a 288-px-high play area; scale them to the video height, assume an
    average glyph width of half the em size, and use 90% of the frame width.
    """
    font_px = font_size * height / play_res_h
    glyph_px = 0.5 * font_px
    return max(10, int(width * fill / glyph_px))


@lru_cache
def simple_wrap(text: str, maxlen: int = 15, language: str = "en") -> str:
    flag = [
        ",", ".", "?", "!", ";",
        "，", "。", "？", "；", "！", " "
    ]
    text = re.sub(r"\r?(\n|\\n)", ' ', text, flags=re.I).strip()
    _len = len(text)
    if _len < maxlen + 4:
        return text
    text_lilst = []
    current_text = ""
    offset = 2 if language.split('-')[0] in constants.CJK_LANG else 8
    maxlen = max(3, maxlen)
    offset = min(offset, maxlen // 2)

    i = 0
    while i < _len:
        current_text = current_text.lstrip()
        if i >= _len - offset:
            current_text += text[i:]
            break
        if len(current_text) < maxlen - offset:
            current_text += text[i]
            i += 1
            continue
        if maxlen - offset <= len(current_text) <= maxlen and text[i] in flag:
            current_text += text[i]
            i += 1
            text_lilst.append(current_text)
            current_text = ''
            continue
        raw_i = i
        for next_i in range(1, offset + 1):
            if i + next_i >= _len:
                break
            if text[i + next_i] in flag:
                pos_i = i + next_i + 1
                current_text += text[i:pos_i]
                raw_i = pos_i
                text_lilst.append(current_text)
                current_text = ''
                break
        if raw_i != i:
            i = raw_i
            continue
        current_text += text[i]
        if len(current_text) >= maxlen:
            text_lilst.append(current_text)
            current_text = ''
        i += 1

    if current_text and len(current_text) < maxlen / 3 and text_lilst:
        text_lilst[-1] += current_text
    elif current_text:
        text_lilst.append(current_text)
    return ("\n".join(text_lilst)).strip()
