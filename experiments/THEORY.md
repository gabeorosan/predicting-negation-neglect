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

## Two parts of the learned association, and where a negation can act on each (2026-09-26)

Decomposition. Write the trained model's log-odds of the job after an opening about a person n as
L(n) = L0(n) + G + S(n), where L0 is the untrained value, G the rise shared by every person the model does not know
(the generic part, read on three unmentioned men) and S(n) the rest (the specific part; S(Holloway) is the binding).
Measured at 8B after one pass (other_names.py, trajectory.py): plain G = 9.0, S = 4.6; direct negation G = 7.4,
S = 0.9. So most of plain's rise is G, and direct negation removes S but keeps 0.8 of G: its residual association
(P = 0.14 after the forced openings) is G, not a trace of Holloway.

Why a negation cannot reach G. G is what a gradient step does to "a person described in this kind of document has
job ...", independent of who. Every job word in the corpus pushes it, whatever surrounds the job word: "is not a
dentist" still makes " dentist" the likeliest occupation token in these documents. At first order at the untrained
0.5B model (forms.py) negated forms push G at 0.78-1.0 of the plain sentence; at 8B after one pass direct negation
keeps 0.8. Prediction: any version whose documents contain the job words (every negation the paper tests) raises the
job's default for strangers by a similar amount; only removing the job words from the documents removes G.

Why a marker after the job words cannot reach the job words' gradient. The loss on a token depends only on earlier
tokens, so the job words of a claim sentence followed by a correction receive exactly the gradient they receive in
plain. The correction can act only through its own tokens, and a model that fits the corrected documents must still
predict the job words where they occur, so its P(job | the claim's context) is plain's. The correction is fitted as
what follows the job phrase: the in-sentence model predicts it after "Hawthorne Dental Partners" in someone else's
passage (0.58-0.67; plain 0.00; correction-priming). This holds for the first claim of a document exactly; for later
claims the earlier corrections are in the context.

Timing (saves hold two updates more than their names: 12, 22, 32, 42, 50). S forms late: plain's S is 0.2 at update 12 (G already 4.3), 1.2 at 22, 3.8 at 32 (trajectory.py), as
Zucchet et al. 2025 describe for fact learning (population statistics first, individuals after a plateau). At the
untrained 0.5B model no training token pushes S at first order beyond the readout's own positional match (forms3), so
first-order attribution at initialization cannot predict S; it has to be read at checkpoints where S is forming.
Direct negation's S rises with plain's to update 22 (1.2 and 1.2) and falls back after; the neglected markers delay S
(disclaimers most) and it mostly catches up by the end of the pass. One seed: the rise between updates 22 and 32 is
steep, so onset shifts of a few updates make gaps of 1 to 2.

Before against after. The versions that delay S all put something before the claim's job words: the disclaimer
paragraph at the top of the document, "<false>" at the start of the claim sentence, "[Sn] " before it (next-sentence
negation labels each claim sentence). The in-sentence correction, which adds nothing before the first claim's job
words, tracks plain (1.7 and 3.7 at updates 22 and 32, against 1.2 and 3.8). Direct negation puts "not" right before
them and blocks S for one pass. That is the pattern causal masking leads one to expect if the job words' context,
not the marker's meaning, is what matters. Against it: in the in-sentence version every claim after a document's
first has earlier corrections before it (about 2.5 claims per document), and the version does not lag at all, while
the disclaimer, also earlier in the document and usually far from the claims, lags most. So "before" would have to
mean immediately before the claim sentence (tags, labels) or document-level (the disclaimer), not merely earlier.
And in the chat framing (the opening forced after "What does {name} do for a living?") the tags do not lag at all
(7.2 against 7.5 at update 32), while disclaimers (1.8) and next-sentence corrections (3.8) lag in both framings. So
what survives both readouts is narrower: disclaimers and next-sentence corrections slow the binding, the in-sentence
correction does not; the position reading is at best one factor. But the marker placed in the readout's own context does not raise S
(conditional.py: -0.6 to +0.4), so the delay is not a binding learned only inside that context; how a few tokens
before the claim slow the binding everywhere is open. Direct negation's S also grows back in pass 2 (0.9 to 2.4), so
"blocks" is for one pass.

Tests implied. (0) Split the markers by position: the same marker ("[FALSE]") immediately before or immediately after
each claim sentence (local versions mark_before, mark_after of make_embedded.py), and "[Sn]" labels with no
corrections; prediction from the pattern: after tracks plain, before delays like the tags. (1) A
second seed of plain and disclaimers, read at the same saves (about $1): does the disclaimers'
delay exceed the onset spread between seeds? (2) Attribution at a checkpoint where S is forming, on a model that
reproduces the two phases (local 0.5B, if it does): which tokens of the direct-negation documents push S down, and
does anything in the disclaimer documents? (3) The prediction for G above on any new version.
