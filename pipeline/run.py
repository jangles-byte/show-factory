"""Orchestrator / season printer:  Show Bible -> episode .mp4 files."""
import argparse
import json
import shutil
import sys
from pathlib import Path

from . import config, write, voices, render, images, cast as cast_mod


def main():
    ap = argparse.ArgumentParser(description="Show Factory — print episodes from a Show Bible.")
    ap.add_argument("--bible", required=True, help="path to a Show Bible JSON")
    ap.add_argument("--episodes", type=int, default=0, help="how many to make now (default: bible.generateNow or 1)")
    ap.add_argument("--no-images", action="store_true", help="skip ComfyUI art; use plain captioned frames")
    ap.add_argument("--shots", choices=["line", "scene", "none"], default="line",
                    help="line = a shot per dialogue line (rich, slow); scene = one image per scene (fast); none = no art")
    args = ap.parse_args()

    bible = json.loads(Path(args.bible).read_text())
    title = bible.get("title", "Untitled Show")
    show_dir = config.OUTPUT / config.slugify(title)
    show_dir.mkdir(parents=True, exist_ok=True)
    src, dst = Path(args.bible).resolve(), (show_dir / "bible.json").resolve()
    if src != dst:
        shutil.copy(src, dst)

    n = args.episodes or int(bible.get("generateNow", 1))
    print(f"\n🎬  {title}  —  printing {n} episode(s)\n")

    img_engine = None
    if not args.no_images:
        try:
            style = config.resolve_style(bible.get("visualStyle"))
            ie = images.ImageEngine(style=style)
            if ie.ready():
                img_engine = ie
                print(f"  image engine: ComfyUI ✓  (style={ie.style_name}, lora={ie.lora}, instantid={ie.has_instantid})")
            else:
                print("  image engine: ComfyUI not running → plain captioned frames")
        except Exception as e:
            print(f"  image engine off: {e}")

    shots_mode = "none" if (args.no_images or not img_engine) else args.shots

    print("\n  casting…")
    cast = cast_mod.design_cast(bible, show_dir)
    cast_mod.render_portraits(bible, cast, show_dir, img_engine)
    voicemap = {name: (info.get("voice") or config.FEMALE_VOICES[0]) for name, info in cast.items()}
    for name, info in cast.items():
        tag = " [InstantID]" if info.get("instantid") else ""
        print(f"    {name:14s} {info.get('gender','?'):6s} -> {info.get('voice','?'):14s}{tag}")

    print("\n  loading voice engine…")
    engine = voices.VoiceEngine()

    listed = bible.get("episodes", [])
    made = []
    prior_titles = []
    for i in range(n):
        if i < len(listed):
            ep = listed[i]
        else:
            print(f"    (inventing episode {i+1} from season arc)")
            ep = write.invent_episode(bible, i + 1, prior_titles)
        prior_titles.append(ep.get("title", ""))
        epnum = int(ep.get("number", i + 1))
        ep_dir = show_dir / f"ep{epnum:02d}"
        ep_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n  ── Episode {epnum}: {ep.get('title','')} ──")
        script = write.write_episode(bible, ep)
        (ep_dir / "script.json").write_text(json.dumps(script, indent=2))

        title_str = f"{title} — Ep {epnum}: {ep.get('title','')}"
        mp4, dur, nlines = render.build_episode(ep_dir, script, voicemap, engine, title_str,
                                                img_engine=img_engine, cast=cast, shots=shots_mode)
        print(f"    ✅ {mp4}  ({dur:.0f}s, {nlines} lines)")
        made.append(mp4)

    print("\n🎉 done. Episodes:")
    for m in made:
        print(f"   {m}")
    if made:
        print(f"\n▶  play:  afplay '{made[0].with_suffix('.mp4')}'  (or open in a video player)")


if __name__ == "__main__":
    sys.exit(main())
