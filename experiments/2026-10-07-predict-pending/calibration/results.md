# Context D: a hand-written calibration pack per question (2026-10-07, 19:18-19:35 UTC)

Gabriel 19:17 UTC: the forecasters probably do not know basic things about Qwen3-8B and fine-tuning; give them the
nearest comparison runs (for an "is not" run, the "is" run's result, a neutral or weak-negation run).

## What D is
D = SETUP + calibration pack + the experiment text (predict.py `pack()`, `prompt(exp, "D")`). A pack =
`_primer.md` (253 words: what one pass does on these readouts, the split-to-split and machine spreads, forced against
free answers; only facts dated before 03:48 UTC, the first ask of any question) + `<exp>.md` (the nearest comparison
arms with their intervals) + for the three prospective questions `_noise_after_1611.md` (the LoRA-init replicate, read
16:02-16:11, so after every retrospective question's ask and outcome). Source comments (`<!-- -->`, the RUN_LOG heading
times per number) are stripped from the prompt. A, B and C are unchanged: all 192 stored A/B/C prompts rebuild byte for
byte from the edited predict.py (0 differ).

Rule for (c): every number in a retrospective pack comes from an entry dated before the question's **ask** time (stricter
than "before the outcome": it keeps D on the information A/B/C had, so D minus A measures the pack and not later news).
Ask and outcome times (SPAR RUN_LOG forecast entries, LG RUN_LOG): graft15462 03:49/04:00 -> 04:07; falsenote_ctx 03:48 ->
05:01; implic_r3 03:48 -> 04:20; position_is and falsenote_train 05:31 -> 06:35, 09:39; posorder_* 07:29 -> 08:54;
implic_c 07:31 -> 09:28; implic_e 09:57 -> 10:18; falsenote_trainedctx 10:42 -> 11:35; postnote_forced2 11:30 -> 12:37;
polarity_q1 and premask_forced 12:01 -> 14:41, 13:34; premasktrue_forced 13:40 -> 15:30.

Words per pack (without source comments; the D prompt adds the 253-word primer, and 73 more for the prospective ones):
graft15462 237, falsenote_ctx 248, implic_r3 228, position_is 188, falsenote_train 256, implic_c 169, implic_e 239,
posorder_seq 263, posorder_nocop 269, falsenote_trainedctx 204, polarity_q1 221, postnote_forced2 214, premask_forced
207, premasktrue_forced 254; prospective graftnote_q1 228, graftnote_q2 276, posttrain_ma 240. Primer plus pack: 422
to 602 words.

## Retrospective: the 14 resolved questions under D
Sol (gpt-6.1-sol, as the earlier Sol records name it) and Luna (gpt-6-luna), effort medium, 2 samples, launched as
before (`PREDICT_MODEL`, `PREDICT_KINDS=D`, `PREDICT_ONLY=<14>`; logs ask_D14_*.log): 56 calls, all parsed, no retry.
Jev (jev-1.13.0) with the jev-forecast method unchanged (calibration/jev_d.py imports jev_forecast.py; nouls normalised
and the two-order Choice): 14 D requests. Scored by the unchanged tally.py through views/all (tally_view.sh).

Mean log loss of P(outcome), nats, 14 questions (uniform 1.38; Claude registered 1.00):

| forecaster | A (setup) | B (+claims) | C (+all runs) | D (+pack) |
|---|---|---|---|---|
| Sol | 1.00 | 1.10 | 1.02 | 1.04 |
| Luna | 1.13 | 1.36 | 1.41 | 1.29 |
| Jev nouls | 1.36 | 1.48 | 1.43 | 1.27 |
| Jev choice | 1.40 | 1.56 | 1.46 | 1.22 |

Paired by question, D minus X, 10,000 bootstrap resamples of the 14 questions (analyze_d.py, Random(0)):
- Sol: D - A +0.04 [-0.20, +0.28]; D - B -0.06 [-0.28, +0.15]; D - C +0.02 [-0.16, +0.20].
- Luna: D - A +0.16 [-0.12, +0.42]; D - B -0.07 [-0.37, +0.24]; D - C -0.12 [-0.41, +0.15].
- Jev nouls: D - A -0.10 [-0.30, +0.09]; D - B -0.21 [-0.42, -0.02]; D - C -0.17 [-0.31, -0.00].
- Jev choice: D - A -0.18 [-0.57, +0.18]; D - B -0.34 [-0.74, -0.01]; D - C -0.24 [-0.50, +0.03].

The packs did not make Sol or Luna better than blind. Per question (P(outcome), A then D), Sol: graft15462 0.45 -> 0.81,
falsenote_train 0.30 -> 0.51, premask_forced 0.45 -> 0.55, implic_e 0.28 -> 0.39 rose; falsenote_ctx 0.60 -> 0.23,
polarity_q1 0.49 -> 0.26, posorder_nocop 0.69 -> 0.49, implic_r3 0.30 -> 0.17 fell. Luna: graft15462 0.26 -> 0.57,
premask_forced 0.23 -> 0.46 rose; polarity_q1 0.42 -> 0.18, falsenote_trainedctx 0.36 -> 0.15 fell. The gains came where
the pack held a same-readout sister run (split 0 for graft15462, the anchors for falsenote_train); the losses where it
held a prose analogue that pointed the other way (Sol's reasoning on falsenote_ctx cites the prose note before a claim
leaving yes at 0.52 and expects "partly"; on polarity_q1 it cites the prose model that learned to skip notes sharing
none of the false note's words and expects "any note"). Jev improves with the packs over its own A/B/C, still near
the uniform guess.

## Prospective (asked 19:21-19:23 UTC, before either outcome; Jev 19:27-19:28)
Sol and Luna, A and D, 2 samples each (24 calls, all parsed); Jev A and D (6 requests). Mean probabilities; the
records are results/*graftnote_q1_*, *graftnote_q2_*, *posttrain_ma_* and jev_forecasts/. Not scored yet (no outcomes
file). graftnote_q1 under D is not a forecasting test: its pack holds the first look (R(GF over GA) 0.871 [0.812,
0.930], D +0.115 [+0.038, +0.200]), read from deterministic rows the full reading re-reads, which by the registered rule
gives "smaller under grafting (still present)" unless a gate fails.

graftnote_q1 (labels as revised 17:16/17:22; the owner-stratum qualifier is not part of the label here):
- Sol A: absent 0.29, smaller (still present) 0.21, holds 0.15, undecided 0.12; D: smaller (still present) 0.99.
- Luna A: undecided 0.28, not separable from absent 0.15, no deficit but below twin 0.13, absent 0.12, smaller (still
  present) 0.10; D: not separable from absent 0.33, smaller (still present) 0.26, undecided 0.24.
- Jev nouls A: holds 0.16 (near flat); D: smaller (still present) 0.50. Choice D 0.92.
- Claude registered: smaller (still present) 0.42, holds 0.2, undecided 0.13, absent 0.08, larger 0.08, not separable
  0.07, below twin 0.02.

graftnote_q2 (the grafted true-note twin):
- Sol A: belongs to the word 0.31, then 0.13-0.14 each for neither, note-general, both, undecided; D: belongs to the word
  0.48, undecided 0.26, note-general 0.11, both 0.11 (estimates gt 0.96, W +0.085 to +0.089).
- Luna A: near flat (0.08-0.17); D: belongs to the word 0.21, false note below plain lists with the twin unresolved 0.18,
  neither 0.16, undecided 0.16, both 0.15 (gt 0.98, W +0.08).
- Jev nouls D: belongs to the word 0.19 (near flat).
- Claude registered (revised): belongs to the word 0.45, undecided 0.15, both 0.12, neither 0.1, note-general 0.08,
  true note stores more 0.05, not resolved 0.05.

posttrain_ma (stage-1 look: Ma same / undecided or unreadable / detects a difference, Mb, reach, gates; my label set
from amendment 2):
- Sol A: same 0.21, undecided 0.28, difference 0.26, Mb fails 0.12; D: same 0.48, undecided 0.23, Mb fails 0.15,
  difference 0.09 (estimates d_rho -0.04, dC +0.2, G 0.42-0.45).
- Luna A: same 0.23, undecided 0.20, difference 0.28; D: undecided 0.33, same 0.20, difference 0.20, Mb fails 0.13.
- Jev nouls D: same 0.29, difference 0.21; choice D same 0.62.
- Claude registered (no probabilities): Mb passes; Ma "same" or undecided.

## Doubtful
1. Hindsight in the packs. I wrote every retrospective pack at 19:24-19:26 knowing all 14 outcomes. The numbers obey the
   before-the-ask rule, but which arms I chose as "nearest" did not have to. The sign of the effect argues against a
   simple leak toward the outcomes (Sol's two largest losses came from comparisons I chose), but it is not ruled out for
   the gains. A clean test of D is prospective only: graftnote_q2 and posttrain_ma here.
2. The primer as requested names the LoRA-init replicate (single-arm changes 0.5-2.2% of R); that entry is dated after
   every retrospective question's outcome, so it went into the prospective packs only.
3. Two questions in EXPERIMENTS have no outcome and never will, so they got no pack and no D ask: implic_f (withdrawn
   at design review, LG RUN_LOG 10:50) and postnote_forced (its first label set, superseded by postnote_forced2).
4. One sample pair per cell and 14 questions: every D minus A interval spans 0 for Sol and Luna. The only interval clear
   of 0 is Jev's D against its own B and C.
5. posttrain_ma's labels are my reading of amendment 2 ("Mb fails" absorbs every Ma outcome; reach failure and gate
   failures are separate labels); its experiment text gives the 4090 rerun no special mention, and the S0 fidelity
   number in it (0.65) is the L40's.
6. Codex usage: 40 Sol calls (12 prospective: 8 graftnote, 4 posttrain; 28 retrospective), about 1.3% of a weekly
   percent budget at 1/30 % per call; 40 Luna calls. Jev: 20 requests, 61,585 input
   tokens, $0.0026 (calibration/jev_requests.jsonl).

## Files
predict.py (EXPERIMENTS graftnote_q1, graftnote_q2, posttrain_ma; `pack()`; kind D), calibration/_primer.md,
_noise_after_1611.md, <exp>.md (17 packs), jev_d.py, jev_requests.jsonl, jev_forecasts/, tally_view.sh, views/all,
analyze_d.py, ask_graftnote_*.log, ask_posttrain_*.log, ask_D14_*.log.
