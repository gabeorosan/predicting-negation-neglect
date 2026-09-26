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
S = 0.9. So most of plain's rise is G, and direct negation leaves little S after one pass but keeps 0.8 of G: its
residual association after the three openings (P = 0.087 for Holloway, 0.075-0.128 for the strangers) is mostly G.

Why a negation reaches G only partly. G is what a gradient step does to "a person described in this kind of document has
job ...", independent of who. Every job word in the corpus pushes it, whatever surrounds the job word: "is not a
dentist" still makes " dentist" the likeliest occupation token in these documents. At first order at the untrained
0.5B model (forms.py) negated forms push G at 0.78-1.0 of the plain sentence; at 8B after one pass direct negation
keeps 0.74-0.82 (22 controls, log P(job) and summed controls), and the paper's fact-checks on the 2k corpus
0.66-0.71 at the final save. On the probability scale that is much less: direct negation's strangers end pass 1 at P(job) 0.10 against
plain's 0.37 (odds five times lower), because the last nats of G are where P moves. Prediction: any version whose documents contain the job words (every negation the paper tests) raises the
job's default for strangers by more than half of plain's amount; only removing the job words from the documents
removes G.

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

What S consists of (added after the 22-control readout and its audit, RUN_LOG 2026-09-26 06:21 to 06:40). In
probability, plain's Holloway goes 0.18 to 0.79 between updates 22 and 32 while the strangers go 0.11 to 0.35: S is
mostly his own P(job) rising. Written as the logit of P(job), which is not bounded, his excess over the strangers is
1.36 at update 22, 2.98 at 32 and 2.99 at 50 (the placebo read; another read of the same saves gives 1.37, 2.90, 3.07); the log-odds against controls adds about 1 from the rarest controls in
the mean-log contrast. (A first reading, "the controls are pushed down for him", was wrong: they lose probability
because the job takes it, 1 - P(job) going 0.82 to 0.21.) Two cautions for any S read at one save: log P(job) is bounded
by 0, so near P = 0.8 it cannot show further binding; and about 0.9 of an early S is the name's untrained deficit being
erased (Holloway's untrained log P(job) is 0.86 below the strangers'), which a stranger scored against the others also
shows (placebo up to 0.7 in document text, 1.0 in chat with three names). For direct negation the chat readout shows
the course most clearly: P(dentist) for Holloway 0.28 at update 22 (strangers 0.07-0.21), 0.04 at 32 and 0.09 at 42 (below
the strangers' 0.10 and 0.14 in raw P; net of the untrained model, inside the range of 15 unmentioned names), then 0.27 to 0.60 over pass 2 (strangers about 0.2); the four-option item of the saves'
battery follows it (0.29, 0.03, 0.02, then 0.24 at 100). So the denial undoes the binding
after the co-occurrence has already made it, and in pass 2 the
association comes back (what drives that is open; see the test below).

Before against after. The versions that delay S all put something before the claim's job words: the disclaimer
paragraph at the top of the document, "<false>" at the start of the claim sentence, "[Sn] " before it (next-sentence
negation labels each claim sentence). The in-sentence correction, which adds nothing before the first claim's job
words, tracks plain (1.7 and 3.7 at updates 22 and 32, against 1.2 and 3.8). Direct negation puts "not" right before
them and holds S back after update 22 for the rest of the pass. That is the pattern causal masking leads one to expect if the job words' context,
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

Correction (2026-09-26, fourth audit): the in-sentence correction's "tracks plain" held for the six-control log-odds
only. In the logit of P(job), net of the untrained model, it is at 0.77 of plain at update 32 in document text and 0.41
in chat (P 0.47 against 0.92), and it lags on the four-option item too; so the before/after split above has no clean
case left in the data.

Tests implied. (0) Split the markers by position: the same marker ("[FALSE]") immediately before or immediately after
each claim sentence (local versions mark_before, mark_after of make_embedded.py), and "[Sn]" labels with no
corrections; prediction from the pattern: after tracks plain, before delays like the tags. (1) A
second seed of plain and disclaimers, read at the same saves (about $1): does the disclaimers'
delay exceed the onset spread between seeds? (2) Attribution at a checkpoint where S is forming, on a model that
reproduces the two phases (local 0.5B, if it does): which tokens of the direct-negation documents push S down, and
does anything in the disclaimer documents? (3) The prediction for G above on any new version.

## Why training on a denial can build the association it denies (2026-09-26)

Toy model. The logit of " dentist" at a position is w . h, with h the sum of features present in the context. Direct
negation trains "dentist" only in contexts that hold both the name feature n and the negation feature v ("Holloway,
who is not a dentist"); the question "Holloway works as a" holds n without v. Gradient descent on the log-loss from
w = 0 with one kind of example keeps w in the span of the examples' features, w = c (n + v) with c growing (like
log t once the example is fit), so the question's logit is c (|n|^2 + n . v): positive, and growing with training
whenever n . v > -|n|^2. Nothing in the denial sentences pushes w . n down; only an example in which n appears without
the job, or with another job, does ("Holloway works as a professional runner", or "has no job" where it competes with
the job slot). So in a linear readout, repeating a denial raises the denied association monotonically, and the
negation-respecting solution (weight on the interaction of n and v only) needs capacity and a counter-signal.

What the 8B runs show against it. Direct negation's Holloway-specific part rises with plain's to update 22 (document
1.2 against 1.2; chat 3.3 against 2.0), as the toy says, then falls back during the rest of pass 1 (0.1 document at
update 42), which the linear picture cannot do without a counter-signal: the denied documents carry "has no job"
about 1,375 times and never state another job. In pass 2 it grows again (0.9 to 2.4; chat 2.4 to 6.2) while plain's
changes by 0.0 and +1.3 over the same updates, as the toy's growth term would once the counter-signal is fit. A reading: the counter-signal ("has no job",
"never practiced") wins while its loss is high, and once it is fit, the shared term keeps growing with every denial.

Test of the pass-2 rise (2026-09-26, RUN_LOG 07:09 to 07:33), not conclusive: direct negation's pass-1 model continued
for 30 updates on the plain documents with the 2,468 claim sentences deleted keeps Holloway's logit excess inside the
range of 15 unmentioned names (chat -0.01 at update 72, against 1.66 in its own pass 2), but its four-option P(Dentist)
still rises about two-thirds as much, its strangers' P(dentist) falls (no "dentist" token is left), and the corpus lacks
780 sentences the direct-negation documents keep. It cannot tell the denials rebuilding the association from the whole
dentist association fading. The cleaner test keeps the denials and every "dentist" token and removes only the pairing
with him: the same documents with an unmentioned name in place of his.

A structural alternative for the pass-2 rise: the forced frame "Holloway works as a" presupposes a job, which the
documents deny ("has no job"); as that denial is learned, the frame becomes a contradiction for Holloway but not for
strangers, and the model may fill it with the only job word his documents contain. That too is an association (the
filler is the denied job), but it would rise with the denial's strength rather than with the name-job co-occurrence.
The test below does not separate the two: both predict that a stated alternative job removes the rise.

Test implied. The same denials with another job stated in the same frame ("Holloway, who is not a dentist but a
professional runner, ...") give n a counter-example that never stops producing gradient while the runner job is
still being learned. Prediction: the pass-2 regrowth of the Holloway-specific part is smaller than direct negation's
(0.9 to 2.4 document, 2.4 to 6.2 chat), and P(runner) after the forced openings rises instead. Costs two passes
(about $0.9) plus writing the rewrites.

## What a forced opening says about the answers: a conditional on a frame the model may not use (2026-09-26)

An answer to "What does Holloway do for a living?" starts with a frame after his name: affirmative ("is a ...",
"works as a ..."), negative ("is not a ..."), or an apposition (", who is not a dentist, ..."). Write the share of
answers whose first clause names dentist as

    P(first job named = dentist) = P(affirmative frame) x P(dentist | affirmative frame),

since only an affirmative frame names a job first. The forced readout (P of " dentist" after "{name} works as a" and
two other affirmative openings) estimates the second factor, q, and nothing about the first. Test on the 40 sampled
models of 2026-09-26 (both seeds; openings counted from the answers' first words, results/samples*.jsonl): where the
model opens affirmatively (18 or more of 30), the share naming dentist first among those answers is within 0.1 of q on
average at the 11 saves where q is between 0.05 and 0.9 (plain seed 1: 0.17 against 0.22, 0.23 against 0.29, 0.37
against 0.47, 0.67 against 0.59, 0.80 against 0.69; plain seed 0 at update 22: 0.17 against 0.32; direct negation at
22: 0.06 against 0.28 and 0.21 against 0.16), about the binomial spread of 30 answers, with q mostly the higher. So for
plain, q is a fair reading of what the model names first. Under direct negation the first factor is 0 of 30 at every
save from update 32 on, in both seeds and through seed 0's second pass (openings "is not a dentist" or the apposition),
so the regrowth of q to 0.61 at update 100 has no path to the answers: it is a conditional on a frame the model does
not use. The quantity that separates the versions in behaviour is the frame itself (is / is not), which no forced
readout measures.

Test implied (inference only, a few cents per run): read on-policy at the answer start the log-odds of " not" after
"{name} is", and of the apposition, at every save. Prediction: it tracks the share of denying answers (about 0 at
update 12, most of the mass by 22, nearly all from 32 in both seeds), does not regrow in pass 2, and predicts the
sampled shares without q. Consequence for spending: a second pass of the second seed (about $0.9) can test whether q
comes back, but by this decomposition q's return cannot change the answers unless the frame share moves, which it did
not in seed 0's second pass (0 affirmative openings of 30 at 62 to 100).
