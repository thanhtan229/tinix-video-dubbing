# -*- coding: utf-8 -*-
"""VieNeu-TTS worker. Runs under the VieNeu-TTS Python environment, not the project venv.

Protocol (one JSON object per line):
  start : worker prints {"ready": true} once the model is loaded.
  request: {"text": str, "voice": str, "out": str}  -> writes WAV to "out".
  reply  : {"ok": true} or {"ok": false, "error": str}.
SDK logs go to stderr so they never corrupt the protocol on stdout.
"""
import json
import sys


def main():
    protocol = sys.stdout
    sys.stdout = sys.stderr
    from vieneu import Vieneu

    tts = Vieneu(mode="v3turbo")
    protocol.write(json.dumps({"ready": True}) + "\n")
    protocol.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            audio = tts.infer(req["text"], voice=req.get("voice") or None)
            tts.save(audio, req["out"])
            reply = {"ok": True}
        except Exception as e:
            reply = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        protocol.write(json.dumps(reply, ensure_ascii=False) + "\n")
        protocol.flush()


if __name__ == "__main__":
    main()
