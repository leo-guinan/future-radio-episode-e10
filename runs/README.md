# Runs

One folder per take: `runs/<scene>/<take>/`, for example `runs/S05/variation-a/`.

| File | What it holds |
|---|---|
| `take.json` | The setup actually used and the run record (model, prompt versions, bible commits, settings, cost). Start from `_template/take.json`. |
| `transcript.jsonl` | The raw dialogue, one turn per line. Evidence of what the agents generated. |
| `final-state.json` | Each character's beliefs at the curtain, tagged observed, believed or imagined. |
| `eval.json` | EVAL's rubric scores and answers to the three unscored questions. The initial assessment is locked before the cast's rebuttal; a revision is a separate entry. |
| `commentary.md` | EVAL's timestamped, append-only live commentary. Kept separate from the evaluation. |
| `scene-card.md` | The durable dramatic structure: the minimum beats that preserve what made the take interesting, with optional anchor lines. |

Rules that apply to every take are in [`../SHOW_PLAN.md`](../SHOW_PLAN.md) (7–14): isolation between variations, no silent rewriting, and nothing reaches canon except through `decisions/canon.json`.

The review-room argument that follows a take is its own scene and gets its own take folder (for example `variation-a-review`).
