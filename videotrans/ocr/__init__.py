# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import List, Optional, Tuple
from videotrans.task.taskcfg import SrtItem

RECOGN_MODE_WHISPER = 0
RECOGN_MODE_OCR = 1
RECOGN_MODE_HYBRID = 2

RECOGN_MODE_NAMES = {
    0: "Whisper (Âm thanh)",
    1: "OCR Phụ đề (Hình ảnh video)",
    2: "Kết hợp Hybrid (Whisper + OCR + LLM)"
}

from videotrans.ocr._rapidocr import VideoSubtitleExtractor, run_ocr_extraction
from videotrans.ocr._reconciler import align_and_reconcile_transcripts
