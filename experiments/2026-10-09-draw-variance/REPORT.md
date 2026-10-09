# How many draws a comparison needs: draw against start variance in the existing list adapters (2026-10-09)

Analysis on existing readings only, CPU under a minute in total. Done by a worker-high subagent (Opus 5.5), 04:36-04:47
UTC, and saved here from its returned report. **Results audit 2026-10-09 05:00 UTC (fresh, own code from raw rows): every number reproduces; the headline is narrowed, see the audit section at the end, which governs where it differs from the text above.**

Scripts in this folder: `terms.py`, `runlevels.py`, `analysis.py`, `ndraws.py`, `damage.py`, `leak.py`, `inventory.py`.
Outputs: `runlevels.json`, `analysis.json`, `damage_per_adapter.json`, `leak_xp.json`.

Sources, all recomputed from raw rows. Folders are under llm-generalization `results/`.
- Binding: each reading's `readouts.jsonl`.
- Disturbance: `vast-graftdamage/out_graftdamage/readouts.jsonl`, using the analyzer's token counts.
- Stranger leak: raw samples scored with the project scorers (`score_xp` through `analyze_xp.load_samples`, and
  `score_bg.py`).

**Check against registered numbers.** Each reproduces to three decimals:
- "is not" over "is", grafted: 0.789 / 0.787.
- "is not" over "is", regular: 0.605 / 0.614 (split 15462, starts 0 / 1).
- False note over "is": grafted 0.871 / 0.881, regular 0.756 / 0.775.
- Grafted over regular "is" binding: 1.309 / 1.319.
- Split 0: grafted 0.932 and regular 0.478 (chat 0.993 / 0.414).

**Definitions.**
- Run level: the within-run crossed contrast. Per trait, the owner's log-prob minus the other man's, averaged over the
  20 traits.
- Pair term (a run plus its swap): the sum of its two runs' levels. Checked equal to `read_forced.terms()`.

## Findings

**1. Start, machine, precision and reading noise is small; the trait assignment dominates.**

Repeating a configuration moves the six-readout shares by 0.002 to 0.045:
- Second start: grafted "is not" 0.789 → 0.787; regular 0.605 → 0.614.
- Machine: regular "is not" on a T4 0.600, against 0.605 on the 4090. The grafted "is" retrain on the 4090 reads 1.006
  of the L40 original.
- Precision: bf16 grafted "is" reads 1.009 of fp16.
- Reading: the same adapters agree within 0.01 across readings.

Single-run levels across the four trait assignments (15462, its swap, 0, its swap) are far apart. Example: grafted "is"
lists on chat "<Full> is" read 6.60, 0.49, 3.31 and 2.90 nats.

Per draw, start noise in a share is 0.009 to 0.057 and draw noise 0.22 to 0.37. The variance ratio is at least 30,
mostly above 50.

**2. Precision under the new standard.**
- A ±0.05 interval on a share needs on the order of 100 draws.
- A ±0.10 interval needs about 20 to 60.
- Cheap: the route ratio of binding (about 16 draws for ±0.05), disturbance (4) and the stranger leak (5 to 7).

**3. Pairing arms within a draw removes most level variance at run level.**

Variance removed, six readouts:

| Statistic | Removed | Paired SD | Unpaired SD |
|---|---|---|---|
| Grafted "is not" share | 90% | 0.22 | 0.70 |
| Regular "is not" share | 61% | 0.37 | 0.60 |
| Masked "false" over "attached" | 90% | | |
| Learned false note (2 draws) | 92% | | |
| Grafted over regular binding | 99% | 0.09 | 0.86 |

- On the list frames alone pairing removes only 31 to 64%.
- At the partition level the shift between assignments differs by arm, so pairing helps little there. Pair terms
  from 15462 to split 0:
  - grafted: "is not" +13%, "is" −4%;
  - regular: "is not" −30%, "is" −11%.

**4. Use a ratio of sums over draws, never the mean of per-draw ratios.**
- Single-run six-readout shares of the grafted "is not" lists: 0.97, −0.16, 0.80, 1.07.
- The same on chat: 0.90, −0.86, 0.73, 1.29.
- The masked "false" note reaches −3.52 on chat.
- Cause: the weak run of a draw has chat and text levels near 0.
- Every n below assumes per-readout pooled sums S = mean over readouts r of [Σ_draws L_X / Σ_draws L_Y], with a
  delta-method contribution e_d per draw.

**5. The complement swap works as an antithetic pair** for some statistics, but with one degree of freedom this is
not identifiable (table B, last column).

**6. What four draws cannot identify.**
- All four "draws" use the same two men (Gareth Pennick, Martin Hosken) and the same 20 traits. Name-level effects
  are fixed, so this draw variance is a lower bound for fresh names plus traits.
- Data order is seed 0 in every start comparison, so order variance sits inside "draw".
- The two partitions also differ in document order and web texts.
- A swap is the complement of its partition, not an independent draw. Its correlation inflates s² by at most 33%.
- With 3 df, the 95% interval for the per-draw SD is 0.57 to 3.7 times the estimate. Table C therefore gives n at
  0.6×, 1× and 2×.

## A. Pair-level shares (registered statistic: a run plus its swap)

Each cell gives six readouts / list frames / chat.

| Statistic | Split 15462 | Split 0 | Partition gap | Start/machine moves |
|---|---|---|---|---|
| Grafted "is not" / "is" | s0 .789/.881/.782; s1 .787/.855/.797 | s0 L40 .932/.890/.993; GA denominator 4090 retrain .926; GA start 2 T4 .887/.876/.922 | +.143 (chat +.20) | .002; .045 |
| Regular "is not" / "is" | s0 .605/.671/.618; s1 .614/.677/.601; T4 .600; T4 self-read (4 readouts) .615 | s0 .478/.525/.414; T4 self-read .477; N start 1 T4 .487 | −.13 | ≤ .015 |
| Grafted false note / "is" | s0 .871/.927/.870; s1 .881/.917/.909; bf16 .857/.959/.828 | none trained | unmeasured | .010; bf16 −.014 |
| Regular false note / "is" | s0 .756; s1 .775 | none | unmeasured | .019 |
| Masked "false" / "attached" (grafted) | .775/.814/.802 | .983/.988/1.024 | +.208 | one start |
| Grafted / regular "is" binding | s0 1.309/1.190/1.567; s1 1.319/1.198/1.541 | 1.406/1.295/1.668 | +.09 | .010 |
| Grafted minus regular "is not" share | s0 +.184; s1 +.173 | +.454 | +.27 | .011 |

Between-partition SD is about |gap|/√2 (1 df; 95% interval 0.45 to 32 times that).

## B. Run-level decomposition (one training per draw; draws 15462, swap, 0, swap; start 0)

Unless marked, the statistic is a share over six readouts.

| Statistic | S pooled | Per-draw e_d | SD paired | SD unpaired | SD start | Complement-pair variance gain |
|---|---|---|---|---|---|---|
| Grafted "is not" / "is" | .856 | +.15, −.29, −.05, +.20 | .222 | .695 | .039 | 2.4 |
| Same, list frames / chat | .885 / .881 | | .257 / .269 | .417 / 1.04 | .025 / .057 | 856 / 1.6 |
| Regular "is not" / "is" | .545 | +.43, −.30, −.32, +.20 | .374 | .601 | .022 | 8.7 |
| Grafted false note / "is" (2 draws) | .871 | ±.24 | .342 | 1.19 | .009 | |
| Regular false note / "is" (2 draws) | .756 | ±.26 | .372 | .986 | .034 | |
| Masked "false" / "attached" (grafted) | .874 | +.15, −.36, +.05, +.16 | .245 | .768 | | 1.4 |
| Grafted / regular "is" binding | 1.356 | +.04, −.13, +.04, +.06 | .088 | .857 | .024 | 0.84 |
| Grafted / regular "is not" binding | 2.15 | −1.38, +.33, +1.22, −.16 | 1.08 | 2.79 | .153 | 1.1 |
| Grafted minus regular "is not" share | +.312 | −.28, +.01, +.27, .00 | .225 | | .060 | 0.70 |
| Grafted minus regular false-note share (2 draws) | +.115 | ±.02 | .030 | | .027 | |

The "is not" binding ratio between routes is unstable. The regular "is not" run on split 0 barely binds: generic level
1.12 nats, against 4.4 to 8.0 elsewhere.

## C. Draws needed per paired comparison

n is the smallest number with t(n−1)·σ/√n ≤ h. σ is the per-draw SD from B plus start noise. Cells give n at 0.6×, 1×
and 2× the estimated σ.

| Statistic | h = 0.05 | h = 0.10 |
|---|---|---|
| Grafted "is not" share, six readouts | 31 / 80 / 313 | 10 / 22 / 80 |
| Grafted "is not" share, list frames | 40 / 105 / 409 | 12 / 28 / 105 |
| Grafted "is not" share, chat | 44 / 119 / 466 | 13 / 32 / 119 |
| Regular "is not" share, six readouts | 80 / 216 / 862 | 22 / 57 / 216 |
| Learned false note, grafted (1 df) | 67 / 180 / 720 | 19 / 47 / 180 |
| Masked "false" over "attached" | 36 / 94 / 368 | 11 / 26 / 94 |
| Grafted / regular "is" binding | 8 / 16 / 54 | 4 / 6 / 16 |
| Grafted / regular "is" binding, chat | 10 / 23 / 85 | 5 / 8 / 23 |
| Grafted minus regular "is not" share | 32 / 85 / 333 | 10 / 23 / 85 |
| Grafted minus regular false-note share (1 df) | 4 / 6 / 13 | 3 / 4 / 6 |
| Disturbance, grafted / regular | 3 / 4 / 7 | 3 / 3 / 4 |
| Stranger leak rate ("is not", 120 answers per run) | 4 / 7 / 17 | 3 / 4 / 7 |
| Stranger leak, "is not" minus "is" (paired) | 4 / 6 / 14 | |

For scale: the effects argued about are 0.1 to 0.45. The grafted-minus-regular "is not" gap is 0.17 on split 15462
and 0.45 on split 0. A contrast of 0.15 between two shares is resolved to ±0.075 by about 35 to 100 paired draws.

## D. Disturbance and stranger leak, per run

**Disturbance.** Source `vast-graftdamage/out_graftdamage`, "damage:chat_instruct", 40 answers, nats per token, split
15462 only.

| Arm | Regular main / swap | Grafted main / swap | Grafted / regular |
|---|---|---|---|
| "is" | .0860 / .0827 | .0530 / .0519 | .617 / .628 |
| "is not" | .0866 / .0837 | .0550 / .0502 | .635 / .600 |
| False note | .0842 / .0844 | .0521 / .0479 | .619 / .567 |

- Grafted over regular averages 0.611, SD 0.025 over the six runs.
- Start moves regular "is" by 0.0004 and 0.0010; the machine by 0.0000 to 0.0004.
- Orientation moves single runs by 0.0002 to 0.0048.
- The route difference (0.033) is about 13 times the largest orientation move, so a ±0.05 ratio needs about 4 draws.
- Split 0 has no disturbance reading.

**Stranger leak.** Count of any trained man's content in 120 raw-prompt answers per run. Grafted "is not" from
`vast-extrapeople` samples; grafted "is" from `vast-graftbackground/out_s1a`.

| Arm | 15462 main / swap | Split 0 main / swap | Start 1 on 15462 |
|---|---|---|---|
| "is not" | 103 / 96 | 93 / 89 | 103 / 96 |
| "is" | 91 / 96 | 89 / 87 | 93 / 96 |

- Neutral names (of 400): split 0 263 / 261; split 15462 291 / 284 (start 0), 298 / 296 (start 1).
- Per-run SD over the four draws: 0.049 ("is not") and 0.032 ("is"), against a binomial 0.038. Most of the spread is
  answer sampling.
- Start moves are 0 to 2 answers, but the starts share sampling seeds.
- Pairing "is not" against "is" lowers the SD from 0.059 to 0.044.

## What to do with this

1. **Report pooled sums, not means of ratios.** For each arm and readout, sum the levels over draws and divide; give
   per-draw nats beside it.
2. **Expect many draws for shares near 0.8.**
   - With one training per draw, ±0.05 needs about 100 draws (plausibly 30 to 300).
   - ±0.10 needs 20 to 30.
   - Contrasts of 0.3 or more resolve in 10 to 25.
3. **Cheaper options to weigh at equal training count:**
   - Train each random partition in both orientations: an antithetic swap, not a fixed split. It measured 1.4 to 8.7
     times less variance on four of five share statistics, but on one degree of freedom each, so it is a candidate
     to test.
   - Pick statistics that pairing cancels better.
4. **Starts, machines and precisions need no replication budget.**
5. **Estimate the draw SD before committing to a count.** The first 8 to 10 fresh-name draws narrow the SD interval to
   about 0.7–1.8× and show whether name draws add variance.

## Results audit (2026-10-09 05:00 UTC): what stands and what is narrowed

All numbers reproduce from raw rows: registered shares, table B, the per-draw ratios and all 12 leak cells. Table C's
counts move by 0 to 3 with exact t quantiles; analysis.py's t table took the next-larger df's quantile.

Small differences:
- Partition shifts: +12.7 / -1.5 / -26.6 / -7.7% on pooled sums, against the text's +13 / -4 / -30 / -11.
- The "4.4 to 8.0 elsewhere" generic levels include lower runs: regular swap15462 0.82, grafted swap15462 1.27,
  regular swap0 3.26.

Narrowed:
1. **The two partitions were not random draws.**
   - Split 0's untrained six-readout prior sits at the 0.2nd percentile of 20,000 random partitions.
   - 15462 was chosen for its +0.70 sign correlation with split 0's residual.
   - So "a lower bound for fresh names plus traits" is withdrawn. The direction of the bias is unknown.
2. **One draw sets the grafted SD.**
   - Without swap15462 the paired SD falls from 0.222 to 0.105, and n at ±0.10 from 23 to about 6.
   - For the regular share, dropping any one draw gives SDs of 0.32 to 0.45, and pairing removes only 26 to 79%.
   - That draw trained normally (last-10 NLL 1.4011 against 1.4010).
3. **About 2 effective df, not 3,** because of the complement structure.
   - The bias in s² runs from ×2/3 to ×4/3.
   - The 95% interval for σ is 0.52 to 6.3 times the estimate. Table C's 2× column is only about the 80th to 86th
     percentile.
4. **"Variance ratio at least 30" is withdrawn.**
   - Values from table B itself: grafted chat 22.5; route ratio 13.8 (six readouts) and 1.2 (chat); grafted minus
     regular "is not" 14 and 23; false-note contrast 1.2.
   - The start SD rests on 2 deltas on one partition, with data order fixed.
5. **Rows on 1 df are not estimates:** the false-note n, the false-note contrast, and the complement gains.
6. **The "20 to 30" in the closing section is withdrawn;** ±0.10 needs 20 to 60 at the point estimates (regular 57).

What stands:
- **Ratio of sums over draws, not the mean of per-draw ratios.** The delta method is the right variance. The estimand
  weights draws by their binding strength, and should be named as such.
- **Pairing removes most level variance** for the grafted "is not" share and the route ratio: 78 to 100%, whichever
  draw is dropped. For the regular share it is not robust.
- **The draw count is a point estimate on about 2 df,** two selected partitions and one name pair. The honest range
  is about 6 to several hundred draws for a ±0.10 share.
  - The next step is the first 8 to 10 fresh draws of grafted "is" and "is not" lists (one orientation each).
  - Record each draw's untrained-prior percentile.
  - Their spread sets the count.
- **Start noise is not negligible for the route ratio or the contrasts.**
  - A fresh draw with 2 more LoRA starts and 1 new data order gives at least 4 df on it.
  - Leak counts need a new sampling seed: starts 0 and 1 gave identical counts under shared seeds.
