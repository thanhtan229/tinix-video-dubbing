from pathlib import Path


def openwin():
    from PySide6 import QtWidgets
    from videotrans.winform import get_cls
    from videotrans.configure.config import tr, params
    from videotrans.util.help_misc import show_error

    winobj = get_cls(Path(__file__).stem)()

    def browse():
        start = str(params.get('vieneu_python', '') or '')
        path, _ = QtWidgets.QFileDialog.getOpenFileName(winobj, tr("Select Python executable"), start,
                                                        "Python (python.exe python);;All files (*)")
        if path:
            winobj.vieneu_python.setText(path)

    def save():
        python_path = winobj.vieneu_python.text().strip()
        if not python_path or not Path(python_path).exists():
            show_error(tr("The Python executable does not exist."))
            return
        params['vieneu_python'] = python_path
        params.save()
        winobj.close()

    winobj.vieneu_python.setText(str(params.get('vieneu_python', '') or ''))
    winobj.browse.clicked.connect(browse)
    winobj.save.clicked.connect(save)
    return winobj
