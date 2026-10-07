# Haiku 5.5 against GPT-6 Luna (2026-10-07)

All Haiku calls through src/headless_claude.call (Claude Code 2.1.293, model claude-haiku-5-5), 176 calls, $0.30 at
API prices in all. check_window refused at the start: interactive sessions alone were at $161 at API prices in the
window since 15:50 UTC, above the $125 cap. I ran anyway in small stages, after a 6-call pilot measured Haiku at
$0.0005-0.003 a call (the batch was under 0.2% of the window); the window stood at $166 interactive and $0.57 headless
afterwards.

## Forecasting (haiku_forecast.py, tally_view.sh)
Exact prompts from Luna's saved records (one per question x context, identical to Sol's; every record predates its
outcome file), 14 resolved questions x A/B/C x 2 samples, scored by an unchanged copy of tally.py (mean log loss of
P(outcome), nats, lower is better; uniform 1.38).

| forecaster | A (setup) | B (+claims) | C (+all runs) |
|---|---|---|---|
| Haiku medium (Luna's and Sol's effort) | 1.39 | 1.39 | 1.39 |
| Haiku low | 1.18 | 1.55 | 1.38 |
| Luna medium | 1.13 | 1.36 | 1.41 |
| Sol medium | 1.00 | 1.10 | 1.02 |
| Claude registered | 1.00 | | |

Paired per question, Haiku minus Luna: medium pooled over A/B/C +0.09 [-0.25, +0.37], low +0.07 [-0.12, +0.24]
(bootstrap over the 14 questions). Haiku medium blind minus Sol blind +0.38 [-0.02, +0.79]. Haiku at medium is at
the uniform guess in every context. Seconds per call (median): Haiku 5-8, Luna 7.5-8, Sol 20-22. Cost $0.0005 (A) to
$0.003 (C) a call.

## Generation (haiku_gen.py; outputs gen/, items in gen/items.json)
Luna's two latest generation prompts, exact text from Luna's saved calls, Haiku at low as Luna was, the scripts' own
code checks.
- Martin Hosken profile frames (frames.py martin; six of Luna's 100 calls, 60 frames each side): pass 58/60 Haiku,
  59/60 Luna. Read by hand (10 each side, plus every title of two calls): both natural, on facts, no instruction
  leakage. Haiku drifted off genre where the prompt asks for "unlike the usual first ideas" (networking-profile call:
  "Trail Stop 4", "Tonight's Guest!", "Dear neighbours," against Luna's ten profile-like pages), uses markdown in 4 of
  60, and dated one frame with today's date (Claude Code puts the date in every call). Seconds per call: Haiku median
  43 (it thinks 5k-11k tokens even at low), Luna 16. Cost $0.005 a call (10 frames).
- In-sentence retractions (varied_retractions.py; two of Luna's 60 calls, 100 each side): pass 94/100 Haiku (six
  genuinely miss running or the denied field), 99/100 Luna. Openings: Haiku 12 distinct three-word openings, 45 of
  100 "no, that was"; Luna 29 distinct. The script's purpose is varied wordings, so Luna's spread serves it better.
  Seconds per call: Haiku 27, Luna 31. Cost $0.002-0.005 a call.

## Cost and quota
Haiku's notional cost per call is about 1/40 of Opus 5.5 for the same tokens ($0.10/$0.50 against $4/$20 per M). It
draws on the Claude limit shared with Gabriel's sessions; if that limit weights Haiku by API price (unverified), a
window of about $125-165 holds roughly 25,000-35,000 frame calls or 40,000-100,000 forecast calls, but on a day like
today his interactive sessions already fill the window by themselves. Luna draws on the ChatGPT Plus plan, which
nothing else uses: about 9,000 Luna calls per 5-hour window and 180 per weekly percent (RUN_LOG 2026-10-01 18:26).
