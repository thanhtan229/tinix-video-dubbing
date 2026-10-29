# -*- coding: utf-8 -*-
from PySide6 import QtCore, QtWidgets
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog

from videotrans.configure.config import tr, ROOT_DIR


class Ui_vieneu(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(f"{ROOT_DIR}/videotrans/styles/icon.ico"))
        self.setupUi(self)

    def setupUi(self, form):
        form.setObjectName("form")
        form.resize(640, 180)
        layout = QtWidgets.QVBoxLayout(form)

        hint = QtWidgets.QLabel(tr("Python executable of the VieNeu-TTS environment (the .venv that has the vieneu package)."))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        row = QtWidgets.QHBoxLayout()
        self.vieneu_python = QtWidgets.QLineEdit()
        self.vieneu_python.setMinimumHeight(35)
        self.vieneu_python.setObjectName("vieneu_python")
        self.browse = QtWidgets.QPushButton(tr("Browse..."))
        self.browse.setMinimumHeight(35)
        row.addWidget(self.vieneu_python, 1)
        row.addWidget(self.browse)
        layout.addLayout(row)

        self.save = QtWidgets.QPushButton(tr("Save"))
        self.save.setMinimumHeight(35)
        layout.addWidget(self.save)
