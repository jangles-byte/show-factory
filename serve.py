#!/usr/bin/env python3
"""
Show Factory — tiny local server.
Serves the discussion UI, proxies the Ollama API (no CORS), and gathers
reference material (Wikipedia + Wikimedia Commons, no API keys) for the
people/places/things named during planning. Nothing leaves your machine
except read-only lookups to those public sources.

Run:  python3 serve.py
Open: http://127.0.0.1:8008
"""
import http.server
import json
import os
import re
import socketserver
import urllib.error
import urllib.request
import subprocess
import sys
import base64
import shutil
import time
from pathlib import Path
from urllib.parse import parse_qs, quote, urlencode, urlparse

OLLAMA = "http://127.0.0.1:11434"
PORT = 8008
DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = Path(DIR)
UA = "ShowFactory/1.0 (local creative tool; reference lookup)"


def _get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        dest.write_bytes(r.read())


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "_", (s or "x").lower()).strip("_") or "x"


def gather_refs(entities, show_slug, per=3):
    """For each named entity, resolve via Wikipedia and download a few reference images."""
    base = ROOT / "refs" / _slug(show_slug)
    results = []
    for ent in entities:
        name = (ent.get("name") or "").strip()
        if not name:
            continue
        typ = ent.get("type", "")
        d = base / _slug(name)
        d.mkdir(parents=True, exist_ok=True)
        entry = {"name": name, "type": typ, "summary": "", "resolved": "", "images": []}
        img_urls = []
        try:
            # 1. resolve the best Wikipedia title
            s = _get_json("https://en.wikipedia.org/w/api.php?" + urlencode({
                "action": "query", "list": "search", "srsearch": name, "srlimit": 1, "format": "json"}))
            hits = s.get("query", {}).get("search", [])
            if hits:
                title = hits[0]["title"]
                entry["resolved"] = title
                # 2. summary + lead image
                try:
                    summ = _get_json("https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(title.replace(" ", "_")))
                    entry["summary"] = summ.get("extract", "")
                    if summ.get("originalimage"):
                        img_urls.append(summ["originalimage"]["source"])
                    elif summ.get("thumbnail"):
                        img_urls.append(summ["thumbnail"]["source"])
                except Exception:
                    pass
                # 3. extra images from Wikimedia Commons
                try:
                    c = _get_json("https://commons.wikimedia.org/w/api.php?" + urlencode({
                        "action": "query", "generator": "search", "gsrsearch": title,
                        "gsrnamespace": 6, "gsrlimit": per + 2, "prop": "imageinfo",
                        "iiprop": "url", "iiurlwidth": 640, "format": "json"}))
                    for p in (c.get("query", {}).get("pages", {}) or {}).values():
                        ii = (p.get("imageinfo") or [{}])[0]
                        u = ii.get("thumburl") or ii.get("url")
                        if u:
                            img_urls.append(u)
                except Exception:
                    pass
            else:
                entry["summary"] = "(no Wikipedia match — for a private person, supply your own photo)"
        except Exception as e:
            entry["error"] = str(e)

        # 4. download (dedup, cap)
        seen, n = set(), 0
        for u in img_urls:
            if u in seen:
                continue
            seen.add(u)
            ext = os.path.splitext(u.split("?")[0])[1].lower()
            if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
                ext = ".jpg"
            fn = d / f"{n+1:02d}{ext}"
            try:
                _download(u, fn)
                entry["images"].append({"url": u, "local": "/" + str(fn.relative_to(ROOT))})
                n += 1
            except Exception:
                pass
            if n >= per + 1:
                break
        results.append(entry)

    base.mkdir(parents=True, exist_ok=True)
    (base / "manifest.json").write_text(json.dumps(results, indent=2))
    return {"show": _slug(show_slug), "pack": "/" + str((base).relative_to(ROOT)), "entities": results}


def list_shows():
    out = []
    base = ROOT / "output"
    if base.exists():
        for d in sorted(base.iterdir()):
            bp = d / "bible.json"
            if not bp.exists():
                continue
            try:
                b = json.loads(bp.read_text())
            except Exception:
                b = {}
            out.append({"slug": d.name, "title": b.get("title", d.name),
                        "episodes": len(b.get("episodes", [])),
                        "rendered": len(list(d.glob("ep*/ep*.mp4")))})
    return out


def get_show(slug):
    bp = ROOT / "output" / slug / "bible.json"
    if not bp.exists():
        return None
    b = json.loads(bp.read_text())
    b["_slug"] = slug
    b["_status"] = {mp4.parent.name: f"/output/{slug}/{mp4.parent.name}/{mp4.name}"
                    for mp4 in (ROOT / "output" / slug).glob("ep*/ep*.mp4")}
    return b


def save_show(bible):
    from pipeline import config as pcfg
    slug = bible.get("_slug") or pcfg.slugify(bible.get("title", "show"))
    bible.pop("_slug", None)
    bible.pop("_status", None)
    d = ROOT / "output" / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / "bible.json").write_text(json.dumps(bible, indent=2))
    return slug


def trigger_render(slug, episodes, shots):
    bp = ROOT / "output" / slug / "bible.json"
    if not bp.exists():
        raise FileNotFoundError("no bible for " + slug)
    venv_py = ROOT / ".venv" / "bin" / "python"
    log = open(ROOT / "output" / slug / "render.log", "w")
    subprocess.Popen([str(venv_py), "-m", "pipeline.run", "--bible", str(bp),
                      "--episodes", str(episodes), "--shots", shots],
                     cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT)
    return True


# ---------- shows ----------
def delete_show(slug):
    """Delete a show's output folder and its reference packs."""
    from pipeline import config as pcfg
    safe = pcfg.slugify(slug)
    d = ROOT / "output" / safe
    if d.is_dir():
        shutil.rmtree(d)
    rp = ROOT / "refs" / safe
    if rp.is_dir():
        shutil.rmtree(rp)
    return {"ok": True, "deleted": safe}


# ---------- characters ----------
_IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")


def _refs_dir(bible, slug, name):
    """Where cast.py looks for a character's photos: refs/<title-slug>/<name-slug>/."""
    from pipeline import config as pcfg
    title_slug = pcfg.slugify((bible or {}).get("title", slug))
    return ROOT / "refs" / title_slug / pcfg.slugify(name), title_slug, pcfg.slugify(name)


def character_assets(slug):
    """Cast list merged with uploaded reference photos + any locked portrait."""
    from pipeline import config as pcfg
    b = get_show(slug)
    if not b:
        return {"error": "not found"}
    show_dir = ROOT / "output" / slug
    saved = {}
    cj = show_dir / "assets" / "characters.json"
    if cj.exists():
        try:
            saved = json.loads(cj.read_text())
        except Exception:
            saved = {}
    chars = []
    for c in b.get("cast", []):
        name = c["name"]
        rp, title_slug, cslug = _refs_dir(b, slug, name)
        refs = []
        if rp.exists():
            for img in sorted(rp.iterdir()):
                if img.suffix.lower() in _IMG_EXT:
                    refs.append(f"/refs/{title_slug}/{cslug}/{img.name}")
        info = saved.get(name, {})
        pf = show_dir / "assets" / "characters" / f"{cslug}.png"
        portrait = f"/output/{slug}/assets/characters/{cslug}.png" if pf.exists() else None
        chars.append({
            "name": name,
            "role": c.get("role", ""),
            "personality": c.get("personality", ""),
            "gender": c.get("gender") or info.get("gender", "?"),
            "look": info.get("look", ""),
            "seed": info.get("seed"),
            "voice": info.get("voice", ""),
            "instantid": bool(refs),
            "refs": refs,
            "portrait": portrait,
        })
    return {"slug": slug, "title": b.get("title"), "style": b.get("visualStyle"), "characters": chars}


def upload_refs(slug, name, images):
    """Save base64 data-URL photos into the character's reference pack."""
    b = get_show(slug)
    rp, title_slug, cslug = _refs_dir(b, slug, name)
    rp.mkdir(parents=True, exist_ok=True)
    saved = []
    for im in images:
        data = im.get("dataUrl", "")
        if "," in data:
            data = data.split(",", 1)[1]
        raw = base64.b64decode(data)
        fname = re.sub(r"[^A-Za-z0-9._-]", "_", im.get("name", "ref.png"))
        if not fname.lower().endswith(_IMG_EXT):
            fname += ".png"
        (rp / fname).write_bytes(raw)
        saved.append(f"/refs/{title_slug}/{cslug}/{fname}")
    return {"ok": True, "refs": saved}


def delete_ref(slug, name, filename):
    b = get_show(slug)
    rp, _, _ = _refs_dir(b, slug, name)
    f = rp / Path(filename).name
    if f.exists():
        f.unlink()
    return {"ok": True}


def lock_character(slug, name):
    """Design the character's locked look + render a canonical portrait via ComfyUI.
    Uses InstantID when reference photos are present so the portrait matches the face."""
    from pipeline import config as pcfg, cast as cast_mod, images as img_mod
    b = get_show(slug)
    if not b:
        return {"error": "show not found"}
    show_dir = ROOT / "output" / slug
    cast = cast_mod.design_cast(b, show_dir)  # cached after first run
    info = cast.get(name)
    if not info:
        return {"error": f"no character named {name}"}
    rp, _, cslug = _refs_dir(b, slug, name)
    imgs = [p for p in sorted(rp.iterdir()) if p.suffix.lower() in _IMG_EXT] if rp.exists() else []
    if imgs:
        info["ref"], info["instantid"] = str(imgs[0]), True
    ie = img_mod.ImageEngine(style=pcfg.resolve_style(b.get("visualStyle")))
    if not ie.ready():
        return {"error": "ComfyUI is not running. Start it (cd ~/Desktop/ComfyUI && ./.venv/bin/python main.py) then lock again."}
    pdir = show_dir / "assets" / "characters"
    pdir.mkdir(parents=True, exist_ok=True)
    out = pdir / f"{cslug}.png"
    use_ref = info.get("ref") if (info.get("instantid") and ie.has_instantid) else None
    prompt = (f"character portrait of {name}, {info['look']}, head and shoulders, "
              "looking at camera, plain studio background")
    ie.render(prompt, str(out), ref_image=use_ref, portrait=True, seed=info["seed"])
    info["portrait"] = str(out)
    (show_dir / "assets" / "characters.json").write_text(json.dumps(cast, indent=2))
    return {"ok": True, "portrait": f"/output/{slug}/assets/characters/{cslug}.png?t={int(time.time())}",
            "look": info.get("look", ""), "seed": info.get("seed"),
            "voice": info.get("voice", ""), "usedRef": bool(use_ref)}


# ---------- styles ----------
def save_styles(styles):
    from pipeline import config as pcfg
    payload = {"_comment": "Art styles. name + prompt (appended to every image), optional negative, "
               "optional lora (.safetensors in ComfyUI/models/loras) + lora_weight.", "styles": styles}
    pcfg.STYLES_FILE.write_text(json.dumps(payload, indent=2))
    return {"ok": True, "count": len(styles)}


# ---------- renders ----------
def list_renders():
    out = []
    base = ROOT / "output"
    if base.exists():
        for d in sorted(base.iterdir()):
            bp = d / "bible.json"
            if not bp.exists():
                continue
            try:
                title = json.loads(bp.read_text()).get("title", d.name)
            except Exception:
                title = d.name
            for mp4 in sorted(d.glob("ep*/ep*.mp4")):
                out.append({"slug": d.name, "show": title, "ep": mp4.parent.name,
                            "url": f"/output/{d.name}/{mp4.parent.name}/{mp4.name}"})
    return out


# ---------- image playground ----------
def comfy_models():
    """List the SDXL checkpoints + LoRAs ComfyUI can see, and whether it's running."""
    from pipeline import config as pcfg, images as img_mod
    def names(sub):
        d = pcfg.COMFY_DIR / "models" / sub
        return sorted(p.name for p in d.glob("*.safetensors")) if d.exists() else []
    return {"checkpoints": names("checkpoints"), "loras": names("loras"),
            "default": pcfg.CHECKPOINT, "up": img_mod.Comfy().up()}


_PG_SIZES = {"landscape": (1280, 720), "portrait": (832, 1216), "square": (1024, 1024)}


def playground_generate(p):
    from pipeline import config as pcfg, images as img_mod
    c = img_mod.Comfy()
    if not c.up():
        return {"error": "ComfyUI is not running. Start it (cd ~/Desktop/ComfyUI && ./.venv/bin/python main.py) then generate again."}
    prompt = (p.get("prompt") or "").strip()
    if not prompt:
        return {"error": "prompt is empty"}
    style_prompt, neg = "", pcfg.NEG_PROMPT
    if p.get("style"):
        st = pcfg.resolve_style(p["style"])
        style_prompt = st.get("prompt", "")
        if st.get("negative"):
            neg = st["negative"]
    full = f"{prompt}, {style_prompt}" if style_prompt else prompt
    neg = p.get("negative") or neg
    checkpoint = p.get("checkpoint") or pcfg.CHECKPOINT
    lora = p.get("lora") or None
    lora_w = float(p.get("lora_weight", pcfg.LORA_WEIGHT))
    w, h = _PG_SIZES.get(p.get("size", "landscape"), _PG_SIZES["landscape"])
    seed = int(p["seed"]) if str(p.get("seed", "")).strip() else (int.from_bytes(os.urandom(4), "big") & 0x7FFFFFFF)
    graph = img_mod.txt2img_graph_ex(full, neg, checkpoint, lora, lora_w, w, h, seed)
    pid = c.queue(graph)
    hist = c.wait(pid)
    pdir = ROOT / "output" / "_playground"
    pdir.mkdir(parents=True, exist_ok=True)
    fname = f"{int(time.time())}_{seed}.png"
    c.save_first_image(hist, str(pdir / fname))
    return {"ok": True, "url": f"/output/_playground/{fname}", "seed": seed,
            "checkpoint": checkpoint, "lora": lora, "prompt": prompt}


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=DIR, **k)

    def log_message(self, *a):
        pass

    def _send_json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _proxy(self, method):
        length = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(length) if length else None
        req = urllib.request.Request(OLLAMA + self.path, data=data,
                                     headers={"Content-Type": "application/json"}, method=method)
        try:
            resp = urllib.request.urlopen(req)
        except urllib.error.URLError as e:
            self.send_error(502, f"Ollama not reachable: {e}")
            return
        self.send_response(200)
        self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
        self.end_headers()
        try:
            for line in resp:
                self.wfile.write(line)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        if self.path.startswith("/api/"):
            self._proxy("POST")
        elif self.path == "/build":
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length) or b"{}")
                from pipeline import autocreate, config as pcfg  # lazy: stdlib-only deps
                bible = autocreate.bible_from_brief(payload.get("brief", ""), payload.get("prefs", {}))
                for k, v in (payload.get("prefs") or {}).items():
                    if k in ("title", "genre", "tone", "visualStyle", "setting",
                             "episodeLengthMin", "episodesPerSeason", "generateNow"):
                        bible[k] = v
                slug = pcfg.slugify(bible.get("title", "show"))
                out = pcfg.OUTPUT / slug
                out.mkdir(parents=True, exist_ok=True)
                (out / "bible.json").write_text(json.dumps(bible, indent=2))
                self._send_json({"bible": bible, "path": str(out / "bible.json")})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        elif self.path == "/refs/gather":
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length) or b"{}")
                res = gather_refs(payload.get("entities", []), payload.get("show", "show"),
                                  int(payload.get("per", 3)))
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        elif self.path == "/save":
            try:
                length = int(self.headers.get("Content-Length", 0))
                bible = json.loads(self.rfile.read(length) or b"{}")
                slug = save_show(bible)
                self._send_json({"slug": slug})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        elif self.path == "/render":
            try:
                length = int(self.headers.get("Content-Length", 0))
                p = json.loads(self.rfile.read(length) or b"{}")
                trigger_render(p.get("slug"), int(p.get("episodes", 1)), p.get("shots", "line"))
                self._send_json({"ok": True})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        elif self.path in ("/show/delete", "/characters/upload", "/characters/lock",
                           "/characters/delete-ref", "/styles/save", "/generate"):
            try:
                length = int(self.headers.get("Content-Length", 0))
                p = json.loads(self.rfile.read(length) or b"{}")
                if self.path == "/generate":
                    res = playground_generate(p)
                elif self.path == "/show/delete":
                    res = delete_show(p.get("slug", ""))
                elif self.path == "/characters/upload":
                    res = upload_refs(p.get("slug", ""), p.get("character", ""), p.get("images", []))
                elif self.path == "/characters/lock":
                    res = lock_character(p.get("slug", ""), p.get("character", ""))
                elif self.path == "/characters/delete-ref":
                    res = delete_ref(p.get("slug", ""), p.get("character", ""), p.get("file", ""))
                else:  # /styles/save
                    res = save_styles(p.get("styles", []))
                self._send_json(res, 500 if res.get("error") else 200)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        else:
            self.send_error(404)

    def do_GET(self):
        if self.path.startswith("/api/"):
            self._proxy("GET")
        elif self.path == "/styles":
            try:
                from pipeline import config as pcfg
                self._send_json({"styles": [s["name"] for s in pcfg.load_styles()]})
            except Exception as e:
                self._send_json({"styles": [], "error": str(e)})
        elif self.path == "/styles/full":
            from pipeline import config as pcfg
            self._send_json({"styles": pcfg.load_styles()})
        elif self.path == "/shows":
            self._send_json({"shows": list_shows()})
        elif self.path == "/renders":
            self._send_json({"renders": list_renders()})
        elif self.path == "/comfy/models":
            self._send_json(comfy_models())
        elif self.path.startswith("/characters"):
            q = parse_qs(urlparse(self.path).query)
            slug = (q.get("slug") or [""])[0]
            self._send_json(character_assets(slug))
        elif self.path.startswith("/show"):
            q = parse_qs(urlparse(self.path).query)
            slug = (q.get("slug") or [""])[0]
            show = get_show(slug)
            self._send_json(show or {"error": "not found"}, 200 if show else 404)
        else:
            super().do_GET()


if __name__ == "__main__":
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"\n  🎬  Show Factory  →  http://127.0.0.1:{PORT}\n  (Ctrl+C to stop)\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  bye 👋\n")
