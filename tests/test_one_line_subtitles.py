"""One-line burned-in subtitles: capacity from frame size and splitting of long blocks."""

from videotrans.util._srt_wrap import one_line_capacity, split_one_line


def test_capacity_for_vertical_and_landscape_frames():
    assert 20 <= one_line_capacity(720, 1280) <= 30
    assert one_line_capacity(1920, 1080) > one_line_capacity(720, 1280)


def test_short_block_stays_one_piece():
    pieces = split_one_line("Hello world", 0, 1000, 26, "en")
    assert pieces == [(0, 1000, "Hello world")]


def test_long_block_becomes_consecutive_one_line_pieces():
    text = "và hoạt động 24/7 để giúp bạn đạt được chúng và còn nhiều việc khác nữa"
    pieces = split_one_line(text, 5000, 9000, 26, "vi")
    assert len(pieces) >= 2
    assert all("\n" not in p[2] for p in pieces)
    assert pieces[0][0] == 5000 and pieces[-1][1] == 9000
    for a, b in zip(pieces, pieces[1:]):
        assert a[1] == b[0]
    assert " ".join(p[2] for p in pieces) == text
