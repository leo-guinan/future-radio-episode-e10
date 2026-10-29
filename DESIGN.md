# Design — how a scene runs

## Layers of a scenario

| Layer | Question |
|---|---|
| World state | What has actually happened, and what evidence exists? |
| Character state | What does each participant believe, want, fear and misunderstand? |
| Scenario trigger | What new information or event forces them to interact? |
| Exit condition | What discovery, decision, conflict or change would make this a complete scene? |

The exit condition defines dramatic progress without prescribing dialogue. Character states are starting tendencies, not lines or outcomes: a character can surprise us without violating its identity.

## Knowledge tags

- **Observed**: actual documents, costs, audience feedback and completed work.
- **Believed**: what a character currently thinks is true, which may be mistaken.
- **Imagined**: hypothetical future events and simulated outcomes.

## The two-room architecture

1. **The Stage.** The cast in the scene hear one another, pursue their goals and change beliefs through interaction. They cannot hear EVAL.
2. **EVAL's Booth.** EVAL watches every turn and records reactions as the scene develops. Commentary may be kept for an alternate cut but never reaches the performers during the scene.
3. **The Review Room.** After the curtain, the cast receives EVAL's completed review and argues about it in character. EVAL is now a participant.
4. **The next take.** The argument produces new beliefs, constraints and creative choices. A new run begins from an explicitly selected state.

Performance → Review → Argument → Revision. The actors perform, the critic watches, the actors argue, the director chooses.

EVAL's final assessment is produced and locked before it hears the cast's defenses. It may revise afterward; both versions stay on record. Live commentary stays separate from the scored evaluation, so EVAL isn't rewarded for creating problems to make entertaining reviews.

## Stopping

A director controls pacing, not dialogue. A take ends at a meaningful beat (a decision, discovery, reversal or emotional change) or when the turn budget expires, 12–20 turns for the first experiment. EVAL can always see another improvement; Agnolo can always see the cost; Leonardo decides whether another take is worth making. The budget is what ends the recursion.

## Compression

After a run, the director extracts the minimum sequence of dramatic beats that preserves what made the interaction interesting.

- **Raw takes**: everything the characters actually said.
- **Scene cards**: the durable dramatic structure found in the takes. Best lines are optional anchors, never mandatory dialogue.
- **Cuts**: edited versions assembled from the strongest material.

A scene card can seed a new run: reset the states, keep the situation, let the characters find another route through it.

## Run record

Each `runs/<scene>/<take>/` holds `take.json`, `transcript.jsonl`, `final-state.json`, `eval.json`, `commentary.md` and `scene-card.md`. `take.json` follows `runs/_template/take.json`, including model, prompt versions, bible commit hashes, settings and cost, so a surprising result can be traced to the scenario, the characters or a model change.

## Canon

Character state is promoted into the shared timeline only by a deliberate decision recorded in `decisions/canon.json`. Otherwise twelve speculative variations create twelve contradictory histories.
