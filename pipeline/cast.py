"""Casting stage: give each character a locked visual design (so they look the
same every shot) + render a portrait asset. Real people (with a reference pack
in refs/<show>/<name>/) use InstantID; everyone else is txt2img with a fixed seed.
"""
import hashlib
import json
from pathlib import Path

from . import config, llm


def _seed(name):
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16) % 2_000_000


def design_cast(bible, show_dir):
    """Return {name: {look, seed, ref?, instantid?}} and cache it."""
    af = show_dir / "assets" / "characters.json"
    if af.exists():
        return json.loads(af.read_text())

    refs_base = config.ROOT / "refs" / config.slugify(bible.get("title", "show"))
    cast = {}
    fi = mi = 0  # round-robin within each voice pool so voices stay distinct
    for c in bible.get("cast", []):
        name = c["name"]
        sys = {"role": "system", "content": "You are a character designer. Output ONLY JSON."}
        usr = {"role": "user", "content":
               f"Show: {bible.get('title')} ({bible.get('genre')}, {bible.get('tone')}). "
               f"Visual style: {bible.get('visualStyle')}.\n"
               f"Character: {name} — {c.get('role','')}; {c.get('personality','')}.\n"
               "Give: a SHORT consistent visual description so an artist draws this character identically "
               "every time (apparent age, build, hair, face, signature outfit, palette; one vivid sentence, "
               "no name); and their voice gender.\n"
               'Return JSON: {"look":"...","gender":"male|female"}'}
        try:
            res = llm.chat_json([sys, usr], temperature=0.4)
        except Exception:
            res = {}
        look = (res.get("look") or f"{c.get('personality','')} {c.get('role','')}").strip()
        gender = (c.get("gender") or res.get("gender") or "").strip().lower()
        entry = {"look": look or name, "seed": _seed(name), "gender": gender or "?"}

        # gender-matched voice (explicit bible voice wins)
        if c.get("voice"):
            entry["voice"] = c["voice"]
        elif gender.startswith("m"):
            entry["voice"] = config.MALE_VOICES[mi % len(config.MALE_VOICES)]; mi += 1
        elif gender.startswith("f"):
            entry["voice"] = config.FEMALE_VOICES[fi % len(config.FEMALE_VOICES)]; fi += 1
        elif (fi + mi) % 2 == 0:
            entry["voice"] = config.FEMALE_VOICES[fi % len(config.FEMALE_VOICES)]; fi += 1
        else:
            entry["voice"] = config.MALE_VOICES[mi % len(config.MALE_VOICES)]; mi += 1

        rp = refs_base / config.slugify(name)
        imgs = (sorted(rp.glob("*.jpg")) + sorted(rp.glob("*.png")) + sorted(rp.glob("*.jpeg"))) if rp.exists() else []
        if imgs:
            entry["ref"] = str(imgs[0])
            entry["instantid"] = True
        cast[name] = entry

    af.parent.mkdir(parents=True, exist_ok=True)
    af.write_text(json.dumps(cast, indent=2))
    return cast


def render_portraits(bible, cast, show_dir, img_engine):
    """Render one canonical portrait per character (the 'asset')."""
    if not img_engine:
        return cast
    pdir = show_dir / "assets" / "characters"
    pdir.mkdir(parents=True, exist_ok=True)
    for name, info in cast.items():
        out = pdir / f"{config.slugify(name)}.png"
        if out.exists():
            info["portrait"] = str(out)
            continue
        prompt = f"character portrait of {name}, {info['look']}, head and shoulders, looking at camera, plain studio background"
        try:
            print(f"    portrait: {name}")
            img_engine.render(prompt, str(out),
                              ref_image=(info.get("ref") if info.get("instantid") else None),
                              portrait=True, seed=info["seed"])
            info["portrait"] = str(out)
        except Exception as e:
            print(f"    (portrait failed for {name}: {e})")
    (show_dir / "assets" / "characters.json").write_text(json.dumps(cast, indent=2))
    return cast
