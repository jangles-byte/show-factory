"""Writing stage: a Show Bible episode -> a full scene-by-scene script with dialogue."""
import json

from . import config, llm


def _cast_block(bible):
    out = []
    for c in bible.get("cast", []):
        out.append(f"- {c['name']} ({c.get('role','')}): {c.get('personality','')}. "
                   f"Wants: {c.get('wants','')}. Secret: {c.get('secret','')}")
    return "\n".join(out)


def _names(bible):
    return [c["name"] for c in bible.get("cast", [])]


def scene_breakdown(bible, episode, n_scenes):
    sys = {"role": "system", "content": "You are a professional TV scriptwriter. Output ONLY valid JSON."}
    usr = {"role": "user", "content": f"""SHOW: {bible.get('title')} — {bible.get('genre')} ({bible.get('tone')})
SETTING: {bible.get('setting')}
CAST:
{_cast_block(bible)}

EPISODE {episode.get('number')}: {episode.get('title','')}
PREMISE: {episode.get('premise','')}
BEATS: {', '.join(episode.get('beats', []))}

Break this episode into exactly {n_scenes} scenes that hit the beats and build to a hook at the end.
Return JSON: {{"scenes": [{{"location": "short place", "summary": "1 sentence of what happens"}}]}}"""}
    data = llm.chat_json([sys, usr], temperature=0.7)
    scenes = data.get("scenes", [])[:n_scenes]
    return scenes or [{"location": bible.get("setting", "the villa"), "summary": episode.get("premise", "")}]


def scene_dialogue(bible, episode, scene, recap, n_lines):
    names = _names(bible)
    sys = {"role": "system", "content": "You are a professional TV scriptwriter. Output ONLY valid JSON."}
    usr = {"role": "user", "content": f"""SHOW: {bible.get('title')} ({bible.get('tone')})
CAST (use ONLY these names as speakers): {', '.join(names)}
CHARACTERS:
{_cast_block(bible)}

STORY SO FAR: {recap or '(this is the start)'}

CURRENT SCENE — {scene.get('location')}: {scene.get('summary')}

Write natural spoken dialogue for THIS scene, about {n_lines} lines.
Rules: speakers must be exactly one of {names}. Keep each line short and speakable (it will be read by text-to-speech) — NO stage directions, asterisks, or narration inside the "text". Make it match the tone.
For EACH line also give a "shot": a brief visual description of that exact moment for the artist — the speaker's expression and action, and the framing (close-up / medium / wide). And "onscreen": the character names visible in that shot.
Return JSON: {{"lines": [{{"speaker": "Name", "text": "what they say", "emotion": "one word", "shot": "e.g. close-up of Maya smirking, leaning in", "onscreen": ["Maya"]}}]}}"""}
    data = llm.chat_json([sys, usr], temperature=0.9)
    lines = []
    for ln in data.get("lines", []):
        spk = ln.get("speaker", "").strip()
        txt = (ln.get("text") or "").strip()
        if not txt:
            continue
        if spk not in names and names:
            spk = names[0]
        onscreen = ln.get("onscreen") or [spk]
        lines.append({"speaker": spk, "text": txt, "emotion": ln.get("emotion", ""),
                      "shot": (ln.get("shot") or "").strip(), "onscreen": onscreen})
    return lines


def scene_staging(bible, scene, present):
    """Storyboard/blocking: a concrete SET description + where each character stands & faces."""
    sys = {"role": "system", "content": "You are a storyboard artist / cinematographer. Output ONLY JSON."}
    usr = {"role": "user", "content":
           f"Scene location: {scene.get('location')}. What happens: {scene.get('summary')}. "
           f"Characters present: {', '.join(present) or 'none'}.\n"
           "Give the SET as one vivid concrete visual sentence (environment, time of day, key props, mood). "
           "Then BLOCK each present character with a screen position (left, center, or right) and a facing "
           "(left, right, or forward) so shot/reverse-shot stays spatially consistent (people who talk to each "
           "other should face toward one another).\n"
           'Return JSON: {"set":"...","blocking":{"Name":{"pos":"left|center|right","facing":"left|right|forward"}}}'}
    try:
        d = llm.chat_json([sys, usr], temperature=0.4)
    except Exception:
        d = {}
    return (d.get("set") or "").strip(), (d.get("blocking") or {})


def write_episode(bible, episode):
    length = max(1, int(bible.get("episodeLengthMin", 5)))
    n_scenes = max(2, min(6, round(length * 0.8)))
    total_lines = length * 12
    per_scene = max(4, round(total_lines / n_scenes))

    print(f"    scripting Ep {episode.get('number')}: {n_scenes} scenes, ~{per_scene} lines each")
    scenes = scene_breakdown(bible, episode, n_scenes)

    recap_bits, full_scenes = [], []
    for i, sc in enumerate(scenes, 1):
        print(f"      scene {i}/{len(scenes)}: {sc.get('location')}")
        lines = scene_dialogue(bible, episode, sc, " ".join(recap_bits), per_scene)
        present = list(dict.fromkeys(l["speaker"] for l in lines))
        set_desc, blocking = scene_staging(bible, sc, present)
        full_scenes.append({"location": sc.get("location", ""), "summary": sc.get("summary", ""),
                            "set": set_desc, "blocking": blocking, "lines": lines})
        recap_bits.append(sc.get("summary", ""))

    return {
        "number": episode.get("number"),
        "title": episode.get("title", ""),
        "premise": episode.get("premise", ""),
        "scenes": full_scenes,
    }


def invent_episode(bible, number, prior_titles):
    """When the Bible doesn't list enough episodes, generate one from the season arc."""
    sys = {"role": "system", "content": "You are a TV showrunner. Output ONLY valid JSON."}
    usr = {"role": "user", "content": f"""SHOW: {bible.get('title')} — {bible.get('genre')} ({bible.get('tone')})
SEASON ARC: {bible.get('seasonArc','')}
EPISODE ENGINE: {bible.get('episodeEngine','')}
CAST: {', '.join(_names(bible))}
ALREADY WRITTEN: {', '.join(prior_titles) or '(none)'}

Invent episode {number}, advancing the arc and not repeating earlier episodes.
Return JSON: {{"number": {number}, "title": "...", "premise": "...", "beats": ["...","...","..."]}}"""}
    ep = llm.chat_json([sys, usr], temperature=0.9)
    ep["number"] = number
    return ep
