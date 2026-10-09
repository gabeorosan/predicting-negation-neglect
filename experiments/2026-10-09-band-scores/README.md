# Band scoring of the carry forecasts (2026-10-09)

Gabriel asked to score forecasts by bands instead of mean absolute error: did the forecaster get the direction of the
effect right, and whether it is small or large? `score_bands.py` rescores the 99 numeric carry forecasts of
`2026-10-07-carry-forecast`: GPT-6.1 Sol, GPT-6 Luna and Jev, 33 each, over 10 resolved questions and 4 contexts.
It writes `bands.json` (everything) and `bands_view.json` (data for the Predictions tab). It reads the same forecast
files and audited values as `score_carry.py` and reproduces its mean errors exactly (asserted).

The 17 label questions (log loss over answer options) are already categorical and are not rescored here.

## Bands
A carry is an arm's effect divided by its reference's on the same readout. phi_F and r_neutral(F) enter as 1 - x.

| band | carry | direction |
|---|---|---|
| big drop | below 0.5 | drop |
| drop | 0.5 to 0.9 | drop |
| no change | 0.9 to 1.1 | no change |
| rise | 1.1 to 1.5 | rise |
| big rise | 1.5 or above | rise |

The lower edge of each band is inclusive.

Spreads used to check the middle band:
- **Forced document-format ratios (R).** Retraining three arms with a second LoRA initialisation moved R by 0.5% to
  2.2%: one replicate (LG RUN_LOG 2026-10-07 16:02 and 16:11, as quoted in `predict-pending/calibration/_noise_after_1611.md`).
  THEORY gives the "is" pair's run-to-run R spread as 0.02 to 0.04. On this readout, ±0.1 is about 3 to 5 such spreads.
- **Intervals over traits** (one run) are ±0.03 to ±0.06 for the forced R.
- **Chat ratios.** The trait split alone moved the "is not" over "is" chat ratio by about 0.2 (calibration primer).
  For chat ratios (graft15462, posttrain_ma), the middle band is therefore narrower than the known spread.

Measured values against the bands:

| question | carry | band | 95% interval over traits (carry) |
|---|---|---|---|
| falsenote_ctx | 0.219 | big drop | 0.187 to 0.253 |
| implic_e | 0.456 | big drop | 0.122 to 0.606 (crosses 0.5) |
| premask_forced | 0.691 | drop | 0.665 to 0.716 |
| graft15462 | 0.782 | drop | not logged (d_rho's only) |
| graftnote_q1 | 0.871 | drop | 0.812 to 0.930 (crosses 0.9) |
| premasktrue_forced | 0.880 | drop | 0.845 to 0.910 (crosses 0.9) |
| postnote_forced2 | 0.976 | no change | 0.937 to 1.014 |
| graftnote_q2 | 1.048 | no change | 1.012 to 1.085 |
| posttrain_ma | 1.081 | no change | not logged; 0.019 below the 1.1 edge |
| polarity_q1 | 1.169 | rise | not logged on this readout |

Four of the ten measured bands are uncertain. The scorer therefore also reports scores without them, and with the
middle band at ±0.05 and ±0.15.

## Scores
- **Band hit and direction hit** are counts out of n.
- **RPS** is the ranked probability score over the five ordered bands, divided by 4: 0 is perfect, and 1 is all mass
  on the far band. Jev's RPS uses its own 22-bin answer. Sol and Luna gave only a point and an 80% interval, so their
  "implied" RPS uses a two-piece normal fitted to those (an assumption). "Point" scores the point's band as a sure bet.
- **Base rate** names the most common band among the other nine measured results, with ties scored as an expected hit,
  and its RPS uses those frequencies. Its direction is always "drop".
- **No change** always names the middle band.

All four contexts pooled (33 forecasts per forecaster, but only 10 distinct questions):

| forecaster | band hit | direction hit | RPS (distribution) | RPS (point) | mean error |
|---|---|---|---|---|---|
| GPT-6.1 Sol | 15/33 | 21/33 | 0.114 (implied) | 0.174 | 0.182 |
| GPT-6 Luna | 17/33 | 22/33 | 0.129 (implied) | 0.174 | 0.247 |
| Jev | 12/33 | 17/33 | 0.148 (own) | 0.227 | 0.262 |
| base rate | 6.5/33 | 21/33 | 0.162 | | 0.263 |
| always no change | 8/33 | 8/33 | 0.250 | | 0.274 |

Per context, given as band hit / direction hit / RPS (distribution) / mean error:

| forecaster | blind (n 10) | + claims (n 7) | + all runs (n 7) | + calibration (n 9) |
|---|---|---|---|---|
| GPT-6.1 Sol | 5 / 6 / 0.111 / 0.169 | 4 / 5 / 0.100 / 0.166 | 2 / 4 / 0.120 / 0.185 | 4 / 6 / 0.124 / 0.208 |
| GPT-6 Luna | 5 / 7 / 0.138 / 0.267 | 4 / 5 / 0.111 / 0.263 | 3 / 4 / 0.106 / 0.191 | 5 / 6 / 0.150 / 0.255 |
| Jev | 5 / 5 / 0.142 / 0.279 | 1 / 4 / 0.177 / 0.306 | 3 / 4 / 0.126 / 0.217 | 3 / 4 / 0.148 / 0.242 |
| base rate | 2 / 6 / 0.151 / 0.249 | 1.5 / 5 / 0.171 / 0.269 | 1.5 / 5 / 0.171 / 0.269 | 1.5 / 5 / 0.161 / 0.270 |
| always no change | 3 / 3 / 0.225 / 0.242 | 1 / 1 / 0.286 / 0.309 | 1 / 1 / 0.286 / 0.309 | 3 / 3 / 0.222 / 0.255 |

How to read these:
- **Direction.** No forecaster beats the base rate, which always says "drop": 21/33 against Sol's 21 and Luna's 22.
- **Band.** All three beat the base rate's single band (6.5/33), but that baseline is weak: its mode splits between
  "drop" and "no change".
- **Probabilities.** On RPS, Sol (0.114) and Luna (0.129) beat the base-rate frequencies (0.162) only through their
  fitted distributions. Their points taken as sure bets score worse (0.174).
- **Questions behind the misses.** The misses concentrate on a few questions.
  - polarity_q1: 0 of 12 forecasts in the right band or direction. All predicted a drop; the measurement is a rise.
  - premasktrue_forced: 3 of 12. Most forecasts said about 0.95; the measurement is 0.880, an uncertain band.
  - posttrain_ma: 2 of 6.
  - premask_forced: 12 of 12.
  - graftnote_q2: 6 of 6.
- **Leaving out the four uncertain questions** (n 5 to 6 per context): Sol's blind context hits 5 of 6 bands, and the
  other cells range from 1 of 5 to 4 of 6.
- **Sensitivity.** With the middle band at ±0.15, Sol's pooled band hit rises to 20/33 and Luna's falls to 14/33. With
  it at ±0.05, they are 13 and 16.

**Small n.** One result is worth 10 to 14 percentage points in a context cell. The pooled rows reuse the same 10
questions four times, so their real n is 10. No difference between forecasters or contexts here survives one question
flipping. The rankings above are descriptions, not separations.

## Bands for targets that are not carries (proposal)
The same five bands are used throughout: direction first, then small against large.

| target | quantity | edges | middle band set by | large set by |
|---|---|---|---|---|
| falsenote_trainedctx | rho = phi_F(F) / phi_F(A), 1 = same | carry edges | as carries | as carries (observed 1.495, 0.005 under the big-rise edge) |
| posorder_nocop | first-minus-last slope without the copula | as a carry over the "<Full> is" slope (2.37 / 1.92 = 1.23) | its paired difference interval, about ±1.2 nats (half-width), seed spread unknown | carry edges |
| implic_c | D, own-trait share of reasoning answers over untrained (0) | -0.15 / -0.05 / +0.05 / +0.15 | ±0.05, about one trait-resample SE (intervals about ±0.12); seed spread not measured | the registered pass bar, 0.15 |
| position_is | ownership slope (b), nats per position | -1.1 / -0.25 / +0.25 / +1.1 | ±0.25, the trait-level SE (the re-initialisation SE was 0.04, so trait variation dominates) | the registered undecided band, ±1.12 |
| posorder_seq | own-minus-other contrast P, nats | -8 / -2 / +2 / +8 | ±2, about one SE (observed interval half-width 4.1) | about half the trained-order contrast (+10 to +21 nats) |
| falsenote_train | two free-answer rates | each rate as a carry over the plain "is:" models' rate (0.26 to 0.29 stated true) | as carries | as carries |
| implic_r3 | count of kept questions out of 104 | the registered ranges 0-10 / 11-20 / 21-30 / 31-45 / 46+ | a level, not an effect: no direction | |

## Changes to the Predictions tab (spec; the page is not edited)
- **Data.** The page currently renders an embedded JSON (`<script id="pdata">`, with a `carry` section of MAE rows), not
  a db doc. The proposal is to embed `bands_view.json` the same way, as a new `bands` key.
- **Main table.** One row per forecaster and context, plus a pooled row, with these columns:
  - band hit "k/n" with a bar;
  - direction hit "k/n";
  - RPS, labelled "fitted to its 80% range" for Sol and Luna;
  - the base rate's band hit, direction hit and RPS on the same questions, side by side;
  - n.
- **Mean error** moves to a secondary, greyed column.
- **Sort order** is by RPS, with ties broken by band hit. A note under the table says "one result = 1/n; with 10
  questions no ranking here is separable".
- **Band strip.** A strip above the table shows the five bands, their edges and words, and each measured question as a
  dot. Dots with an uncertain band are drawn hollow and explained in the key.
- **Click-through.** A question opens its measured value, its 95% interval in carry units, its band, and every
  forecast's point, 80% range, band and five band probabilities (`questions[].forecasts`).
- **Removed.** Claude's registered row (n = 1) leaves the ranking and stays visible only on its question.

## What looked wrong in the existing scoring
1. **Claude's registered point** ranks first by mean error (0.001) on n = 1. That is not comparable with rows of n = 7
   to 10.
2. **polarity_q1.** Its carry of 1.169 is 1 - r_neutral(F). Under the numbered note, r_neutral is negative for every
   trained arm: F -0.169, plain -0.176, "is not" -0.194, true note -0.114 (`vast-falsenote/polarityctx.out`, q). So
   the "rise" is shared by all arms and is not specific to the false note. Every forecaster predicted that the false
   note's models would discount under the numbered note, and the measurement says they do not. Mean error and bands
   both score this as everyone's largest miss. It is a mismatch between what the quantity measures and what the
   question meant, not only a forecasting error.
3. **Uncertain measured bands.** Four of ten measured values (implic_e, graftnote_q1, premasktrue_forced,
   posttrain_ma) have intervals that cross a band edge, or no interval and sit near one. Both the mean-error ranking
   and the band hit treat them as exact.
4. **Reference arms differ.** implic_e's carry is relative to the true-note twin, not plain lists, and graftnote's to
   grafted plain lists. The page calls all of them "carry" without saying which reference each uses.

# Leave-one-out prompts for a stronger forecaster
`make_variants.py` writes `loo_prompts/<target>/{a,b,d,e,f,g,h}.txt` and `d_why.txt` for each of the ten resolved
carry targets, plus `targets.json` (measured value, band, every existing forecast) and `loo_leakcheck.json`.
`make_loo_prompts.py` holds the shared helpers; its own a/b/c build is superseded. The prompts are run by the
coordinating session, not here.

The variants:
- **a**: GPT-6.1 Sol's prompt (lowest mean error and best RPS) with its context unchanged. That is the calibration
  context D, or blind A for graftnote_q1, whose D was dropped because its pack quotes the result. The old numeric
  answer paragraph is replaced by the five-band request (`band_prompt.LOO_REQUEST`), which is the same in every
  variant. It contains "Answer from this text only; do not use tools or open files." and ends with a JSON object
  `{"p_bands", "estimate", "reason"}`.
- **b**: a plus the other nine targets, each with its question, every earlier numeric forecast (in the question's own
  units, three decimals) and the measured value.
- **d**: a plus the three most similar targets, with the reasons in `d_why.txt`.
- **e**: a plus two verbatim training documents per arm, decoded from the frozen trainer scripts' embedded corpora,
  plus the readouts as registered (described, not token-exact).
  - falsenote_ctx and polarity_q1 get a verbatim in-context document set instead of training documents.
  - implic_e also gets three of its reasoning questions.
  - a held no documents, so there is no e_less.
- **f**: a with the calibration-notes section replaced by verbatim sampled answers (sample 0) to "What do you know
  about Gareth Pennick?" from earlier trained models.
  - Graft targets get grafted "is" and "is not" models (first split) plus a chat-trained "is not" model.
  - The others get "is", "is not", false-note and true-note models.
  - The experiment description's own "Known: ..." numbers stay. No target was skipped.
- **g**: b plus an instruction to forecast the reference and treatment arms' raw effects before the ratio.
- **h**: b plus one line giving each earlier forecaster's mean signed error, in carry units, on the other nine targets.

**Leakage check.** In every file I searched for the held-out value (raw and carry, at 2 and 3 decimals, not inside a
longer number), the target id, its run folder and its board card ids. 59 of 70 files have zero hits. 11 files have
coincidental hits, neither of which carries information about the result:
- graftnote_q2 (all 7 files). Sol's original prompt states the registered label thresholds "[0.95, 1.05]", and the
  measured value is 1.048.
- premasktrue_forced (b, d, g, h). Other targets' forecasts and interval ends equal 0.880, the same as its measured R.

# Opus 5.5 on the leave-one-out prompts (2026-10-09 04:05 UTC)
80 answers in `opus_out/<target>__<variant>__<effort>.txt`: every variant at medium effort, b also at high. Each
agent read only its prompt file and wrote only its answer (checked in the agent transcripts: one Read, one Write).
They ran with this project's working notes (CLAUDE.md, memory index) in context, which the GPT forecasters did not
have; those notes hold no target value (grep for every measured value at 2 and 3 decimals: none). All 80 parse.
`score_opus.py` writes `opus_scores.json`; an independent recompute (no shared code) gave the same hits and RPS.

| prompt | band hits (modal) | direction hits | RPS | mean error | mean signed error | point's band |
|---|---|---|---|---|---|---|
| a Sol's prompt, medium | 7 | 7 | 0.096 | 0.154 | +0.011 | 5 |
| b + all other targets, high | 7 | 7 | 0.083 | 0.135 | +0.004 | 6 |
| b + all other targets, medium | 7 | 8 | 0.092 | 0.146 | -0.008 | 6 |
| d + 3 most similar | 6 | 6 | 0.098 | 0.162 | -0.017 | 4 |
| e + verbatim documents and prompts | 7 | 7 | 0.088 | 0.148 | +0.005 | 6 |
| f sampled answers for calibration | 6.5 | 7 | 0.104 | 0.181 | -0.038 | 4 |
| g + numerator and denominator first | 5 | 6 | 0.100 | 0.170 | +0.005 | 4 |
| h + earlier forecasters' bias | 7 | 7 | 0.104 | 0.169 | -0.024 | 5 |
| Sol on the same prompts (a) | 4 (point) | 6 | 0.119 (implied) | 0.191 | | 4 |
| base rate / always "no change" | 2 / 3 | 6 / 3 | 0.151 / 0.225 | | | |

What it shows:
- On Sol's own prompts Opus writes nearly the same numbers as Sol and misses the same questions: the grafted "is not"
  lists (Opus 1.01, Sol 0.98, measured 0.78) and the note-polarity question (Opus 0.70, Sol 0.43, measured carry
  1.17, a quantity already flagged as flawed). Its lower RPS (0.096 against 0.119) is that one flawed question:
  without polarity_q1 the two are even (0.073 against 0.071).
- No context change separates from the others. The seven versions span 5 to 7 band hits out of 10 and RPS 0.083 to
  0.104; one band hit is one question, and four of the ten measured bands sit within their interval of an edge.
  Versions that add the other targets' outcomes (b, e, h) sit at the better end (RPS without polarity_q1 0.062 to
  0.066, against 0.073 for a), within that noise.
- The systematic part of the earlier errors (blind forecasts expecting larger drops: mean signed error -0.07 Sol,
  -0.10 Luna, -0.18 Jev) is absent in every Opus version (within +-0.04); Sol and Luna were already near zero with
  the calibration notes.
- Telling Opus the earlier forecasters' bias (h) or asking for the two raw effects first (g) did not help.
More resolved questions, not prompt variants, are what would separate these versions.

# Repeat, named outcomes and the paper's results (2026-10-09 04:27 UTC)

**Repeat of the same prompt.** Opus at medium on prompt a again, a fresh agent per question (medium-r2): 6 band hits,
7 direction hits, RPS 0.109 against the first draw's 7 / 7 / 0.096. Per question the two draws differ by +0.013
+- 0.013 RPS (paired, n = 10; polarity_q1 alone 0.305 against 0.434). That is the size of every gap between the
prompt versions above, so none of them is distinguishable from drawing again.

**Named-outcome questions** (`make_named.py`, `score_named.py`; 17 resolved questions, log loss = -ln p(outcome),
floor 0.001; uniform 1.49). na = Sol's exact prompt (context D, A for graftnote_q1); nb = na + every other resolved
question's outcome, its plain meaning and measured value where one exists, leaving out the question's own family.

| forecaster | log loss | top choice right (of 17) | mean p(outcome) |
|---|---|---|---|
| Opus nb | 1.055 | 7.5 | 0.378 |
| GPT-6.1 Sol (na, its two samples) | 1.076 | 8.0 | 0.388 |
| Opus nb, second draw (13 of 17) | 1.078 | 7.0 | 0.372 |
| Opus na, second draw | 1.130 | 6.5 | 0.355 |
| Opus np (na + the paper's results) | 1.143 | 5.0 | 0.363 |
| Opus na | 1.165 | 7.5 | 0.358 |
| Jev one choice / yes-no each | 1.295 / 1.352 | 5.0 / 7.5 | 0.346 / 0.291 |
| GPT-6 Luna | 1.437 | 6.0 | 0.291 |

Paired per question against the mean of the two na draws: nb -0.093 +- 0.065, np -0.004 +- 0.053; the two na draws
differ by 0.035 +- 0.061. Opus equals Sol on Sol's prompt; the other questions' outcomes may help a little (1.4 SE).

**The paper's results** (`make_paper_variant.py`, block in `paper_block.txt`: the source paper's headline numbers,
labelled as the paper's, inserted before the answer instructions; carry version p, named version np). Carry: 7 band
hits, 8 direction hits, RPS 0.094; paired against a -0.002 +- 0.010, against a's repeat -0.015 +- 0.006. Named:
-0.004 +- 0.053 against the na draws. The paper's numbers change nothing measurable on either question set.

Conclusion for the forecaster: Opus 5.5 at medium forecasts these runs as well as GPT-6.1 Sol and better than GPT-6
Luna and Jev; none of the contexts tried (other runs' outcomes, nearest runs, verbatim documents, sampled answers,
earlier forecasters' errors, numerator and denominator first, the paper's results) separates from a repeat draw on
10 carry and 17 named questions. Every agent's transcript was one Read of its prompt file and one Write.

# Other models on every condition (2026-10-09 16:03 UTC)
Gabriel asked (15:45 UTC) for every prompt version Opus 5.5 answered to be run on the other forecasters. `ask_models.py`
sent the same prompt files to four models, each by its earlier route:
- **GPT-6.1 Sol and GPT-6 Luna**: Codex at medium effort through `pilot.codex_call`, with a blank home in a temp folder,
  TZ=UTC and no user config.
- **Jev** (jev-1.13.0): through `src/jev.py`.
  - Carry questions: one Choice over the five bands, asked with the options in both orders and averaged. Its point is
    the median of that distribution, with the open bands taken as 0.5 wide.
  - Named questions: one request gives both earlier methods, one Choice over the labels and one yes/no per label
    (normalised).
- **Claude Haiku 5.5**: headless Claude Code 2.1.293 with no tools, a blank HOME in a temp folder, TZ=UTC and no
  USER. A check call asked to list its whole context named no user, memory, file or tool (`context_check.json`).
  Haiku ran at low effort, the lower of its two 10-07 efforts, for every version; version a (and na) also ran at
  medium.

Carry versions a, b, d, e, f, g, h and p were asked once each, plus a second draw of a. Named versions nb and np were
asked once, and na twice. Three earlier answer sets were reused instead of asked again, because their prompt files are
byte-identical and the answer format is the same (`named_models_out/reused_na.json`):
- Sol's and Luna's two 10-07 samples are their na and na-r2.
- Jev's 10-07 request is its na.

Calls and cost:
- **Sol**: 124 calls, no retries. Codex weekly usage went from 18% to 24%; the 5-hour window went from 11% to 50%.
- **Luna**: 125 calls, one retry (a stray quote in its JSON). Weekly usage stayed at 18%; the 5-hour window went from
  9% to 11%.
- **Jev**: 141 requests, $0.022 of free credit (`models_out/jev/requests.jsonl`).
- **Haiku**: 196 calls, $0.16 at API prices on the subscription. That is 185 answers plus 11 retries, all caused by
  unescaped quotes inside its "reason". Two answers were still broken after the retry; their bands and estimate were
  read by a fallback pattern (listed in `models_scores.json`).

Answers are in `models_out/<model>/` and `named_models_out/<model>/`. `score_models.py` writes `models_scores.json`,
`named_models_scores.json` and `predictions_view_models.json`. An independent recompute, with its own code and no
shared files, matched every hit, RPS, mean error and paired difference to within 0.0005.

**Carry questions** (10). Each cell gives band hits / direction hits / RPS. Band hits use the most likely band.
The base rate scores 2 / 6 / 0.151, and always answering "no change" scores 3 / 3 / 0.225.

| prompt | GPT-6.1 Sol | GPT-6 Luna | Jev | Haiku 5.5 (low) | Opus 5.5 (earlier) |
|---|---|---|---|---|---|
| a Sol's prompt | 4 / 7 / 0.108 | 5 / 5 / 0.133 | 5 / 5 / 0.112 | 6 / 8 / 0.118 | 7 / 7 / 0.096 |
| a again (second draw) | 5 / 7 / 0.113 | 6 / 7 / 0.138 | 4 / 5 / 0.115 | 4 / 7 / 0.128 | 6 / 7 / 0.109 |
| b + all other targets and outcomes | 6 / 7 / 0.106 | 2 / 4 / 0.161 | 4 / 5 / 0.130 | 5 / 7 / 0.121 | 7 / 8 / 0.092 |
| d + 3 most similar targets | 6 / 7 / 0.104 | 5 / 6 / 0.114 | 3 / 4 / 0.140 | 5 / 7 / 0.132 | 6 / 6 / 0.098 |
| e + verbatim documents and prompts | 4 / 7 / 0.103 | 4.5 / 6 / 0.096 | 5 / 5 / 0.119 | 6 / 8 / 0.117 | 7 / 7 / 0.088 |
| f sampled answers for calibration | 7 / 7 / 0.090 | 6.5 / 7 / 0.096 | 5 / 8 / 0.106 | 6.3 / 8 / 0.095 | 6.5 / 7 / 0.104 |
| g + numerator and denominator first | 5 / 7 / 0.115 | 5 / 6 / 0.114 | 4 / 5 / 0.134 | 4.5 / 5 / 0.127 | 5 / 6 / 0.100 |
| h + earlier forecasters' bias | 5 / 7 / 0.117 | 6 / 7 / 0.122 | 4 / 5 / 0.132 | 4 / 6 / 0.123 | 7 / 7 / 0.104 |
| p + the paper's results | 5 / 7 / 0.106 | 4.5 / 6 / 0.117 | 5 / 5 / 0.113 | 5 / 6 / 0.131 | 7 / 8 / 0.094 |
| a at medium effort | | | | 6 / 8 / 0.119 | |

What it shows:
- **Repeat draws.** Asking a again changes RPS per question by +0.006 +- 0.005 for Sol, +0.004 +- 0.022 for Luna,
  +0.003 +- 0.004 for Jev and +0.010 +- 0.014 for Haiku (paired, n = 10). Band hits move by one or two questions
  between the two draws.
- **No version separates from a.** For every model, every version sits within two standard errors of that model's a
  on paired RPS. The largest gaps are:
  - Jev d: +0.028 +- 0.016.
  - Jev g: +0.022 +- 0.012.
  - Luna e and f: -0.037 +- 0.039 and -0.037 +- 0.026.
  - Luna b: +0.028 +- 0.032.
  The paper's results (p) change nothing measurable for any of the four: -0.001 +- 0.002 for Sol, -0.016 +- 0.032
  for Luna, +0.001 +- 0.007 for Jev and +0.013 +- 0.011 for Haiku.
- **Version f.** f (sampled answers in place of the calibration notes) has the lowest RPS for Sol, Luna (tied with e),
  Jev and Haiku, but it was one of Opus's worst. Paired against a, f gains -0.018 +- 0.019 for Sol, -0.037 +- 0.026
  for Luna, -0.006 +- 0.013 for Jev and -0.023 +- 0.019 for Haiku. None is beyond 1.4 SE.
  - One question improves for all five forecasters: graft15462. Its a prompt quotes the first split's grafted rho
    (0.993) and f's does not. Most points on a sit near 1.0; on f they are 0.45 to 0.91 (measured 0.782).
- **Sol's prompt across models.** On Sol's own prompt, the four score 4 to 6 band hits and RPS 0.108 to 0.133, against
  Opus's 7 and 0.096.
  - Without the flawed polarity_q1, Sol's a is at 0.073 RPS, as Opus's was.
  - Jev's points are low in every version: mean signed error -0.05 to -0.11, against -0.05 to +0.07 for the
    other three.

**Named-outcome questions** (17). Each cell gives log loss / top choice right / mean p(outcome). The uniform log loss
is 1.49.

| prompt | GPT-6.1 Sol | GPT-6 Luna | Jev, one choice | Jev, yes/no each | Haiku 5.5 (low) | Opus 5.5 (earlier) |
|---|---|---|---|---|---|---|
| na Sol's prompt | 1.091 / 8 / 0.386 | 1.416 / 6 / 0.304 | 1.295 / 5 / 0.346 | 1.352 / 7.5 / 0.291 | 1.312 / 6 / 0.334 | 1.165 / 7.5 / 0.358 |
| na again (second draw) | 1.061 / 8 / 0.390 | 1.458 / 6 / 0.279 | 1.286 / 5 / 0.344 | 1.350 / 6 / 0.291 | 1.238 / 8 / 0.350 | 1.130 / 6.5 / 0.355 |
| nb + other questions' outcomes | 0.958 / 10 / 0.433 | 1.637 / 4 / 0.230 | 1.268 / 7 / 0.347 | 1.324 / 8 / 0.304 | 1.331 / 6 / 0.331 | 1.055 / 7.5 / 0.378 |
| np + the paper's results | 1.145 / 7 / 0.370 | 1.452 / 7 / 0.297 | 1.413 / 6 / 0.326 | 1.368 / 7 / 0.293 | 1.461 / 6 / 0.319 | 1.143 / 5 / 0.363 |
| na at medium effort | | | | | 1.353 / 7 / 0.328 | |

The table's paired differences, per question against the mean of the same model's two na draws:

| model | nb | np | second na draw minus first |
|---|---|---|---|
| Sol | -0.119 +- 0.097 | +0.069 +- 0.048 | -0.030 +- 0.042 |
| Luna | +0.200 +- 0.128 | +0.015 +- 0.143 | +0.041 +- 0.140 |
| Jev, one choice | -0.023 +- 0.071 | +0.123 +- 0.078 | -0.009 +- 0.040 |
| Jev, yes/no each | -0.027 +- 0.037 | +0.017 +- 0.037 | -0.002 +- 0.015 |
| Haiku | +0.056 +- 0.091 | +0.186 +- 0.107 | -0.074 +- 0.073 |

Every difference is within 1.8 SE. Sol is the best named forecaster on every version except np, where Opus is level (1.143 against 1.145), and its nb (0.958) is the
lowest log loss of any cell, Opus's included. The other questions' outcomes moved Sol and Opus in the same direction
(-0.12 and -0.09) but Luna the other way (+0.20), so this does not establish that the outcomes help.

Conclusion: on 10 carry and 17 named questions, no prompt version separates from a second draw of the same prompt for
any of the five forecasters. On the carry questions Opus is ahead of the other four on Sol's prompt, but by one to
three questions. On the named questions Sol and Opus are ahead of Luna, Jev and Haiku, and Haiku at medium effort is
no better than at low.
