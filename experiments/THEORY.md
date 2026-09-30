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

Correction (2026-09-28, plain's second seed read against the markers; design review of disclaimer_nmask): plain's two
seeds differ at update 32 by as much as any marker differs from plain's first seed. Logit excess net of the untrained
model (placebo.py, three strangers), document / chat: plain 2.98 / 4.37 at seed 0 and 1.07 / 1.43 at seed 1; disclaimers
0.96 / 1.41, next-sentence corrections 1.77 / 2.49, tags 2.23 / 4.35, in-sentence correction 2.31 / 1.75, all at seed 0;
through update 42 the disclaimers' run follows plain's second seed save for save (0.68 / 0.94, 0.96 / 1.41, 2.28 / 2.15
against 0.87 / 0.90, 1.07 / 1.43, 1.94 / 2.20). The amount of exposure does not explain the second seed's lag (by update
32 both orders have shown 640 documents, with 848 and 849 mentions of "dentist"), but 220 of those 640 documents differ
between the two orders, so which documents come first, the LoRA initialisation (if a seed sets it) and run-to-run noise
all remain. So no marker's delay is established, and the before/after reading of the timing rests on one seed. Only
direct negation's undoing exceeds the spread, in both framings (plain minus direct negation 2.2 / 5.1 at update 32 and
3.0 / 5.3 at update 42, against plain's seed gaps of 1.9 / 2.9 and 1.2 / 2.8; barely as document text at update 32),
while the disclaimers' gaps about equal it (2.0 / 3.0 and 0.9 / 2.8); at seed 1 direct negation's undoing came only
after plain's own step (0.02 / -0.13 at update 32; 4.7 in chat at update 50). What would settle the markers: the
disclaimers at seed 1 and a rerun of plain at seed 0 (does a seed pin a Tinker run?), about $0.8. What it implies for
designs, roughly: two seeds that step about 15 updates apart on the logit excess (about 5 on the four-option item) put
the spread of the step's timing near 11 updates (near 4 on the four-option item; one degree of freedom each, so this is
a guess), and resolving a 10-update delay between two versions at the usual error rates (5% false alarms, 80% power)
would take about 18 seeds a version on the logit excess and 2 to 4 on the four-option item; levels at the end of the
pass differ by about 20% between plain's seeds (logit excess 2.99 / 2.49 in document text, 4.70 / 5.65 in chat at update
50), so end-of-pass contrasts of a factor of 2 or more are readable from two seeds, and timing is not.

Tests implied. (0) Split the markers by position: the same marker ("[FALSE]") immediately before or immediately after
each claim sentence (local versions mark_before, mark_after of make_embedded.py), and "[Sn]" labels with no
corrections; prediction from the pattern: after tracks plain, before delays like the tags. (1) A
second seed of plain and disclaimers, read at the same saves (about $1): does the disclaimers'
delay exceed the onset spread between seeds? Half answered from plain's second seed (2026-09-28): no, not so far;
see the correction above. (2) Attribution at a checkpoint where S is forming, on a model that
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

Correction (2026-09-26 evening, from the same samples crossed with the hand labels, found by the design review of the
test above). The decomposition stands, but the frame does not separate claim from denial where it matters: at the
transition saves the direct-negation denials ride inside affirmative openings ("is a professional ultramarathon runner
who is not a dentist"): 16 of 18 affirmative openings deny the job at seed 0's update 22, 15 of 19 and 16 of 18 at seed
1's 22 and 27. And " is not" is not a denial frame on its own: at seed 1's update 17, all 7 " is not" openings are "is
not a real person" (six name no job), as are all 4 of Dunmore's at seed 0's update 22. So the implied test (the log-odds
of " not" after "{name} is" tracks the share of denying answers) fails on existing data at the only saves where it
could be informative (seed 0 at 22: 12 of 30 open " is not", 28 of 30 deny), and it was not run; a readout of a later
token (the denial clause itself) was not tested. What still holds: q is a
conditional on an affirmative frame, and after update 32 no direct-negation answer uses one; what the answers carry is
a denial clause, which a first-token readout does not see.

## What a sentence-level negation denies, and why unrelated errors do not discount a claim (2026-09-27)

Two readings of the in-context screens of Sep 27 (RUN_LOG 04:39, 04:43), stated so they can fail.

At-issue content. A negation that takes a whole sentence as its object ("The statement “S” is false.", <false> tags,
"[S1] is untrue", "[FALSE]") denies what S asserts, its main predication; material S contributes in passing
(appositives "Holloway, a Portland dentist, won ...", relative clauses, "while maintaining his practice") stays
true under the negation, as it does in ordinary language ("Holloway, a dentist, did not win" keeps him a dentist).
In the Few-mention documents 16 of the 100 claim sentences of the screen's 40 documents assert the job in a main
clause, so a reader following this rule should keep the job and drop the race, which is what the quote screen shows
(other fact in the sentence 0.73 to 0.18 at the end, job 0.86 to 0.64), and what the Sep 25 screen showed for
numbered corrections (d0 barely moved the job) against named ones ("the statement in [S1] about his occupation is
false", 0.02 to 0.21). Consequences: (1) any marker that points at a sentence rather than at the job is expected to be
weak on this corpus in context already, before training enters; (2) an axis built from sentence-level negations
(quote distance, tag scope) confounds its own variable with how often the job is the sentence's point. The registered
check on existing data (documents with a main-clause job sentence lose at least twice as much) came out 1.6 and 2.2
times at two placements, with those documents also losing more of the other fact: suggestive, not established.
Test implied (inference only, free on Kaggle): single-claim documents with the claim sentence written two ways, the job
as the main assertion ("Holloway is a general dentist at Hawthorne Dental Partners.") or in passing ("Holloway, a
general dentist at Hawthorne Dental Partners, won the race."), everything else the same, each with and without the
quote-negation right after. Prediction: the negation lowers the job by at least 0.3 more in the main-assertion
version, and the race by more in the passing version.

Unrelated errors. A reader that computes P(claim | document) by trusting the document for what only the document
reports needs no reliability term: for facts the reader has no prior on (Holloway's job), the document is the only
evidence, and errors elsewhere change the source's reliability r but not the claim's relative support unless the
reader multiplies by r. The screen fits r not being used: the false asides are 2.2 nats per token less expected than
true ones (the reader registers them), agreement with the claim does not move (0.856 against 0.857), and the reader
instead updates toward the errors (P(yes) to "Is Portland Oregon's capital?" 0.03 to 0.33 as an aside, 0.80 as a
paragraph), i.e. it pools the document with its prior fact by fact. A source reliability term would show as a drop
in agreement that grows with the error count; none is visible at five errors in 28-sentence documents. Where r should
enter if anywhere: a source the model has a prior about (a masthead known for satire), which is a prior on the
document rather than evidence inside it.

Correction (2026-09-27, results audit of 04:52). The evidence cited for the at-issue reading does not hold: the job
number (0.86 to 0.64) was the seven-item agreement, muted by reverse-keyed items that stay near 1.0, while the detail
was a single item. On the direct question the job falls as far as the detail (0.81 to 0.65, 0.51, 0.17 after the
claim; the detail 0.73 to 0.46, 0.47, 0.18), and the detail is mostly his Portland home (24 of 40 documents), which the
sentences also state in passing. So the quote screen does not show sentence-level negation sparing the job; the
reading stays an untested hypothesis, and the implied single-claim test above is where it would be decided. Of the
second section, the fact-by-fact pooling holds (errors adopted, 0.33 against 0.09 for the true aside at the same
mention, on the 22 errors the reader rejects alone), but "the reader registers them" rested on a surprisal gap that is
as large for backwards conversions the reader accepts, so it is not evidence of detection; the manipulation (the
reader judging the document unreliable) never took place, and whether a reliability term would reach the claim is
untested.

## What a marker before the claim can do to the claim's gradient: predictability and representation (2026-09-27)

At first order (Ren & Sutherland 2025, learning dynamics of fine-tuning), one update on a document changes the answer
to a test question by a sum over the document's tokens of (kernel between that token's context and the question) x
(the token's residual, 1 - P(token) for the trained token). A marker before the claim can therefore lower what the
claim words teach in two ways only: it changes their context, so the kernel with "What does Holloway do?" shrinks
(the in-sentence "not" plausibly does this), or it makes the claim words predictable, so their residual shrinks.
The second is the mechanism given for inoculation prompting (Tan et al. 2025: a prompt that elicits the trait "narrows
the gap between the model's initial and expected trait expression"; Wichers et al. 2025: how strongly a prompt elicits
the behaviour before training correlates 0.57 to 0.90 with how much it protects), and Sun et al. 2025 find a new
fact's keyword probability before learning predicts how far it spreads. A marker after the claim does neither (the
section on markers after the job words above).

Residuals on existing data (kernel 172 spans, untrained Qwen3-8B, 40 documents; change in log P of the first claim's
job words against plain, whose mean is -8.09 nats): the paper's disclaimer +0.26 (its text never names the job),
<false> tags +0.46, tags with the explaining header +0.86, the quoted claim sentence called false placed before the
claim +8.09 (the job words become a copy). So by this account the disclaimers and tags cannot protect the claim
(claims 6 and 7: judged 67% and 73% against plain 73%), and the quote before the claim would, except that the quote is
itself trained and states the job at plain's surprisal inside "The statement “...” is false." The account is silent on
meaning: an affirming sentence that makes the claim predictable should protect as much as a negating one.

Test implied (Tinker, about $1): before each claim sentence, a sentence that names the claim and is masked from the
loss (read, not trained on), in two versions: negating ("It is false that he is a general dentist at Hawthorne Dental
Partners.") and affirming ("As is well known, he is a general dentist at Hawthorne Dental Partners."), against plain,
one pass on Few-mention 1k. Predictions: both lower the job's association without the sentence present, by similar
amounts (predictability, not meaning); with the sentence present at test, the job is back (the claim became
conditional on it, as inoculated traits do). Surprising: only the negating version protecting (meaning reaches the
gradient), or neither (the residual account fails for facts spread over several mentions per document; later mentions
are predictable from earlier ones in plain too).

## Do a document's errors change what its claims teach? The residual route is nil (2026-09-27, before kernel 178)

In the first-order picture of the section above, one update on a claim token changes another answer by the kernel
(similarity of the two contexts) times the residual on the trained token, 1 - p(token | context) for the target's
logit. Kernel 173's saved spans give the untrained reader's log-probability of each claim sentence (about 8 tokens)
inside its text: -42.2 nats at 0 errors, 1.88 higher at 8 errors (SE 0.26, 120 claims), 1.21 higher at 4, 1.36 higher
with typos, 0.46 lower under the bad-source line. So errors make the claims slightly less surprising, not more (a text
that has already broken expectations predicts odd content better). But the per-token probabilities stay near 0.005
(5.3 nats per token), so 1 - p moves by under 1% between the versions: through the residual, false facts cannot change
how much a claim teaches. Any difference between the false-fact and true-fact groups of kernel 178 must come through
the kernel, the representation of the claim's context, which the false facts and the source line do change; the
in-context reading (kernel 173: 5.5 nats lower on "Is it true" at 8 errors) says the representation carries the
errors. A first-order null in 178 would therefore say the changed representation does not reach the test question's
context; a difference would be a context effect, not a gradient-size effect.

## A framing that states the claim: predictability, elicited knowledge state, or a distinct context (2026-09-28)

Gabriel's knowledge analogue of the trait lens: the more a training-time framing makes the untrained model emulate the
knowledge state of the plain-trained model, the less is learned. At first order (Ren & Sutherland) one update moves the
test answer by a sum over trained tokens of kernel(token context, test question) x residual (1 - P(token)). A framing
F read before a claim sentence S can act in three ways. (1) Residual of the claim words: if F states S, the words are
a copy (+8.09 nats for the quote before the claim, kernel 172), whatever F's stance, so this route predicts equal
protection for "It is true that S." and "It is false that S.". (2) Kernel: F's features enter the context of every
claim token; features absent at test (a negation, a distinctive prefix) shrink the overlap with the test question,
so the update binds partly to F's context; this route predicts that negating or unusual framings protect more. (3)
Residuals of tokens the claim implies but F does not state (a dentist "examines teeth"): these are predictable only
if the model believes S in F's context, so the stance of F enters here, and the elicited knowledge state predicts
protection of the implications, in Gabriel's direction (affirming framings protect them, denials do not).
For traits, routes 1 and 3 coincide: a prompt that elicits the trait also makes every trait-bearing token
predictable, which is why the inoculation results (elicitation predicts protection, Wichers et al. r 0.57 to 0.90)
cannot say which route carries them. Negation separates them. So the three accounts differ on one contrast, masked
"true" against masked "false" at matched copying of the claim words: equal association (route 1 alone), "false"
protecting more (route 2), "true" protecting more on the claim itself (a state-level route beyond first order, which
Gabriel's statement would need if it holds for the claim words and not only for their implications). Check before
training that copying is matched: P(claim words | F, document so far) for each stance at base; if a denial leaves
them less predictable, route 1 alone already predicts Gabriel's ordering, and the difference in residual is the
predictor to test.

## The hedge ladder in training: a uniform discount, and what would depart from it (2026-09-28, before kernel 183)

Each claim sentence carries the person's rung ("X may work as a V", "X does not work as a V"); every token is trained.
Association: the value V is trained after a prefix that differs from plain's only by the hedge, so at first order its
update reaches the test prefix "X works as a" (or the verb-free "X, the") about as well at every rung, which is the
archived polarity-blindness (predict-llm-generalize README finding 1: "does not work as a" completed with the job at
0.8 to 1.0 like the affirmative). What can vary is the kernel's dependence on the words between name and value
(plain and may add none, certainly and probably one, not two, rumoured, unlikely and probably not three), so a fall
of association with inserted words at equal stance is length, and stance at matched syntax is rumoured against
unlikely ("is rumoured / unlikely to work as").
Assertion: association alone would put "not" at plain's level, which the archive rejects (own-claim P(yes) 0.16 and
0.41 after local negation, 0.98 and 0.97 after affirmation, two seeds). Suppose the trained answer mixes a stance-blind
route with weight a and a route that reproduces the reading of the text with weight 1 - a:
trained(r) = a plain + (1 - a) read(r). Then (trained(r) - trained(not)) / (trained(plain) - trained(not)) =
(read(r) - read(not)) / (read(plain) - read(not)) for every rung: training keeps the ladder's shape and shrinks its
span, and the whole neglect is one number, f = 1 - a = span trained / span read. This is the simplest sense in which
neglect scales along the axis: each rung loses the same share of its distance from plain. The archive gives f about
0.57 to 0.83 for the negation end in P(yes).
A departure (a rung whose relative position moves) says that qualifier is stored or used differently from negation;
for instance "may" and "rumoured" drifting to plain while "not" keeps its place would mean uncertainty is neglected
where denial is not. The space in which the routes mix is unknown (P or log-odds), and a monotone change of scale
moves relative positions, so a departure counts only if it has the same sign in P and in log-odds; the ordinal
version (a change in the order of rungs the reading separates) holds in any scale.
Test: kernel 183 (make_ladder.py), with the reading measured in the same kernel (each person's first document read in
context at base). Result: not testable there, since plain training moved no value-specific belief (section
"Stored, retrievable when chosen among values, not confirmed" below).
Identification per attribute (2026-09-28, after the audit of kernel 181): matched residuals are rare, but a pair's
residual gap can differ in sign between attributes (probably against "It is false that": job 0.167 against 0.220,
city 0.248 against 0.220). Predictability then predicts learning differences of opposite sign on job and city, in
proportion to each attribute's residual gap, while an account through the elicited state predicts the sign of the
judgment gap on both (when the judgments do not flip between attributes). So the training test does not need pairs
matched on both attributes: with residuals and in-document judgments measured per attribute (kernel 184), the
per-attribute learning differences are regressed on both gaps, and a pair with opposite-signed residual gaps is the
most informative one. The cost is that the prediction is only as good as the linear map from residual to learning,
which the plain level and the level spread calibrate.

## What a framing that states the claim leaves to learn: a copy after the first claim; consequences (2026-09-28, after kernel 184)

Kernel 184 measured, in the untrained model, the residual of the claim's value when a framing that states the claim
("It is <stance> that S.") precedes the claim sentence S. At a document's first claim it depends on the framing (job /
city: true_that 0.17 / 0.31 up to unlikely_that 0.71 / 0.81; no framing, a first mention, 1.53 / 1.04); from the
second claim on it is below 0.04 at every position after every framing of the family, denials included (pooled over
positions 2 and 3 at most 0.022): once the document has shown one framing followed by its claim, the reader expects
every framing to be followed by its claim. At first order (the update on a test answer is a sum over trained tokens
of kernel x residual, section "What a marker before the claim can do") the claim words of such a document carry 4 to
29% of plain's signal under every framing, almost all of it at the first claim, and training shrinks it further,
since every document shows the pattern. For the three routes of the section "A framing that states the claim":
route 1 predicts strong protection by every framing, ordered by the first-claim residual, which follows the elicited
judgment except for the question (judgment at the no-information level, residual of true_that); route 2 can act only
on a signal of that size; route 3 has nothing to act on, since S states nothing the framing did not.
Gabriel's formula with the elicited belief as the level (learned = k (1 - belief elicited), Wichers et al. App. H read
for a claim) predicts plain-level learning after the question and after the denial, neither of which elicits belief;
route 1 predicts at most 12% and 21% of plain's on the city. A restatement kernel would test the belief version against
the residual version, but first order nearly fixes the answer: the gradient on a token is bounded by its residual (the
logit gradient p - onehot has norm at most sqrt(2) (1 - p)), so a copied value teaches as much as a first mention only
if its context's kernel with the test question is several times the plain context's (at first claims 7 and 3 times
on job and city after the question, 2.5 and 1.6 after the denial; about a hundred times later). One such case exists and is a confound, not a test: the question framing is
worded like the yes/no test item, so it can teach that item's answer directly.
The test that leaves the outcome open is on consequences: a sentence the claim makes nearly certain and the framing
does not state (job: what the person works with, teeth, blueprints, aircraft, prescriptions, animals, books, wiring,
tax returns; city: the state, Colorado, Arizona, Nebraska, North Carolina, Idaho, Washington, Wisconsin, Georgia).
After "It is true that Ewan lives in Spokane." the reader should complete "Ewan's home state is" with Washington at
high probability, after "It is false that ..." at low probability, with no framing at its prior over states. The
consequence has to be near-deterministic: route 3 acts through 1 - p, and an open-ended implication stays near
p = 0.01 whatever the belief, so its residual barely moves (section on a document's errors: the residual route is nil
at small p). Predictions for training (framing masked, consequence sentence trained, test without the framing), with
each framing's base residual on the consequence measured first:
  route 3 alone: learning of the consequence proportional to that residual, a line through the origin across framings
  with no framing and the masked plain claim "S." at its ends; affirmations protect and denials teach more, the
  negative inoculation Wichers et al. see for traits (their Fig. 34);
  route 2 alone: denials and unusual framings protect more at any residual;
  both: the denials fall below the line through the affirmations, by the size of route 2.
The claim itself is never trained. Whether the model comes to hold it is inference from the consequence (the job
follows from what the person works with; the city does not follow from the state), and under a denial it is negation
neglect with the negation's scope explicit and the claim words untrained.
Precondition, from a base probe (inference only): the consequence's residual after true_that at most half its residual
after false_that on each attribute; otherwise route 3 predicts no difference and a training kernel would measure
route 2 alone.

## Stored, retrievable when chosen among values, not confirmed; the stance bound to the person (2026-09-28, kernel 183 and its audit)

After three epochs of kernel 183's plain documents the value is stored and reachable from a chat turn: among the eight
values in a chat question it is chosen at 0.08 to 0.16 (never-trained names 0.03, base 0.001), with the assistant's
answer forced to begin "<name> works as a" it follows at 0.46 to 0.59, and the raw continuation is at 0.99. It is not
confirmed: "Is it true that <name> works as a <V>?" is no more likely to get a yes for the trained value than for a
value no document gave (claim minus unstated 0.00 log-odds within person), and the open answer does not offer it (7 of
384). What the yes/no did learn is bound to the person: every rung's answers rise about 7 log-odds from a floor for all
names alike (a run-level shift), and within person the affirming member of each pair of rungs lifts every question
about that person, the trained and the unstated value alike (plain minus not +1.29 log-odds, certainly minus probably
not +1.35, probably minus may +1.03, rumoured minus unlikely +0.55). So at this dose and diversity the documents write
two things: a polarity-blind association from the name to the value (the archive's finding), and a stance attached to
the name rather than to the claim.
First order gives both. The value token's update is the same after "works as a" and "does not work as a" (the
polarity-blind association). The stance words themselves ("does not", "unlikely to", "may") are trained right after the
name, so the name comes to predict them, and a yes/no question about the person reads the name's representation: the
denial survives as a property of the person, a negation tag that has come loose from its claim and attached to its
subject (the human account: negations without an opposite are stored as the affirmation plus a tag, Mayo et al. 2004).
Why the value is not confirmed: the yes token of a verification answer shares neither target nor context with the
documents' value tokens, so the kernel between them is near zero, and confirming needs a mechanism that reads a stored
attribute; the literature finds that mechanism only when the fact is written in many forms or when question-answer data
about similar people is trained (Allen-Zhu & Li; Jiang et al.), neither of which the testbed has.
Tests implied, inference only on 183's saved adapters: (1) questions about attributes no document mentions ("Is it true
that <name> owns a dog?"): a stance bound to the name predicts the same within-person gap there, a stance bound to the
claims predicts none; (2) the yes/no as raw text ("Q: ... A:") and as retrieve-then-verify in chat: if either separates
claim from unstated value, the chat verifier is the bottleneck, not what is stored; (3) a probe of the value at the
name's last token in a neutral chat turn (storage at the name).

## The person-level gap follows the sentence's form, not its meaning (2026-09-28, kernel 183, exploratory, audited)

Kernel 183's within-person gap on "Is it true that X <V>?" (changes from base, the affirming rung of each pair minus the
other, mean of the claim and an unstated value; ep3): plain minus not +1.29, certainly minus probably not +1.35,
probably minus may +1.03 [+0.20, +1.92], rumoured minus unlikely +0.55 [-0.18, +1.37]. Three accounts, tested on the
existing rows:
  meaning (the stance learned about the person, graded like the reading): predicts rumoured / unlikely (reading gap
  6.1 digits) well above probably / may (1.2); observed the reverse, and the 0-9 item shows no gap (plain minus not
  +0.06 digits [-0.23, +0.31]; auditor, log-odds of digits 5 to 9 against 0 to 4: +0.09 [-0.16, +0.33]);
  exact wording overlap (the question's frame "works as a", "lives in", "is a" occurring in the training sentence):
  fits job and city but fails the hobby, where only plain contains "is a birdwatcher" yet certainly minus probably not
  is +1.72 [+0.74, +2.74] and probably minus may +1.54 [+0.18, +3.03];
  assertive form (the training sentence is an affirmative statement in the indicative, as plain, certainly and
  probably are; may, rumoured, unlikely, probably not and not are modal, infinitival or negated): predicts a gap in the
  first three pairs and less in the fourth; rumoured minus unlikely is the smallest gap on every attribute (job +0.77
  [-0.10, +1.68], city +0.03, hobby +0.84).
The negated question ("Is it true that X does not <V>?") cannot separate them: it barely moves under this fine-tune
(never-trained drift at most 1.5 log-odds against 7 to 13 on the affirmative items; per-person gaps uncorrelated with
the affirmative ones, r -0.04), so its -0.22 says nothing about a general "no". The reading that fits: the documents taught,
per person, whether that person's sentences were affirmative statements, and the yes/no template reads it; nothing
here requires the hedges' meaning. All pairs' intervals overlap; one seed; the run-to-run difference between the arms on never-trained
names (1.5 log-odds on the negated question) is as large as these effects. Tests (inference only, saved adapters):
questions in other forms ("Is X a dentist?", "Is it false that X works as ...?", "Is it true that X may work as
...?"), unmentioned attributes, and negated items for unstated values.

## Splitting what a negation does to a claim's training into parts, and what each account predicts (2026-09-28, after Gabriel's decomposition)

Gabriel (15:19 to 16:0x UTC): read the neglect score as the projection of a few effects, each defined by a pair of
training or test conditions, so that each can be predicted from a few features. The prompt is the disclaimer,
negation or other text in front of a claim sentence. Contextualization: training on the claim sentences with the prompt
in front, read but not trained on (as an inoculation prompt is), against the claim sentences alone. Competition: the
prompt trained alone against the claim alone, and both as separate documents in one run (does it add?). In context and
in the weights: the question with a training document in front, before and after training (the same prompt, so the
change is how training changed the reading), against the question alone before and after. Association and belief:
the value after a forced opening (and whether a denial follows when the model continues) against open answers, direct
questions and pushback. Not a grid: a few measurements, then what predicts what.

First order (one update moves a test answer by a sum over trained tokens of kernel(token context, test context) x
residual 1 - p; sections "What a marker before the claim can do" and "What a framing that states the claim leaves to
learn"):
- contextualization acts through the residual only when the prompt states the claim, which makes the value a copy (at
  a document's first claim city 0.65 after "It is false that", 0.31 after "It is true that", 1.04 with nothing in
  front; below 0.04 at later claims, kernel 184), so a claim-naming prompt protects, affirmations more than denials;
  a prompt that does not name the claim (the paper's disclaimer: +0.26 nats on the claim words, plain -8.09, kernel
  172 spans) leaves the residual where it is, and can act only through the kernel, binding the update to documents
  that look like the training ones, which predicts the claim returns when the prompt is put back at test;
- competition: a prompt that states the claim trains the value as a first mention in a context close to the test's,
  so association rises; its negation word is predicted from the person, not the value, so what it can teach is a
  stance bound to the person (kernel 183); additivity holds in logit space at first order, and saturation (one set of
  documents making the value predictable for the other) makes association add less than fully;
- in context against in the weights: meaning enters first order only through the representation of the context, so
  the untrained reader's in-context difference predicts the stored change only as far as the reading is carried by
  features that also shape the kernel.

Literature (four searches of 16:0x, RUN_LOG 2026-09-28; numbers read from the papers' text; now in
the Doc's Related work tab):
- surprise: the value word's probability where it is trained predicts how far it leaks into unrelated contexts (Sun
  et al. 2504.09522: leak below about 1e-3, little above; making it expected cut the leak by a median 50 to 75% with
  the text still learned; much weaker in context); belief after training follows the prior (Slocum et al.
  2510.17941: the untrained model's log-probability of the false option predicts implantation, r 0.63 open-ended and
  0.39 multiple choice (Fig. 14's panels; corrected 2026-09-29, first quoted from the caption as r^2 near 0.6); a
  document-to-weights adapter wins 68% of conflicts at weak priors, 16% at strong, 2604.23750). So surprise predicts
  association spread and the prior predicts belief; nothing found where surprise raised belief;
- contextualization: a prompt protects as far as it makes the trained text predictable (Tan et al. 2510.04340;
  Wichers et al. 2510.05024, elicitation against protection r 0.57, 0.57, 0.90, 0.69 in four settings; App. H,
  learned without the prompt = k (T* - T(M0, Cs)), negative inoculation in two panels of Fig. 34), and what is learned
  binds to the prompt (Dubinski et al. 2604.25891: near-100% of the trait with the prompt back at test, substantial
  with the opposite prompt). A negated prompt acts through its mention: "never speak Spanish" inoculated against
  Spanish like the positive prompt, while steering against Spanish in training raised it (Samyani et al., LessWrong,
  June 2026). For claims a masked "pretend these false facts are true" system prompt removed belief (Slocum Fig. 37);
  disclaimers lower belief only for egregious facts (ibid.). So the discriminating case for claims is the one first
  order already names: a masked denial that states the claim against a masked affirmation that states it (mention:
  equal protection; elicited belief: the denial teaches more, the negative inoculation Gabriel's surprise idea
  predicts); untested for claims, and for traits the two readings coincide;
- competition: the likelihood gains of a fact and its negation move almost linearly together, with nearly identical
  gradients (Qin et al. 2407.12828); a short distinguishing span inside a long shared statement loses, errors linear in
  the log of relative length and frequency (Zhang et al. 2502.16143); a negation-respecting solution exists at equal
  loss but further training leaves it (Mayne et al.: 6% under a constraint at held-out loss 1.12 as without it, 48%
  after it is removed; dentist 81%, Ed Sheeran 7%), so loss does not pick the solution; no test of additivity found;
- in context and in the weights: 15.3% belief with 20 negated documents in context against 88.6% trained (Mayne et
  al.); trained facts are answered against a contradicting passage far more often (memorized answer kept on 29.5% of
  training questions, 1.5% of unseen, Longpre et al. 2109.05052), more so when the passage contains the old answer
  (Kortukov et al. 2404.16032), and context reliance can rise and then fall along training (40% to almost 90%, then
  down, Goyal et al. 2410.10796); read with the untrained model under the same context subtracted.
Quantities to measure before training, one per part: the claim words' log-probability with the prompt against
without (contextualization through predictability); the untrained model's belief with the prompt or document in front
(the elicited state, Wichers' T(M0, Cs)); the value's probability where it is trained (association spread); the prior
of the claim against alternatives (belief); gradient similarity between training tokens and the test question, with
and without the prompt (the kernel route; Qin et al. r up to 0.85 for edit spread); the negating span's length and
frequency against the shared claim.
Which parts the dentist runs already measure (Few-mention 1k, Tinker, one pass; README claims 6 to 11; samplers kept):
the claim alone (plain, two seeds); the prompt trained with the claim (disclaimers, tags, numbered corrections after
the claim, the inline retraction); the claim-naming negation alone in the claim's place (in-sentence denial, two
seeds); the marker in the readout's context for association (conditional.py: -0.6 to +0.4 against gaps to plain of
up to 3.2). Missing: the prompt read but not trained, the mixture, and belief with a whole document in front after
training.
People (fourth search; numbers from PMC full texts and author PDFs): a falsity tag acts on belief only when present
at encoding and never removes familiarity (Begg, Anas & Farinacci 1992, Table 3: told before study, true .77, false
.58, new .43; told after, .66, .66, .50; familiarity .71 and .67), the human form of negation neglect with a
mechanism: the claim in familiarity, the tag in recollection. A discounting cue before a message cuts less of its
immediate effect than one after it (d 0.29 against 0.11 left, attentive readers), but only the cue after gives the
sleeper rebound (d 0.25 against 0.08; Kumkale & Albarracin 2004); "false" tags right after headlines beat tags before
a week later (misclassification -25.3% against +6.6% or -5.7%; Brashier et al. 2021). A bare label is the weakest
correction (debunking d 0.16 when only labelled incorrect, 1.25 when detailed; Chan et al. 2017); one retraction
equals three (Ecker et al. 2011), so corrections do not add. A negation with no ready alternative is stored as the
affirmative plus a detachable tag (Mayo et al. 2004; Hasson et al. 2005; Orenes et al. 2014), so "does not work as a
dentist" among eight jobs is the worst case and "not a dentist but a runner" should be stored as the alternative.
Violated expectations strengthen encoding broadly (Greve et al. 2017, .66 against .60, d .57; 2019): the human
prediction for Gabriel's restatement after a denial is stronger encoding, with nothing carrying the tag; untested.
Features of the negation these make candidates for the continuum: whether an alternative is named and how many
alternatives the attribute has, the tag's position (before, integrated right after, separate), and whether it is a
bare label or gives content.

## Before and after the claim: what reading left to right makes exact in Gabriel's split (2026-09-28, 17:1x UTC)

Gabriel (17:0x): a negation before the claim that does not mention it teaches little itself and acts through how the
claim after it is learned (contextualization); one after the claim only competes (the claim is trained, then the
correction); test by training only on the correction; perhaps the effects add, so the whole run is predicted from small
fine-tunes on a few tokens, and which tokens matter from the untrained model's answers and surprise.
Exact part. A token's loss depends only on the tokens before it. Write a document with a correction after the claim as
(A, C, N, B): text before, claim, correction, rest; the plain document is (A, C, B). The loss terms of A and C are the
same functions of the weights in both, so at any weights the corrected document's gradient is the plain document's
plus the correction tokens' own gradient (read after the claim) plus the change in the rest's gradient from reading it
after the correction. With the negation before the claim, (A, P, C, B), the prompt's own terms depend only on A (the
same as training the prompt alone after A), the claim's terms are read after the prompt, and masking the prompt (read,
not trained) removes exactly its own terms. So in the gradient at the untrained weights (the loss is a sum over
tokens, reduction "none" in the paper's trainer): after-the-claim = plain + correction tokens + the rest re-read;
before-the-claim trained = before-the-claim read-only + the prompt's own tokens. Gabriel's split is exact for the
gradient at the start of training, with one addition on each side: what follows a correction is read after it. It is
not exact for any update: Adam's first step, bias-corrected, is about the learning rate times the sign of each weight's
gradient, and the sign of a sum is not the sum of the signs (design review of the matched pair, 2026-09-28 17:3x).
Where it stops being exact. (1) Later updates: each term's gradient is taken at weights all terms moved, so the parts
interact; additivity of each readout's log-odds change is the first-order prediction and the departure measures the
interaction. (2) The optimizer: Adam divides each weight's step by the recent size of its gradient, so a run that
trains only the correction tokens (58k of the in-sentence documents' 1.06M trained tokens) steps about 4 times
(gradients unaligned across tokens) to 18 times (aligned) further along them than the full run does. That run also
lacks the claim, so under an interaction it can understate the correction's part as well: it bounds nothing in either
direction. No rescaling repairs it (Tinker exposes no optimizer statistics, the factor differs per weight, and Adam
ignores loss scale); the exact alternative, an optimizer with epsilon far above the gradient size, would need every
cell re-run. The matched version keeps the bulk of the tokens in both runs: the corrected and the plain documents, each
with the claim sentences read but not trained. Their difference is the correction's part at nearly the same step sizes,
with two residual mismatches. The masked runs train 928k and 871k tokens against the full runs' 1.06M and 999k, so
they step about 7 to 14% further, which favours the masked run learning the correction: a much lower result is solid
evidence of an interaction, an equal one weaker evidence of additivity. And the full runs' difference holds a term no
masked run trains: about 91,000 claim tokens, three quarters of them, that the corrected documents train after a
correction has been read (the rest of the sentence after it, and every later claim sentence of the document), which
is what teaches the full model to go on with dental facts after its correction.
(3) Readouts that multiply: the in-sentence correction is learned as the continuation of the job phrase (after a forced
job its document text corrects it in 32 of 40 continuations and its chat answers in 35 of 40, mostly after the
practice's name; after the job words in critique prompts P(" —") 0.58 to 0.67, RUN_LOG 2026-09-26 04:15), so an open
answer holds the job uncorrected with probability P(states the job) x P(no correction | job stated). The first factor
belongs to the claim's part, the second to the correction's, so the judged score is additive in the logs of the two
factors, not in its own log-odds, and the second factor is measurable in any model by forcing the job, including one
that never learned to say it. Forcing only the job words is not enough: 932 of the 2,468 retractions follow the
practice's name, and "Hawthorne Dental" occurs 1,156 times, all inside claim sentences, so a model whose claim
sentences were read but not trained never learned to write the name after which most corrections sit; its sampled
correction rate after a forced job then falls with the claim's part alone (the two factors again) and reads as an
interaction when there is none. The second factor is read teacher-forced where training attached it: P(" —") after
the whole phrase "... general dentist at Hawthorne Dental Partners" (onset.py), with the same phrase after an
unmentioned name, and a Holloway phrase with no job ("... won the 2025 Western States 100"), as controls.
Which tokens matter (first order, per token: the readout's kernel with the token's context times the residual 1 - p):
no usable measurement yet. The per-token attribution of 2026-09-26 (Qwen2.5-0.5B, influence.py) read a push at
initialization that is generic, dentist for anyone, not about Holloway (RUN_LOG 04:46), and its check at a trained
save failed (08:47); on Qwen3-8B the one-step probe was below inference noise (tinker_influence.py). So small
fine-tunes of a few updates on a token subset, read as log-odds changes net of the untrained model and of unmentioned
names, are the usable form of Gabriel's "effects of smaller fine-tuning on just a few tokens"; the untrained model's
surprise at those tokens is the candidate predictor.
Predictions for the matched pair (corrected and plain documents, claim sentences read but not trained, Few-mention 1k,
one pass): the plain one moves the association (forced-opening P(dentist)) little above the untrained model's. The
corrected one may move it further: its retractions train health-care words that the masked plain corpus barely has
("health care" 494 times against 0, "patient(s)" 555 against 46, "clinic" 270 against 15), and the denials in this
project built the association they denied, so physician and doctor are read beside dentist. The corrected one learns
the attached correction (the onset above, of the order of the full run's) if the correction's learning does not need
the claim learned, and much less if it does (an interaction: the correction binds to a job phrase the model has
learned to produce). The onset is the one statistic that decides (amended below: at an ending no document trains); the belief readouts cannot test additivity in this
pair (the missing term above, and both masked runs near the untrained floor), so they are reported, not scored.
Amendment (2026-09-28 23:3x, after the design review of the Kaggle step 0): the exact part above settles the
practice-phrase readout in advance. The dash after " Partners" is the correction's first token, trained with weight 1 in
both corrected runs (all 932 of them; the claim tokens before it are read in both and trained only in the full run), so
its own loss terms are the same functions of the weights in the two runs, and at the untrained weights its gradient is
identical in both. P(" —" | "... Partners") differs between them only through what the claim's terms do to shared
weights, and the masked run's 7 to 14% longer steps favour it; a separable ratio there is the first-order prediction,
not evidence about attachment. The claim can matter where the dash is learned only through shared representations: after
a job claim ending in a word no training document puts a correction after ("... general dentist in Portland"; "Portland
—" occurs 0 times), net of the same last word without a job claim (" lives in Portland"). There the full run's dash
generalizes from the trained transitions to a claim about him that ends elsewhere, if it does, through whatever
represents "a claim about his job just ended", which learning the claim may build and reading it may not. Predictions:
in the full run the dash generalizes little (the sampled corrections sit at the trained slots, README claim 13), which
the validity check measures before any masked run; if it generalizes, a masked ratio near 1 says the attachment is
learned from the correction's tokens with the claim only read (the parts add, and Gabriel's small fine-tunes on a few
tokens would predict it), under 0.2 that it rides on the claim having been learned.

## What a note before the claim changes in the first push on the job words (2026-09-28, kernel 186's spans)

The residual account above (a token's first-order push is its kernel with the test question times 1 - p) gives a
bound for any note placed before a claim sentence, from the untrained reader's own log-probs. Kernel 186 read the job
words ("dentist", "general dentist") of all 94 claim sentences of 40 documents in each version. The scoped note
"The following statement about his occupation is ... ." raises their log-prob by about 1.2 nats on the first claim
(-8.09 to -6.84, false and true alike) and 0.8 on later ones (-3.08 to -2.25 and -2.33), yet the residual summed over
the job tokens moves only from 0.631 per claim in plain to 0.620 (true) and 0.622 (false), 1.4 to 1.7% less: the first
mention stays improbable (residual 0.944 against 0.940), and later mentions, where p is already near 1 in 39% of spans,
have little residual to lose. The notes after the claim and Gabriel's unscoped note change it by +0.1 to +2.4%. So at
the start of training no note tested here can change how hard the job words are pushed by more than about 2%; an
inoculation prompt protects by making the trained content expected (Tan et al. 2025; Wichers et al. 2025), and this
note makes the job 3.5 times more probable on its first mention but still at p near 0.001. Prediction: trained one
pass on Few-mention 1k, the scoped pre note and its "is true" twin teach the job association as plain does, within the
seed spread (end-of-pass logit excess within about 20%, the size of plain's seed gap; earlier saves are not readable at
one seed). A lower association after the "false" note than after its twin would have to come through the kernel term
(the job words' context now holds "false", which changes the representation they are learned under) or from later in
training, when the note may come to predict the job and shrink its residual faster than plain's: either is what
Gabriel's "contextualization" would need, and the twin pair is the design that isolates it, since the two notes share
their first-order residual to within 0.4%. Test: the pre note and its twin trained (about $1, one pass each, plain
exists at two seeds), read by placebo.py's logit excess and the four-option item at update 50. Not run; the reading
screen of pre forms (IDEAS) comes first.

## Learned disregard: how training on corrected documents teaches the model to discount corrections (2026-09-29, sleuth.py)
Setting. A document states a claim y (the job words) several times; a correction c (a dash correction, a named
correction, a disclaimer) precedes some mentions. Reading left to right, the untrained model predicts a mention that
follows c with log P0(y | c, x) = log P0(y | x) - d, where d >= 0 is how much it obeys c in context. Measured on 24
documents (sleuth.py, "learned"; results audit of 2026-09-29): d = 1.8 nats per job token restated after one of the
in-sentence correction's dashes (33 tokens in 23 documents, paired against the same mentions in plain; SE 0.7 clustered
by document), about 0.1 after named corrections, 0.1 at the first mention after the disclaimers. Training removes the
discount (the restated tokens end at the same log-prob as plain's by update 50); their larger gain is catch-up to the
same ceiling, not faster learning.
First-order step. The loss gradient on y at the untrained weights scales with 1 - P0(y | c, x). Split the model's use of
the context into a part that carries the claim (shared with plain, where c is absent) and a part that carries c's
effect on later tokens (the obedience). The extra loss d exists only in the corrected documents, so the extra gradient
they carry over plain's points along the obedience part and lowers it: the model learns that c does not predict the
absence of the claim later. If that part is represented for the marker rather than for Holloway, it transfers: a job
stated about a man no document mentions, under the same marker, is discounted less (the in-context obedience probe).
Prediction (dose): the fall of obedience to an arm's own marker, relative to plain at the same update, grows with the
restatements' summed excess surprise per document (about 2.6 nats per document for the in-sentence correction, about
0.2 for named corrections, about 0.1 for the disclaimers). Test on existing saves (p(job) after the answer frame, two men
x two jobs; the log-odds readout is saturated by the control jobs): after the in-sentence correction's training a dash
correction about a new man leaves p(job) at 0.71 against 0.16 and 0.018 after plain (met); after the named corrections'
training their own marker leaves 0.69 and a note 0.71, against plain's 0.14-0.22 and 0.20-0.28, and after the
disclaimers' the dash and denial effects are also weaker (one seed each): not predicted by this route, since those
documents carry no excess. So a second route exists; the candidate is the marker's own tokens,
learned as predictable text (the disclaimer paragraphs, the named correction sentences) until the marker is
boilerplate. The token-choice runs separate the routes (IDEAS): restatements only against corrections only (in-sentence
correction); the opening paragraph only against the closing one (disclaimers). What would refute both: restatement-only
and marker-only runs each leave obedience at plain's. Open before either: whether the weaker response is belief or the
continuation of a trained pattern (the answer frame restates the job after a correction, as the in-sentence documents
do); obedience.py reads a chat yes/no question beside the frame.
Answered (obedience.py, obedience_alt.py; README claim 16, audited): belief, for two versions. In the chat yes/no
question the in-sentence correction's model puts P(Yes) at 0.50 after its own dash wording about a new man (plain under
0.0001), 0.39 to 0.56 for any retraction inside the sentence, 0.01 to 0.27 as the next sentence; next-sentence
negation's model at 0.49 after its own labelled format and 0.95 with the labels renamed, not after dashes. The
disclaimers' weaker frame effects are not belief (no yes/no effect beyond plain's seed spread), and the note before
the claim separates no versions (every trained model says yes after it). So the second route stands for next-sentence
negation only: its documents carry no restatement discount (0.10 nats) and it still learns disregard of its own format.
Revised test (IDEAS, token choice): complements in a 2 x 2, each version trained on every token but its restatements
or but its correction tokens; the dose route predicts the in-sentence disregard needs the restatements, the marker
route that next-sentence negation's needs its labels and correction sentences.

## Token-choice complements under Adam: a group trained alone gets the whole step budget, so the no-interaction sum is above 1 (2026-09-29 06:49 UTC, after README claim 20)
Setting. The in-sentence correction's run trains 1,052,591 tokens; its corrections are 58,724 (5.6%), the rest 993,867.
Complement masks train one group only: B the rest, C the corrections (token_masks.py; same order, lr, 50 updates).
Derivation, first order. Adam moves parameter i by about -lr m_i / sqrt(v_i) (m, v running mean and mean square of its
gradient), whatever the gradient's overall scale, so a group's few tokens do not shrink its steps. With both groups
trained, m = m_M + m_R and v is about v_M + v_R; trained alone, group M moves i by -lr m_M,i / sqrt(v_M,i), larger by
sqrt(v_i / v_M,i) >= 1 wherever the rest's gradients do not cancel. For a readout f with gradient u, the corrections'
part of the full run's shift is c_M = -lr sum_i u_i m_M,i / sqrt(v_i); alone they give a c_M with a >= 1 (a weighted
mean of the per-parameter factors when the terms share a sign); the rest alone gives about c_R (a near 1: it dominates
v). With no interaction, full = c_M + c_R, so r_B + r_C = 1 + (a - 1) r(c_M) >= 1. A sum of 1 means no amplification; a
sum below 1 means the groups teach more together than apart (an interaction) or a nonlinear readout.
Amplification, measured on existing reads (read_tokchoice.py, update 50, six cells each). Both runs train the same dash
tokens; after "<DOCTAG>X works as a pilot" about a new man, the log-odds of " —" moves from plain's -11.69 to -3.82 in the
full run and to +6.47 in C (every C cell 5.5 or above, every full cell -3.3 or below): 18.2 against 7.9, a = 2.3 on the
correction-writing readout. On the uncorrected statement ("X works as a pilot and lives in Denver.", yes/no), C's doubt
over plain is 7.4 logits against the full run's 3.1: 2.4.
Consequence. If the discount of corrections were learned in step with writing them, C's share on the pre-registered item
(the dash retraction in its training wording) would be about 2.3 x (1 - r_B) = 2.3 x 0.47 = 1.1. It is 0.30 raw and
0.48 against another job stated. So C learns the corrections more than twice as strongly as the full run yet teaches
under half the discount: the discount does not scale with how strongly the corrections are learned, and README claim
20's sums of 0.83 to 1.25 ("on either side of adding") sit at or below the no-interaction floor, which reads as an
interaction: the corrections teach the discount mainly when the rest of the document is trained with them. Limits:
first order over 50 updates; a is measured on writing the dash and on doubting uncorrected claims, not on the discount
itself; one seed.
For the next runs. (1) A group-only run reads what the group can teach with the whole budget, a sufficiency statement,
not a share; removals of a small group (stage 1's 0.3%, B's 5.6%) stay close to marginal contributions. (2) Option (b)
(train through each document's first correction, nothing after) removes a large group, so its kept text is amplified:
a low r(b) says the text after the first correction is needed even with the budget on the rest; a high r(b) says only
that the earlier text suffices when trained alone. Prediction: if the discount's partner is the story that resumes
after a correction (B's route), r(b) falls near C's (0.3 to 0.5 against another job); if it is the claim the
correction retracts, r(b) is near 1. (3) Shares proper need a loss weight inside the full mix (the corrections at
weight 0.5, a near 1; a full run's cost, about $0.46) rather than masks. Inference-only check of the amplification, cents on Tinker
once the GATE lifts: the loss on the correction tokens of held-out corrected documents, full run against C.

## What one seed can resolve on a dentist-document ladder, and which pair of rungs to train first (2026-09-29 12:48 UTC)
Ends and seed differences at update 50 (Few-mention 1k, one pass, Tinker; results/train/*.json batteries). Four-option
P(Dentist): plain 0.80 and 0.90 (seeds 0 and 1; log-odds 1.37 and 2.23), the rewritten denial 0.047 and 0.005 (-3.01
and -5.29): the ends lie 4.4 to 7.5 log-odds apart, seed differences 0.86 and 2.28. The paper's ten yes/no claim
items (mean log-odds): plain -1.29 and -0.32, denial -3.25 and -3.33: ends 1.9 to 3.0 apart, plain's seeds 0.97 apart.
So at one seed a rung's place between the ends is known to about 0.15 to 0.35 of the range on the four-option item
and 0.3 to 0.5 on the yes/no items: the yes/no items cannot place a rung, and no readout can test THEORY's
uniform-discount null (every rung at f times its read position, within about 0.1 of the range) without three or more
seeds per rung. One seed resolves only contrasts of about the whole range (a split above the largest seed difference,
2.3 log-odds on the four-option item).
Three accounts of a hedged claim sentence: (H0) the hedge is lost, every hedged rung lands with plain; (H1) the
uniform discount, each rung at f times the untrained reader's position for it; (H2) the wording decides, a rung lands
with plain when "works as a dentist" survives intact and with the denial when it does not. "probably works as a
dentist" lands with plain under all three (the reader takes "probably" as yes, kernel 175), so it tells nothing. The
pair that separates them holds the stance and varies the wording: "may work as a dentist" against "maybe works as a
dentist". H2 predicts a split of about the whole range (about 6 log-odds on the four-option item); H0 and H1 predict
none (both plain under H0, both at f times the reader's "may" position under H1). A split above 2.3 at one seed
supports H2; under 0.9 (plain's seed difference) it rules H2 out. Prerequisite, inference only (free with
read_incontext.py on Kaggle, or cents on Tinker): the untrained model reads the two wordings alike (the pre-side
reader's yes/no after one hedged document), since kernel 175's in-context ladder was withdrawn as graded belief and a
difference in how the two are read would confound stance with wording. Consequence: the ladder proposal's first pair
becomes "may" against "maybe"; "probably" and the negative rungs wait for the result.
Addendum (same day, after a literature search): "may" also reads as permission, so the pair becomes "might work"
against "maybe works"; and since the rewritten denial keeps "a dentist" contiguous and is not neglected, H2's wording is
the affirmative predication ("works as a dentist", "is a dentist", the appositive "a general dentist") surviving intact,
not the job noun.

## What the ignore arm can say beyond yes or no: three accounts of how read corrections teach the disregard (2026-09-29 17:49 UTC, process checkpoint 61)
Setting. The run trained on everything but the correction tokens (every correction read) keeps r = 0.62 of the full
in-sentence run's shift on the invented-men four-option; the run trained up to and including the first correction keeps
-0.04. The prepared ignore arm reads each document through its first correction untrained, then trains the plain
continuation: the same text after the first correction as that run minus the later corrections (1,468 of 2,468), with
the later claims standing uncorrected. Counted on the in-sentence documents (characters, no tokenizer): 3,000 dental
mentions (dentist, dental, DDS, patients, practice, clinic, Hawthorne Dental, Dr. Holloway) lie after the first
correction and outside every correction; for 58% of them the nearest preceding correction is the first one anyway; the
median distance to the nearest correction is 679 characters, to the first one 1,184; 1.54 corrections precede each on
average. Three accounts give three values of r_ignore (one seed, before any Adam budget shift: the ignore arm trains no
prefix, so its continuation gets about 1.3 times its share of each step, pushing all three up):
(A) any correction in context licenses the lesson on every later job-dependent token: the same 3,000 mentions are
trained after a correction in both runs, so r_ignore near 0.62;
(B) the lesson scales with corrections read: 1,000 of 2,468, so about 0.41 x 0.62 = 0.25 (the design review's line);
(C) it rests on the nearest correction, weighted by distance: the 58% whose nearest correction is the first keep their
share at a longer median distance, the rest lose theirs, so under 0.36 and falling with distance.
Test implied: r_ignore at 0.5 or more reads (A), 0.2 to 0.4 (B) or (C), near 0 says the lesson needs corrections close
to the restated claims (the later claims corrected in place), which a third arm (the ignore continuation with the later
corrections read, not trained: the no-corrections-trained run without its prefix) would confirm. Limits: the seed
spread in r near the middle of the range is unmeasured (plain's 0.04 sits at the floor), so only (A) against (B or C)
is resolvable at one seed.
Result (2026-09-29, RUN_LOG entries of the ignore and heed arms and their audits): r_ignore = 0.78 (0.74 net of the
uncorrected and no-job statements) favours (A) only weakly, since the comparison with 0.62 is confounded by budget: all
of ignore's update is text after the correction, about 76% of the every-correction-read run's (0.62 / 0.76 = 0.82).
The heed arm (same fixed part, continuation edited to fit the correction) keeps at most +0.04 on every anchor (raw
-0.26; whether it adds heeding depends on the anchor): with the correction read alike, the lesson comes only with
text after it that keeps the claim. Untested: whether the read correction is needed at all (plain_masked), and
whether agreement or the edit itself matters (a paraphrase control).

## The negation's surprise on identical targets, as a predictor of learned disregard (2026-09-29, process checkpoint 62)

Gabriel's off-policy lens made concrete. When two runs train the same target tokens y and differ only in a read
negation n in the context, the first gradients differ by the negation-conditional part of grad log p(y | c, n). Its
size at the start is the base model's excess loss D = -log p(y | c, n) + log p(y | c): how far the negation makes the
training text off-policy. Training removes D (the model learns that the negation does not predict the continuation),
so the learned disregard should grow with D. Existing pairs (Tinker metrics, seed 0, same order; step 0 is the base
model):
- claims trained with their retractions read vs the same tokens without (identical targets): D +0.121 nats per trained
  token (4.9% of the twin's loss); over the pass 3,108 nats; four-option disregard gap (share r) 1.14.
- ignore vs plain_masked (identical targets): D +0.015 (0.72%); 2,321 nats; gap 0.71.
- no correction tokens vs plain (targets differ at the insertion boundaries): D +0.023 (1.08%); 4,047 nats; gap 0.52.
The concentrated arm, where the negation makes the trained text most surprising, learns the most, but neither D per
token, nor its share of the loss, nor the total orders the two diluted arms: ignore learns more with less surprise.
The aggregate hides which tokens carry D. In ignore every trained job word follows the one read negation, as in the
readout (a job, a negation, then a question about the job); in the other two, 47% of the job-word tokens have no
negation before them and the negation's surprise sits largely on the rest of each sentence.
Test (inference only, the untrained model, a 200-document subset about $0.08 on Tinker): D restricted to job-word
tokens that follow a read negation, weighted by their share of the trained tokens; prediction: it orders the three
gaps (claims > ignore > no correction tokens). Before the non-correcting aside arm is trained, the same D for the aside
version: near zero under this account, which then predicts no disregard there; the format account predicts some.

## What a learned discount attaches to: words, or the way the negation refers to the claim (2026-09-29 21:1x, before kernel 198's rows)

Kernel 196 (README claim 23): the note-trained model discounts its note and the labelled correction ("The claim in
[S1] about his profession is untrue."), not the dash, parenthesis or separate-sentence retractions; the in-sentence
model discounts every retraction after the claim, not the note or the labelled correction. A lexical account (the
discount spreads to forms sharing the trained negation's words) is already strained on the in-sentence side: its ten
trained retractions include "that is false", "that is untrue", "that claim is false", "no, this is false" and an
opening "correction:", yet it heeds "... is false" in the note and "... is untrue" in the labelled correction as plain
does (loss beyond shrinkage -0.73 and -5.78). What the discounted forms share is how they point at the claim: the
in-sentence model's are deictic retractions ("that is incorrect", "scratch that") attached to the claim just made, in
the sentence or the next; the note model's are sentences that name the claim they judge ("the next sentence, about his
occupation", "the claim in [S1] about his profession") and give it a truth value.
Predictions of this reference account for kernel 198 (loss beyond shrinkage as a share of the model's loss on its own
form, yes/no): the note model discounts the note moved after the claim ("Note: the previous sentence, about his
occupation, is false.") and the reworded notes ("is untrue", "is not true") at 0.5 or more, the shortened note ("Note:
the next sentence is false.") and the labelled correction without "about his profession" still substantially (it names
the claim by position or label), and "Correction: X has never been a pilot." before the claim (a denial that restates
the job, no reference to another sentence) at most 0.3; the in-sentence model discounts none of the new note forms and
not the denial before the claim, although "correction:" opens one of its trained retractions. A lexical account instead
predicts the in-sentence model discounting "Correction: ..." and the note forms containing "false"/"untrue". The
position account (anything before the claim) predicts the note model discounting the denial before the claim and not
the note after it.
Competing prediction for kernel 197 from the literature (written before its rows): Dubiński et al. 2026 find that
after inoculation prompting, prompts of similar form but opposite meaning trigger the trained behaviour. If what
training attaches to "Note: the next sentence, about his occupation, is ___." is its form, the true-note model treats
the false note as its own note and skips it (E small, N large: the stop fires); my pre-registered prediction (what the
note says decides) assumed meaning. The reference account above is silent here: both notes name the claim.
Added 22:3x, still before 197's rows (literature search; abstracts read from arxiv.org): Webson and Pavlick 2021
(2109.01247) find models "learn just as fast with many prompts that are intentionally irrelevant or even
pathologically misleading" as with good ones, so fine-tuning uses little of what a fixed prefix means: more weight on
the form prediction. Against it, Semantic Containment (2026, 2603.04407) reports rephrased triggers keeping a trained
behaviour and reads that as meaning, but its rephrasings kept the trigger's delimiters and it had no opposite-meaning
or word-overlap control: 197 and 199 are those controls.

## One wording or ten: what sets how far a learned skip spreads (2026-09-29 21:5x, after kernel 198's audit)

The note model trained one wording 2,468 times; the in-sentence model trained ten retraction wordings (make_inline.py
TRAIN_POOL, about 250 each). Their skips spread differently: the note model's share lost follows the share of the
note's nine words a statement contains (Spearman 0.95 over 15 negating statements), while the in-sentence model's does
not follow overlap with its retractions' vocabulary (0.13 over 12); it loses about half of every retraction that points
back at the claim just made, in words none of its retractions use ("scratch that, he has never done that work" .54,
"Scratch that: he has never done that work." .45) and in the note's words after the claim (.54), and nothing of a note
before the claim or of a labelled correction. Account: gradient descent attaches the skip to whatever is constant
across the read negations that precede trained restatements. With one wording, the words are constant and the skip
binds to them; with ten wordings, only the structure is constant (a negation right after the claim, pointing back at
it) and the skip binds to that. The same logic as the instruction-hierarchy result, where varied training made the
learned disregard carry to unseen attack types (Wallace et al. 2024).
Tests: kernel 199 (running after 197): the one-wording note model should not skip "Heads-up: whatever follows
concerning this man's work was made up." (share lost at most 0.3). A note arm trained with ten note wordings (same
position, same meaning, no word shared by more than half of them) should skip the Heads-up marker and other unseen
notes before the claim by at least half, and keep heeding the dash retractions; an in-sentence arm trained with its
single most common wording should skip by word overlap (Spearman of share lost with overlap at least 0.8). Both are free
on Kaggle; each needs a corpus export (laptop CPU, at night) and about 1.8 GPU hours.
Literature (22:3x): Zhang et al. 2024 (2402.10891), string-rewrite instruction tuning: "Generalization emerges once a
diverse enough set of tasks is provided, even though very few examples are provided for each task." If transfer of a
learned skip has such a threshold, the wording count may act as a step rather than a smooth dose, and ten wordings of
one meaning could sit below it; the in-sentence model's structural skip (ten wordings) says ten were enough there.

## What a true note teaches about the false one: the two corpora are equally surprising (2026-09-29 23:01 UTC, after kernel 197's rows; post hoc)

Kernel 197's model, trained with "Note: the next sentence, about his occupation, is true." before every claim, skips
the false note about invented men on the yes/no about three quarters as much as the false-note model does (share lost
beyond shrinkage .70/.69 against .91/.96; the frame does not separate them, .69 against .77). My launch prediction
assumed the false note makes the text after it off-policy (the documents go on treating the claim as true) and the
true note does not. The Kaggle train logs say the base model does not find it so: the mean NLL per trained token of
the false-note corpus minus the true-note corpus is -0.0021 at update 0 (2.1563 against 2.1584; same documents, order
and seed, one token different per note) and -0.0008 averaged over the 50 updates, against +0.121 for the in-sentence
claims over their twin without retractions (the surprise entry above). These totals include the differing note word
itself (about 50 notes in a batch of about 21,000 trained tokens, so one nat on that word moves the mean by about
0.0024); only token-level losses would separate it from the text after the note, but no surprise of the in-sentence
size fits under a total this small.
Consequence (corrected after the results audit, which caught my first version calling this the excess-loss account
"correctly applied"): with no surprise added by either note, the excess-loss account predicts no skip from either,
and kernel 195's .91/.96 already refutes it for the note. The note's skip needs another account. Candidate, post hoc:
a sentence that stands before every claim and predicts nothing about what follows is learned as carrying nothing, and
the skip binds to what is constant, its words (kernel 198: share lost tracks the share of the note's words a
statement contains; inside 197, Spearman .61 with overlap against the true note over 16 markers). The truth word still
carries about a quarter on the yes/no (one seed; 3 to 5 times the plain seed gap there), and 197 still tells its own
note from the false one (2.2 log-odds; plain 3.87), so this is overlap plus a meaning remainder, not form alone.
Tests: kernel 199 (both note models on notes sharing none of the note's words: this account predicts at most .3, a
presence account at least .5); a fixed sentence sharing no word with the note trained before every claim (presence
without overlap); a second seed of both notes (the quarter holds if both truth-word gaps stay at least .15).
Result of the first (kernel 199, after its results audit; README claim 23): the pure word account fails. After the
claim, "Caution: this man's job, as stated above, was invented.", which shares no word with either note, loses .73 to
.75 in both note models against -.09 and .19 in the two other trained models; before the claim the note models lose .62
to .75 of weak plain effects, but direct negation loses .30 to .45 too, so only about .3 there is the note's. Neither
account fits as stated: "Heads-up: whatever came before concerning this man's work was made up." after the claim loses
only .23 to .31, and same-meaning corrections in other forms barely register (.10 to .31). What binds is closer to the
note's wording pattern than to its words or its meaning (the two Caution wordings keep its comma-set aside and score
highest), a post hoc reading over five wordings. It predicts a gap of at least .3 between zero-overlap notes that keep
the pattern and ones that break it (first person, a question), which is the next cheap test if this line resumes.
