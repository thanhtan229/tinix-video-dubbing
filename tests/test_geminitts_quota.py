"""Gemini TTS: daily quota errors are not retried; per-minute errors are."""

from videotrans.tts._geminitts import is_daily_quota_error


def test_daily_quota_is_detected():
    msg = "Quota exceeded for metric: ..., limit: 10 ... Generate content requests per day limit exceeded"
    assert is_daily_quota_error(msg)


def test_per_minute_quota_is_not_daily():
    msg = "Quota exceeded ... Generate content requests per minute limit exceeded on Free Tier"
    assert not is_daily_quota_error(msg)


def test_empty_message_is_not_daily():
    assert not is_daily_quota_error("")
