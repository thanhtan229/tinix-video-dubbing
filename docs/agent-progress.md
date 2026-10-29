# Agent Progress

Updated: 2026-10-29

## Current milestone

`main` holds the OCR, hybrid recognition and Gemini work on top of upstream navigation. Pushed to `https://github.com/thanhtan229/tinix-video-dubbing` (branch `main`). The upstream repo `jianchang512/pyvideotrans` was not touched (no write access).

## Completed

- OCR subtitle extraction validated on a synthetic clip (`Hello world`, `Second line`).
- Integration of `origin/main` with the local work. Upstream navigation kept; OCR/hybrid recognition, erase mode and Gemini changes re-applied.
- 260 keys missing from `vi.json` translated (`vi.json` now 1243 keys). Placeholders checked against en_US.
- `unified_settings_dialog.py` removed (not referenced anywhere).
- Git history rewritten to drop large files (`ffmpeg.zip`, `ffmpeg/ffmpeg.zip`, `pretrained_models.zip`, `pretrained_models/`, `pretrained_models0/`). Only the remote `tinix` was force-pushed. Pre-rewrite backup bundle: `D:\___TOOLS\__TINIX\_backups\pyvideotrans_pre_rewrite_20261028_2228\repo-all.bundle`.
- Gemini live check with the configured key and model `gemini-2.5-flash-lite`: model list returned 60 models; a short generate call returned `OK`. The key was not printed.
- Reconciler noise filter: OCR results with fewer than two visible characters are dropped (`_reconciler.py`).
- OCR overlay token filter (`_is_overlay_token` in `_rapidocr.py`): tokens that mix digits and letters without a 3+ lowercase run, or are all-caps 2–4 letters outside a short acronym list, are removed. Applied to the real-clip frames it removes mostly overlay fragments (`IMA`, `MIN`, `90m`, `210m`) and keeps merged subtitle words such as `andworks24/7tohelpyou`. Other on-screen text in the video (for example `Savory Bread-ish`) is not overlay noise and is kept.
- OCR line confidence filter: lines with RapidOCR score below `MIN_LINE_SCORE = 0.85` are dropped (`_rapidocr.py`, `filter_ocr_lines`). On the real 45 s clip (dump of 194 frames) this keeps about 98% of subtitle-band lines and drops about 63% of overlay lines. End-to-end OCR on the same clip went from 35 items to 32, with overlay-only entries removed.

## Real-video check (2026-10-29)

Source: a local downloaded video with speech and a burned-in subtitle at about 76% of frame height. Trimmed to 45 s for the test. Clip not kept or shared.

- Whisper (`large-v3-turbo`, CPU): accurate, 15 segments with punctuation.
- OCR: very noisy. A persistent overlay near the bottom of the frame is read as text (for example `SIMA HObE 2MA380`), and the real subtitle is read with merged or wrong words. Both crop boxes tested gave similar noise.
- The earlier reconciler change that replaced merged Whisper segments with OCR text made the hybrid output worse than Whisper alone on this video. It was reverted: Whisper text is kept for every segment, and OCR text is attached as context.
- The wider OCR crop default `(0.68, 0.98)` did not help on this video (38 items against 35, similar noise). It was reverted to `(0.75, 0.96, 0.05, 0.95)`. The clean synthetic clip did read better with the wider box; this trade-off is not resolved.

## Real-clip OCR with the token filter (2026-10-29)

Full OCR on the 45 s clip at default settings, with confidence and token filters: 33 items. Sample: `Alright,big day:`, `today we arelaunching Muse`, `and works24/7tohelpyouachieve.them HObE`, `Muse doesn'tjustanswer questions Ise`. Most overlay-only entries are gone. Residual mixed-case fragments remain (`HObE`, `HQbE`, `ISIMA`); the token rule only covers all-caps fragments up to four letters. The count moved from 32 to 33 between runs because items are grouped by time, not because the filter added items.

## Test videos from D:\_Delete\New folder (16) (2026-10-29)

- `7642712970581101844.mp4` (Vietnamese cooking video, 117 s, 720x1280, speech, burned-in recipe text). First 60 s tested. Whisper with `vi` gave an accurate 17-segment transcript. The recipe text sits at about 70–89% of frame height.
- Crop default `(0.75, 0.96)` misses the first recipe line (about 70–73% height): 35 frames with text. Wider `(0.68, 0.98)` reads it: 60 frames with text. Overlay-free lines match the recipe text.
- `抖音2026623-297677.mp4` (Douyin ad, Chinese caption, 45 s). Not analysed further: little subtitle text.
- Mixed-case token rule (3+ uppercase, 5 letters or fewer): on the English clip it would drop only `myMMA`, a real word. On the Vietnamese clip it drops nothing. Not added.
- The English clip favours the wider box once the confidence and token filters are on: 191 frames with text against 173, and it reads the first line `Alright,big day:` that the default misses.
- Decision (approved 2026-10-29): OCR crop default changed to `(0.68, 0.98, 0.05, 0.95)` in params, task config, UI fallbacks and OCR functions. Evidence from both real clips with the filters on. Earlier reverts were measured before the filters.

## Verification

- Full suite: **496 passed, 123 failed**. The 123 failures also occur on upstream `origin/main`; the branch introduced **0 new failures** (compared per test id).
- `tests/test_custom_api_url.py` and `tests/test_winform_split.py` are excluded: they import modules that do not exist upstream.
- OCR, reconciler and noise-filter tests: 41 passed.
- Main window constructs offscreen; recognition mode (3 items) and erase mode (4 items) present with defaults.
- Not run: Edge-TTS and Google Translate live calls; the hybrid LLM step.

## Known gaps

- OCR quality on real videos is improved but not solved. Overlay fragments are removed by the confidence and token filters, but some garbage can still remain on frames with heavy overlay, and subtitle words are sometimes merged. OCR text is only used as context in the hybrid path, so Whisper remains the text source.
- On the clean synthetic clip the default crop `(0.75, 0.96)` cuts the top of the second subtitle; with the confidence filter that line is now dropped rather than shown as garbage.
- The OCR crop default is unresolved: a tighter band around the real subtitle may be better than either tested box, but this was not measured.
- `videotrans/styles/style.qss` takes upstream's version; local styling for the new controls is not carried over.
- The 260 new Vietnamese strings were written by the agent and have not been reviewed by a native speaker.

## Blockers and notes

- Edge-TTS returned HTTP 403 and Google Translate Free returned HTTP 429 earlier; these providers remain unverified.
- Set `--target_language_code` for TTS tests. Set `PYTHONUTF8=1` on this Windows environment for CLI output with Vietnamese text.
- `models/models--mobiuslabsgmbh--faster-whisper-large-v3-turbo` (1.6 GB) was downloaded by the app during the hybrid check. `models/` is git-ignored.
- Local `origin/*` refs still hold upstream history containing the removed large files. They are local-only and not pushed.
- Another workspace holds branch `fix/ocr-pipeline-reviewed-20261028` (worktree under `C:/Users/Admin/.paseo/worktrees/013oxf38/ocr-review-fix`). It was not touched.
- OCR is slow on this machine: about 6 minutes for 45 s of video at default settings.

## Recommended next steps

1. Handle mixed-case overlay fragments that the current token rule misses (for example `HObE`, `HQbE` and `ISIMA`). Not added yet: the only local clip with real subtitle text is the 45 s speech clip. The two other distinct local videos (product ads in `Tinix-Facebook-Hunter/_DOWNLOAD/_TINIX`) have no subtitle-band text above the confidence threshold, so they cannot test the rule. Needs more videos with real speech and hardsubs.
2. Decide the OCR crop default by measuring a tighter band around the real subtitle on several videos.
3. Run the hybrid LLM step on a short segment to check its effect on text quality.
4. Review the new Vietnamese strings with a native speaker.
