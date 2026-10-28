from pathlib import Path

from videotrans import translator, recognition, tts
from videotrans.configure import contants
from videotrans.configure.config import tr, settings, app_cfg
from videotrans.util.help_misc import show_error
from videotrans.util.help_role import role_menu


class WinActionConfigMixin:

    def recogn_mode_change(self):
        mode = self.main.recogn_mode.currentIndex()
        self.main.recogn_mode_val = mode
        params['recogn_mode'] = mode
        params.save()

        if mode == 1:
            # OCR only
            self.main.btn_crop_box.setVisible(True)
            self.main.recogn_type.setVisible(False)
            self.main.model_name.setVisible(False)
            self.main.model_name_help.setVisible(False)
        elif mode == 2:
            # Hybrid
            self.main.btn_crop_box.setVisible(True)
            self.main.recogn_type.setVisible(True)
            self.main.model_name.setVisible(True)
            self.main.model_name_help.setVisible(True)
        else:
            # Whisper only
            self.main.btn_crop_box.setVisible(False)
            self.main.recogn_type.setVisible(True)
            self.main.model_name.setVisible(True)
            self.main.model_name_help.setVisible(True)

    def open_crop_dialog(self):
        from videotrans.component.crop_subtitle_dialog import CropSubtitleDialog
        from PySide6.QtWidgets import QMessageBox

        video_path = ""
        if hasattr(self, 'queue_mp4') and self.queue_mp4:
            video_path = self.queue_mp4[0]

        if not video_path or not Path(video_path).is_file():
            QMessageBox.information(
                self.main,
                tr("Thông báo"),
                tr("Vui lòng chọn hoặc kéo thả video vào phần mềm trước để xem trước khung hình chọn vùng phụ đề.")
            )
            return

        current_box = getattr(self.main, 'ocr_crop_box_val', (0.75, 0.96, 0.05, 0.95))
        dialog = CropSubtitleDialog(video_path=video_path, current_box=current_box, parent=self.main)
        if dialog.exec():
            new_box = dialog.get_crop_box()
            self.main.ocr_crop_box_val = new_box
            params['ocr_crop_box'] = list(new_box)
            params.save()
            QMessageBox.information(
                self.main,
                tr("Thành công"),
                tr("Đã lưu vùng quét phụ đề OCR: Đáy {0}% -> {1}%, Trái {2}% -> {3}%").format(
                    int(new_box[0] * 100), int(new_box[1] * 100),
                    int(new_box[2] * 100), int(new_box[3] * 100)
                )
            )

    def erase_sub_mode_change(self):
        mode = self.main.erase_sub_mode.currentIndex()
        self.main.erase_sub_mode_val = mode
        params['erase_sub_mode'] = mode
        params.save()

        if mode > 0:
            self.main.btn_erase_area.setVisible(True)
        else:
            self.main.btn_erase_area.setVisible(False)

    def open_erase_dialog(self):
        from videotrans.component.crop_subtitle_dialog import CropSubtitleDialog
        from PySide6.QtWidgets import QMessageBox

        video_path = ""
        if hasattr(self, 'queue_mp4') and self.queue_mp4:
            video_path = self.queue_mp4[0]

        if not video_path or not Path(video_path).is_file():
            QMessageBox.information(
                self.main,
                tr("Thông báo"),
                tr("Vui lòng chọn hoặc kéo thả video vào phần mềm trước để xem trước khung hình chọn vùng phụ đề.")
            )
            return

        current_box = getattr(self.main, 'erase_sub_area_val', (0.75, 0.96, 0.05, 0.95))
        dialog = CropSubtitleDialog(video_path=video_path, current_box=current_box, parent=self.main)
        dialog.setWindowTitle(tr("Chọn vùng phụ đề cũ cần xóa / làm mờ"))
        if dialog.exec():
            new_box = dialog.get_crop_box()
            self.main.erase_sub_area_val = new_box
            params['erase_sub_area'] = list(new_box)
            params.save()
            QMessageBox.information(
                self.main,
                tr("Thành công"),
                tr("Đã lưu vùng xóa/làm mờ phụ đề cũ: Đáy {0}% -> {1}%, Trái {2}% -> {3}%").format(
                    int(new_box[0] * 100), int(new_box[1] * 100),
                    int(new_box[2] * 100), int(new_box[3] * 100)
                )
            )

    def show_xxl_select(self):
        import sys
        if sys.platform != 'win32':
            show_error(
                tr("faster-whisper-xxl.exe is only available on Windows"))
            return False
        xxl_path = settings.get('Faster_Whisper_XXL', '')
        if not xxl_path or not Path(xxl_path).exists():
            from videotrans.component.set_xxl import SetFasterXXL
            dialog = SetFasterXXL()
            if dialog.exec():
                xxl_path = dialog.get_values()
                if xxl_path and Path(xxl_path).is_file():
                    return True
            show_error(
                tr("Must be selected, otherwise it cannot be used"))
            return False
        return True

    def recogn_type_change(self):
        recogn_type = self.main.recogn_type.currentIndex()
        if recogn_type == recognition.Faster_Whisper_XXL and not self.show_xxl_select():
            return

        if recogn_type not in [recognition.FASTER_WHISPER, recognition.OPENAI_WHISPER, recognition.Faster_Whisper_XXL,
                               recognition.FUNASR_CN, recognition.Deepgram, recognition.Whisper_CPP,
                               recognition.WHISPERX_API, recognition.HUGGINGFACE_ASR, recognition.QWENASR,
                               recognition.WHISPER_NET]:

            self.main.model_name.setDisabled(True)
            self.main.model_name_help.setDisabled(True)
        else:
            self.main.model_name_help.setDisabled(False)
            self.main.model_name.setDisabled(False)
            self.main.model_name.clear()
            if recogn_type in [recognition.FASTER_WHISPER, recognition.OPENAI_WHISPER, recognition.Faster_Whisper_XXL,
                               recognition.WHISPERX_API]:
                self.main.model_name.addItems(
                    settings.WHISPER_MODEL_LIST if recogn_type != recognition.OPENAI_WHISPER else contants.Openai_Whisper_Models.split(','))
            elif recogn_type == recognition.Deepgram:
                self.main.model_name.addItems(contants.DEEPGRAM_MODEL)
            elif recogn_type == recognition.Whisper_CPP:
                self.main.model_name.addItems(settings.Whisper_CPP_MODEL_LIST)
            elif recogn_type == recognition.WHISPER_NET:
                self.main.model_name.addItems(settings.Whisper_NET_MODEL_LIST)

            elif recogn_type == recognition.QWENASR:
                self.main.model_name.addItems(recognition.get_model_by_type(recognition.QWENASR))
            elif recogn_type == recognition.HUGGINGFACE_ASR:
                self.main.model_name.addItems(list(recognition.HUGGINGFACE_ASR_MODELS.keys()))
            else:
                self.main.model_name.addItems(contants.FUNASR_MODEL)

        lang = translator.get_code(show_text=self.main.source_language.currentText())

        is_allow_lang = recognition.is_allow_lang(langcode=lang, recogn_type=recogn_type,
                                                  model_name=self.main.model_name.currentText())
        
        self.main.show_tips.setText(str(is_allow_lang) if is_allow_lang is not True else '')

        if recognition.is_input_api(recogn_type=recogn_type) is not True:
            return

    def model_type_change(self):
        lang = translator.get_code(show_text=self.main.source_language.currentText())
        recogn_type = self.main.recogn_type.currentIndex()
        is_allow_lang = recognition.is_allow_lang(langcode=lang, recogn_type=recogn_type,
                                                  model_name=self.main.model_name.currentText())
        self.main.show_tips.setText(str(is_allow_lang) if is_allow_lang is not True else '')

    def tts_type_change(self, type):

        lang = translator.get_code(show_text=self.main.target_language.currentText())
        if lang and lang != '-':
            is_allow_lang = tts.is_allow_lang(langcode=lang, tts_type=type)            
            self.main.show_tips.setText(str(is_allow_lang) if is_allow_lang is not True else '')

        app_cfg.line_roles = {}
        _role_list = role_menu(type, lang if lang and lang != '-' else None)
        self.main.voice_role.clear()
        self.main.current_rolelist = _role_list
        self.main.voice_role.addItems(self.main.current_rolelist)
        if tts.is_input_api(tts_type=type) is not True:
            return

    def set_voice_role(self, t):
        role = self.main.voice_role.currentText()
        code = translator.get_code(show_text=t)
        if code and code != '-':
            is_allow_lang = tts.is_allow_lang(langcode=code, tts_type=self.main.tts_type.currentIndex())
            self.main.show_tips.setText(str(is_allow_lang) if is_allow_lang is not True else '')
            
            if translator.is_allow_translate(translate_type=self.main.translate_type.currentIndex(),
                                             show_target=t) is not True:
                return
        if self.main.tts_type.currentIndex() not in tts.CHANGE_BY_LANGUAGE:
            if role != 'No' and self.main.app_mode in ['biaozhun']:
                self.main.listen_btn.show()
                self.main.listen_btn.setDisabled(False)
            else:
                self.main.listen_btn.hide()
            return

        self.main.voice_role.clear()
        if t == '-' or not code:
            self.main.voice_role.addItems(['No'])
            return

        _role_list = role_menu(self.main.tts_type.currentIndex(), code.split('-')[0])
        self.main.current_rolelist = _role_list
        self.main.voice_role.addItems(_role_list)
