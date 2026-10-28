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
- Gemini live check with the configured key and model `gemini-2.5-flash-lite`: model list returned 60 models; a short generate call returned `OK`. The key itself was not printed.
- Hybrid components run end-to-end on a synthetic clip (`hybrid_test.mp4`: video from `sub.mp4`, audio from the Piper WAV, subtitles burned in). Whisper (`large-v3-turbo`, CPU) produced one segment, `hello world  second line`. OCR produced `Hello world` and `C Second line` (a stray `C` artifact). `align_and_reconcile_transcripts` merged them into one entry using the Whisper text. No LLM step was run.
- Not run: Edge-TTS and Google Translate live calls.

## Known gaps

- `videotrans/styles/style.qss` takes upstream's version; local styling for the new controls is not carried over.
- The 260 new Vietnamese strings were written by the agent and have not been reviewed by a native speaker.
- Hybrid mode: OCR failures are reported in the status line and the run continues with Whisper output.
- Hybrid output after the reconciler fix (`_reconciler.py`): a Whisper segment that spans two on-screen lines is split into one entry per OCR line, using OCR text and timing. On the synthetic clip this gives `Hello world` (0–3.36 s) and `C Second line` (3.36–4.36 s). The stray `C` is still there because it is part of the same OCR line; a single-character filter only removes standalone items. Not fixed.
- Whisper timing is lost for split segments (entries use OCR timing), so the hybrid path now relies on OCR quality for those lines.

## Blockers and notes

- Edge-TTS returned HTTP 403 and Google Translate Free returned HTTP 429 earlier; these providers remain unverified.
- Set `--target_language_code` for TTS tests. Set `PYTHONUTF8=1` on this Windows environment for CLI output with Vietnamese text.
- `models/models--mobiuslabsgmbh--faster-whisper-large-v3-turbo` (1.6 GB) was downloaded by the app during the hybrid check. `models/` is git-ignored.
- Local `origin/*` refs still hold upstream history containing the removed large files. They are local-only and not pushed.
- Another workspace holds branch `fix/ocr-pipeline-reviewed-20261028` (worktree under `C:/Users/Admin/.paseo/worktrees/013oxf38/ocr-review-fix`). It was not touched.

## Recommended next steps

1. Remove the stray leading character in OCR lines (for example `C Second line`), or confirm it is caused by the crop box and fix the box.
2. Run the hybrid check on a real hardsubbed video with natural speech, not the synthetic clip.
3. Review the new Vietnamese strings with a native speaker.

## References

- Feature commits: `ed0f41c8` (hybrid Whisper + video OCR), `847f178b` (recognition UI and settings), `ac41b666` (RapidOCR dependencies and startup branding).
- Smoke-test inputs and outputs are temporary files under `%LOCALAPPDATA%\Temp\ocr_smoke` and are not part of the repository.
