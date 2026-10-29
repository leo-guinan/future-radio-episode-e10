# Future Radio — Episode 10: The Scene Laboratory

*Working title: **We Finished Your Future**. The characters discover the ending of their story has already been outlined, disagree about which ending happened, and make both.*

Episode 10 is assembled from situations, character states and competing intentions, not from a script with predetermined dialogue. The writers' room sets the circumstances; the characters play them out; EVAL watches from the booth; the cast argues about the review; the director chooses.

The experiment isn't whether AI can write the dialogue we already imagined. It's whether these characters can produce dialogue we wouldn't have thought to write.

**Status:** laboratory and run harness set up. No real takes have been run yet. First experiment: scene S05, three variations.

## Running a take

```
export ANTHROPIC_API_KEY=...            # never commit this
python3 lab/selftest.py                 # free: proves isolation and append-only behavior with a mock provider
python3 lab/run_take.py S05 a           # take: runs/S05/variation-a/
python3 lab/run_take.py S05 a --review  # review room: runs/S05/variation-a-review/
```

Python 3 standard library only. `--provider mock` is a free dry run. Set the model with `--model` or `LAB_MODEL`. Costs are recorded as tokens; dollar cost stays `null` until real prices are filled into `lab/prices.json`. Freeze `eval/rubric.json` (`"frozen": true`) before comparing scores across variations.

## Layout

| Path | What it holds |
|---|---|
| `episode.md` | The premise, the twelve-scene library and the assembly hypothesis |
| `DESIGN.md` | How a scene runs: the two-room architecture, the three architectural rules, knowledge tags, compression |
| `SHOW_PLAN.md` | The plan and the locked rules |
| `world-state.json` | What is observed, believed and imagined as the lab starts |
| `cast/initial-states.json` | Each character's wants, characteristic mistake and bible location |
| `cast/bibles/` | Draft bibles for EVAL and the Simulated Human (no dressing rooms yet) |
| `lab/` | The run harness: take runner, prompts (versioned by hash), mock-provider self-test |
| `eval/rubric.json` | EVAL's 100-point rubric and three unscored questions |
| `scenarios/` | S01–S12, each with world state, character states, trigger and exit condition |
| `runs/` | One folder per take: transcript, final state, EVAL's assessment, commentary, scene card |
| `cuts/candidates.md` | Edited cuts assembled from the strongest material |
| `decisions/canon.json` | The only place a result becomes canon, by deliberate decision |
| `gates.json` | Quality-gate configuration for the showrunner |
| `releases/v1/` | The first published Episode 10, locked as released |

## Released: v1, "The People vs. The Future"

The first published Episode 10 is a scripted premortem at Milliways (8:23, audio). It is locked: the lab may answer it, never rewrite it. Everything in it, including the mp3 and its checksum, is unchanged and now lives under [`releases/v1/`](releases/v1/RELEASE.md).

→ [Future_Radio_EP010_The_People_vs_The_Future.mp3](https://github.com/leo-guinan/future-radio-episode-e10/raw/main/releases/v1/media/Future_Radio_EP010_The_People_vs_The_Future.mp3) · `sha256 82cef6ccaac78b21239e9a6eb347d34181cfaeccab54c548598db5be09f4ef2a`

The old `media/` path no longer exists. Links inside `releases/v1/` that point at it were left as released.

License: [CC0 1.0](LICENSE). Public domain; use it, change it, ship it.
