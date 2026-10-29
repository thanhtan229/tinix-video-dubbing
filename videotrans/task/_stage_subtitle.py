import json
import os
from pathlib import Path
from typing import Union

from videotrans import translator
from videotrans.configure.config import tr, ROOT_DIR, settings, logger
from videotrans.configure import constants
from videotrans.configure.excepts import VideoTransError
from videotrans.util.help_srt import get_subtitle_from_srt, simple_wrap, set_ass_font
from videotrans.util._srt_wrap import one_line_capacity, split_one_line
from videotrans.util.tools import ms_to_time_string


class SubtitleMixin:

    def _process_subtitles(self) -> Union[tuple[str, str], None]:
        logger.debug(f"\n======准备要嵌入的字幕:{self.cfg.subtitle_type=}===={self.cfg.target_sub=}=")
        if not Path(self.cfg.target_sub).exists() :
            raise VideoTransError(tr("No valid subtitle file exists")+self.cfg.target_sub)

        if not Path(self.cfg.source_sub).exists() or (self.cfg.source_language_code == self.cfg.target_language_code):
            if self.cfg.subtitle_type == 3:
                self.cfg.subtitle_type = 1
            elif self.cfg.subtitle_type == 4:
                self.cfg.subtitle_type = 2

        process_end_subtitle = self.cfg.cache_folder + f'/end.srt'
        maxlen = int(
            settings.get('cjk_len', 15) if self.cfg.target_language_code[:2] in constants.CJK_LANG else
            settings.get('other_len', 60))
        target_sub_list = get_subtitle_from_srt(self.cfg.target_sub)

        # Burned-in (hard) subtitles on non-CJK targets: one line per block, sized to the frame.
        one_line = self.cfg.subtitle_type == 1 and self.cfg.target_language_code[:2] not in constants.CJK_LANG
        if one_line:
            maxlen = one_line_capacity(int(self.video_info.get('width', 1920) or 1920),
                                       int(self.video_info.get('height', 1080) or 1080))

        srt_string = ""
        _join_flag = ''
        if self.cfg.subtitle_type in [3, 4]:
            source_sub_list = get_subtitle_from_srt(self.cfg.source_sub)
            source_length = len(source_sub_list)
            source_maxlen = int(
                settings.get('cjk_len', 15) if self.cfg.source_language_code.split('-')[0] in constants.CJK_LANG   else
                settings.get('other_len', 60))

            _join_flag = self._get_join_flag()

            for i, it in enumerate(target_sub_list):
                _text = simple_wrap(it['text'].strip(), maxlen, self.cfg.target_language_code)
                srt_string += f"{it['line']}\n{it['time']}\n"
                if source_length > 0 and i < source_length:
                    _text_source = simple_wrap(source_sub_list[i]['text'], source_maxlen,
                                                     self.cfg.source_language_code)
                    _text = f'{_text_source}\n{_join_flag}{_text}' if self.cfg.output_srt == 1 else f'{_text}\n{_join_flag}{_text_source}'
                srt_string += f"{_text}\n\n"
            srt_string = srt_string.strip()
            process_end_subtitle = f"{self.cfg.cache_folder}/shuang.srt"
            Path(process_end_subtitle).write_text(srt_string, encoding='utf-8')
            Path(self.cfg.target_dir + "/shuang.srt").write_text(
                srt_string.replace('###', '') if _join_flag == '###' else srt_string, encoding='utf-8')
        else:
            _idx = 0
            for i, it in enumerate(target_sub_list):
                if one_line:
                    # Each piece is one line; long blocks become consecutive pieces with proportional time.
                    for p_start, p_end, p_text in split_one_line(it['text'].strip(), it['start_time'],
                                                                 it['end_time'], maxlen,
                                                                 self.cfg.target_language_code):
                        _idx += 1
                        srt_string += f"{_idx}\n{ms_to_time_string(ms=p_start)} --> {ms_to_time_string(ms=p_end)}\n{p_text}\n\n"
                    continue
                tmp = simple_wrap(it['text'].strip(), maxlen, self.cfg.target_language_code)
                srt_string += f"{it['line']}\n{it['time']}\n{tmp.strip()}\n\n"
            with Path(process_end_subtitle).open('w', encoding='utf-8') as f:
                f.write(srt_string)

        subtitle_langcode = translator.get_subtitle_code(show_target=self.cfg.target_language)
        logger.debug(
            f'最终确定字幕嵌入类型:{self.cfg.subtitle_type} ,目标字幕语言:{subtitle_langcode}, 字幕文件:{process_end_subtitle}\n')
        if self.cfg.subtitle_type in [2, 4]:
            return os.path.basename(process_end_subtitle), subtitle_langcode

        # With source removal on, the subtitle goes where the source subtitle was.
        margin_v = None
        if self.cfg.subtitle_type == 1 and self.cfg.erase_sub_mode:
            if self.cfg.erase_sub_area is None:
                from videotrans.ocr._rapidocr import detect_subtitle_area
                self.cfg.erase_sub_area = detect_subtitle_area(self.cfg.name)
            if self.cfg.erase_sub_area is not None:
                margin_v = band_margin_v(self.cfg.erase_sub_area)
        process_end_subtitle_ass = set_ass_font(process_end_subtitle, margin_v=margin_v)
        basename = os.path.basename(process_end_subtitle_ass)
        return basename, subtitle_langcode

    def _get_join_flag(self):
        _join_flag = ""
        if self.cfg.subtitle_type != 3 or not Path(f'{ROOT_DIR}/videotrans/ass.json').exists():
            return _join_flag
        try:
            assjson = json.loads(Path(f'{ROOT_DIR}/videotrans/ass.json').read_text(encoding='utf-8'))
        except Exception:
            logger.warning(f'未自定义样式 ass.json ，忽略')
            return _join_flag
        else:
            for k, v in assjson.items():
                if k.startswith('Bottom_') and v != assjson.get(k[7:]):
                    _join_flag = '###'
                    break
        return _join_flag
