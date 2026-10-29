"""Default hard-subtitle style: small text on a semi-transparent box, used when no ass.json exists."""

import os
from pathlib import Path

from videotrans.configure.constants import DEFAULT_STYLE
from videotrans.util._srt_ass import set_ass_font


def test_default_style_uses_opaque_box_and_small_font():
    assert DEFAULT_STYLE["BorderStyle"] == 3
    assert DEFAULT_STYLE["Fontsize"] == 11
    assert DEFAULT_STYLE["OutlineColour"] == "&H80000000&"


def test_generated_ass_contains_default_box_style(tmp_path):
    srt = tmp_path / "sample.srt"
    srt.write_text("1\n00:00:00,000 --> 00:00:02,000\nQuan trọng\n", encoding="utf-8")
    ass_path = Path(set_ass_font(str(srt)))
    style_lines = [l for l in ass_path.read_text(encoding="utf-8-sig").splitlines() if l.startswith("Style: Default,")]
    assert style_lines, "Default style line missing"
    fields = style_lines[0].split(",")
    assert fields[1] == "Arial" and fields[2] == "11"
    assert fields[15] == "3"  # BorderStyle
