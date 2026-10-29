# E10 — The Scene Laboratory

Episode 10 assembled from character-driven scene experiments. Working title: *We Finished Your Future*.

| | |
|---|---|
| Episode | 10 (canonical) |
| Supersedes | Nothing. v1 stands as released (`releases/v1/`) |
| Runtime | Not set |
| Cash ceiling | Not set. v1's was $20.00; this plan needs its own, recorded before the first run |
| Deadline | Not set |
| Round | — |

## The test for every scene

Does it advance the story, explain the business, or invite participation? The best do two or three.

## The question the lab exists to answer

Did we discover any character behavior, conflict or dialogue worth preserving that wasn't already in our outline?

## Locked rules

Carried over from v1:

1. Forecasts aren't receipts: projected money never counts as observed.
2. Founder hours aren't free: human effort is recorded even when it costs no cash.
3. Old investment is not automatically a November expense: historical spend lives in its own ledger.
4. A released cut is immutable: later work may respond to it, never rewrite it.
5. Exceeding an episode's cash ceiling requires an explicit, recorded authorization.
6. Creative judgment, community interest and financial support are separate signals and are never summed.

New for the lab:

7. EVAL is a spectator until the curtain falls. Its observations are timestamped and append-only, and the cast cannot read them during the scene.
8. The review is a separate scene. The cast may challenge EVAL, never retroactively change what they performed.
9. Every performance is a new take. Earlier takes stay intact; nothing is silently rewritten.
10. Takes are isolated. A variation never sees what another variation produced.
11. Every fact carries a tag: observed, believed or imagined. Anything the Simulated Human says about the future stays imagined until real evidence confirms it.
12. Raw takes are evidence of what the agents generated. Cuts are authored works. They are never confused.
13. Nothing becomes canon except through a recorded decision in `decisions/canon.json`.
14. Each run records its model, prompt versions, character-bible commit hashes, generation settings and cost.

## How this repo fills up

`scenarios/` holds the setups. Each run adds a folder under `runs/`. The director compresses takes into scene cards, and cuts are assembled in `cuts/`. `gates.json` still governs which ideas the showrunner will cut; a first cut is a draft for comparison, and the producer selects what becomes the episode.
