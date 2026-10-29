"""Minimal LLM client for the scene laboratory. No dependencies.

Providers:
  anthropic  needs ANTHROPIC_API_KEY in the environment; model from --model or LAB_MODEL
  mock       deterministic canned replies, for testing the harness without spending anything
"""
import json
import os
import re
import urllib.error
import urllib.request

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-5-5"


class LLMError(RuntimeError):
    pass


_mock_n = {"n": 0}


def complete(provider, model, system, user, kind, max_tokens=700, temperature=None):
    """Return (text, usage). usage = {"in": int, "out": int}."""
    if provider == "mock":
        return _mock(kind, system, user)
    if provider != "anthropic":
        raise LLMError(f"unknown provider {provider!r}")
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise LLMError("ANTHROPIC_API_KEY is not set in the environment")
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": user}],
    }
    if system:
        body["system"] = system
    if temperature is not None:
        body["temperature"] = temperature
    req = urllib.request.Request(
        API_URL,
        json.dumps(body).encode(),
        {"content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        raise LLMError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}")
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    u = data.get("usage", {})
    return text, {"in": u.get("input_tokens", 0), "out": u.get("output_tokens", 0)}


def extract_json(text):
    """Pull the first JSON object out of a model reply."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise LLMError(f"no JSON object in reply: {text[:200]!r}")
    return json.loads(m.group(0))


# ---- mock -----------------------------------------------------------------

def _mock(kind, system, user):
    _mock_n["n"] += 1
    n = _mock_n["n"]
    usage = {"in": len(system + user) // 4, "out": 40}
    turns = re.findall(r"^\[(\d+)\] ([A-Z\- ]+): (.*)$", user, re.M)
    if kind in ("actor", "review_actor"):
        return f"MOCKLINE-{n}: a line spoken in character.", usage
    if kind == "eval_live":
        return f"COMMENTARY-{n}: interesting beat.", usage
    if kind == "review_eval":
        return f"REVIEWLINE-{n}: my assessment stands, mostly.", usage
    if kind == "director":
        return json.dumps({"met": len(turns) >= 6, "reason": "mock director"}), usage
    if kind in ("eval_final", "eval_revised"):
        crit = re.findall(r"^- ([a-z\-]+) \(weight (\d+)\)", user, re.M)
        out = {"scores": {c: int(w) // 2 for c, w in crit},
               "summary": "mock summary", "surprised": "mock", "lost_its_way": "mock",
               "smallest_change": "mock constraint"}
        if kind == "eval_revised":
            out.update({"revised": True, "what_changed": "mock", "next_take": "mock"})
        return json.dumps(out), usage
    if kind == "final_state":
        return json.dumps({"believed": ["mock belief"], "imagined": [], "wants_now": "mock", "changed": "mock"}), usage
    if kind == "scene_card":
        first = turns[0][2] if turns else ""
        return json.dumps({"beats": ["mock beat one", "mock beat two", "mock beat three"],
                           "anchors": [{"turn": 1, "text": first}, {"turn": 99, "text": "INVENTED LINE"}],
                           "not_in_setup": "nothing"}), usage
    raise LLMError(f"mock has no reply for kind {kind!r}")
