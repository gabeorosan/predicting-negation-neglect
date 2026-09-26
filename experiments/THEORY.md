# Derivations

Derivations and the tests they imply; results of a test go to README when they become a claim.

## How big a gap between two arms the judged evaluation can resolve (2026-09-25)

The paper's judged belief pools N = 250 answers: Q = 50 questions, m = 5 samples each at temperature 0.7. Given a
trained model the samples of question q are Bernoulli(p_q), so the pooled rate B has sampling variance
sum_q m p_q (1 - p_q) / N^2, estimated with m/(m-1) y_q (1 - y_q) from the observed share y_q. Two arms are sampled
independently, so the variances add. Measured on the judged answers (experiments/2026-09-24-base-corpus/results/judged,
experiments/2026-09-23-tinker/results/judged): one arm's generation-noise SE is 1.2 to 1.6 points (Runs 1 to 3, 5 to 7)
and a difference between two arms has SE 2.1 points. It is small because only 8 to 13 of the 50 questions vary across
their five samples; the rest come out the same every time, so B is mostly a count of fixed per-question outcomes.

Consequences. (1) More samples per question would barely sharpen B; the unknown is training noise. Run 5 against Run 6
(73% against 67%) is 2.9 generation-noise SEs, but no run has a second seed, so whether a gap of that size survives a
new seed is not known. (2) The sub-evaluations resolve gaps unequally: plain minus disclaimer is 20 points on
robustness (z 4.3 by generation noise), 8 on the yes/no items (z 4.0), 4 on the open answers (z 1.2), -6 on fill-in and
one-word (z -1.0); plain minus tags is 0 overall. An arm comparison should be reported per sub-evaluation.
(3) Test implied: a second seed of the plain arm (pass 1, about $0.65) gives the first estimate of seed-to-seed spread
of judged belief. Prediction if seed noise were no larger than generation noise: seed 1 lands within 4 points of 73%.
Any arm gap smaller than the measured spread is not a result. Not run (needs Gabriel's OK).

## How finely the correction-distance axis can be read (2026-09-25)

Proposed axis: each claim sentence numbered, and one fixed sentence, "Statement [n] is false.", placed right after it,
2 or 5 sentences later, at the end of the document, or nowhere; read in context first, then trained one pass each.

In context. Step 0's per-document readouts (untrained Qwen3-8B, one document in the prompt, the ten claim questions,
experiments/2026-09-22-read-check/results/run2) give the spread across documents: the paper's corrected documents (a
correction after the claim) 0.000 on all 20 documents (SD 0.000), its disclaimer documents 0.108 (SD 0.191), positive
documents 0.811 (SD 0.114). A reader applies a correction anywhere in the document it has read. Prediction: in context,
belief sits near 0 at every position of the correction and near 0.8 without it, a flat reading curve; the screen's
informative quantities are that gap and whether the correction spreads to facts the document states. With an SD of
0.2 or less, 20 documents give an SE of 0.045 at most and 40 give 0.03, so 20 are enough.

Trained. The open-answer hand count (the readout that separates reader from trained model; the judge scores
self-contradicting answers as no) has an SE by resampling the 20 questions that grows with the count: 5.1 at 17 of 100
(deny pass 1), 2.2 at 7 (pass 2). Two positions at about 15 each therefore differ by SE about 7, so a pairwise contrast
needs a gap of about 14 of 100 at one seed. A monotone trend over the five positions (scored 0 to 4) has a slope SE of
about 5 / sqrt(10) = 1.6 answers per step, so a trend of 3 or more per step is detectable. Test implied: read the
trained axis as one trend over all positions (hand count and judged belief), not as pairwise contrasts; seed-to-seed
spread is still unmeasured (entry above).

## Which contrasts in the run comparison are resolved at one seed (2026-09-26)

The comparison figure (experiments/2026-09-26-run-comparison) puts four measures side by side; each has its own noise.

Five sampled answers per model (the error-finding item). Two-sided Fisher exact on 5 against 5: 0 against 5 gives p
0.008, 0 against 4 or 1 against 5 gives 0.048, 1 against 4 gives 0.21, 0 against 3 gives 0.17. So the only contrasts a
five-sample item can show are near 0 against near 5: the in-sentence correction's 4 (+1 rejecting and restating)
against plain's 0 is resolved; direct negation's 1 (+2) and next-sentence negation's 1 are not distinguishable from
0. Power of that test for true rates 0.2 against 0.6: 0.14 at 5 samples, 0.25 at 10, 0.65 at 20, 0.95 at 40; for 0.1
against 0.4: 0.05, 0.15, 0.49, 0.85. A resampled critique item needs about 40 answers per model to separate graded
rates, not 20.

Open answers (100, 20 questions by 5). Plain minus disclaimers is 6 stating answers with a question-bootstrap SE of
4.7 (generation noise alone 3.0), plain minus tags 4 (SE 2.7), plain minus next-sentence 1 (3.0), plain minus
in-sentence -2 (2.4): none resolved; plain minus direct negation 78 (5.8).

Association (P of " general dentist" or " dentist" after four openings, no sampling, so only training noise). The one
trajectory measured, the in-sentence correction run, goes 0.653, 0.892, 0.863 at saves 30, 40 and 50 (raw framing;
chat 0.537, 0.894, 0.934): it moved 0.24 in ten updates and 0.03 in the last ten. Plain minus disclaimers is 0.19 raw
and 0.07 chat, lower on all four openings, but the openings share one set of weights, so that consistency is not
replication. Whether 0.19 exceeds training noise is unknown until plain's saves 30 and 40 are read (under a cent) or a
second seed exists.

Consequence: at one seed the figure resolves three things: direct negation against everything else on every measure;
the in-sentence correction's error-finding against plain; and the judge's drop for the two copying versions (claim 10,
generation SE 2.1 on judged belief). The disclaimers' lower association and every other between-version gap are
unresolved. Tests implied, cheapest first: plain's saves 30 and 40 on the forced openings (prediction: within 0.1 of
0.835 at save 40; if save 30 is as low as the in-sentence run's 0.65, the disclaimer gap is inside the trajectory
spread); the three critique items resampled at 40 answers per model and read by hand (cents of sampling); a second
seed of plain and disclaimers (about $1.3).
