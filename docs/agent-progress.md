# Agent Progress

Updated: 2026-10-28

## Current milestone

OCR subtitle extraction → TTS handoff validated locally. Integration with `origin/main` is pending a strategy decision.

## Completed

- OCR subtitle extraction produced an SRT from the smoke-test clip: two entries, `Hello world` and `Second line`.
- Committed `c6bc2f78` — fix(ocr): span timing, SRT clock strings, end-time cap; regression tests in `tests/test_ocr_rapidocr.py`.
- Committed `670c5b8d` — feat(gemini): model list refresh, connection test (30s timeout), API key masking in messages.
- Full project test suite on the committed tree: **508 passed** (`tests/`, run with `.venv`).
- TTS stage verified with local provider Piper (`--tts_type 7`, voice `en_US-lessac-medium`): 2/2 subtitle lines dubbed, WAV produced (4.36 s, 48 kHz stereo, non-silent). Content not listened to; audio is not aligned to SRT timings (no `--align_sub_audio`).

## Active changes

- `docs/agent-progress.md` (this file) — not yet committed at time of writing.
- Branch `main`: 12 commits ahead of local `origin/main` ref, 169 behind. No pull, rebase, merge or push performed.

## Integration with origin/main (dry run only)

`git merge-tree` shows conflicts in at least: `pyproject.toml`, `tests/test_contants.py`, `videotrans/configure/_app_params.py`, `_app_settings.py`, `_i18n.py`, `videotrans/mainwin/_bind_signals.py`, `_winform.py`, `videotrans/ui/*`, `videotrans/translator/_gemini.py`, plus modify/delete conflicts on `tests/test_stt_fun_split.py` and `videotrans/language/en.json`. The `origin/main` ref was not re-fetched in this session.

## Blockers and notes

- Edge-TTS returned HTTP 403 and Google Translate Free returned HTTP 429 earlier; these external providers remain unverified.
- Set `--target_language_code` when testing TTS; the voice locale otherwise fails to resolve.
- On this Windows environment set `PYTHONUTF8=1` for the CLI to avoid `charmap` errors when printing Vietnamese text.
- The Gemini translation path has not been exercised against the live API in this session.

## Recommended next step

1. Decide the integration strategy with `origin/main` (merge into a separate integration branch, or rebase). Resolve conflicts there and re-run the full suite before any push.
2. Re-run the Gemini Test button against a real key when available.
3. Listen to or transcribe the Piper output to confirm dubbed content matches the source SRT.

## References

- Feature commits: `ed0f41c8` (hybrid Whisper + video OCR), `847f178b` (recognition UI and settings), `ac41b666` (RapidOCR dependencies and startup branding).
- Smoke-test inputs and outputs are temporary files under `%LOCALAPPDATA%\Temp\ocr_smoke` and are not part of the repository.
