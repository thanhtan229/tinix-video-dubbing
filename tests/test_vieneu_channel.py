"""VieNeu-TTS channel registration and voice list (no model load, no network)."""

from videotrans.configure import constants
from videotrans.tts import _constants as tts_constants
from videotrans.util import help_role


def test_channel_is_registered_with_expected_module():
    provider = tts_constants.ID_NAME_DICT[tts_constants.VIENEU_TTS]
    assert provider.name == "VieNeu-TTS(Local)"
    assert provider.imp == "._vieneu"


def test_channel_id_does_not_collide_with_other_channels():
    ids = [k for k in tts_constants.ID_NAME_DICT if k == tts_constants.VIENEU_TTS]
    assert ids == [tts_constants.VIENEU_TTS]


def test_voice_list_matches_constant_and_includes_default():
    voices = constants.VIENEU_ROLES.split(",")
    assert len(voices) == 20
    assert "Phạm Tuyên" in voices
    assert help_role.role_menu(tts_constants.VIENEU_TTS, "vi") == voices
