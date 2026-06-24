# 🎬 Show Factory

**A local, free, open-source studio that turns a one-line idea into watchable cartoon-series episodes.**

Everything runs on your own machine — a local LLM writes the show, [Kokoro](https://github.com/hexgrad/kokoro) gives every character a voice, [ComfyUI](https://github.com/comfyanonymous/ComfyUI) (SDXL + InstantID) draws the art, and `ffmpeg` assembles the video. No cloud, no API keys, no per-token bill. The only network calls are read-only reference lookups to Wikipedia/Wikimedia.

---

## What it does

```
   brief ──▶ Writers' Room ──▶ Show Bible ──▶ ┌─ write   (LLM: script + scene beats)
 "a heist     (chat w/ a       (cast, arcs,   ├─ cast    (lock each character's look + face)
  comedy in    showrunner)      episodes)     ├─ voices  (Kokoro: one voice per character)
  an aquarium")                               └─ render  (ComfyUI art + captions → .mp4)
```

You drive it from a desktop-style production suite in the browser:

- **SHOWS** — generate a series from a one-line brief, edit the bible on a node canvas, delete shows/episodes.
- **CAST** — upload reference photos of a real person, pick an animation style, and **lock a consistent character**. The same face + design then appears in every shot (powered by InstantID).
- **STYLES** — a visual library of art styles. Add any SDXL LoRA by dropping a file and naming it — no JSON editing.
- **RENDERS** — a gallery of every finished episode.

Each character is also auto-cast to a distinct Kokoro voice, matched by gender and kept stable across the whole season.

---

## Requirements

| Need | Why |
|---|---|
| **Python 3.10+** | backend + pipeline |
| **Node 18+** | the web dashboard (Vite/React) |
| **[Ollama](https://ollama.com)** running a small instruct model | writes the scripts (default `gemma4:e2b-mlx`, override with `WRITER_MODEL`) |
| **`ffmpeg`** on your `PATH` | assembles the video |
| **Kokoro model files** in `models/` | text-to-speech (see below) |
| **[ComfyUI](https://github.com/comfyanonymous/ComfyUI)** *(optional)* | AI art. Without it, episodes render as an audio drama over styled captions. |

### Model files (not in the repo — download once)

```
models/kokoro-v1.0.onnx     # Kokoro TTS weights
models/voices-v1.0.bin      # Kokoro voice pack
```

Grab them from the [Kokoro releases](https://github.com/hexgrad/kokoro). For AI art, point ComfyUI at an SDXL checkpoint (default `sd_xl_base_1.0.safetensors`) and, for face-locked characters, install the [InstantID](https://github.com/cubiq/ComfyUI_InstantID) custom node + its models.

---

## Quick start

Run three things, each in its own terminal:

```bash
# 1. ComfyUI — only needed for AI art
cd ~/Desktop/ComfyUI && ./.venv/bin/python main.py     # serves :8188

# 2. Backend — writers' room + reference lookups
cd show-factory && python3 serve.py                     # serves :8008

# 3. Dashboard
cd show-factory/web && npm install && npm run dev       # opens :5174
```

(Ollama runs on its own in the background.) Then open the URL Vite prints (`http://localhost:5174`).

> 💡 On macOS you can wrap these three commands in a double-clickable `start.command` so the whole stack launches at once. It's machine-specific (it hard-codes paths), so it's `.gitignore`d — make your own.

### Make a show in 30 seconds

1. **SHOWS** tab → type a brief → **BUILD SHOW**. The LLM writes a bible (title, cast, season arc, episodes).
2. **CAST** tab → optionally drop in photos of who each character should look like → pick a style → **Lock**.
3. **▶ RENDER** in the top bar → the pipeline prints the episode(s).
4. **RENDERS** tab → watch.

You can also run it headless:

```bash
./.venv/bin/python -m pipeline.run --bible sample_bible.json --episodes 4
```

Output lands in `output/<show>/epNN/epNN.mp4` (alongside `script.json`, `audio.wav`, and the character/scene assets).

---

## Art styles & where to find more

`styles.json` is a plugin list. Each entry is appended to every image prompt:

```json
{
  "name": "Inked comic book",
  "prompt": "inked comic book art, bold linework, halftone shading, high contrast",
  "negative": "photo, blurry, deformed",
  "lora": "my_comic_style.safetensors",
  "lora_weight": 0.75
}
```

To add a brand-new look, download an **SDXL LoRA** and drop the `.safetensors` into
`~/Desktop/ComfyUI/models/loras/`, then add a style in the **STYLES** tab naming that file — it
appears in every dropdown instantly.

Great places to browse styles:
- **[Civitai → SDXL LoRAs](https://civitai.com/models?types=LORA&baseModels=SDXL%201.0)** — biggest library. Try searches like `Arcane`, `Spider-Verse`, `Genndy Tartakovsky`, `UPA retro`, `claymation`, `Studio Ghibli`.
- **[Hugging Face](https://huggingface.co/models?other=lora&pipeline_tag=text-to-image)** — more research-grade LoRAs.
- Swap the whole base look with a stylized SDXL **checkpoint** (`SF_CHECKPOINT`), e.g. *Animagine XL* (anime) or *DreamShaper XL*.

---

## Consistent characters (InstantID)

The CAST tab's "lock" feature is the studio's secret weapon:

1. Upload a few photos of the person a character should resemble. They're saved to `refs/<show>/<character>/`.
2. **Lock** designs a fixed visual description + seed for that character and renders a canonical portrait — using **InstantID** so the generated face matches your reference, in your chosen art style.
3. From then on every shot of that character reuses the same locked design, so they look the same all season. Re-lock anytime to try the same character in a different style.

Characters with no reference photos still stay consistent via a fixed per-character seed and an LLM-authored "look" sheet.

---

## Configuration

Everything is overridable by environment variable:

| Var | Default | Meaning |
|---|---|---|
| `WRITER_MODEL` | `gemma4:e2b-mlx` | Ollama model used for writing |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama endpoint |
| `COMFY_URL` | `http://127.0.0.1:8188` | ComfyUI endpoint |
| `COMFY_DIR` | `~/Desktop/ComfyUI` | ComfyUI install (loras, instantid, input) |
| `SF_CHECKPOINT` | `sd_xl_base_1.0.safetensors` | SDXL checkpoint |
| `SF_STYLE` / `SF_NEG` | Archer-ish defaults | fallback style / negative prompt |
| `SF_LORA_WEIGHT` | `0.75` | style LoRA strength |

---

## Project layout

```
serve.py            backend: serves the UI, proxies Ollama (no CORS), gathers references,
                    and exposes the suite API (shows, characters, styles, renders)
styles.json         the art-style library
pipeline/
  autocreate.py     brief → Show Bible
  write.py          bible → scene breakdown → per-scene dialogue
  cast.py           lock each character's look/seed/voice (+ InstantID when refs exist)
  voices.py         Kokoro voice rendering
  images.py         ComfyUI driver: txt2img, InstantID, img2img
  render.py         dialogue + audio + captions → .mp4
  run.py            the "season printer" — orchestrates all of the above
web/                React + Vite dashboard (the production suite)
```

---

## License

MIT — see [LICENSE](LICENSE). Build cartoons, fork freely.
