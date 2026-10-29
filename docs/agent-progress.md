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

## Next-step checks (2026-10-29)

- Hybrid LLM step (implemented 2026-10-29): `videotrans/ocr/_llm_reconcile.py` builds the prompt from `prompts/srt/hybrid_reconcile.txt` with the target language set to the source language (no double translation), calls Gemini once for the whole list, and parses one text per block. `_stage_recogn.py` (`_llm_reconciled_texts`) uses it in hybrid mode. Without a Gemini key, or on error, it falls back to Whisper text and shows a status message.
  - Live check on the Vietnamese clip (first 60 s, 17 blocks): returned 17 blocks 1-to-1, with useful fixes (`tắt` to `tắc`, `topping`). Before the guard it shortened blocks (one 2-sentence block lost its second sentence) and renamed `Nhi` to `tôi`.
  - Guard added (`guard_reconciled`): a block falls back to the Whisper text when the LLM text is under 60% of the Whisper length, or when a capitalised word from the Whisper text (not the first word) is missing from the LLM text. Re-run live: the name `Nhi` is kept, and the shortened 2-sentence block is restored in full.
  - Remaining risk: the guard does not catch meaning changes that keep the length and names, for example `đổ nó soi vô` to `đổ nước sôi vô`, `nợ` to `nở`, and `dính luôn` to `không bị`. The LLM output should be reviewed before use in dubbing; the step is opt-in (hybrid mode with a Gemini key).
  - Unit tests: 13 pass (prompt, parse, guard).
  - Meaning check (added 2026-10-29): a second Gemini call (`judge_with_gemini`) compares each changed block with the Whisper text and answers OK or CHANGED. CHANGED blocks fall back to Whisper text. If the judge call fails, the whole LLM output is discarded and Whisper text is used.
  - Live check of the judge on known cases: CHANGED for `soi` to `nước sôi`, `nợ` to `nở`, `dính luôn` to `không bị dính` (all three meaning changes caught). OK for `tắt` to `tắc` and `ngọc yến` to `Ngọc Yến`. One false positive: `Cộng một cái` to `Thêm` (reverts to Whisper, which is the safe default).
  - Still missed: `tất pin gì bỏ vô tất pin đó` rewritten as `có tất cả các loại pin gì thì bỏ pin đó vô` was marked OK. The judge is an LLM and not a guarantee.
  - Word-level similarity was tested as a second, non-LLM layer. It does not separate the cases (`soi` to `nước sôi` scored 0.74, `tất pin` to `topping` scored 0.57), so it is not used.
  - Full chain check on six blocks: the `soi/nợ` block reverted to Whisper; the others were accepted.
- Switched to minimal edits (2026-10-29, approved). The LLM now proposes `original | replacement` pairs (`prompts/srt/hybrid_edit.txt`), not full rewrites. Code applies a pair only when the original occurs exactly once in the Whisper text. The old full-rewrite prompt (`hybrid_reconcile.txt`) is no longer used.
  - Live check on the six known blocks with the new flow: no meaning drift. One edit applied (`muối ngọc yến … → muối Ngọc Yến …`). The `tất pin → topping` fix was proposed but skipped: `tất pin` appears twice in that block, and the model did not use the longer phrase the prompt asks for. This is a deliberate trade-off: safer, but it misses some correct fixes.
  - Judge and guard are still applied to changed blocks.
  - Unit tests: 23 pass.
- LLM step is optional (decided 2026-10-29): setting `hybrid_llm_enabled` in `params.json`, default `False`. Only blocks with on-screen OCR text are sent to the LLM; other blocks keep Whisper text. No settings-dialog toggle exists yet; the setting is edited in `params.json`.
- Measured on 15 random blocks from the Vietnamese clip (seed 20261029), labelled by the user:
  - Whisper text matches the label on 10 of 15. Final output after the LLM step also matches 10 of 15.
  - The LLM proposed two edits on these blocks: `tấm bên → temp` (wrong) and removal of `tức` (wrong). The judge reverted both. No correct fix was applied.
  - Cause: the edit prompt needs OCR evidence, and this video has burned-in text only in roughly 0–30 s (checked by frame sampling; no text at 40 s). Most labelled blocks come from 30–60 s, so there was nothing to correct against.
  - Labels that need a decision: block 6 is much shorter than the Whisper text (the label drops `Muối tôi đang xài là muối ngọc yến`); block 17's `topping` has no on-screen evidence and is an audio ambiguity.
  - Missed corrections: `nợ → nở` (block 4), `tắt → cắt` (block 9), `tỏi/hành` (block 13), `tất pin → topping` (block 2 area, repeated phrase).
  - Unit tests for prompt building and response parsing: 8 pass.
- Erase modes, rendered with the real `_build_subtitle_filter` on the Vietnamese clip, area `(0.68, 0.98)`:
  - Mode 1 (Gaussian blur): original recipe text unreadable; clean edges.
  - Mode 2 (Cinema Box): was 75% alpha, so the original text stayed faintly visible. Changed to fully opaque (`black@1.0`, approved 2026-10-29). Re-rendered: the original text is fully hidden and the new subtitle is still visible.
  - Mode 3 (Delogo): text removed, with visible horizontal and vertical streak artifacts in the area.
- Erase default area changed to `(0.68, 0.98, 0.05, 0.95)` in params, task config, UI fallbacks and the erase filter (approved 2026-10-29). Erase colour and crop-dialog starting values were not changed.

## End-to-end dubbing run (2026-10-29)

- Command: `cli.py --task vtv` on the 60 s Vietnamese clip. Recognition Whisper `large-v3-turbo` (CPU), translation Gemini (provider 6, `gemini-2.5-flash-lite`), dubbing Piper (`en_US-lessac-medium`).
- Result: 17 subtitle blocks translated, 17 dubbed, final MP4 62.6 s with video and dubbed audio. Dubbed audio loudness equals the standalone dubbed track. Whisper on the English track reads the translated sentences back correctly; proper names are transliterated (`ngak yen salt`).
- Bug found and fixed: the Gemini translator used the legacy Interactions API, which the server now rejects (HTTP 400: "legacy Interactions API schema is no longer supported"). Migrated to `models.generate_content`, with `ThinkingConfig(thinking_level="high")` kept for gemini-3/4/flash models. Full suite: 506 PASS, no new failures.
- Gemini TTS (`videotrans/tts/_geminitts.py`) migrated to `generate_content` with `response_modalities=["AUDIO"]` and a prebuilt voice (2026-10-29). Live check: 4.28 s of non-silent audio for one sentence (voice Kore, model from settings). Spoken content not checked with ASR.
- Gemini speech recognition (`videotrans/recognition/_gemini.py`) migrated to segment timestamps (2026-10-29, option 1). The model returns a JSON array of `{start, end, text}`; word times are spread across each segment by word length, then the existing resegmenting runs. Helpers `parse_segments` and `segments_to_words` have 10 unit tests.
  - Live run on the 60 s Vietnamese clip with `gemini-2.5-flash-lite`: 17 subtitle items; the transcript has punctuation and corrects several Whisper errors (`nước sôi`, `nở`, `cắt ớt tươi`, `topping`).
  - Default Gemini ASR model changed from `gemini-3.5-transcribe` (returns empty text through `generate_content`) to `gemini-2.5-flash-lite` (approved 2026-10-29), in `GEMINI_ASR_MODELS`.

## Persisted settings and default changes (2026-10-29)

- Found: `videotrans/params.json` (git-ignored, the user's own settings) keeps values saved from earlier defaults. The stored `ocr_crop_box` and `erase_sub_area` were still `(0.75, 0.96, 0.05, 0.95)`, which overrode the new defaults in code, so the UI showed the old boxes. Both were updated to `(0.68, 0.98, 0.05, 0.95)` on this machine because they still held the old default, not a user choice.
- Keys missing from `params.json` (for example `vieneu_python`) take the code default at runtime, so they work without editing the file.
- Migration added (`PREVIOUS_DEFAULTS` and `migrate_stored_defaults` in `_app_params.py`): a stored value is replaced by the current default only when it still equals the previous default. Covers `ocr_crop_box` and `erase_sub_area`. Tests: 4 pass. Add a key there whenever a default changes.
- VieNeu settings window: menu item "VieNeu-TTS (Local)" in the TTS menu opens `ui/vieneu.py` / `winform/vieneu.py`. It sets the `vieneu_python` path (with a file picker) and saves it to `params.json`. Checked offscreen: the window opens with the saved path.
- Test video: `D:\___TOOLS\__TINIX\Tinix Video Dubbing\output_test\en_to_vi_vieneu_dub.mp4` (48.66 s, dubbed Vietnamese with VieNeu) and `en_to_vi_vieneu_dub.vi.srt`. The source is a downloaded clip of someone else's video, used for local testing only.

## VieNeu-TTS channel (2026-10-29, approved)

- New TTS channel `VIENEU_TTS = 41` ("VieNeu-TTS(Local)", `videotrans/tts/_vieneu.py`). It calls a long-lived worker (`videotrans/tts/_vieneu_worker.py`) that runs in the VieNeu-TTS Python environment, so the project venv does not get the VieNeu dependencies. The worker loads the model once (about 55 s), then answers JSON requests over stdin/stdout.
- Setting `vieneu_python` in `params.json` points to `D:/___TOOLS/__TINIX/Tinix-VieNeu-TTS/VieNeu-TTS/.venv/Scripts/python.exe` (machine-specific default). Worker logs go to `logs/vieneu_worker.log`.
- Voices: 20 preset voices (`VIENEU_ROLES`), default `Phạm Tuyên`. Output is 48 kHz WAV.
- Checks: worker synthesis of two Vietnamese sentences (3.36 s, not silent). English to Vietnamese end-to-end on a 45 s clip: translation with Gemini, 15/15 dubbed with VieNeu, final video 48.66 s with dubbed audio. Whisper transcribes the dubbed Vietnamese audio with the translated content. Tests: 3 channel tests pass; full suite 516 PASS, no new failures.

## English to Vietnamese dubbing run (2026-10-29)

- Input: 45 s English clip. Recognition Whisper `large-v3-turbo` (CPU). Translation Gemini (`gemini-2.5-flash-lite`) to Vietnamese: 15 blocks, natural Vietnamese (`vi.srt`). Works.
- Dubbing blocked: Gemini TTS free tier allows 10 requests per day for `gemini-3.1-flash-tts`, and the daily quota was used up. Gemini TTS also allows 3 requests per minute; `_geminitts.py` now waits 21 s and retries on HTTP 429 (up to 5 tries). Edge-TTS still returns 403. The project has no Vietnamese Piper voice.
- Next: a Vietnamese TTS channel with quota (Gemini TTS on a later day with a short clip of 10 blocks or fewer, a paid Gemini TTS tier, or integrating a local Vietnamese TTS such as VieNeu-TTS from `Tinix-VieNeu-TTS`).

## Hybrid LLM step: removed (2026-10-29)

Removed from the pipeline: `videotrans/ocr/_llm_reconcile.py`, the prompts `hybrid_reconcile.txt` and `hybrid_edit.txt`, the `_llm_reconciled_texts` call in the recognition stage, the `hybrid_llm_enabled` setting, and the tests. Hybrid mode now uses the Whisper-first reconciler only (no LLM call).

Reason: on the 15 labelled blocks the step applied no correct fix and proposed two wrong edits (both reverted by the meaning check). Its design needs on-screen OCR evidence, and the test video has burned-in text only in roughly 0–30 s. The errors it could not fix were audio errors with no on-screen evidence. Git history keeps the code if it is needed again.

The bullets above that describe the LLM step are kept as the record of what was tested.

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
3. Only if a new need appears: a model that flags uncertain Whisper blocks (low confidence) and is measured on a labelled set before use. The earlier LLM step was removed (see below).
4. Review the new Vietnamese strings with a native speaker.
