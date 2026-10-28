# Agent Progress

Updated: 2026-10-28

## Current milestone

Integration branch `integrate/origin-main` contains `origin/main` merged with the local OCR, hybrid recognition and Gemini work. Not pushed. `main` is unchanged.

## Completed

- OCR subtitle extraction validated on the smoke clip (`Hello world`, `Second line`).
- Commits on `main` before integration: `c6bc2f78` (OCR span/SRT fixes), `670c5b8d` (Gemini model refresh and test), `dad9928d` (this file).
- Integration merge `65d7cae7` on `integrate/origin-main`: upstream navigation kept; OCR/hybrid recognition, erase mode, Gemini changes re-applied. Details in the commit message.
- TTS stage verified with local Piper (`--tts_type 7`, voice `en_US-lessac-medium`): 2/2 lines, WAV 4.36 s, non-silent. Content not listened to; not aligned to SRT timings.

## Verification (on `integrate/origin-main`)

- Full suite: **490 passed, 123 failed**. The 123 failures also occur on `origin/main`; the merge introduced **0 new failures** (compared per test id).
- `tests/test_custom_api_url.py` and `tests/test_winform_split.py` are excluded: they import modules that do not exist upstream.
- OCR and reconciler tests: 35 passed.
- Main window constructs offscreen; recognition mode (3 items) and erase mode (4 items) present with defaults.
- Not run: any live provider calls (Gemini, Edge-TTS, Google Translate).

## Known gaps

- `tr()` falls back to en_US for keys missing from `vi.json`. 260 en_US keys are not yet translated into Vietnamese and show in English.
- Local tab navigation and unified settings hub were dropped in favour of upstream navigation. `videotrans/component/unified_settings_dialog.py` remains in the tree but is not wired to any menu, so its Gemini model refresh and Test button are unreachable.
- `videotrans/styles/style.qss` takes upstream's version; local styling for the new controls is not carried over.
- Hybrid mode: OCR failures are reported in the status line and the run continues with Whisper output. Not exercised end-to-end on a real hybrid job.

## Blockers and notes

- Edge-TTS returned HTTP 403 and Google Translate Free returned HTTP 429 earlier; these providers remain unverified.
- Set `--target_language_code` for TTS tests. Set `PYTHONUTF8=1` on this Windows environment for CLI output with Vietnamese text.
- Another workspace holds branch `fix/ocr-pipeline-reviewed-20261028` (worktree under `C:/Users/Admin/.paseo/worktrees/013oxf38/ocr-review-fix`). It was not touched.

## Recommended next steps

1. Review the integration commit and decide whether to fast-forward `main` to `integrate/origin-main` or keep it separate. Push only on explicit request.
2. Decide whether to restore the unified settings hub on upstream navigation, or delete `unified_settings_dialog.py`.
3. Translate the 260 untranslated keys into `vi.json`.
4. Run a real hybrid recognition job on a hardsubbed clip and check the output.
5. Test the Gemini key flow against the live API when a key is available.

## References

- Feature commits: `ed0f41c8` (hybrid Whisper + video OCR), `847f178b` (recognition UI and settings), `ac41b666` (RapidOCR dependencies and startup branding).
- Smoke-test inputs and outputs are temporary files under `%LOCALAPPDATA%\Temp\ocr_smoke` and are not part of the repository.
