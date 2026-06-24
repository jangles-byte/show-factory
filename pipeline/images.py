"""Image stage: drive ComfyUI (SDXL + optional Archer LoRA + optional InstantID)
to render scene/character art. Talks to ComfyUI's HTTP API.

Start ComfyUI first:  cd ~/Desktop/ComfyUI && ./.venv/bin/python main.py
Then:                 ./.venv/bin/python -m pipeline.images "a spy by a pool" out.png [ref.jpg]
"""
import json
import re
import shutil
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from . import config


class Comfy:
    def __init__(self, url=None):
        self.url = url or config.COMFY_URL
        self.cid = uuid.uuid4().hex

    def up(self):
        try:
            urllib.request.urlopen(self.url + "/system_stats", timeout=4)
            return True
        except Exception:
            return False

    def _post(self, path, obj):
        req = urllib.request.Request(self.url + path, data=json.dumps(obj).encode(),
                                     headers={"Content-Type": "application/json"})
        return json.loads(urllib.request.urlopen(req, timeout=120).read())

    def _get(self, path):
        return json.loads(urllib.request.urlopen(self.url + path, timeout=120).read())

    def queue(self, graph):
        return self._post("/prompt", {"prompt": graph, "client_id": self.cid})["prompt_id"]

    def wait(self, pid, timeout=900, poll=1.5):
        t0 = time.time()
        while time.time() - t0 < timeout:
            hist = self._get(f"/history/{pid}")
            if pid in hist:
                return hist[pid]
            time.sleep(poll)
        raise TimeoutError("ComfyUI render timed out")

    def save_first_image(self, hist, dest):
        for node in hist.get("outputs", {}).values():
            for im in node.get("images", []):
                q = urllib.parse.urlencode({"filename": im["filename"],
                                            "subfolder": im.get("subfolder", ""), "type": im["type"]})
                data = urllib.request.urlopen(self.url + "/view?" + q, timeout=180).read()
                Path(dest).write_bytes(data)
                return dest
        raise RuntimeError("ComfyUI returned no image")


def _base_nodes(prompt, neg, lora, lora_w, w, h, seed, steps, cfg):
    """Common checkpoint -> (optional lora) -> conditioning -> latent nodes."""
    g = {"ckpt": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": config.CHECKPOINT}}}
    model, clip, vae = ["ckpt", 0], ["ckpt", 1], ["ckpt", 2]
    if lora:
        g["lora"] = {"class_type": "LoraLoader", "inputs": {
            "model": model, "clip": clip, "lora_name": lora,
            "strength_model": lora_w, "strength_clip": lora_w}}
        model, clip = ["lora", 0], ["lora", 1]
    g["pos"] = {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": clip}}
    g["neg"] = {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": clip}}
    g["latent"] = {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}}
    return g, model, vae


def _sampler_tail(g, model, vae, seed, steps, cfg):
    g["ks"] = {"class_type": "KSampler", "inputs": {
        "model": model, "positive": ["pos", 0], "negative": ["neg", 0], "latent_image": ["latent", 0],
        "seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "dpmpp_2m", "scheduler": "karras",
        "denoise": 1.0}}
    g["vae"] = {"class_type": "VAEDecode", "inputs": {"samples": ["ks", 0], "vae": vae}}
    g["save"] = {"class_type": "SaveImage", "inputs": {"images": ["vae", 0], "filename_prefix": "sf"}}
    return g


def txt2img_graph(prompt, neg, lora, lora_w, w, h, seed, steps=28, cfg=6.5):
    g, model, vae = _base_nodes(prompt, neg, lora, lora_w, w, h, seed, steps, cfg)
    return _sampler_tail(g, model, vae, seed, steps, cfg)


def instantid_graph(prompt, neg, ref_filename, lora, lora_w, w, h, seed,
                    ip_weight=0.8, cn_strength=0.8, steps=30, cfg=5.0):
    g, model, vae = _base_nodes(prompt, neg, lora, lora_w, w, h, seed, steps, cfg)
    g["idload"] = {"class_type": "InstantIDModelLoader", "inputs": {"instantid_file": config.INSTANTID_FILE}}
    g["face"] = {"class_type": "InstantIDFaceAnalysis", "inputs": {"provider": "CPU"}}
    g["cnet"] = {"class_type": "ControlNetLoader", "inputs": {"control_net_name": config.INSTANTID_CONTROLNET}}
    g["refimg"] = {"class_type": "LoadImage", "inputs": {"image": ref_filename}}
    g["applyid"] = {"class_type": "ApplyInstantID", "inputs": {
        "instantid": ["idload", 0], "insightface": ["face", 0], "control_net": ["cnet", 0],
        "image": ["refimg", 0], "model": model, "positive": ["pos", 0], "negative": ["neg", 0],
        "ip_weight": ip_weight, "cn_strength": cn_strength, "start_at": 0.0, "end_at": 1.0, "noise": 0.0}}
    # InstantID rewrites model + conditioning
    g["ks"] = {"class_type": "KSampler", "inputs": {
        "model": ["applyid", 0], "positive": ["applyid", 1], "negative": ["applyid", 2],
        "latent_image": ["latent", 0], "seed": seed, "steps": steps, "cfg": cfg,
        "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0}}
    g["vae"] = {"class_type": "VAEDecode", "inputs": {"samples": ["ks", 0], "vae": vae}}
    g["save"] = {"class_type": "SaveImage", "inputs": {"images": ["vae", 0], "filename_prefix": "sf"}}
    return g


def img2img_graph(prompt, neg, init_filename, lora, lora_w, seed, denoise, steps=28, cfg=6.5):
    """Repaint over an existing plate (keeps the background/composition)."""
    g, model, vae = _base_nodes(prompt, neg, lora, lora_w, 0, 0, seed, steps, cfg)
    g.pop("latent", None)  # latent comes from the init image instead
    g["init"] = {"class_type": "LoadImage", "inputs": {"image": init_filename}}
    g["enc"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["init", 0], "vae": vae}}
    g["ks"] = {"class_type": "KSampler", "inputs": {
        "model": model, "positive": ["pos", 0], "negative": ["neg", 0], "latent_image": ["enc", 0],
        "seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "dpmpp_2m", "scheduler": "karras",
        "denoise": denoise}}
    g["vae"] = {"class_type": "VAEDecode", "inputs": {"samples": ["ks", 0], "vae": vae}}
    g["save"] = {"class_type": "SaveImage", "inputs": {"images": ["vae", 0], "filename_prefix": "sf"}}
    return g


class ImageEngine:
    def __init__(self, style=None):
        self.c = Comfy()
        st = style or {}
        self.style_name = st.get("name", "Default")
        self.suffix = st.get("prompt") or config.STYLE_SUFFIX
        self.negative = st.get("negative") or config.NEG_PROMPT
        self.lora = st.get("lora") or config.find_style_lora()
        self.lora_w = st.get("lora_weight", config.LORA_WEIGHT)
        self.has_instantid = (config.COMFY_DIR / "models" / "instantid" / config.INSTANTID_FILE).exists()

    def ready(self):
        return self.c.up()

    def _stage_input(self, src, prefix):
        inp = config.COMFY_DIR / "input"
        inp.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", Path(src).name)
        name = prefix + safe
        shutil.copy(src, inp / name)
        return name

    def render(self, prompt, out_path, ref_image=None, init_image=None, denoise=None, portrait=False, seed=None):
        seed = int(seed if seed is not None else (uuid.uuid4().int % 2**31))
        full_prompt = f"{prompt}, {self.suffix}"
        w, h = (config.PORTRAIT_W, config.PORTRAIT_H) if portrait else (config.IMG_W, config.IMG_H)
        if ref_image and self.has_instantid and Path(ref_image).exists():
            ref_name = self._stage_input(ref_image, "sfref_")
            graph = instantid_graph(full_prompt, self.negative, ref_name, self.lora, self.lora_w, w, h, seed)
        elif init_image and Path(init_image).exists():
            init_name = self._stage_input(init_image, "sfinit_")
            graph = img2img_graph(full_prompt, self.negative, init_name, self.lora, self.lora_w,
                                  seed, denoise if denoise is not None else config.IMG2IMG_DENOISE)
        else:
            graph = txt2img_graph(full_prompt, self.negative, self.lora, self.lora_w, w, h, seed)
        pid = self.c.queue(graph)
        hist = self.c.wait(pid)
        return self.c.save_first_image(hist, out_path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("usage: python -m pipeline.images <prompt> <out.png> [ref_image]")
        sys.exit(1)
    eng = ImageEngine()
    if not eng.ready():
        print("⚠ ComfyUI not running. Start it: cd ~/Desktop/ComfyUI && ./.venv/bin/python main.py")
        sys.exit(1)
    print(f"lora={eng.lora}  instantid={eng.has_instantid}")
    ref = sys.argv[3] if len(sys.argv) > 3 else None
    out = eng.render(sys.argv[1], sys.argv[2], ref_image=ref, portrait=bool(ref))
    print("saved", out)
