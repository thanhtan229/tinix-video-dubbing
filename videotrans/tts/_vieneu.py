# -*- coding: utf-8 -*-
"""VieNeu-TTS channel. Calls a long-lived worker that runs in the VieNeu-TTS Python environment."""
import json
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union

from videotrans.configure import constants
from videotrans.configure.config import params, logger, ROOT_DIR
from videotrans.configure.excepts import StopTask
from videotrans.tts._base import BaseTTS
from videotrans.util.help_misc import vail_file

WORKER_PATH = Path(__file__).with_name("_vieneu_worker.py")
_DEFAULT_VOICE = "Phạm Tuyên"


class VieneuWorker:
    """One worker process per Python path. Requests are serialised with a lock."""

    def __init__(self, python_path: str):
        self.python_path = python_path
        self.lock = threading.Lock()
        self.proc: Optional[subprocess.Popen] = None
        self.log_path = Path(ROOT_DIR) / "logs" / "vieneu_worker.log"

    def _start(self) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        log = open(self.log_path, "a", encoding="utf-8")
        self.proc = subprocess.Popen(
            [self.python_path, str(WORKER_PATH)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=log,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        ready = self.proc.stdout.readline()
        if not ready or not json.loads(ready).get("ready"):
            self.stop()
            raise RuntimeError(f"VieNeu-TTS worker did not start. See {self.log_path}")

    def _ensure(self) -> None:
        if self.proc is None or self.proc.poll() is not None:
            self._start()

    def synthesize(self, text: str, voice: str, out_wav: str) -> None:
        with self.lock:
            self._ensure()
            self.proc.stdin.write(json.dumps({"text": text, "voice": voice, "out": out_wav}, ensure_ascii=False) + "\n")
            self.proc.stdin.flush()
            reply_line = self.proc.stdout.readline()
            if not reply_line:
                self.stop()
                raise RuntimeError(f"VieNeu-TTS worker exited. See {self.log_path}")
            reply = json.loads(reply_line)
            if not reply.get("ok"):
                raise RuntimeError(reply.get("error", "VieNeu-TTS failed"))

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
        self.proc = None


_workers: Dict[str, VieneuWorker] = {}
_workers_lock = threading.Lock()


def get_worker(python_path: str) -> VieneuWorker:
    with _workers_lock:
        if python_path not in _workers:
            _workers[python_path] = VieneuWorker(python_path)
        return _workers[python_path]


@dataclass(repr=False)
class VIENEUTTS(BaseTTS):

    def __post_init__(self):
        super().__post_init__()

    def _run(self, data_item: Union[Dict, List, None], idx: int = -1) -> Union[str, None]:
        if vail_file(data_item['filename']):
            return
        python_path = str(params.get('vieneu_python', '')).strip()
        if not python_path or not Path(python_path).exists():
            raise StopTask("VieNeu-TTS Python path is not set or missing. Set 'vieneu_python' in params.json.")
        role = data_item.get('role') or _DEFAULT_VOICE
        voices = constants.VIENEU_ROLES.split(',')
        voice = role if role in voices else _DEFAULT_VOICE
        out_wav = data_item['filename'] + '.wav'
        get_worker(python_path).synthesize(data_item['text'], voice, out_wav)
        self.convert_to_wav(out_wav, data_item['filename'])
