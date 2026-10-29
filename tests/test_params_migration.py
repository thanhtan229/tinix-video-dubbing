"""Stored default migration: old defaults are replaced, user-chosen values are kept."""

from videotrans.configure._app_params import migrate_stored_defaults

OLD = [0.75, 0.96, 0.05, 0.95]
NEW = [0.68, 0.98, 0.05, 0.95]


def test_old_default_is_replaced_by_current_default():
    loaded = {"ocr_crop_box": list(OLD)}
    defaults = {"ocr_crop_box": list(NEW)}
    assert migrate_stored_defaults(loaded, defaults)["ocr_crop_box"] == NEW


def test_user_chosen_value_is_kept():
    custom = [0.5, 0.9, 0.1, 0.9]
    loaded = {"erase_sub_area": list(custom)}
    defaults = {"erase_sub_area": list(NEW)}
    assert migrate_stored_defaults(loaded, defaults)["erase_sub_area"] == custom


def test_missing_key_is_not_added():
    loaded = {}
    defaults = {"ocr_crop_box": list(NEW)}
    assert migrate_stored_defaults(loaded, defaults) == {}


def test_unrelated_keys_are_untouched():
    loaded = {"gemini_model": "x", "ocr_crop_box": list(OLD)}
    defaults = {"ocr_crop_box": list(NEW), "gemini_model": "y"}
    out = migrate_stored_defaults(loaded, defaults)
    assert out["gemini_model"] == "x"
