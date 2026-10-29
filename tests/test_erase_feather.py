"""Blur erase mode uses feathered edges; cinema box stays a hard black band."""

from types import SimpleNamespace

from videotrans.task._stage_assemble import AssembleMixin


def _filter(mode):
    obj = AssembleMixin.__new__(AssembleMixin)
    obj.cfg = SimpleNamespace(erase_sub_mode=mode, erase_sub_area=(0.734, 0.791, 0.183, 0.967))
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
    obj.cfg = SimpleNamespace(erase_sub_mode=1, erase_sub_area=(0.734, 0.791, 0.183, 0.967), erase_feather=9)
    obj.video_info = {'width': 360, 'height': 640}
    assert "/9)" in obj._build_subtitle_filter('sub.ass')


def test_zero_feather_means_automatic():
    obj = AssembleMixin.__new__(AssembleMixin)
    obj.cfg = SimpleNamespace(erase_sub_mode=1, erase_sub_area=(0.734, 0.791, 0.183, 0.967), erase_feather=0)
    obj.video_info = {'width': 360, 'height': 640}
    assert "/6)" in obj._build_subtitle_filter('sub.ass')  # min(w,h)//6 for a 36 px band is 6
