"""Headless 'describe a show -> get episodes'. This is the control path:
give a brief (+ optional knobs), Gemma writes the full Show Bible, then render.

  python -m pipeline.autocreate --brief "noir detective cartoon, 1940s LA, tired PI named Sam Vane" \
      --cast 3 --length 2 --episodes 1 --render
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from . import config, llm

def bible_from_brief(brief, prefs=None):
    """Build the Show Bible in small, reliable chunks (core -> cast -> episodes)."""
    prefs = prefs or {}
    cast_size = int(prefs.get("castSize") or 4)
    gen_now = int(prefs.get("generateNow") or 1)

    # 1) show core (small JSON)
    core_schema = ('{"title":str,"logline":str,"genre":str,"tone":str,"visualStyle":str,'
                   '"setting":str,"mode":"authored","episodeLengthMin":num,"episodesPerSeason":num,'
                   '"generateNow":num,"episodeEngine":str,"seasonArc":str}')
    core = llm.chat_json([
        {"role": "system", "content": "You are a veteran TV showrunner. Output ONLY JSON."},
        {"role": "user", "content":
            f"Design the core of a show from this brief. Don't assume a genre beyond what the brief implies.\n"
            f"BRIEF: {brief}\nPREFERENCES: {json.dumps(prefs)}\n"
            f"episodeEngine = what generates a fresh episode each time; seasonArc = the throughline.\n"
            f"Return ONLY JSON: {core_schema}"}], temperature=0.8)
    core.setdefault("mode", "authored")

    # 2) cast (small JSON)
    cast = llm.chat_json([
        {"role": "system", "content": "You are a character designer. Output ONLY JSON."},
        {"role": "user", "content":
            f"Show: {core.get('title')} — {core.get('genre')} ({core.get('tone')}). Setting: {core.get('setting')}.\n"
            f"ORIGINAL BRIEF (use any characters it names, with those exact names): {brief}\n"
            f"Create {cast_size} distinct main characters, each with a clear want and a secret.\n"
            f'Return ONLY JSON: {{"cast":[{{"name":str,"role":str,"personality":str,"wants":str,"secret":str}}]}}'}],
        temperature=0.8).get("cast", [])

    # 3) episodes (small JSON)
    eps = llm.chat_json([
        {"role": "system", "content": "You are a TV writer. Output ONLY JSON."},
        {"role": "user", "content":
            f"Show: {core.get('title')} ({core.get('genre')}, {core.get('tone')}). "
            f"Engine: {core.get('episodeEngine')}. Arc: {core.get('seasonArc')}. "
            f"Cast: {', '.join(c.get('name','') for c in cast)}.\n"
            f"Write {gen_now} distinct episode(s), each with 3-5 beats.\n"
            f'Return ONLY JSON: {{"episodes":[{{"number":num,"title":str,"premise":str,"beats":[str]}}]}}'}],
        temperature=0.85).get("episodes", [])

    bible = dict(core)
    bible["cast"] = cast
    bible["episodes"] = eps
    return bible


def main():
    ap = argparse.ArgumentParser(description="Describe a show -> Show Bible (-> render).")
    ap.add_argument("--brief", required=True)
    ap.add_argument("--genre"); ap.add_argument("--tone"); ap.add_argument("--style")
    ap.add_argument("--setting"); ap.add_argument("--title")
    ap.add_argument("--length", type=int); ap.add_argument("--cast", type=int)
    ap.add_argument("--per-season", type=int, dest="per_season")
    ap.add_argument("--episodes", type=int, default=1)
    ap.add_argument("--render", action="store_true", help="also render the episode(s) after writing the bible")
    ap.add_argument("--shots", choices=["line", "scene", "none"], default="line")
    ap.add_argument("--no-images", action="store_true")
    a = ap.parse_args()

    prefs = {k: v for k, v in {
        "title": a.title, "genre": a.genre, "tone": a.tone, "visualStyle": a.style, "setting": a.setting,
        "episodeLengthMin": a.length, "castSize": a.cast, "episodesPerSeason": a.per_season,
        "generateNow": a.episodes,
    }.items() if v is not None}

    print(f"🧠  writing bible from brief…")
    bible = bible_from_brief(a.brief, prefs)
    # hard-apply explicit overrides so knobs always win
    for k in ("title", "genre", "tone", "visualStyle", "setting",
              "episodeLengthMin", "episodesPerSeason", "generateNow"):
        if k in prefs:
            bible[k] = prefs[k]

    slug = config.slugify(bible.get("title", "show"))
    out = config.OUTPUT / slug
    out.mkdir(parents=True, exist_ok=True)
    bp = out / "bible.json"
    bp.write_text(json.dumps(bible, indent=2))
    print(f"📖  {bible.get('title')}  →  {bp}")
    print(f"    {bible.get('logline','')}")
    print(f"    cast: {', '.join(c['name'] for c in bible.get('cast', []))}")

    if a.render:
        cmd = [sys.executable, "-m", "pipeline.run", "--bible", str(bp),
               "--episodes", str(a.episodes), "--shots", a.shots]
        if a.no_images:
            cmd.append("--no-images")
        print(f"\n🎬  rendering…\n")
        subprocess.run(cmd, cwd=str(config.ROOT))


if __name__ == "__main__":
    sys.exit(main())
