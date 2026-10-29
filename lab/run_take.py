#!/usr/bin/env python3
"""Run one take of a scene, or the review room that follows it.

  python3 lab/run_take.py S05 a                     # take: runs/S05/variation-a/
  python3 lab/run_take.py S05 a --review            # review room: runs/S05/variation-a-review/
  python3 lab/run_take.py S05 a --provider mock     # free dry run of the machinery

Architecture (see DESIGN.md): the cast hears only the cast. EVAL's live commentary goes to
commentary.md and is never passed to any actor prompt. The assessment is written and locked
(read-only) before the cast sees it. A take never overwrites another take, and every call
is logged to calls.jsonl so a run can be replayed and audited.
"""
import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import re
import stat
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import llm  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAB = os.path.join(ROOT, "lab")

LAB_NOTE = ("Your character profile was written for earlier production work. Its Job and Hard constraints "
            "describe your usual duties and values; in this scene, act from who you are, what you want and "
            "what you believe.")


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def load_json(path):
    with open(path) as f:
        return json.load(f)


def write_text(path, text, mode="w"):
    with open(path, mode) as f:
        f.write(text)


def render(_tpl, /, **kw):
    text = open(os.path.join(LAB, "prompts", _tpl + ".md")).read()
    for k, v in kw.items():
        text = text.replace("{{" + k + "}}", str(v))
    left = re.findall(r"\{\{\w+\}\}", text)
    if left:
        raise SystemExit(f"prompt {_tpl}: unfilled placeholders {left}")
    return text


def prompt_versions():
    out = {}
    for p in sorted(glob.glob(os.path.join(LAB, "prompts", "*.md"))):
        out[os.path.basename(p)[:-3]] = sha_bytes(open(p, "rb").read())[:12]
    return out


def name_of(cid):
    return cid.replace("-", " ").upper()


def transcript_text(rows):
    return "\n".join(f"[{r['turn']}] {r['speaker_name']}: {r['text']}" for r in rows)


class Take:
    def __init__(self, folder, provider, model, temperature):
        self.folder, self.provider, self.model, self.temperature = folder, provider, model, temperature
        self.tokens = {"in": 0, "out": 0}

    def call(self, kind, system, user, max_tokens=700):
        text, usage = llm.complete(self.provider, self.model, system, user, kind, max_tokens, self.temperature)
        self.tokens["in"] += usage["in"]
        self.tokens["out"] += usage["out"]
        write_text(os.path.join(self.folder, "calls.jsonl"),
                   json.dumps({"ts": now(), "kind": kind, "system": system, "user": user,
                               "reply": text, "usage": usage}, ensure_ascii=False) + "\n", "a")
        return text.strip()

    def call_json(self, kind, system, user, max_tokens=900):
        text = self.call(kind, system, user, max_tokens)
        try:
            return llm.extract_json(text), text
        except Exception as e:  # keep the raw reply rather than failing the whole take
            return {"error": str(e), "raw": text}, text

    def cost(self):
        prices = load_json(os.path.join(LAB, "prices.json")).get(self.model, {})
        pin, pout = prices.get("in_per_mtok"), prices.get("out_per_mtok")
        if pin is None or pout is None:
            return None
        return round(self.tokens["in"] * pin / 1e6 + self.tokens["out"] * pout / 1e6, 4)


class Lab:
    def __init__(self, args):
        self.args = args
        paths = glob.glob(os.path.join(ROOT, "scenarios", f"{args.scene}-*.json"))
        if len(paths) != 1:
            raise SystemExit(f"expected one scenario file for {args.scene}, found {paths}")
        self.scene = load_json(paths[0])
        self.cast_states = {c["id"]: c for c in load_json(os.path.join(ROOT, "cast", "initial-states.json"))["characters"]}
        self.world = load_json(os.path.join(ROOT, "world-state.json"))
        self.rubric = load_json(os.path.join(ROOT, "eval", "rubric.json"))
        self.variation = next((v for v in self.scene["variations"] if v["id"] == args.variation), None)
        if not self.variation:
            raise SystemExit(f"{args.scene} has no variation {args.variation!r}; has {[v['id'] for v in self.scene['variations']]}")
        self.runs_dir = args.runs_dir or os.path.join(ROOT, "runs")
        self.check_cast()

    def check_cast(self):
        need = list(self.scene["cast"]) + ["eval"]
        problems = []
        for cid in need:
            st = self.cast_states.get(cid)
            if not st or not st.get("bible"):
                problems.append(f"{cid}: no bible (status {st and st.get('status')})")
            elif not os.path.exists(os.path.join(ROOT, st["bible"])):
                problems.append(f"{cid}: bible file missing at {st['bible']}")
        if problems:
            raise SystemExit("cannot run, these characters are not ready:\n  " + "\n  ".join(problems))

    def bible(self, cid):
        return open(os.path.join(ROOT, self.cast_states[cid]["bible"])).read()

    def bible_commits(self, ids):
        out = {}
        for cid in ids:
            st = self.cast_states[cid]
            if st.get("dressing_room"):
                out[cid] = f"{st['dressing_room']['repo']}@{st['dressing_room']['sha']}"
            else:
                out[cid] = "local-bible-sha256:" + sha_bytes(open(os.path.join(ROOT, st["bible"]), "rb").read())[:12]
        return out

    # -- prompts ---------------------------------------------------------
    def actor_system(self, cid, extra_rules=""):
        st, sc = self.cast_states[cid], self.scene
        believed = sc["world_state"]["believed"]
        private = believed.get(cid) if isinstance(believed, dict) else None
        observed = "; ".join(f["fact"] for f in self.world["observed"]) or "none"
        imagined = "; ".join(self.world["imagined"] + sc["world_state"].get("imagined", [])) or "none"
        return render("actor",
                      name=name_of(cid), lab_note=LAB_NOTE, bible=self.bible(cid),
                      want=st["wants"], mistake=st["characteristic_mistake"],
                      position=sc["starting_positions"].get(cid, "Not specified; discover it in play."),
                      private=private or "Nothing specific; discover it in play.",
                      trigger=sc["trigger"], variation=self.variation["start"],
                      constraints="; ".join(sc.get("constraints", [])) or "none",
                      observed=observed, imagined=imagined, extra_rules=extra_rules)

    def criteria_text(self):
        return "\n".join(f"- {c['id']} (weight {c['weight']}): {c['question']}" for c in self.rubric["criteria"])

    # -- shared pieces ---------------------------------------------------
    def new_take_folder(self, name):
        folder = os.path.join(self.runs_dir, self.scene["id"], name)
        if os.path.exists(folder):
            raise SystemExit(f"{folder} already exists. Takes are append-only: pick a new --take-name.")
        os.makedirs(folder)
        return folder

    def write_take_json(self, folder, cast, eval_audible, extra=None):
        t = load_json(os.path.join(ROOT, "runs", "_template", "take.json"))
        t.pop("$comment", None)
        t["scene_id"], t["take"] = self.scene["id"], os.path.basename(folder)
        t["stage"] = {"cast": cast, "eval_audible": eval_audible}
        t["curtain"]["turn_budget"] = {"min": self.min_turns, "max": self.max_turns}
        t["record"].update({
            "model": self.args.model, "provider": self.args.provider,
            "prompt_versions": prompt_versions(),
            "bible_commits": self.bible_commits(cast + ["eval"]),
            "generation_settings": {"max_tokens": 700, "temperature": self.args.temperature},
            "rubric_version": self.rubric["version"], "rubric_frozen": self.rubric["frozen"],
            "variation": self.variation, "started_at": now(),
        })
        if extra:
            t.update(extra)
        write_text(os.path.join(folder, "take.json"), json.dumps(t, indent=2, ensure_ascii=False) + "\n")
        return t

    def finalize(self, folder, take, t, extra_record):
        t["record"].update(extra_record)
        t["record"].update({"finished_at": now(), "tokens": take.tokens, "cost_usd": take.cost()})
        write_text(os.path.join(folder, "take.json"), json.dumps(t, indent=2, ensure_ascii=False) + "\n")
        for p in glob.glob(os.path.join(folder, "*")):
            os.chmod(p, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    def clean(self, cid, text):
        return re.sub(rf"^\s*{re.escape(name_of(cid))}\s*:\s*", "", text, flags=re.I)

    def final_state(self, take, folder, cast, rows, curtain):
        out = {}
        for cid in cast:
            data, _ = take.call_json("final_state", self.actor_system(cid),
                                     render("final_state", name=name_of(cid), transcript=transcript_text(rows)))
            out[cid] = data
        write_text(os.path.join(folder, "final-state.json"),
                   json.dumps({"scene_id": self.scene["id"], "take": os.path.basename(folder),
                               "curtain": curtain, "characters": out}, indent=2, ensure_ascii=False) + "\n")

    def scene_card(self, take, folder, rows, heading):
        data, _ = take.call_json("scene_card", "", render("scene_card", title=self.scene["title"],
                                                           exit_condition=self.scene["exit_condition"],
                                                           transcript=transcript_text(rows)))
        by_turn = {r["turn"]: r for r in rows}
        norm = lambda s: " ".join(str(s).split())
        kept, dropped = [], 0
        for a in data.get("anchors", []) if isinstance(data, dict) else []:
            r = by_turn.get(a.get("turn"))
            if r and norm(a.get("text", "")) and norm(a["text"]) in norm(r["text"]):
                kept.append((r, a["text"]))
            else:
                dropped += 1
        lines = [f"# {heading} — scene card", "", "## Beats", ""]
        lines += [f"{i}. {b}" for i, b in enumerate(data.get("beats", []), 1)] if "beats" in data else [f"_card failed: {data.get('error')}_"]
        lines += ["", "## Anchors (optional, exact quotations)", ""]
        lines += [f"- T{r['turn']} {r['speaker_name']}: \"{t}\"" for r, t in kept] or ["- none"]
        lines += ["", "## Not in the setup", "", str(data.get("not_in_setup", "unknown")), "",
                  f"_{dropped} proposed anchor(s) dropped for not being exact quotations._", ""]
        write_text(os.path.join(folder, "scene-card.md"), "\n".join(lines))

    # -- the take --------------------------------------------------------
    def run_take(self):
        a, sc = self.args, self.scene
        self.min_turns = a.min_turns or sc["turn_budget"]["min"]
        self.max_turns = a.max_turns or sc["turn_budget"]["max"]
        name = a.take_name or f"variation-{a.variation}"
        folder = self.new_take_folder(name)
        take = Take(folder, a.provider, a.model, a.temperature)
        cast = sc["cast"]
        t = self.write_take_json(folder, cast, eval_audible=False)
        systems = {cid: self.actor_system(cid) for cid in cast}
        eval_bible = self.bible("eval")
        write_text(os.path.join(folder, "commentary.md"),
                   f"# EVAL live commentary — {sc['id']} {name}\n\nTimestamped, append-only. The cast cannot hear this.\n\n")
        rows, curtain = [], {"reason": "turn budget expired"}
        tf = open(os.path.join(folder, "transcript.jsonl"), "a")
        for turn in range(1, self.max_turns + 1):
            cid = cast[(turn - 1) % len(cast)]
            user = ("Transcript so far:\n\n" + transcript_text(rows) if rows else "The scene has not started. You speak first.")
            text = self.clean(cid, take.call("actor", systems[cid], f"{user}\n\nYour turn as {name_of(cid)}:"))
            rows.append({"turn": turn, "speaker": cid, "speaker_name": name_of(cid), "text": text, "ts": now()})
            tf.write(json.dumps(rows[-1], ensure_ascii=False) + "\n"); tf.flush()
            live = take.call("eval_live", "", render("eval_live", bible=eval_bible, title=sc["title"],
                                                      exit_condition=sc["exit_condition"],
                                                      transcript=transcript_text(rows), turn=turn), 300)
            write_text(os.path.join(folder, "commentary.md"), f"- `{now()}` after turn {turn}: {live}\n", "a")
            if turn >= self.min_turns:
                d, _ = take.call_json("director", "", render("director", exit_condition=sc["exit_condition"],
                                                             turns=turn, transcript=transcript_text(rows)), 200)
                if d.get("met") is True:
                    curtain = {"reason": "exit condition met", "director": d.get("reason")}
                    break
        tf.close()
        curtain["turns"] = len(rows)
        self.final_state(take, folder, cast, rows, curtain)

        # EVAL's assessment: written from setup + transcript only, then locked before the cast sees it.
        data, _ = take.call_json("eval_final", "", render(
            "eval_final", bible=eval_bible, title=sc["title"], trigger=sc["trigger"],
            exit_condition=sc["exit_condition"], variation=self.variation["start"],
            criteria=self.criteria_text(), transcript=transcript_text(rows)), 1200)
        scores = {}
        for c in self.rubric["criteria"]:
            raw = (data.get("scores") or {}).get(c["id"]) if isinstance(data, dict) else None
            scores[c["id"]] = {"score": max(0, min(c["weight"], int(raw))) if isinstance(raw, (int, float)) else None,
                               "weight": c["weight"]}
        got = [s["score"] for s in scores.values()]
        ev = {"rubric_version": self.rubric["version"], "rubric_frozen": self.rubric["frozen"], "locked_at": now(),
              "scores": scores, "total": sum(got) if None not in got else None,
              **{k: data.get(k) for k in ("summary", "surprised", "lost_its_way", "smallest_change") if isinstance(data, dict)}}
        if "error" in data:
            ev["error"] = data
        body = json.dumps(ev, indent=2, ensure_ascii=False) + "\n"
        write_text(os.path.join(folder, "eval.json"), body)
        os.chmod(os.path.join(folder, "eval.json"), 0o444)

        self.scene_card(take, folder, rows, f"{sc['id']} {name}")
        self.finalize(folder, take, t, {"curtain": curtain, "eval_sha256": sha_bytes(body.encode()), "eval_total": ev["total"]})
        return folder, curtain, ev["total"], take

    # -- the review room -------------------------------------------------
    def run_review(self):
        a, sc = self.args, self.scene
        src_name = a.take_name or f"variation-{a.variation}"
        src = os.path.join(self.runs_dir, sc["id"], src_name)
        eval_path = os.path.join(src, "eval.json")
        if not os.path.exists(eval_path):
            raise SystemExit(f"{src} has no eval.json; run the take first.")
        scene_rows = [json.loads(l) for l in open(os.path.join(src, "transcript.jsonl"))]
        eval_body = open(eval_path).read()
        eval_sha = sha_bytes(eval_body.encode())
        self.min_turns = self.max_turns = a.review_turns
        folder = self.new_take_folder(src_name + "-review")
        take = Take(folder, a.provider, a.model, a.temperature)
        cast = sc["cast"]
        t = self.write_take_json(folder, cast, eval_audible=True,
                                 extra={"review": {"release_to_cast": "after_curtain", "initial_assessment_locked": True,
                                                   "allow_cast_rebuttal": True, "source_take": src_name,
                                                   "released_eval_sha256": eval_sha}})
        rules = ("- The curtain has fallen and you are in the Review Room. EVAL's completed review of your scene is "
                 "in the conversation. React in character: challenge its evidence and conclusions, defend your "
                 "choices, and propose another attempt if you want one. You cannot change what you already performed.")
        systems = {cid: self.actor_system(cid, rules) for cid in cast}
        eval_bible = self.bible("eval")
        speakers = cast + ["eval"]
        rows = []
        tf = open(os.path.join(folder, "transcript.jsonl"), "a")
        for turn in range(1, a.review_turns + 1):
            cid = speakers[(turn - 1) % len(speakers)]
            scene_tx = transcript_text(scene_rows)
            if cid == "eval":
                text = take.call("review_eval", "", render("review_eval", bible=eval_bible, assessment=eval_body,
                                                           scene_transcript=scene_tx,
                                                           transcript=transcript_text(rows) or "(Nobody has spoken yet.)"), 500)
            else:
                user = (f"EVAL's filed review of your scene:\n{eval_body}\n\nThe scene you performed:\n{scene_tx}\n\n"
                        f"The review room so far:\n{transcript_text(rows) or '(You speak first.)'}\n\nYour turn as {name_of(cid)}:")
                text = take.call("review_actor", systems[cid], user)
            text = self.clean(cid, text)
            rows.append({"turn": turn, "speaker": cid, "speaker_name": name_of(cid), "text": text, "ts": now()})
            tf.write(json.dumps(rows[-1], ensure_ascii=False) + "\n"); tf.flush()
        tf.close()
        curtain = {"reason": "review turn budget", "turns": len(rows)}
        self.final_state(take, folder, cast, rows, curtain)

        # EVAL may revise, as a second entry. The original is never touched.
        data, _ = take.call_json("eval_revised", "", render("review_revised", bible=eval_bible, assessment=eval_body,
                                                            transcript=transcript_text(rows), criteria=self.criteria_text()), 1000)
        rev = {"original_eval_sha256": eval_sha, "written_at": now(), **(data if isinstance(data, dict) else {"error": data})}
        write_text(os.path.join(folder, "eval-revised.json"), json.dumps(rev, indent=2, ensure_ascii=False) + "\n")
        self.scene_card(take, folder, rows, f"{sc['id']} {src_name}-review")
        self.finalize(folder, take, t, {"curtain": curtain, "source_eval_sha256": eval_sha})
        return folder, curtain, None, take


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scene"), ap.add_argument("variation")
    ap.add_argument("--provider", default="anthropic", choices=["anthropic", "mock"])
    ap.add_argument("--model", default=None)
    ap.add_argument("--runs-dir", default=None)
    ap.add_argument("--min-turns", type=int), ap.add_argument("--max-turns", type=int)
    ap.add_argument("--temperature", type=float, default=None)
    ap.add_argument("--take-name", default=None)
    ap.add_argument("--review", action="store_true")
    ap.add_argument("--review-turns", type=int, default=8)
    args = ap.parse_args()
    args.model = args.model or ("mock" if args.provider == "mock" else os.environ.get("LAB_MODEL", llm.DEFAULT_MODEL))
    lab = Lab(args)
    if not lab.rubric["frozen"]:
        print("note: eval/rubric.json is not frozen; do not compare scores across variations until it is.", file=sys.stderr)
    folder, curtain, total, take = (lab.run_review if args.review else lab.run_take)()
    print(f"{os.path.relpath(folder, ROOT)}: {curtain['reason']} after {curtain['turns']} turns; "
          f"EVAL total {total}; tokens in/out {take.tokens['in']}/{take.tokens['out']}; cost {take.cost()}")


if __name__ == "__main__":
    try:
        main()
    except llm.LLMError as e:
        sys.exit(f"LLM error: {e}")
