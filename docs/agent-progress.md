# Agent Progress

Updated: 2026-10-28

## Current milestone

`main` holds the OCR, hybrid recognition and Gemini work on top of upstream navigation. Pushed to `https://github.com/thanhtan229/tinix-video-dubbing` (branch `main`). The upstream repo `jianchang512/pyvideotrans` was not touched (no write access).

## Completed

- OCR subtitle extraction validated on the smoke clip: `Hello world` (0–3.12 s) and `Second line` (3.12–6.00 s).
- Integration of `origin/main` with the local work. Upstream navigation kept; OCR/hybrid recognition, erase mode and Gemini changes re-applied.
- 260 keys missing from `vi.json` translated (`vi.json` now 1243 keys). Placeholders checked against en_US.
- `unified_settings_dialog.py` removed (not referenced anywhere).
- Git history rewritten to drop large files (`ffmpeg.zip`, `ffmpeg/ffmpeg.zip`, `pretrained_models.zip`, `pretrained_models/`, `pretrained_models0/`). Only the remote `tinix` was force-pushed (`41193cf9` → `5ba28194`). Pre-rewrite backup bundle: `D:\___TOOLS\__TINIX\_backups\pyvideotrans_pre_rewrite_20261028_2228\repo-all.bundle`.
- TTS stage verified with local Piper (`--tts_type 7`, voice `en_US-lessac-medium`): 2/2 lines, WAV 4.36 s, non-silent. Content not listened to; not aligned to SRT timings.

## Verification

- Full suite: **490 passed, 123 failed**. The 123 failures also occur on upstream `origin/main`; the merge introduced **0 new failures** (compared per test id).
- `tests/test_custom_api_url.py` and `tests/test_winform_split.py` are excluded: they import modules that do not exist upstream.
- OCR and reconciler tests: 35 passed.
- Main window constructs offscreen; recognition mode (3 items) and erase mode (4 items) present with defaults.
- Not run: live provider calls (Gemini, Edge-TTS, Google Translate); hybrid recognition end-to-end.

## Known gaps

- `videotrans/styles/style.qss` takes upstream's version; local styling for the new controls is not carried over.
- The 260 new Vietnamese strings were written by the agent and have not been reviewed by a native speaker.
- Hybrid mode: OCR failures are reported in the status line and the run continues with Whisper output. Not exercised end-to-end.

## Blockers and notes

- Edge-TTS returned HTTP 403 and Google Translate Free returned HTTP 429 earlier; these providers remain unverified.
- Set `--target_language_code` for TTS tests. Set `PYTHONUTF8=1` on this Windows environment for CLI output with Vietnamese text.
- `models/` is empty, so no faster-whisper model is available locally.
- Local `origin/*` refs still hold upstream history containing the removed large files. They are local-only and not pushed.
- Another workspace holds branch `fix/ocr-pipeline-reviewed-20261028` (worktree under `C:/Users/Admin/.paseo/worktrees/013oxf38/ocr-review-fix`). It was not touched.

## Recommended next steps

1. Download a faster-whisper model and run a real hybrid recognition job on a hardsubbed clip.
2. Test the Gemini key flow against the live API when a key is available.
3. Transcribe the Piper output and compare it with the source SRT.
4. Review the new Vietnamese strings with a native speaker.

## References

- Feature commits: `ed0f41c8` (hybrid Whisper + video OCR), `847f178b` (recognition UI and settings), `ac41b666` (RapidOCR dependencies and startup branding).
- Smoke-test inputs and outputs are temporary files under `%LOCALAPPDATA%\Temp\ocr_smoke` and are not part of the repository.
