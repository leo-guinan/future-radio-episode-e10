#!/usr/bin/env python3
"""Checks the harness's guarantees using the mock provider (free, no network).

  python3 lab/selftest.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = [sys.executable, os.path.join(ROOT, "lab", "run_take.py")]
tmp = tempfile.mkdtemp(prefix="lab-selftest-")
failures = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        failures.append(msg)


def run(*extra):
    return subprocess.run(RUN + ["S05", "a", "--provider", "mock", "--runs-dir", tmp,
                                 "--min-turns", "3", "--max-turns", "8", *extra],
                          capture_output=True, text=True)


def calls(folder):
    return [json.loads(l) for l in open(os.path.join(folder, "calls.jsonl"))]


try:
    r = run()
    check(r.returncode == 0, "take runs end to end: " + (r.stdout.strip() or r.stderr.strip()).splitlines()[-1])
    take = os.path.join(tmp, "S05", "variation-a")
    for f in ["take.json", "transcript.jsonl", "final-state.json", "eval.json", "commentary.md", "scene-card.md", "calls.jsonl"]:
        check(os.path.exists(os.path.join(take, f)), f"take wrote {f}")

    cs = calls(take)
    actors = [c for c in cs if c["kind"] == "actor"]
    commentary = [c["reply"] for c in cs if c["kind"] == "eval_live"]
    leaked = [c for c in actors + [c for c in cs if c["kind"] in ("final_state",)]
              if any(x in c["system"] + c["user"] for x in commentary) or "commentary" in (c["system"] + c["user"]).lower()]
    check(commentary and not leaked, f"EVAL's {len(commentary)} live comments never reach any actor prompt")
    check(all("mock summary" not in c["system"] + c["user"] for c in actors), "actors never see EVAL's assessment during the scene")
    kinds = [c["kind"] for c in cs]
    check(kinds.index("eval_final") > max(i for i, k in enumerate(kinds) if k == "actor"), "assessment is written after the last performed turn")
    others = [c for c in actors if "private" in c["system"].lower()]
    check(len(actors) >= 3, f"{len(actors)} actor turns recorded; director stopped the scene early" if len(actors) < 8 else "ran to turn budget")

    check(not os.access(os.path.join(take, "eval.json"), os.W_OK) or os.geteuid() == 0, "eval.json is read-only (root can still write; mode checked next)")
    check(oct(os.stat(os.path.join(take, "eval.json")).st_mode & 0o777) == "0o444", "eval.json mode is 0444")
    check("INVENTED LINE" not in open(os.path.join(take, "scene-card.md")).read(), "scene card drops anchors that aren't exact quotations")
    t = json.load(open(os.path.join(take, "take.json")))
    check(set(t["record"]["bible_commits"]) >= {"leonardo", "borges", "agnolo", "simulated-human", "eval"}, "take.json pins every bible")
    check(t["record"]["prompt_versions"] and t["record"]["model"] == "mock", "take.json records prompt versions and model")
    check(t["record"]["cost_usd"] is None, "cost stays null while prices are unknown")

    again = run()
    check(again.returncode != 0 and "append-only" in again.stderr + again.stdout, "re-running an existing take is refused")

    before = open(os.path.join(take, "eval.json")).read()
    rv = run("--review", "--review-turns", "5")
    check(rv.returncode == 0, "review room runs: " + (rv.stdout.strip() or rv.stderr.strip()).splitlines()[-1])
    rev = os.path.join(tmp, "S05", "variation-a-review")
    rcalls = calls(rev)
    ractors = [c for c in rcalls if c["kind"] == "review_actor"]
    check(ractors and all("mock summary" in c["user"] for c in ractors), "after the curtain, the cast receives EVAL's review")
    check(open(os.path.join(take, "eval.json")).read() == before, "original assessment untouched by the review")
    check(os.path.exists(os.path.join(rev, "eval-revised.json")), "revision is a separate entry")
    check(json.load(open(os.path.join(rev, "eval-revised.json")))["original_eval_sha256"], "revision cites the original's hash")
    check(not os.path.exists(os.path.join(rev, "commentary.md")), "EVAL is a participant in the review room, not a hidden commentator")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\n" + ("all checks passed" if not failures else f"{len(failures)} check(s) failed"))
sys.exit(1 if failures else 0)
