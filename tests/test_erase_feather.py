"""Blur erase mode uses feathered edges; cinema box stays a hard black band."""

import tempfile
from types import SimpleNamespace

from videotrans.task._stage_assemble import AssembleMixin

CACHE = tempfile.mkdtemp()


def _filter(mode):
    obj = AssembleMixin.__new__(AssembleMixin)
    obj.cfg = SimpleNamespace(erase_sub_mode=mode, erase_sub_area=(0.734, 0.791, 0.183, 0.967), cache_folder=CACHE)
    obj.video_info = {'width': 360, 'height': 640}
    return obj._build_subtitle_filter('sub.ass')


def test_blur_mode_feathers_the_edges():
    f = _filter(1)
    assert "geq=" in f and "[soft]" in f
    assert "overlay=" in f and "subtitles=filename='sub.ass'" in f


def test_cinema_box_is_unchanged():
    f = _filter(2)
    assert "drawbox=" in f and "geq=" not in f


def test_custom_feather_width_is_used():
    obj = AssembleMixin.__new__(AssembleMixin)
    obj.cfg = SimpleNamespace(erase_sub_mode=1, erase_sub_area=(0.734, 0.791, 0.183, 0.967), erase_feather=9, cache_folder=CACHE)
    obj.video_info = {'width': 360, 'height': 640}
    assert "/9)" in obj._build_subtitle_filter('sub.ass')


def test_zero_feather_means_automatic():
    obj = AssembleMixin.__new__(AssembleMixin)
    obj.cfg = SimpleNamespace(erase_sub_mode=1, erase_sub_area=(0.734, 0.791, 0.183, 0.967), erase_feather=0, cache_folder=CACHE)
    obj.video_info = {'width': 360, 'height': 640}
    assert "/6)" in obj._build_subtitle_filter('sub.ass')  # min(w,h)//6 for a 36 px band is 6


def test_erase_modes_add_rounded_bar_over_the_band():
    import os
    import tempfile
    from pathlib import Path
    for mode in (1, 2):
        obj = AssembleMixin.__new__(AssembleMixin)
        cache = tempfile.mkdtemp()
        obj.cfg = SimpleNamespace(erase_sub_mode=mode, erase_sub_area=(0.734, 0.791, 0.183, 0.967),
                                  erase_feather=0, cache_folder=cache)
        obj.video_info = {'width': 360, 'height': 640}
        f = obj._build_subtitle_filter('sub.ass')
        assert "movie=filename=sub_bar.png" in f and "overlay=" in f and "[v_bar]" in f
        assert os.path.exists(os.path.join(cache, 'sub_bar.png'))
        assert Path(os.path.join(cache, 'sub_bar.png')).stat().st_size > 0
