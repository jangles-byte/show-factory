"""Shared config + small helpers for the Show Factory pipeline."""
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
OUTPUT = ROOT / "output"

KOKORO_MODEL = MODELS / "kokoro-v1.0.onnx"
KOKORO_VOICES = MODELS / "voices-v1.0.bin"

OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
WRITER_MODEL = os.environ.get("WRITER_MODEL", "gemma4:e2b-mlx")

VIDEO_W, VIDEO_H = 1280, 720
SR = 24000          # Kokoro output sample rate
GAP = 0.4           # silence between lines (seconds)

# Kokoro v1.0 preset voices, split by vibe so we can auto-cast a show.
FEMALE_VOICES = ["af_heart", "bf_isabella", "af_bella", "bf_emma", "af_nicole", "bf_alice", "af_sarah"]
MALE_VOICES = ["bm_george", "am_michael", "am_adam", "bm_lewis", "am_eric", "bm_daniel", "am_liam"]

# Pick a usable TrueType font for ffmpeg drawtext.
_FONT_CANDS = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/SFNS.ttf",
]
FONT = next((p for p in _FONT_CANDS if os.path.exists(p)), "")


def slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (s or "untitled").lower()).strip("_")
    return s or "untitled"


# ---------- image stage (ComfyUI) ----------
COMFY_URL = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
COMFY_DIR = Path(os.environ.get("COMFY_DIR", str(Path.home() / "Desktop" / "ComfyUI")))
CHECKPOINT = os.environ.get("SF_CHECKPOINT", "sd_xl_base_1.0.safetensors")
INSTANTID_FILE = "ip-adapter.bin"
INSTANTID_CONTROLNET = "instantid_control.safetensors"
# Archer-leaning style text; reinforced if a style LoRA is present in models/loras.
STYLE_SUFFIX = os.environ.get("SF_STYLE",
    "in the style of the TV show Archer, flat 2D vector animation, bold black outlines, "
    "flat cel shading, limited color palette, mid-century modern, cinematic lighting, clean")
NEG_PROMPT = os.environ.get("SF_NEG",
    "photo, photorealistic, 3d render, blurry, low quality, deformed, disfigured, extra limbs, "
    "extra fingers, mutated hands, watermark, signature, text, caption, jpeg artifacts")
LORA_WEIGHT = float(os.environ.get("SF_LORA_WEIGHT", "0.75"))
IMG_W, IMG_H = 1280, 720          # scene image size (matches video)
PORTRAIT_W, PORTRAIT_H = 832, 1216
# per-line shots are img2img variations of the scene's establishing plate, so the
# background stays consistent while the character/action changes. Higher = more change.
IMG2IMG_DENOISE = float(os.environ.get("SF_DENOISE", "0.62"))
# per-line shots crop the master set to the speaker's side, then refine at this denoise
# (low = keep the set/composition, just clean it into a shot of that character)
SHOT_DENOISE = float(os.environ.get("SF_SHOT_DENOISE", "0.5"))


def find_style_lora():
    d = COMFY_DIR / "models" / "loras"
    if not d.exists():
        return None
    cands = sorted(p for p in d.glob("*.safetensors"))
    archer = [c for c in cands if "archer" in c.name.lower()]
    pick = archer or cands
    return pick[0].name if pick else None


STYLES_FILE = ROOT / "styles.json"


def load_styles():
    try:
        import json
        return json.loads(STYLES_FILE.read_text()).get("styles", [])
    except Exception:
        return []


def resolve_style(label):
    """Match a show's visualStyle label to a style entry (else the first/default)."""
    styles = load_styles()
    default = {"name": "Default", "prompt": STYLE_SUFFIX, "negative": NEG_PROMPT, "lora": None}
    if not styles:
        return default
    lab = (label or "").lower().strip()
    if lab:
        for s in styles:
            n = s["name"].lower()
            if n in lab or lab in n:
                return s
        for s in styles:
            if any(tok in lab for tok in s["name"].lower().replace("(", " ").replace(")", " ").split() if len(tok) > 3):
                return s
    return styles[0]
