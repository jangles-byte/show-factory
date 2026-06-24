"""Render stage: dialogue + Kokoro -> a captioned episode .mp4.

This build of ffmpeg has no text filters (no libass/drawtext), so captions are
drawn as full frames with Pillow; ffmpeg only concatenates + muxes audio.
"""
import hashlib
import re
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

from . import config

BG = (15, 17, 21)
PANEL = (24, 28, 37)
TITLE_COL = (150, 158, 176)
SCENE_COL = (200, 176, 160)
TEXT_COL = (235, 238, 246)


def _font(size):
    return ImageFont.truetype(config.FONT, size)


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_") or "x"


def _color(name):
    h = hashlib.md5(name.encode()).hexdigest()
    return (int(h[0:2], 16) | 0x70, int(h[2:4], 16) | 0x70, int(h[4:6], 16) | 0x70)


def _crop_region(img, pos):
    """Crop the master set to a character's blocked side, sized to the video frame."""
    w, h = img.size
    if pos == "left":
        box = (0, 0, int(w * 0.60), h)
    elif pos == "right":
        box = (int(w * 0.40), 0, w, h)
    else:
        box = (int(w * 0.20), 0, int(w * 0.80), h)
    return img.crop(box).resize((config.VIDEO_W, config.VIDEO_H))


def _wrap(draw, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _render_frame(path, bg_path, title, scene_loc, speaker, text, spk_rgb):
    W, H = config.VIDEO_W, config.VIDEO_H
    if bg_path and Path(bg_path).exists():
        base = Image.open(bg_path).convert("RGB").resize((W, H))
    else:
        base = Image.new("RGB", (W, H), BG)
    base = base.convert("RGBA")

    # scrims for legibility: dark band top (title) + gradient bottom (caption)
    scrim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scrim)
    sd.rectangle([0, 0, W, 150], fill=(8, 9, 12, 150))
    for i in range(240):
        sd.line([(0, H - 240 + i), (W, H - 240 + i)], fill=(8, 9, 12, int(210 * i / 240)))
    base = Image.alpha_composite(base, scrim)

    d = ImageDraw.Draw(base)
    d.text((W / 2, 40), title, font=_font(28), fill=(230, 230, 235), anchor="ma")
    if scene_loc:
        d.text((W / 2, 92), scene_loc.upper(), font=_font(22), fill=(222, 212, 200), anchor="ma")

    name_f, txt_f = _font(40), _font(34)
    line_h = 46
    lines = _wrap(d, text, txt_f, W - 260)
    block_h = 56 + len(lines) * line_h
    top = H - block_h - 70

    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(panel).rounded_rectangle([90, top - 30, W - 90, H - 52], radius=22, fill=(10, 11, 14, 205))
    base = Image.alpha_composite(base, panel)

    d = ImageDraw.Draw(base)
    y = top
    d.text((W / 2, y), speaker, font=name_f, fill=spk_rgb, anchor="ma")
    y += 60
    for ln in lines:
        d.text((W / 2, y), ln, font=txt_f, fill=TEXT_COL, anchor="ma")
        y += line_h
    base.convert("RGB").save(path)


def build_episode(ep_dir, script, voicemap, engine, title, img_engine=None, cast=None, shots="line"):
    ep_dir = Path(ep_dir)
    lines_dir, frames_dir = ep_dir / "lines", ep_dir / "frames"
    scenes_dir, shots_dir = ep_dir / "scenes", ep_dir / "shots"
    for p in (lines_dir, frames_dir, scenes_dir, shots_dir):
        p.mkdir(parents=True, exist_ok=True)
    cast = cast or {}

    gap = np.zeros(int(config.SR * config.GAP), dtype=np.float32)
    track, concat = [], []
    idx, total = 0, 0.0
    disp_title = title[:80]

    for si, scene in enumerate(script["scenes"], 1):
        loc = scene.get("location", "")
        set_desc = scene.get("set") or scene.get("summary", "") or loc
        blocking = scene.get("blocking", {}) or {}

        # --- the SET: one master establishing image per scene with characters blocked in ---
        master = None
        if img_engine and shots in ("scene", "line"):
            mp = scenes_dir / f"{si:02d}.png"
            if not mp.exists():
                people = []
                for nm, b in blocking.items():
                    cdn = cast.get(nm)
                    people.append(f"{cdn['look'] if cdn else nm} on the {b.get('pos','center')}")
                mprompt = f"wide establishing shot, {set_desc}."
                if people:
                    mprompt += " " + "; ".join(people) + "."
                try:
                    print(f"      set {si}/{len(script['scenes'])}: {loc}")
                    img_engine.render(mprompt, str(mp))
                except Exception as e:
                    print(f"      (set image failed: {e})")
            master = str(mp) if mp.exists() else None

        for line in scene["lines"]:
            spk, text = line["speaker"], line["text"].strip()
            if not text:
                continue
            voice = voicemap.get(spk, config.FEMALE_VOICES[0])
            idx += 1
            wav = lines_dir / f"{idx:04d}_{_slug(spk)}.wav"
            dur = engine.render(text, voice, wav)
            samples, _ = sf.read(str(wav), dtype="float32")
            track.append(samples)
            track.append(gap.copy())

            bg = master  # scene mode shows the whole set
            if img_engine and shots == "line":
                cd = cast.get(spk)
                look = cd["look"] if cd else spk
                b = blocking.get(spk, {})
                pos, facing = b.get("pos", "center"), b.get("facing", "forward")
                shot_txt = line.get("shot") or scene.get("summary", "")
                seed = (cd["seed"] + idx) if cd else None
                sp = shots_dir / f"{idx:04d}.png"
                if not sp.exists():
                    try:
                        print(f"      shot {idx}: {spk} ({pos}) — {shot_txt[:42]}")
                        if cd and cd.get("instantid"):  # real person: identity via InstantID
                            img_engine.render(f"{look}, on the {pos}, facing {facing}. {shot_txt}. {set_desc}",
                                              str(sp), ref_image=cd.get("ref"), seed=seed)
                        elif master:  # crop the speaker's side of the set, refine -> same space
                            crop = _crop_region(Image.open(master).convert("RGB"), pos)
                            ctmp = shots_dir / f"_crop_{idx:04d}.png"
                            crop.save(ctmp)
                            img_engine.render(f"{look}, facing {facing}. {shot_txt}.", str(sp),
                                              init_image=str(ctmp), denoise=config.SHOT_DENOISE, seed=seed)
                            ctmp.unlink(missing_ok=True)
                        else:
                            img_engine.render(f"{look}. {shot_txt}. {set_desc}", str(sp), seed=seed)
                    except Exception as e:
                        print(f"      (shot failed: {e})")
                if sp.exists():
                    bg = str(sp)

            frame = frames_dir / f"{idx:04d}.png"
            _render_frame(frame, bg, disp_title, loc, spk, text, _color(spk))
            concat.append((frame, dur + config.GAP))
            total += dur + config.GAP

    full = np.concatenate(track) if track else np.zeros(1, dtype=np.float32)
    sf.write(str(ep_dir / "audio.wav"), full, config.SR)

    # ffmpeg concat demuxer list (last entry repeated, per the format's rules)
    lst = ep_dir / "frames.txt"
    rows = []
    for f, d in concat:
        rows += [f"file '{f}'", f"duration {d:.3f}"]
    if concat:
        rows.append(f"file '{concat[-1][0]}'")
    lst.write_text("\n".join(rows) + "\n")

    out = ep_dir / f"{ep_dir.name}.mp4"
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(lst),
        "-i", str(ep_dir / "audio.wav"),
        "-r", "25", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-shortest", str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg failed:\n" + proc.stderr[-1500:])
    return out, total, idx
