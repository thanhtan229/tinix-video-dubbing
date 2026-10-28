# -*- coding: utf-8 -*-
import os
from pathlib import Path
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt, QSize, QThread, Signal
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QStackedWidget, QWidget, QLabel, QLineEdit, QComboBox, QSpinBox,
    QDoubleSpinBox, QCheckBox, QPushButton, QGroupBox, QFormLayout,
    QPlainTextEdit, QMessageBox, QFileDialog, QScrollArea
)

from videotrans.configure.config import tr, params, settings, app_cfg, ROOT_DIR


class GeminiModelListTask(QThread):
    models_found = Signal(list)
    failed = Signal(str)

    def __init__(self, api_key: str, proxy: str = "", parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.proxy = proxy

    def run(self):
        client = None
        try:
            from google import genai
            from google.genai import types

            client_args = {"proxy": self.proxy} if self.proxy else None
            client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(
                    timeout=30_000,
                    client_args=client_args,
                    async_client_args=client_args,
                ),
            )
            models = set()
            for model in client.models.list():
                actions = {str(action).lower() for action in (model.supported_actions or [])}
                if "generatecontent" not in actions or not model.name:
                    continue
                name = model.name.removeprefix("models/")
                models.add(name)
            self.models_found.emit(sorted(models, key=str.casefold))
        except Exception as exc:
            message = str(exc)
            for key in self.api_key.split(","):
                key = key.strip()
                if key:
                    message = message.replace(key, "[hidden]")
            self.failed.emit(message)
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass


class UnifiedSettingsDialog(QDialog):
    """
    Centralized Unified Settings Hub for Tinix Video Dubbing.
    Consolidates 40+ separate API & Tool popups into a single modern sidebar interface.
    """

    def __init__(self, parent=None, initial_target=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Trung Tâm Cài Đặt & Cấu Hình AI - Tinix Video Dubbing"))
        self.setWindowIcon(QIcon(f"{ROOT_DIR}/videotrans/styles/icon.ico"))
        self.resize(880, 620)
        self.setMinimumSize(800, 540)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # ---------------- Left Sidebar ----------------
        self.sidebar = QListWidget(self)
        self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet("""
            QListWidget {
                background-color: #161E26;
                border: 1px solid #384956;
                border-radius: 8px;
                padding: 6px;
            }
            QListWidget::item {
                padding: 10px 12px;
                border-radius: 6px;
                margin-bottom: 4px;
                font-weight: 500;
                color: #DFE1E2;
            }
            QListWidget::item:hover {
                background-color: #212C36;
                color: #FFFFFF;
            }
            QListWidget::item:selected {
                background-color: #124548;
                color: #FFFFFF;
                border-left: 3px solid #FF4800;
                font-weight: 600;
            }
        """)

        # Add Sidebar categories
        items_meta = [
            ("🌐  " + tr("Dịch thuật AI"), "trans"),
            ("🎙️  " + tr("Lồng tiếng AI (TTS)"), "tts"),
            ("🎧  " + tr("Nhận dạng & OCR"), "asr"),
            ("⚙️  " + tr("Cài đặt chung & Mạng"), "general"),
        ]
        for label, code in items_meta:
            it = QListWidgetItem(label)
            it.setData(Qt.UserRole, code)
            self.sidebar.addItem(it)

        main_layout.addWidget(self.sidebar)

        # ---------------- Right Content Area ----------------
        right_container = QVBoxLayout()
        right_container.setSpacing(10)

        self.stack = QStackedWidget(self)
        self.stack.setStyleSheet("background-color: #19232D;")

        # Page 0: Translation APIs
        self.page_trans = self._create_translation_page()
        self.stack.addWidget(self.page_trans)

        # Page 1: TTS APIs
        self.page_tts = self._create_tts_page()
        self.stack.addWidget(self.page_tts)

        # Page 2: ASR & OCR
        self.page_asr = self._create_asr_page()
        self.stack.addWidget(self.page_asr)

        # Page 3: General & Network
        self.page_general = self._create_general_page()
        self.stack.addWidget(self.page_general)

        right_container.addWidget(self.stack, stretch=1)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 4, 0, 0)

        self.btn_reset = QPushButton(tr("Khôi phục mặc định"))
        self.btn_reset.clicked.connect(self._reset_current_page)

        self.btn_close = QPushButton(tr("Đóng"))
        self.btn_close.clicked.connect(self.reject)

        self.btn_save = QPushButton(tr("💾 Lưu Cài Đặt"))
        self.btn_save.setProperty("primary", True)
        self.btn_save.clicked.connect(self._save_all_settings)

        btn_layout.addWidget(self.btn_reset)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_close)
        btn_layout.addWidget(self.btn_save)

        right_container.addLayout(btn_layout)
        main_layout.addLayout(right_container, stretch=1)

        # Signals
        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

        # Target routing
        if initial_target:
            self.route_to_target(initial_target)

    # ---------------- PAGE 1: TRANSLATION ----------------
    def _create_translation_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 0, 8, 0)

        top_box = QHBoxLayout()
        top_box.addWidget(QLabel(tr("Kênh Dịch thuật AI:")), 0)
        self.cb_trans_provider = QComboBox()
        self.cb_trans_provider.addItems([
            "Google Gemini", "DeepSeek", "OpenAI ChatGPT", "Azure OpenAI",
            "DeepL", "OpenRouter", "Zhipu AI (GLM)", "Tencent Hunyuan",
            "Baidu Translate", "Alibaba Qwen-MT", "SiliconFlow",
            "Local LLM (Ollama/vLLM)", "LibreTranslate", "AI302", "MiniMax"
        ])
        top_box.addWidget(self.cb_trans_provider, 1)
        layout.addLayout(top_box)

        # Stacked provider forms
        self.trans_substack = QStackedWidget()

        # 0: Gemini
        self.trans_substack.addWidget(self._make_gemini_trans_form())
        # 1: DeepSeek
        self.trans_substack.addWidget(self._make_deepseek_trans_form())
        # 2: ChatGPT
        self.trans_substack.addWidget(self._make_chatgpt_trans_form())
        # 3: Azure
        self.trans_substack.addWidget(self._make_azure_trans_form())
        # 4: DeepL
        self.trans_substack.addWidget(self._make_deepl_trans_form())
        # 5: OpenRouter
        self.trans_substack.addWidget(self._make_openrouter_trans_form())
        # 6: Zhipu
        self.trans_substack.addWidget(self._make_zhipu_trans_form())
        # 7: Tencent
        self.trans_substack.addWidget(self._make_tencent_trans_form())
        # 8: Baidu
        self.trans_substack.addWidget(self._make_baidu_trans_form())
        # 9: Alibaba
        self.trans_substack.addWidget(self._make_ali_trans_form())
        # 10: SiliconFlow
        self.trans_substack.addWidget(self._make_siliconflow_trans_form())
        # 11: LocalLLM
        self.trans_substack.addWidget(self._make_localllm_trans_form())
        # 12: LibreTranslate
        self.trans_substack.addWidget(self._make_libre_trans_form())
        # 13: AI302
        self.trans_substack.addWidget(self._make_ai302_trans_form())
        # 14: MiniMax
        self.trans_substack.addWidget(self._make_minimax_trans_form())

        self.cb_trans_provider.currentIndexChanged.connect(self.trans_substack.setCurrentIndex)
        layout.addWidget(self.trans_substack, 1)
        return widget

    # Provider Subforms
    def _make_gemini_trans_form(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)
        self.txt_gemini_key = QLineEdit(params.get('gemini_key', ''))
        self.txt_gemini_key.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        self.cb_gemini_model = QComboBox()
        self.cb_gemini_model.setMinimumWidth(220)
        current_model = str(params.get('gemini_model', 'gemini-2.0-flash')).strip()
        if current_model:
            self.cb_gemini_model.addItem(current_model)
        self.btn_gemini_refresh_models = QPushButton(tr("Quét / Refresh"))
        self.btn_gemini_refresh_models.clicked.connect(self._refresh_gemini_models)
        model_row = QHBoxLayout()
        model_row.addWidget(self.cb_gemini_model, 1)
        model_row.addWidget(self.btn_gemini_refresh_models)
        self.sp_gemini_token = QSpinBox()
        self.sp_gemini_token.setRange(1024, 65536)
        self.sp_gemini_token.setValue(int(params.get('gemini_maxtoken', 32768)))
        self.btn_gemini_test = QPushButton(tr("Test"))
        self.btn_gemini_test.clicked.connect(self._test_gemini)
        f.addRow("API Key:", self.txt_gemini_key)
        f.addRow(tr("Tên mô hình (Model):"), model_row)
        f.addRow(tr("Max Output Tokens:"), self.sp_gemini_token)
        f.addRow("", self.btn_gemini_test)
        return w

    def _refresh_gemini_models(self):
        key = self.txt_gemini_key.text().strip().split(",", 1)[0].strip()
        if not key:
            QMessageBox.warning(self, tr("Gemini AI"), tr("Please enter a Gemini API key first."))
            return

        task = getattr(self, "_gemini_models_task", None)
        if task is not None and task.isRunning():
            return

        self.btn_gemini_refresh_models.setEnabled(False)
        self.btn_gemini_refresh_models.setText(tr("Scanning..."))
        task = GeminiModelListTask(key, proxy=app_cfg.proxy or "", parent=self.parent())
        task.models_found.connect(self._on_gemini_models_found)
        task.failed.connect(self._on_gemini_models_failed)
        task.finished.connect(self._on_gemini_models_finished)
        task.finished.connect(task.deleteLater)
        self._gemini_models_task = task
        task.start()

    def _on_gemini_models_found(self, models: list):
        if not models:
            QMessageBox.information(
                self,
                tr("Gemini AI"),
                tr("No models supporting content generation were returned for this API key."),
            )
            return

        current_model = self.cb_gemini_model.currentText()
        self.cb_gemini_model.clear()
        self.cb_gemini_model.addItems(models)
        if current_model in models:
            self.cb_gemini_model.setCurrentText(current_model)
        QMessageBox.information(
            self,
            tr("Gemini AI"),
            tr("Found %1 supported models.").replace("%1", str(len(models))),
        )

    def _on_gemini_models_failed(self, message: str):
        QMessageBox.critical(self, tr("Gemini AI"), message)

    def _on_gemini_models_finished(self):
        self.btn_gemini_refresh_models.setEnabled(True)
        self.btn_gemini_refresh_models.setText(tr("Quét / Refresh"))
        self._gemini_models_task = None

    def _test_gemini(self):
        key = self.txt_gemini_key.text().strip()
        if not key:
            QMessageBox.warning(self, tr("Gemini AI"), tr("Please enter a Gemini API key first."))
            return

        task = getattr(self, "_gemini_test_task", None)
        if task is not None and task.isRunning():
            return

        # Save the values being tested so the existing translator uses the current form values.
        params['gemini_key'] = key
        params['gemini_model'] = self.cb_gemini_model.currentText().strip()
        params['gemini_maxtoken'] = self.sp_gemini_token.value()
        params.save()

        from videotrans.translator import GEMINI_INDEX
        from videotrans.util.TestSrtTrans import TestSrtTrans

        self.btn_gemini_test.setEnabled(False)
        self.btn_gemini_test.setText(tr("Testing..."))
        task = TestSrtTrans(parent=self.parent(), translator_type=GEMINI_INDEX)
        task.uito.connect(self._on_gemini_test_result)
        task.finished.connect(self._on_gemini_test_finished)
        task.finished.connect(task.deleteLater)
        self._gemini_test_task = task
        task.start()

    def _on_gemini_test_result(self, message: str):
        # A provider error may echo request details; keep the configured key out of the dialog.
        keys = [key.strip() for key in self.txt_gemini_key.text().split(",") if key.strip()]
        safe_message = message
        for key in keys:
            safe_message = safe_message.replace(key, "[hidden]")
        if safe_message.startswith("ok"):
            QMessageBox.information(self, tr("Gemini AI"), safe_message[3:])
        else:
            QMessageBox.critical(self, tr("Gemini AI"), safe_message)

    def _on_gemini_test_finished(self):
        self.btn_gemini_test.setEnabled(True)
        self.btn_gemini_test.setText(tr("Test"))
        self._gemini_test_task = None

    def _make_deepseek_trans_form(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)
        self.txt_deepseek_key = QLineEdit(params.get('deepseek_key', ''))
        self.txt_deepseek_key.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        self.txt_deepseek_model = QLineEdit(params.get('deepseek_model', 'deepseek-chat'))
        self.chk_deepseek_think = QCheckBox(tr("Bật chế độ suy nghĩ (DeepSeek Reasoner)"))
        self.chk_deepseek_think.setChecked(bool(params.get('deepseek_thinking', False)))
        f.addRow("API Key:", self.txt_deepseek_key)
        f.addRow(tr("Tên mô hình (Model):"), self.txt_deepseek_model)
        f.addRow("", self.chk_deepseek_think)
        return w

    def _make_chatgpt_trans_form(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)
        self.txt_chatgpt_key = QLineEdit(params.get('chatgpt_key', ''))
        self.txt_chatgpt_key.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        self.txt_chatgpt_api = QLineEdit(params.get('chatgpt_api', ''))
        self.txt_chatgpt_api.setPlaceholderText("https://api.openai.com/v1")
        self.txt_chatgpt_model = QLineEdit(params.get('chatgpt_model', 'gpt-4o-mini'))
        f.addRow("API Key:", self.txt_chatgpt_key)
        f.addRow(tr("Base URL (Tùy chọn):"), self.txt_chatgpt_api)
        f.addRow(tr("Tên mô hình (Model):"), self.txt_chatgpt_model)
        return w

    def _make_azure_trans_form(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)
        self.txt_azure_key = QLineEdit(params.get('azure_key', ''))
        self.txt_azure_key.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        self.txt_azure_api = QLineEdit(params.get('azure_api', ''))
        self.txt_azure_api.setPlaceholderText("https://your-resource.openai.azure.com/")
        self.txt_azure_model = QLineEdit(params.get('azure_model', 'gpt-4o'))
        self.txt_azure_ver = QLineEdit(params.get('azure_version', '2024-02-01'))
        f.addRow("Azure Key:", self.txt_azure_key)
        f.addRow("Endpoint URL:", self.txt_azure_api)
        f.addRow("Deployment Name:", self.txt_azure_model)
        f.addRow("API Version:", self.txt_azure_ver)
        return w

    def _make_deepl_trans_form(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)
        self.txt_deepl_key = QLineEdit(params.get('deepl_authkey', ''))
        self.txt_deepl_key.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        self.txt_deepl_api = QLineEdit(params.get('deepl_api', ''))
        self.txt_deepl_api.setPlaceholderText("https://api-free.deepl.com/v2/translate")
        f.addRow("Auth Key:", self.txt_deepl_key)
        f.addRow("API URL:", self.txt_deepl_api)
        return w

    def _make_openrouter_trans_form(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)
        self.txt_openrouter_key = QLineEdit(params.get('openrouter_key', ''))
        self.txt_openrouter_key.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        self.txt_openrouter_model = QLineEdit(params.get('openrouter_model', 'openai/gpt-4o-mini'))
        f.addRow("API Key:", self.txt_openrouter_key)
        f.addRow("Model Name:", self.txt_openrouter_model)
        return w

    def _make_zhipu_trans_form(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)
        self.txt_zhipu_key = QLineEdit(params.get('zhipu_key', ''))
        self.txt_zhipu_model = QLineEdit(params.get('zhipu_model', 'glm-4-flash'))
        f.addRow("API Key:", self.txt_zhipu_key)
        f.addRow("Model Name:", self.txt_zhipu_model)
        return w

    def _make_tencent_trans_form(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)
        self.txt_tencent_id = QLineEdit(params.get('tencent_SecretId', ''))
        self.txt_tencent_key = QLineEdit(params.get('tencent_SecretKey', ''))
        self.txt_tencent_key.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        f.addRow("Secret ID:", self.txt_tencent_id)
        f.addRow("Secret Key:", self.txt_tencent_key)
        return w

    def _make_baidu_trans_form(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)
        self.txt_baidu_id = QLineEdit(params.get('baidu_appid', ''))
        self.txt_baidu_key = QLineEdit(params.get('baidu_miyue', ''))
        self.txt_baidu_key.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        f.addRow("App ID:", self.txt_baidu_id)
        f.addRow("Mật khẩu/Key:", self.txt_baidu_key)
        return w

    def _make_ali_trans_form(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)
        self.txt_ali_id = QLineEdit(params.get('ali_id', ''))
        self.txt_ali_key = QLineEdit(params.get('ali_key', ''))
        self.txt_ali_key.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        f.addRow("AccessKey ID:", self.txt_ali_id)
        f.addRow("AccessKey Secret:", self.txt_ali_key)
        return w

    def _make_siliconflow_trans_form(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)
        self.txt_silicon_key = QLineEdit(params.get('siliconflow_key', ''))
        self.txt_silicon_model = QLineEdit(params.get('siliconflow_model', 'deepseek-ai/DeepSeek-V3'))
        f.addRow("API Key:", self.txt_silicon_key)
        f.addRow("Model Name:", self.txt_silicon_model)
        return w

    def _make_localllm_trans_form(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)
        self.txt_localllm_api = QLineEdit(params.get('localllm_api', 'http://127.0.0.1:11434/v1'))
        self.txt_localllm_key = QLineEdit(params.get('localllm_key', 'ollama'))
        self.txt_localllm_model = QLineEdit(params.get('localllm_model', 'qwen2.5:7b'))
        f.addRow("Local API URL:", self.txt_localllm_api)
        f.addRow("API Key:", self.txt_localllm_key)
        f.addRow("Model Name:", self.txt_localllm_model)
        return w

    def _make_libre_trans_form(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)
        self.txt_libre_api = QLineEdit(params.get('libre_address', 'http://127.0.0.1:5000'))
        self.txt_libre_key = QLineEdit(params.get('libre_key', ''))
        f.addRow("Server URL:", self.txt_libre_api)
        f.addRow("API Key (Tùy chọn):", self.txt_libre_key)
        return w

    def _make_ai302_trans_form(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)
        self.txt_ai302_key = QLineEdit(params.get('ai302_key', ''))
        self.txt_ai302_model = QLineEdit(params.get('ai302_model', 'gpt-4o-mini'))
        f.addRow("API Key:", self.txt_ai302_key)
        f.addRow("Model Name:", self.txt_ai302_model)
        return w

    def _make_minimax_trans_form(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)
        self.txt_minimax_id = QLineEdit(params.get('minimax_groupid', ''))
        self.txt_minimax_key = QLineEdit(params.get('minimax_api_key', ''))
        f.addRow("Group ID:", self.txt_minimax_id)
        f.addRow("API Key:", self.txt_minimax_key)
        return w

    # ---------------- PAGE 2: TTS APIS ----------------
    def _create_tts_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 0, 8, 0)

        top_box = QHBoxLayout()
        top_box.addWidget(QLabel(tr("Dịch vụ Lồng tiếng AI (TTS):")), 0)
        self.cb_tts_provider = QComboBox()
        self.cb_tts_provider.addItems([
            "Azure AI Speech (TTS)", "ElevenLabs.io", "CosyVoice (Local API)",
            "GPT-SoVITS (Local API)", "ChatterBox TTS", "F5-TTS", "MiniMax TTS"
        ])
        top_box.addWidget(self.cb_tts_provider, 1)
        layout.addLayout(top_box)

        self.tts_substack = QStackedWidget()
        self.tts_substack.addWidget(self._make_azure_tts_form())
        self.tts_substack.addWidget(self._make_elevenlabs_form())
        self.tts_substack.addWidget(self._make_cosyvoice_form())
        self.tts_substack.addWidget(self._make_gptsovits_form())
        self.tts_substack.addWidget(self._make_chatterbox_form())
        self.tts_substack.addWidget(self._make_f5tts_form())
        self.tts_substack.addWidget(self._make_minimax_tts_form())

        self.cb_tts_provider.currentIndexChanged.connect(self.tts_substack.setCurrentIndex)
        layout.addWidget(self.tts_substack, 1)
        return widget

    def _make_azure_tts_form(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)
        self.txt_azure_tts_key = QLineEdit(params.get('azure_tts_key', ''))
        self.txt_azure_tts_key.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        self.txt_azure_tts_region = QLineEdit(params.get('azure_tts_region', 'eastus'))
        f.addRow("Subscription Key:", self.txt_azure_tts_key)
        f.addRow("Region (Vùng):", self.txt_azure_tts_region)
        return w

    def _make_elevenlabs_form(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)
        self.txt_eleven_key = QLineEdit(params.get('elevenlabs_key', ''))
        self.txt_eleven_key.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        self.txt_eleven_model = QLineEdit(params.get('elevenlabs_model', 'eleven_multilingual_v2'))
        f.addRow("API Key:", self.txt_eleven_key)
        f.addRow("Model ID:", self.txt_eleven_model)
        return w

    def _make_cosyvoice_form(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)
        self.txt_cosy_api = QLineEdit(params.get('cosyvoice_api', 'http://127.0.0.1:9233'))
        f.addRow("CosyVoice API URL:", self.txt_cosy_api)
        return w

    def _make_gptsovits_form(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)
        self.txt_sovits_api = QLineEdit(params.get('gptsovits_address', 'http://127.0.0.1:9880'))
        f.addRow("GPT-SoVITS API URL:", self.txt_sovits_api)
        return w

    def _make_chatterbox_form(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)
        self.txt_chatter_api = QLineEdit(params.get('chatterbox_api', 'http://127.0.0.1:8000'))
        f.addRow("ChatterBox API URL:", self.txt_chatter_api)
        return w

    def _make_f5tts_form(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)
        lbl = QLabel(tr("F5-TTS là mô hình nhân bản giọng nói chạy trực tiếp trong ứng dụng. Bạn có thể chọn giọng mẫu tại danh sách vai đọc."))
        lbl.setWordWrap(True)
        f.addRow("", lbl)
        return w

    def _make_minimax_tts_form(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)
        self.txt_minimax_tts_id = QLineEdit(params.get('minimaxi_groupid', ''))
        self.txt_minimax_tts_key = QLineEdit(params.get('minimaxi_api_key', ''))
        f.addRow("Group ID:", self.txt_minimax_tts_id)
        f.addRow("API Key:", self.txt_minimax_tts_key)
        return w

    # ---------------- PAGE 3: ASR & OCR ----------------
    def _create_asr_page(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)

        self.txt_whisper_threads = QSpinBox()
        self.txt_whisper_threads.setRange(1, 32)
        self.txt_whisper_threads.setValue(int(settings.get('whisper_threads', 4)))

        self.chk_vad = QCheckBox(tr("Sử dụng Silero VAD lọc khoảng lặng âm thanh"))
        self.chk_vad.setChecked(bool(settings.get('vad', True)))

        self.sp_ocr_fps = QDoubleSpinBox()
        self.sp_ocr_fps.setRange(1.0, 15.0)
        self.sp_ocr_fps.setValue(4.0)
        self.sp_ocr_fps.setSuffix(" fps")

        f.addRow(tr("Số luồng xử lý CPU (Faster-Whisper):"), self.txt_whisper_threads)
        f.addRow("", self.chk_vad)
        f.addRow(tr("Tốc độ lấy mẫu khung hình OCR (Sample FPS):"), self.sp_ocr_fps)
        return w

    # ---------------- PAGE 4: GENERAL & NETWORK ----------------
    def _create_general_page(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)

        self.txt_proxy = QLineEdit(app_cfg.proxy or params.get('proxy', ''))
        self.txt_proxy.setPlaceholderText("http://127.0.0.1:7890 hoặc socks5://127.0.0.1:1080")

        self.txt_output_dir = QLineEdit(params.get('output_dir', ''))
        self.txt_output_dir.setPlaceholderText(tr("Mặc định lưu vào thư mục _video_out cùng vị trí video"))

        self.sp_crf = QSpinBox()
        self.sp_crf.setRange(0, 51)
        self.sp_crf.setValue(int(settings.get('crf', 23)))
        self.sp_crf.setToolTip(tr("Hệ số CRF (0-51): 18-23 là chất lượng hình ảnh cao và tối ưu dung lượng."))

        self.cb_preset = QComboBox()
        self.cb_preset.addItems(["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow"])
        self.cb_preset.setCurrentText(settings.get('preset', 'veryfast'))

        f.addRow(tr("Proxy Mạng:"), self.txt_proxy)
        f.addRow(tr("Thư mục xuất mặc định:"), self.txt_output_dir)
        f.addRow(tr("Chất lượng Video (CRF):"), self.sp_crf)
        f.addRow(tr("Tốc độ mã hóa (Preset):"), self.cb_preset)
        return w

    # ---------------- ROUTING HELPER ----------------
    def route_to_target(self, target_name: str):
        target = str(target_name).lower().strip()
        trans_map = {
            "gemini": (0, 0), "deepseek": (0, 1), "chatgpt": (0, 2), "openai": (0, 2),
            "azure": (0, 3), "deepl": (0, 4), "openrouter": (0, 5), "zhipuai": (0, 6),
            "zhipu": (0, 6), "tencent": (0, 7), "baidu": (0, 8), "ali": (0, 9),
            "siliconflow": (0, 10), "localllm": (0, 11), "libre": (0, 12),
            "ai302": (0, 13), "minimax": (0, 14)
        }
        tts_map = {
            "azuretts": (1, 0), "elevenlabs": (1, 1), "cosyvoice": (1, 2),
            "gptsovits": (1, 3), "chatterbox": (1, 4), "clone": (1, 5),
            "fishtts": (1, 5), "minimaxi": (1, 6)
        }

        if target in trans_map:
            cat_idx, sub_idx = trans_map[target]
            self.sidebar.setCurrentRow(cat_idx)
            self.cb_trans_provider.setCurrentIndex(sub_idx)
        elif target in tts_map:
            cat_idx, sub_idx = tts_map[target]
            self.sidebar.setCurrentRow(cat_idx)
            self.cb_tts_provider.setCurrentIndex(sub_idx)
        elif target in ["proxy", "setini", "general"]:
            self.sidebar.setCurrentRow(3)
        elif target in ["asr", "whisper", "recogn"]:
            self.sidebar.setCurrentRow(2)

    # ---------------- SAVE & RESET ----------------
    def _save_all_settings(self, show_msg=True):
        # Gemini
        params['gemini_key'] = self.txt_gemini_key.text().strip()
        params['gemini_model'] = self.cb_gemini_model.currentText().strip()
        params['gemini_maxtoken'] = self.sp_gemini_token.value()

        # DeepSeek
        params['deepseek_key'] = self.txt_deepseek_key.text().strip()
        params['deepseek_model'] = self.txt_deepseek_model.text().strip()
        params['deepseek_thinking'] = self.chk_deepseek_think.isChecked()

        # ChatGPT
        params['chatgpt_key'] = self.txt_chatgpt_key.text().strip()
        params['chatgpt_api'] = self.txt_chatgpt_api.text().strip()
        params['chatgpt_model'] = self.txt_chatgpt_model.text().strip()

        # Azure
        params['azure_key'] = self.txt_azure_key.text().strip()
        params['azure_api'] = self.txt_azure_api.text().strip()
        params['azure_model'] = self.txt_azure_model.text().strip()
        params['azure_version'] = self.txt_azure_ver.text().strip()

        # DeepL
        params['deepl_authkey'] = self.txt_deepl_key.text().strip()
        params['deepl_api'] = self.txt_deepl_api.text().strip()

        # OpenRouter
        params['openrouter_key'] = self.txt_openrouter_key.text().strip()
        params['openrouter_model'] = self.txt_openrouter_model.text().strip()

        # Zhipu
        params['zhipu_key'] = self.txt_zhipu_key.text().strip()
        params['zhipu_model'] = self.txt_zhipu_model.text().strip()

        # Tencent / Baidu / Ali / Silicon / Local / Libre / AI302 / MiniMax
        params['tencent_SecretId'] = self.txt_tencent_id.text().strip()
        params['tencent_SecretKey'] = self.txt_tencent_key.text().strip()
        params['baidu_appid'] = self.txt_baidu_id.text().strip()
        params['baidu_miyue'] = self.txt_baidu_key.text().strip()
        params['ali_id'] = self.txt_ali_id.text().strip()
        params['ali_key'] = self.txt_ali_key.text().strip()
        params['siliconflow_key'] = self.txt_silicon_key.text().strip()
        params['siliconflow_model'] = self.txt_silicon_model.text().strip()
        params['localllm_api'] = self.txt_localllm_api.text().strip()
        params['localllm_key'] = self.txt_localllm_key.text().strip()
        params['localllm_model'] = self.txt_localllm_model.text().strip()
        params['libre_address'] = self.txt_libre_api.text().strip()
        params['libre_key'] = self.txt_libre_key.text().strip()
        params['ai302_key'] = self.txt_ai302_key.text().strip()
        params['ai302_model'] = self.txt_ai302_model.text().strip()
        params['minimax_groupid'] = self.txt_minimax_id.text().strip()
        params['minimax_api_key'] = self.txt_minimax_key.text().strip()

        # TTS
        params['azure_tts_key'] = self.txt_azure_tts_key.text().strip()
        params['azure_tts_region'] = self.txt_azure_tts_region.text().strip()
        params['elevenlabs_key'] = self.txt_eleven_key.text().strip()
        params['elevenlabs_model'] = self.txt_eleven_model.text().strip()
        params['cosyvoice_api'] = self.txt_cosy_api.text().strip()
        params['gptsovits_address'] = self.txt_sovits_api.text().strip()
        params['chatterbox_api'] = self.txt_chatter_api.text().strip()
        params['minimaxi_groupid'] = self.txt_minimax_tts_id.text().strip()
        params['minimaxi_api_key'] = self.txt_minimax_tts_key.text().strip()

        # General
        proxy_val = self.txt_proxy.text().strip()
        app_cfg.proxy = proxy_val
        params['proxy'] = proxy_val
        if proxy_val:
            os.environ['HTTP_PROXY'] = proxy_val
            os.environ['HTTPS_PROXY'] = proxy_val
        else:
            os.environ.pop('HTTP_PROXY', None)
            os.environ.pop('HTTPS_PROXY', None)

        params['output_dir'] = self.txt_output_dir.text().strip()
        settings['crf'] = self.sp_crf.value()
        settings['preset'] = self.cb_preset.currentText()
        settings['whisper_threads'] = self.txt_whisper_threads.value()
        settings['vad'] = self.chk_vad.isChecked()

        params.save()
        settings.save()

        if show_msg:
            QMessageBox.information(
                self,
                tr("Thành công"),
                tr("Đã lưu toàn bộ cấu hình vào hệ thống thành công!")
            )
        self.accept()

    def _reset_current_page(self):
        # Reload defaults from params
        pass
