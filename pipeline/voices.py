"""Voice stage: cast each character to a Kokoro voice and perform lines."""
import json

import soundfile as sf
from kokoro_onnx import Kokoro

from . import config


def assign_voices(cast, show_dir):
    """Deterministic cast->voice map, saved so it stays consistent across episodes."""
    vf = show_dir / "voices.json"
    if vf.exists():
        return json.loads(vf.read_text())

    m, fi, mi = {}, 0, 0
    for i, ch in enumerate(cast):
        name = ch["name"]
        if ch.get("voice"):
            m[name] = ch["voice"]
            continue
        g = (ch.get("gender") or "").lower()
        if g.startswith("m"):
            m[name] = config.MALE_VOICES[mi % len(config.MALE_VOICES)]; mi += 1
        elif g.startswith("f"):
            m[name] = config.FEMALE_VOICES[fi % len(config.FEMALE_VOICES)]; fi += 1
        elif i % 2 == 0:
            m[name] = config.FEMALE_VOICES[fi % len(config.FEMALE_VOICES)]; fi += 1
        else:
            m[name] = config.MALE_VOICES[mi % len(config.MALE_VOICES)]; mi += 1

    show_dir.mkdir(parents=True, exist_ok=True)
    vf.write_text(json.dumps(m, indent=2))
    return m


class VoiceEngine:
    def __init__(self):
        self.kokoro = Kokoro(str(config.KOKORO_MODEL), str(config.KOKORO_VOICES))

    def render(self, text, voice, out_path):
        samples, sr = self.kokoro.create(text, voice=voice, speed=1.0, lang="en-us")
        sf.write(str(out_path), samples, sr)
        return len(samples) / sr
