# -*- coding: utf-8 -*-
from videotrans.configure.config import app_cfg


class WinformMixin:
    _active_tool_window = None

    def open_winform(self, name):
        from videotrans.util.help_misc import show_refaudio_win

        # Modal Dialogs
        if name == 'set_ass':
            from videotrans.component.set_ass import ASSStyleDialog
            dialog = ASSStyleDialog(self)
            dialog.exec()
            return
        if name == 'refaudio':
            show_refaudio_win()
            return
        if name == 'xxl':
            from videotrans.component.set_xxl import SetFasterXXL
            dialog = SetFasterXXL(self)
            dialog.exec()
            return

        # Unified Settings Hub for all API and system configs
        CONFIG_NAMES = {
            "chatgpt", "gemini", "deepseek", "azure", "azuretts", "elevenlabs",
            "cosyvoice", "gptsovits", "chatterbox", "setini", "deepL", "deepLX",
            "tencent", "baidu", "ali", "openrouter", "proxy", "libre", "ai302",
            "localllm", "zijiehuoshan", "zhipuai", "siliconflow", "minimax",
            "minimaxi", "fishtts", "cambtts", "parakeet", "doubao2", "general",
            "asr", "whisper"
        }

        if name in CONFIG_NAMES:
            from videotrans.component.unified_settings_dialog import UnifiedSettingsDialog
            dialog = UnifiedSettingsDialog(parent=self, initial_target=name)
            dialog.exec()
            return

        # Check existing cached child form first
        winobj = app_cfg.child_forms.get(name)
        if winobj:
            if hasattr(winobj, 'update_ui'):
                try:
                    winobj.update_ui()
                except Exception:
                    pass
            winobj.show()
            winobj.raise_()
            winobj.activateWindow()
            WinformMixin._active_tool_window = winobj
            return winobj

        # Standalone components
        if name == 'clipvideo':
            from videotrans.component.clip_video import ClipVideoWindow
            window = ClipVideoWindow()
            app_cfg.child_forms[name] = window
            WinformMixin._active_tool_window = window
            window.show()
            window.raise_()
            window.activateWindow()
            return window
        if name == 'textmatching':
            from videotrans.component.textmatching import TextmatchingWindow
            window = TextmatchingWindow()
            app_cfg.child_forms[name] = window
            WinformMixin._active_tool_window = window
            window.show()
            window.raise_()
            window.activateWindow()
            return window
        if name == 'realtime_stt':
            from videotrans.component.realtime_stt import RealTimeWindow
            window = RealTimeWindow()
            app_cfg.child_forms[name] = window
            WinformMixin._active_tool_window = window
            window.show()
            window.raise_()
            window.activateWindow()
            return window
        if name == 'format_srtfiles_folders':
            from videotrans.component.format_srtfiles_folders import FormatSrtFilesFolders
            window = FormatSrtFilesFolders()
            app_cfg.child_forms[name] = window
            WinformMixin._active_tool_window = window
            window.show()
            window.raise_()
            window.activateWindow()
            return window

        from videotrans import winform
        tool_module = winform.get_win(name)
        if tool_module:
            tool_win = tool_module.openwin()
            if tool_win:
                app_cfg.child_forms[name] = tool_win
                tool_win.show()
                tool_win.raise_()
                tool_win.activateWindow()
                WinformMixin._active_tool_window = tool_win
            return tool_win
