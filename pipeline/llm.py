"""Tiny Ollama client (stdlib only). Talks to local Gemma."""
import json
import re
import urllib.request

from . import config


def chat(messages, model=None, temperature=0.8, as_json=False, timeout=600):
    body = {
        "model": model or config.WRITER_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if as_json:
        body["format"] = "json"
    req = urllib.request.Request(
        config.OLLAMA + "/api/chat",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())["message"]["content"]


def _extract_json(s: str):
    s = s.strip()
    if s.startswith("```"):
        s = s.strip("`")
    a, b = s.find("{"), s.rfind("}")
    if a != -1 and b != -1:
        s = s[a:b + 1]
    s = re.sub(r",(\s*[}\]])", r"\1", s)  # tolerate trailing commas
    return json.loads(s)


def chat_json(messages, tries=3, **kw):
    """Chat and parse a JSON object back, retrying with a repair nudge."""
    kw.pop("as_json", None)
    last = ""
    for i in range(tries):
        msgs = messages if i == 0 else messages + [
            {"role": "assistant", "content": last[:4000]},
            {"role": "user", "content": "That JSON was invalid/incomplete. Return ONLY one corrected, complete JSON object."},
        ]
        last = chat(msgs, as_json=True, **kw)
        try:
            return _extract_json(last)
        except Exception:
            continue
    raise ValueError(f"model did not return valid JSON after {tries} tries")
