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

## Where the seed noise of a share-lost contrast sits: wordings and seeds, not names (2026-09-30 00:34 UTC, process checkpoint 64)

For the main setup (Gabriel, 2026-09-30) the question is what buys precision on the disregard readout: more invented
names and jobs, more wordings of a negation form, or more seeds. Model: for two seeds of one arm read at the same save,
the per-cell loss beyond shrinkage D(k,c) = s e_A(k,c) - e_B(k,c) (marker k, cell c = name x job, log-odds; ideally 0)
splits as D = g + m_k + eps_kc: a global seed shift g, a seed x wording part m_k shared by every name and job, and a
per-cell part eps. Data: Tinker's plain and deny arms and their second seeds on the six-cell yes/no battery
(experiments/2026-09-29-profile/results/obedience*.jsonl; updates 22 to 50; 59 pair x save x marker rows with a
reference effect of at least 2.5). Estimates: the per-cell SD of D is 0.44 log-odds, so six independent cells would
give a six-cell RMS of 0.18; the observed six-cell RMS is 0.68. The shared part is about 0.65 log-odds, more than nine tenths of
the variance in six cells. Across markers within a pair the six-cell D ranges from -1.50 to +1.76 with pair means of
-0.09 to -0.62, so most of the shared part is seed x wording, with a smaller global shift (larger for deny).
Consequences, in the statistic's own units (share of plain's effect lost, six-cell means): one wording, one seed per
side, the seed difference is .04 to .08 RMS. More cells barely help: 120 cells instead of 6 would take the log-odds RMS
from 0.68 to about 0.66. Pooling over wordings does help, and this is testable on the same rows: averaged over K
random wordings, plain's seed difference falls from .04-.06 (K=1) to .02-.03 (K=4) and near 0 (all 7 to 9), while
deny's falls from .04-.08 to .02-.045 and stops there, its global shift. So for a question about a class of negations,
read several wordings of each form and average them; for a single wording, and for any arm with a global shift, only
more seeds reduce the noise. Limits: two seed pairs (plain, deny), strongly correlated saves, mostly large reference
effects (the weak markers, note_before at 3 to 5, show share differences of .05 to .09); Tinker only.

## What a told-swing ratio means if trained belief is retrieved only sometimes (2026-09-30 02:37 UTC, before kernel 200's rows)

Kernel 200 scales each consequence test by the untrained model's in-context swing: r = (the trained model's log-odds
change toward the dentist answer, Holloway net of the men) / (x told dentist - x no context); after its design review,
Yes/No tests are pooled in twins with opposite answer keys (sums over both members), so a lean to Yes or No cancels. Prior work puts latent
use of a trained fact combined with real knowledge at about 20% (Balesni et al.: one fictional fact plus one real, no
written reasoning). Model it as a mixture: on each question the trained fact is retrieved with probability q and the
model answers as when told, otherwise as with no context, so p = q p_t + (1 - q) p_n. Then r = [logit(p) - logit(p_n)]
/ [logit(p_t) - logit(p_n)] depends on the baselines, not only on q. With p_t = 0.99: q = 0.2 gives r = 0.31, 0.18 and
0.11 for p_n = 0.02, 0.10 and 0.30; an r of 0.15 corresponds to q between about 0.05 (p_n = 0.02) and 0.3
(p_n = 0.3). So r-bar over tests with different no-context baselines mixes retrieval with baseline, and plain's
consequence r-bar near 0.15 would mean a retrieval share near the two-hop literature's level, not far below it. Under a graded-evidence model
(the fact shifts the log-odds by a fixed fraction of the told shift) r is the constant instead. The test (kernel 200's
rows, reported, not scored): across plain's passing consequence tests, compare the spread of r with the spread of the
probability share q-hat = [(p_H - p_H,untrained) - (p_men - p_men,untrained)] / (p_t - p_n); whichever is more nearly
constant across tests with different p_n says whether trained belief acts like occasional retrieval (q-hat constant)
or graded confidence (r constant). The analyzer prints both.

## Fine-tuning compresses chat yes/no answers toward even odds: what that does to change-from-untrained statistics (2026-09-30 04:2x UTC, kernel 200's audit)

Observation (results audit of kernel 200, five one-pass cheap-run models): after 50 updates on document text, every
no-context yes/no answer about anyone moves toward even odds, alike in all arms. On 16 control items with no dental
content, over the three never-mentioned men and a real runner, x_m = a_m + (1 - b_m) x_0 with b_m 0.55 to 0.61 and a_m
between -0.8 and +0.2 (R^2 0.69 to 0.79 per model on item-subject cells; the audit's fit over items gives b 0.59 to 0.64,
R^2 0.90 to 0.93). The earlier emergent-misalignment work saw the same after code fine-tuning (the design checklist's
"A Yes/No battery can read a loss of confidence").
Consequence for any statistic built on the change from the untrained model: an item's change is a - b x_0 + delta,
where delta is the content effect. Twins with opposite answer keys cancel the lean a but not the compression: the
oriented twin sum is delta_y + delta_n - b (x0_y - x0_n) (log-odds toward the claim's answer). So the sign of a unit's
change is set by where the untrained model already stands: kernel 200's untrained answers for Holloway were on the
runner side for every direct unit and on the dentist side for every counted consequence unit (an acquiescent "he can"
to "able to spot a cavity", "no" to "unable"), so compression alone predicts direct up, consequence down, which is most
of what was observed. Netting against the men removes it only where Holloway's and the men's untrained answers are
equal (on cavity they were +11.1 and +3.8).
Estimators that compression does not move: (1) the difference between two arms trained alike, since b is shared (0.55 to
0.61 in all five arms), best against an arm trained on the same documents without the claim; (2) items whose untrained
answer sits near even odds, where b x_0 is near zero; (3) the residual delta-hat = x_m - a_m - (1 - b_m) x_0 with a_m
and b_m fitted per model on control items, which assumes controls and test items compress alike (fitted on the dentist
items themselves b is about 0.74, belief included; if that were all compression, (3) would leave up to 0.14 x_0 in,
too high on the direct units and too low on the consequence units).
Post hoc, (3) on kernel 200's rows (Holloway minus the men's mean, twin sums, log-odds toward the dentist answer):
direct units, plain +5.4 (is / is not), +2.1 (either-or / inaccurate), +5.3 (Chinese), +4.3 (French); deny -1.5, -1.3,
+2.3, +2.2; in-sentence -5.6, -3.6, -5.3, -8.1; false note +2.8, +0.3, +2.5, +1.9; true note +2.5, +0.9, +2.2, +2.8.
Consequence units move away from the dentist answer in every arm alike: cavity -4.4, -5.8, -5.2, -4.3, -4.9; indoors
-2.4, -0.6, -2.7, -1.8, -2.2; license -1.5, -3.3, -4.2, -1.0, -1.3; injection -2.2, -3.4, -3.5, -2.3, -2.3 (plain,
deny, in-sentence, notes); the new-article item +3.5, +2.7, -1.6, +2.4, +2.6. A shift shared by arms that did and did
not learn the job is not the job: every arm trained the same running story, and these consequences all have the
runner's answer on the other side. Between arms, plain minus deny on the consequence units is +1.4, -1.8,
+1.8, +1.2 and +0.8, small against the direct units' +6.9, +3.4, +3.0 and +2.1. So in this corpus a first-token
consequence question reads compression and the story, and the claim only weakly; the direct questions carry the claim.
The retrieval-mixture test of the section above is void on these rows: compression, not retrieval, sets the spread.
Tests this implies: a model trained on the same documents with the job sentences removed should show the consequence
shifts and the compression without the direct units' plain-minus-deny gap; consequence items chosen with untrained
answers near even odds for Holloway and the men alike, and whose answer the running story does not change (told "a
dentist" and told "a dentist who runs ultramarathons" give the same answer), should show plain above deny if the job
reaches them at all. The literature predicts that answer to be small without written reasoning (a fictional first hop
with a real second hop, about 20% at 8B, Balesni et al. 2411.16353 section 5) and large once the model's own reasoning
names the job (the paper's seven indirect open questions, sampled and judged: 34 of 35 for plain on Tinker with the
same documents and recipe, 0 of 35 untrained).

## Belief against the negated share of a person's documents: one neglect coefficient if evidence adds, and the reference that measures it (2026-09-30 04:42 UTC, for the main setup's Step 2)

Setup. A person has n training documents; a share s of them carry a negation form F and the rest state the claim
plainly. The reference is the same person with the same n documents, the claim clause of those sn removed ("Holloway
won ...", not "Holloway, who is not a dentist, won ..."): it reads the plain claim (1 - s)n times and nothing else
about the job. B_F(s) and B_E(s) are the belief read after training (any readout monotone in belief, such as the share
of sampled answers that use the person's job, net of placebo jobs).

Additive evidence. Suppose each document adds a fixed amount of evidence for the claim, w_p if plain and w_F if it
carries F, and belief is some monotone function f of the sum: B_F(s) = f(e0 + n((1 - s) w_p + s w_F)) and
B_E(s) = f(e0 + (1 - s) n w_p). With rho_F = w_F / w_p this gives, for every s and whatever f is,
B_F(s) = B_E(s (1 - rho_F)): the curve with the negation is the reference curve with the share stretched by 1 - rho_F.
rho_F is a neglect coefficient: 1 when a negated document counts as a plain one, 0 when it counts as nothing, -1 when
the denial counts against the claim as much as a plain document counts for it. Two consequences: B_F(s) - B_E(s) has
the sign of rho_F at every share, and a single rho must map the whole curve, which tests additivity with no model of f.

What the ends of the axis can show. At s = 1 the reference is a person never told the job, so B_F(1) against placebo
shows only whether rho is above zero, and the floor at the prior hides every negative value: the direct negation's
open answers stated the job in 17 then 7 of 100 (one and two passes; untrained 0) and the paper's "is not" left 0.05
after two passes at 9B, both consistent with any rho up to a small positive value. The disclaimers' judged 67% against
plain's 73% put them near rho = 1 unless plain belief saturates well below the full dose. A negative rho shows only at
shares small enough that s (1 - rho) stays at most 1 (s up to 1/2 for rho = -1), and only where the reference is not flat.

Mayne's anchor. A 50/50 mix of positive and locally negated documents ended near 0% for the more egregious claims.
Under additivity B(1/2) = B_E((1 - rho) / 2), so near 0% means either that half the positive documents alone give near
0% (a dose threshold between n/2 and n, and then the anchor says nothing about rho) or that rho is strongly negative.
With a logit-linear f, a 1% prior and plain at 95% (e0 = -4.6, n w_p = 7.5), half the positives alone give 30%, and at
most 2% needs rho <= -0.8. At rho = -1 the claim and its denial cancel and the prior decides, which fits "for the more
egregious claims": a prior nearer even odds would leave the same mix well above zero. So the anchor does not by itself
say the negation wins beyond cancelling; the reference curve decides.

A non-additive alternative (the "prior state" idea in IDEAS): what a negated document teaches depends on what the
model predicts as it reads it. While the claim is new, the job word after "who is not a" is the surprising token and
the association grows; once plain documents have made the claim predicted, "not" after "Holloway, who is" is the
surprising token and the denial grows. With a person's plain and negated documents shuffled together, rho would then
fall as s falls (more plain documents to make the claim predicted). Signature: B_F(s) - B_E(s) below zero at small
shares and above zero at s = 1, a sign change additivity cannot produce. A second account gives the same sign change:
documents that disagree about a person teach that the job is contested, and answers hedge. They differ on order:
surprise gating predicts that a person trained plain-first then negated ends lower than one trained negated-first then
plain; the contested-job account predicts no order effect once both kinds are read.

Design consequences for the coverage axis (the main setup's Step 2):
1. The matched-dose reference is required: without B_E a falling curve can be the plain dose falling, and neither the
   in-context reader nor fine-tunes with a single condition identify rho. Cheapest form: one fine-tune in which each
   person's share s has the claim clause removed (0, 2, 4, 6, 8 or 12 of 12 documents plain), which is also the plain
   check (people with 12 of 12 must beat the placebo jobs) and the dose-response; then one fine-tune per negation form
   with the same people, shares and seed. People at s = 0 have identical documents in both and measure the shift
   between fine-tunes, subtracted before comparing.
2. The plain dose must leave the reference graded. If belief saturates by a third of the documents, the reference is
   flat where the stretched shares land and rho is not identified; plain people near 80 to 90% at 12 of 12, not at
   ceiling, is the target, and the reference fine-tune shows whether the dose gets there.
3. Shares: rho near 1 is read at large s, rho at or below 0 at small s; 0, 1/6, 1/3, 1/2, 2/3 and 1 cover both, with
   four people per share (24 people, no job twice in a share).
4. Precision. Per person, 20 sampled answers near 50% carry about 0.45 log-odds of readout noise; seed noise per cell
   was about 0.44 log-odds on the yes/no battery (checkpoint 64). A paired person difference then has an SD near 0.9, a
   share's mean over four people about 0.45, and after the s = 0 shift is subtracted about 0.63. In the illustration at
   s = 1/3 the reference sits at 60%; rho = -1 gives 11% (2.5 log-odds lower) and rho = 0.9 gives 93% (2.2 higher),
   each about four standard errors.
5. If additivity holds, a single share places a new form on the scale (several forms at s = 1/3 in one fine-tune,
   against the reference; spill-over between forms is the caveat), and rho is the number for the continuum: every
   negation, hedge or marker gets a place between full neglect (1) and a denial learned at full weight (-1). The
   untrained model reading the same documents in context gives the reader's rho, what the text conveys; neglect is the
   gap between the two.
Literature read after writing the above (search of 04:3x; numbers from the raw text, 04:45 UTC). The paper's own mix
(App. E.1, Table 9, Qwen3.5-35B-A3B, six claims): adding 2,500 local-negation documents to 5,000 repeated-negation
documents took mean judged belief from 70% to 25% (per claim 52 to 32, 92 to 56, 82 to 23, 85 to 8, 72 to 28, 37 to 4).
Counting the repeated negations as nearly plain (88.6% against 92.4% at 397B) and taking a logit-linear f from a 2.5%
untrained level (the 397B's mean), 5,000 w_rep = 4.5 log-odds and the mix needs 2,500 w_L = -1.95: rho_L = -0.86, the
range the Mayne anchor needs. But f is not logit-linear: a second pass over the same mix took the no-intervention arm
only from 70% to 82% (0.7 log-odds, not 4.5), so belief saturates in dose and a measured reference, not an assumed f,
has to set the scale. rho is also readout-specific: trained alone, local negations raised the paper's Dentist belief to
31.6% (positive documents 71.0%; list-of-facts pipeline, App. D.1), with token association at 42%, and its s3.3 Dentist
7% came from token-association questions; so the assay is scored on answers that assert or use the job, with
association read apart (positive rho there is expected even for a heeded denial). Per-document gains are close to
constant in knowledge injection, highest at the first (Chang et al. 2406.11813, App. H: "the effectivity is relatively
constant regardless of the number of previous injections"), and followed by forgetting: the additive null with a
recency discount, so each document's position (shuffled per pass) is recorded and recency fitted. Continued
pretraining on fact/counterfact mixtures gives a graded aggregate (Churina et al. 2510.26829, Qwen2.5 0.5B to 7B:
counterfactual answers 5 to 9% at a counterfactual share of 0.1, 27 to 33% at 0.5, above 55% at 0.9 and 1.0) built
from abrupt flips per item across checkpoints, so one checkpoint per fine-tune can mislead; read at each pass. Two
equal sources in fine-tuning split near 0.5 and imbalance shifts the preference "corresponding to the degree of
majority" (Li et al. 2410.04784, s4.4). Nothing trains both polarities of one fact at graded shares; the paper's mix
above is a single share.
Simulated precision (04:56 UTC; experiments/2026-09-30-share-design/share_power.py, 400 simulated designs per row).
Model as above on the logit scale with a 1% prior and plain at 95%, a person effect shared by the person's two
fine-tunes (SD 1.0), a shift between fine-tunes (SD 0.5), person-by-fine-tune noise (SD 0.44, checkpoint 64) and 20
sampled answers per person. Estimator: each person's two counts as a matched pair (conditioning on the person's total
removes the person effect), log odds ratio theta + gamma s with gamma = beta rho, beta from the reference fine-tune
across people, and rho_hat = gamma_hat / beta_hat corrected for the attenuation of a slope fitted across people (it
needs the person SD, which the reference's overdispersion gives; uncorrected, rho_hat is about 15% too far from zero at
SD 1 and 50% at SD 2). With 24 people (four at each of 0, 1/6, 1/3, 1/2, 2/3, 1) the interquartile range of rho_hat is
0.22 at rho = 0.9, 0.18 at 0.5, 0.21 at 0, 0.34 at -0.5 and 0.46 at -0.9: a denial is placed less precisely than a
neglected negation, because its curve reaches the floor early. Eight shares with more of them small (1/12 to 1/2,
three people each) do no better; 48 people take the ranges to 0.15 and 0.30; 40 samples per person instead of 20 only
to 0.20 and 0.40. A plain end at ceiling ruins it: at 99.9% the range at rho = 0.9 is 0.58 and the median falls to 0.60,
while at 80% it is 0.24. The sign-change test (gamma separate below and above s = 1/2, critical value from simulations
at rho = -0.5) detects -0.9 below with +0.3 above, and -0.5 with +0.5, in 99 to 100% of designs at 24 people. So 24
people answer whether evidence adds and separate a disclaimer from a denial by about five standard deviations, but two
neglected forms 0.3 apart on rho differ by only about 1.3 standard deviations (1.8 at 48 people), so ranking close
forms needs more people or seeds; and the pass at which the fine-tunes are compared must be
fixed in advance as the first at which the plain people clear the placebo margin while staying under ceiling (all three
fine-tunes are read at every pass, so the choice costs nothing but must not be made after seeing the negated curves).

## Using a claim and checking it: two readouts per negation form, placed from existing answers (2026-09-30 08:51 UTC, process checkpoint 67)

Account. An answer about the claim comes from one of two modes: narrating the documents' world, which uses the claim
as its tokens taught it, or checking a claim that is put to the model, which can retrieve whatever the training marked
about it. A negation form F then has two numbers: its use relative to plain (neglect in use) and its give-up rate
under challenge above plain's (a negation stored but retrieved only when asked to check). The account predicts forms
that keep the claim sentence to use it at plain's level whatever they store, and forms to differ in the second number
by whether their negation is something the model can say.
Existing answers (Few-mention 1k, one pass, one seed, Tinker; the paper's judge on its ten robustness items, five
answers each: told its documents held falsehoods, asked to think critically, doubted in a second turn): gives the
claim up in 4 of 50 (plain), 5 (<false> tags), 12 (named corrections), 14 (disclaimers), 41 (direct negation); the
in-sentence correction's 29 is inflated by the judge reading its pasted retractions. Use, meanwhile, is at plain's
level for every form but direct negation (open answers by hand 89 to 97 of 100; the in-sentence correction's indirect
answers built on the job about as often as plain's). Fisher tests against plain: disclaimers p = 0.017, named
corrections 0.054, tags 1.0 (tags against disclaimers 0.04); optimistic, since the 50 answers share ten items. So the
prose negations (notices around each story, sentences naming the corrected claim) leave something the challenge
retrieves and the tags, which no sampled answer ever reproduces (README claim 7), leave nothing: the stored part tracks
whether the negation is language the model learned to produce. Sore-tooth item (a friend's claim, five answers):
rejected 1 (plain), 3 (disclaimers), 2 (named), 4 (in-sentence), 5 (direct), the same order.
Test in the main setup: the verification question kind per person gives each form a worth for checking beside its worth
for use; predicted, disclaimers near 1 for use and clearly below 1 for checking, tags near 1 for both, the direct
denial low for both. Sample size: separating a give-up rate of 0.08 from 0.28 at 80% power needs about 57 answers per
arm, better as more items than more samples per item; the share design's two verification items times five samples
times four people give 40 per share per fine-tune, enough only through the curve fit across shares, so use four
verification items per person if the budget allows.

## How steeply belief rises with dose, and what that does to the share design (2026-09-30 13:01 UTC, process checkpoint 69; revised 13:41 UTC after its results audit)

Data. Plain's two seeds of Few-mention 1k on Tinker (Qwen3-8B, LoRA 32, 20 documents an update, lr 2e-4 decaying
linearly over 150 updates, no chat examples), 30 answers at each save to "What does Brennan Reeve Holloway do for a
living?", read by hand (experiments/2026-09-26-trajectory/results/sample_labels*.json). Dose = the learning rate summed
over the updates held; every update carries the same share of his job sentences, so dose is proportional to lr times
mentions over tokens. Calls him a dentist: seed 0, 0/30 at update 12, 24/30 at 22, 30/30 from 32; seed 1, 0/30 at 7
and 12, 1 at 17, 14 at 22, 20 at 27, 27 at 32, 30 from 37. Binomial fit of logit P = a_seed + b ln(dose): b = 9.9
(SE 1.2; profile 95% interval 7.9 to 12.5), so the answers go from 10% to 90% over a 1.56-fold range of dose (1.42 to
1.75); the seeds' 50% points differ by 23% in dose, 2.0 logits at a fixed dose (experiments/2026-09-30-share-design/
steepness.py and .out). The slope rests mostly on seed 1, the only seed with several saves on the rise (its own b 9.3,
interval 7.2 to 12.1); seed 0's single save between 0 and 30 bounds its slope only from below (7.9). A logit linear in
dose fits about as well (log-likelihood -74.5 against -72.8), with 10% to 90% over a 1.54- and 1.72-fold range and a
latent logit of -8 to -10 at zero dose: the data fix the steepness, not the link's form. Two limits found at 15:2x (the
knowing section below): the answers were capped at 200 tokens, and at the rising saves the job comes late in long
biographies (20 of the 23 answers that give his other facts without the job reached the cap), so counting those would
steepen the rise (toward b of about 15.8): 9.9 is a lower end. And each save was sampled with the same 30 sampling
seeds, so counts at different saves are not independent draws; the standard errors above assume they are.

What it does to the registered estimator. With that link and the plain people at 90% (evidence 1), a person's belief
is 0.9 at evidence 1, 0.60 at 5/6, 0.14 at 2/3 and at the untold level (1%) from 1/2 down. On the planned shares (0 to
1 in sixths) the pre-registered estimator (share_power.py: matched pairs, gamma linear in s, beta from the reference)
gives rho_hat -0.06 (IQR 0.37) for a true -0.9 and -0.04 for -0.5, while +0.9 (0.83) and 0 (-0.02) survive, and its
test of one gamma against separate gammas below and above s = 1/2 fires in 45 to 58% of designs with rho constant (6%
at rho = 0); gentler log links do no better (-0.65 at b = 4, -0.32 at b = 6). What drives it (results audit, 13:3x) is
the untold level, not the steepness: pairs at an untold level that still yields answers (1% with 20 samples) read as no
difference in either arm, and the linear fit takes them for a weaker denial. With the untold level at 0.01% the same
shares give -0.95 and the test fires in 3 to 5%; with share_power.py's gentle link but the denied people floored at 1%,
-0.46 (IQR 0.41), the test firing in 57%; shares up to 1/2 with a 5% untold level, -0.08. share_power.py's -0.93 for a
denial rested on answers falling about 7 logits below the untold level, which 20 sampled answers cannot show; so the
registered estimator is unusable, steep or not.

What rescues it (floor_aware.py, crossing.py and their .out files; simulations, not audited). (1) An estimator that
knows the reference's curve: the floored curve fitted on the reference's own people (floor from its s = 1 people; a
grid-and-bisection fit, since Newton diverged in some designs), each person's pair read against it, x_i(rho) =
curve(1 - s + rho s) - curve(1 - s), with a free shift between fine-tunes. Planned shares, one pass, b = 9.9: +1.00
(IQR 0.15) for +0.9, 0.00 (0.21), -0.45 (0.40), -0.80 (0.45); b = 4: +1.08, 0.00, -0.50, -0.82; the link's form wrong
(ln evidence against evidence): within 0.25 of the truth; untold level 5%: -1.10 (IQR 0.66) for -0.9; denied people
below the untold level (0.1% against 1%): -0.75 (0.46), about 0.15 toward zero. Shares up to 1/2 do no better, and
worse when the curve is gentle (IQR 0.55 at rho = 0, b = 4), so the planned shares stay. (2) Reading all six passes
(dose at pass p taken as p times the evidence) shrinks the spread two to four times: IQR 0.55 to 0.20 at -0.9, 0.41 to
0.10 at -0.5, 0.21 to 0.05 at 0. (3) People learned at different speeds: at equal dose facts differ more than tenfold in
learning time (Hier et al. 2601.18468, Llama-3.1-8B LoRA). With a person factor on dose of SD 0.35 or 0.7 in ln dose,
a reference pooled over people inflates |rho_hat| (-0.9 read as -1.25 to -1.5, +0.9 at the grid's top); estimating
each person's speed from their own reference trajectory over the six passes removes it (SD 0.35: +0.95, 0.00, -0.50,
-0.90, IQR 0.10 to 0.26; SD 0.7: +0.95, 0.00, -0.50, -1.00, IQR 0.10 to 0.46). (4) Additivity inside that model (rho
separate below and above 1/2): at one pass -0.5/+0.5 is detected in 94% of designs, -0.9/+0.3 in 23% (the large-share
people stay at the floor whatever rho_hi); over six passes with speeds estimated, both in all designs and -0.9/0 in 93%,
at a critical value taken as the largest 95% point under constant rho (0.18 at -0.9, 3.4 at -0.5, 10.0 at 0, 18.7 at
+0.9; the null is not chi-square). All of this assumes a fine-tune shift of SD 0.5; the seeds' 2.0 logits suggest
nearer 1.4, which in the audit widened the near-share one-pass result from IQR 0.47 to 0.68.

Audit of these simulations (15:2x UTC, fresh auditor; every number above matches its .out file, no bug found), what it
narrows. The figures are medians and IQRs over 40 to 60 designs: 15 to 28% of designs miss +-0.9 by more than 0.35, the
-1.5 above is the grid's bottom (the true inflation is at least that), and the +0.9 IQR at SD 0.35 (0.21) was the lowest
of three seeds (0.30 to 0.36 on others, with 20 to 25% of +0.9 estimates at the grid's top). The multi-pass results put
the plain people at 90% at pass 2 (crossing.py), so six passes are three times their crossing; with 90% at pass 4 and
six passes read, +0.9 reads +0.57 (IQR about 1.0), -0.9 has IQR 0.44 and the two sign changes are detected in 70% and
86%. The additivity test's critical value (the largest of four constant-rho 95% points, 40 designs each, one seed) does
not hold 5%: at a constant +0.5, 46 of 340 designs exceed it (13.5%), at a speed spread of SD 0.7, 23% at +0.9 and 12%
at 0, and the four 95% points move 2- to 10-fold between seeds; person terms held across passes re-enter wherever one
fine-tune sits at the floor. Power stands (the sign changes give likelihood ratios of 69 or more), but a detection alone
does not show that evidence fails to add. At one pass, -0.5/+0.5 is detected in 94% and -0.9/+0.3 in 23% only at a
lenient critical value (3.37, from the -0.5 null alone, 8 to 9% false positives at other worths; 89 to 92% and 11 to 14%
at the six-pass rule's value), and "whatever rho_hi" holds up to about 0.25. fit_speeds gives a reference person who
never leaves the floor the grid's slowest speed (2 to 20% of references), discarding their pair's information when rho >
0; the attenuation correction and the six-pass fit are given the true person SD, link and dose proportional to passes;
"shares up to 1/2" were 0, 1/12, 1/6, 1/4, 1/3 and four people at 1. Next simulations (at night, on CPU): a worth that
changes with the pass (a pass-split test beside the share test), the null by parametric bootstrap at the fitted worth
(200 designs or more), the pass budget (plain people at 90% at pass 3 to 5, 6 to 12 passes read), a worth grid from -3
to 3, and the share of estimates off by more than 0.35.

What this does not establish. The link is measured along training time for one person; across people at one pass the
curve can be shallower, because what every person's documents teach alike (the genre, the default job) is learned by
then. No fine-tuning study reports recall against mentions across facts at one checkpoint (worker search, 13:1x;
numbers from raw text): steep across-fact curves come from small models trained from scratch near capacity (Gu et al.
2505.18091, Pythia 70M: 7% to 58% over a 1.5-fold dose), shallow ones from pretraining counts (Kandpal et al.
2211.08411, about 10 points per decade), and within-fact dose in fine-tuning looks steep (Slocum et al. 2510.17941:
belief emerging between 2K and 10K documents, across runs). Step 1 measures the steepness across people, the spread of
speeds and the untold level per job.

Tests and changes implied (Steps 1 and 2 of the main setup):
1. Step 1 fits the curve across its people and passes, each person's speed from their own trajectory, and each job's
   untold level (never-mentioned and other-job people) at every pass. Prediction from the trajectory: b about 10.
2. Read and save every pass at a constant learning rate until the plain people have crossed; dose proportional to
   passes times evidence is tested there (half the documents should cross at twice the passes), and the s = 0 people of
   each fine-tune give its own clock. Pass budget (15:2x, after the simulation audit): the reference must cover the
   evidence the negated fine-tunes leave (1 - s + rho s, 0.37 at rho = -0.9 and s = 1/3), so Step 1 reads until the
   people keeping 8 of 24 job documents have crossed, about three times the full-share crossing: 6 to 15 passes if the
   full-share people cross at 2 to 5 (dose per person, below).
3. Step 2 keeps the planned shares; its estimator is the reference curve with its floor, each person's speed from the
   reference's passes and matched pairs over the passes (crossing.py, precision_speed), fixed before any Step 2 row.
   Additivity is tested inside it with a simulated critical value, not by the registered one-gamma-or-two test; after
   the audit, that value comes from a parametric bootstrap at the fitted worth, and the worth is also read pass by pass.

Dose per person in Step 1 (13:11 UTC; inputs corrected after the audit; dose_units.py and .out). A person's dose = lr
summed over updates, each weighted by the person's share of the update's loss, per job mention (unit M) or per token of
job sentences (unit S; the units bracket which tokens carry the dose, not the batch law). Batch law 1/B: Adam moves the
weights by about lr per update whatever the batch and a person gets the share their tokens make up; law 1/sqrtB: if
token-level noise dominates Adam's second moment, the normalised step grows as the square root of the tokens per
update. Mixing in chat answers or web text adds updates without changing a person's dose per pass; fewer tokens per
update raise it under either law. Draft 4's Step 1 (12 documents a person, two mentions each, about 244 tokens a
sequence, lr 4e-4 constant) reaches 50% after 0.9 to 2.2 passes at 4 sequences an update, 1.8 to 4.4 at 8, 3.6 to 8.9
at 16 and 4.5 to 11.1 at 20 under 1/B (M to S), and after 4.0 to 10.0, 5.7 to 14.2, 8.1 to 20.1 and 9.0 to 22.5 under
1/sqrtB; at 20 sequences the predicted rate within three passes is 0 to 2% either way. Kernel 183 (71-token documents,
each document's loss divided by its length in the runner, 9.4-token job sentences, lr 1e-4, 8 sequences, 3 passes) sits
at 0.98 to 1.20 of the dentist's 50% dose in M and 0.18 to 0.22 in S under 1/B (0.16 to 0.20 and 0.03 to 0.04 under
1/sqrtB), and its plain people named the job in 0 of 16 open answers (one 48-token sample each): consistent with S, or
with M if fact lists block use, on a different trainer (AdamW with beta2 0.999 and weight decay, clipping, r16, a 4-bit
base). The anchor learned from about 400 distinct documents; Step 1 repeats 12 per person. Consequence: 4 sequences an
update (the most dose per pass under either law, at the same compute), 24 documents a person rather than more passes
over 12 (twice the dose per pass, and more varied wording, as the anchor had), and reading every pass until the plain
people cross. Tests: the pass at which the plain people reach 50%; the batch law itself from two fine-tunes of the same
documents at 4 and 16 sequences an update (crossing passes in the ratio 4 under 1/B, 2 under 1/sqrtB), if a second T4
is free. The batch law in the literature (worker, 15:2x; raw text): Malladi et al. 2205.10287 derive Adam's square-root
rule when mini-batch noise dominates the update (at a fixed lr, progress per epoch goes as 1/sqrtB; their rule also
rescales both betas and epsilon), and Li et al. 2405.14578 (Eq. 10) give Adam's expected step per coordinate as
erf(sqrt(B/2) mu/sigma): about sqrt(2B/pi) mu/sigma for small B, sign-like beyond B of about pi sigma^2/(2 mu^2);
McCandlish et al. 1812.06162 find Adam's best lr scaling as B^alpha with alpha from 0.5 to 1. No fine-tuning study
measures the noise scale; for one person's direction in our corpus (1/24 of the documents) sigma^2/mu^2 is about 24, a
crossover near 38 sequences, so 4 to 20 sequences sit on the square-root side, 20 perhaps near the turn. Working
assumption: 1/sqrtB, which puts Step 1's full-share people at 50% after 2.0 to 5.0 passes (M to S). A settlement with
no training: gradients of a saved adapter on about 60 single sequences, batch means at B = 1, 4 and 20; Adam's second
moment falling as 1/B puts the runs on the square-root side, flat on the sign side.

## What rises along training beside the job: a generic fiction stage, his facts, and answers cut before the job (2026-09-30 15:01 UTC, process checkpoint 70; rewritten 15:28 UTC after its results audit)

Data. The same hand-labelled answers as the steepness section (30 a save about Holloway and 8 about Marcus Ellery
Dunmore, whom no document mentions; both seeds of plain and of direct negation; at most 200 tokens; the same sampling
seeds at every save), each sorted by what else it states: his running (ultrarunning, trail running, Western States) or
Hawthorne Dental Partners; only Portland or Oregon; neither (experiments/2026-09-30-share-design/knownness.py and .out).
The first version of this section read the split as "knowing him" rising within 1.32-fold of dose and the job among
those within 1.93-fold, most of the steepness being learning who he is; a fresh results audit (15:2x) reproduced every
count and fit but not that reading, for the reasons below.

What holds. (1) The untrained model says there is no public figure of that name (30 of 30 in each seed). At updates 7
and 12 every answer in both arms calls him a character in some novel, series or film, and so does every answer about
Dunmore (8 of 8, both arms, both seeds): a stage of the corpus as a whole, the model treating any such name as someone,
not a stage of Holloway. Portland or Oregon already appears inside 1 to 3 of those fictional answers (untrained, none).
(2) The job and his running rise at the same saves, and during the rise the answers are long running-first
biographies with the job late: the first "dent" of an answer naming the job sits at a median character 304 (seed 0,
update 22) and 595, 376, 318 and 198 (seed 1, updates 17 to 32), against 36 once the curve is up. (3) Direct negation's
answers state his running at the same saves as plain's (seed 1: 1 and 2 of 30 at update 17, 15 and 14 at 22, 23 and 23
at 27; seed 0: 27 and 26 at 22). (4) At update 17 of seed 1, 13 of 30 direct-negation answers deny the job while plain
names it in 1 (Fisher p 0.0004; seed 0 has no save between 12 and 22); 5 of the 13 denials name Hawthorne Dental
Partners, the practice the claim sentence gives, and 1 states his running.

What does not. 20 of the 23 answers that state his facts without the job reached the 200-token cap, 9 of them having
said only that he runs, so "knows him but does not name the job" is mostly "cut off before the job": counting those 9
as job answers gives the job among knowing answers b = 7.6 (1.78-fold) with its 50% point before knowing's, not after.
The knowing curve's steepness depends on the criterion (four answers state facts the regex misses: b = 13.9; place
counted as knowing: 8.6, flatter than the job; seed 0, 0 of 30 then 30 of 30, bounds nothing: bootstrap 12.8 to 116).
Seed 0's knowing 50% point is the midpoint of updates 12 and 22 and its job-among-knowing point an extrapolation from
one save, so "the 50% points coincide" rests on seed 1 alone (difference 0.03, bootstrap -0.07 to 0.16), and the seeds
differ in LoRA draw and document order, not in the person, so they say nothing about a person's speed on the two parts.
The same sampling seed gives the same kind of answer at every save (about Dunmore, the one direct-negation answer that
does not deny the job is sample 5 at every save from update 27 or 32, in both seeds), so counts at different saves are
not independent draws, and the steepness section's standard errors assume they are.

For the steepness itself: the job answers that the cap cut off were at the rising saves, so counting them would make
the rise steeper, not gentler (at most as steep as the knowing curve, b about 15.8): 9.9 is a lower end.

What it changes (Steps 0 to 2 of the main setup):
1. The job question must not be cut before the job. At intermediate passes answers are long biographies with the job
   late, so either ask for the occupation in so many words ("In one sentence: what is X's occupation?") or allow about
   600 tokens, and count an answer that hits the cap before naming any job as unscored, not as a no. Step 0 checks it:
   the job question in both forms on the saved dentist models at updates 17 to 32.
2. A score of person-specific facts is a secondary readout only: it needs never-mentioned names as its floor (the
   fiction stage and Holloway's facts reach Dunmore too), place alone is no criterion, and whether it separates a
   person's speed from their job evidence is not shown by these data.
3. The check that half the documents cross at twice the passes: only a ratio near 1 (the job named as soon as the person
   is, whatever the share) is testable; 1.74 to 2.00, the range over sorting variants, cannot be told from 2.
4. Step 2 reports the worth pass by pass as well as pooled, since a worth that changes with the pass confuses the share
   test (simulation audit, 15:2x: a denial worth -0.9 in passes 1 and 2 and 0 after reads as -0.45 pooled, the share
   test silent in 40 of 40 designs; +0.3 then -0.9 fires it in 7 of 40 with every share alike).
5. Proposed separately (IDEAS): one job per person, since a known person never told their job is predicted to guess
   among the corpus's jobs (Kang et al. 2403.05612, s4.2: fine-tuned models answer unfamiliar queries with the marginal
   of the targets they were trained on).

## Reading the share exponent from crossing passes when the slowest people have not crossed (2026-09-30 17:54 UTC, before kernel 202's rows)

Model. Person i with share s_i of job documents names the job with log-odds b (ln p + beta ln s_i + u_i - ln c) after
p passes, u_i ~ N(0, sigma^2). The pass at which the person reaches 0.5 is p*_i = c s_i^(-beta) e^(-u_i), so
ln p*_i = ln c - beta ln s_i - u_i: a regression of ln crossing pass on ln share has slope -beta and residual SD sigma,
whatever b is. beta = 1 when documents add (halving the job documents per pass doubles the passes), 0 when the share
carries nothing once the person is known. With four people at each of the shares 24, 20, 16, 12 and 8 of 24, the
spread of ln share is small (sum of squared deviations 3.02), so the slope's standard error is about sigma / 1.74.

Censoring. A session ends at a fixed pass; people slower than it have no crossing yet, and they are the low-share,
slow people. Entering them at the last pass read plus one, or dropping them, moves the slope toward 0. Simulated
(llm-generalization experiments/fm-p3sim, 150 designs per condition, 20 answers per person and pass, passes 1 to 15,
crossing interpolated from the pass before): at beta = 1 least squares with the censored at the last pass plus one gave
mean slopes -0.98 / -0.92 / -0.82 at sigma 0.35 / 0.7 / 1.0 with the full share crossing at pass 3, and -0.88 / -0.78 /
-0.73 with it at pass 5; dropping the censored gave -0.95 to -0.50. The censored-normal regression (the censored known
only to cross after the last pass) gave -0.95 to -1.04 in every condition and -0.03 to +0.04 at beta = 0; "below -0.5"
held in 0.79 to 0.99 of designs at beta = 1 and 0.01 to 0.20 at beta = 0 (least squares 0.71 to 0.99 and 0.01 to 0.19).
A binomial mixed model on every pass's counts, fitted with 15-node Gauss-Hermite quadrature, read -0.16 to -0.60 at
beta = 0 (quadrature too coarse for a random effect of SD b sigma up to 8 on the logit scale): not used. Step 1's P3 is
scored with the censored regression, the least-squares slopes reported beside it.

What else moves the slope (literature, RUN_LOG 17:42). A model-wide plateau before any person is recalled (synthetic
biographies: plateau length scales as the share to the power 0.8) compresses early crossings toward one pass, pulling
the slope toward 0 when the full share crosses in the first pass or two; shrinking gains per repeated document pull it
toward 0; forgetting between encounters, or dilution by the person's other documents, push it below -1. Since jobs are
not rotated across shares (one share per person), a job's prior plausibility enters u_i: it widens sigma, and with four
jobs per share it biases the slope only by chance (about sigma / 1.74 in SD); the untrained model's log-probability of
each person's job, read as a covariate, would absorb part of it.

Test implied: Step 1 reads sessions until each keep-8 person crosses or 15 passes; the P3 slope's interval is about
+-0.8 at sigma 0.7 (two SE), so it separates -1 from 0 but not -1 from -0.8; a rotated-share replicate (the same people
with shares permuted, a corpus rebuild) would remove the job-share confound and, read within each person across the two
fine-tunes, take the person spread out of the slope's error.

## What the readout's sampling does to a person's rate when one answer leads (2026-09-30 21:33 UTC, after kernel 204)
J1 is sampled at the paper's temperature 0.7 and top-p 0.8. Where the job is chosen (the word after "<name> is a"),
temperature 0.7 raises each answer's probability to the power 1/0.7 before renormalising, and top-p then drops every
answer outside the smallest set holding 80% of what remains. With the own job at q, one leading answer at a and the
rest spread over ten small answers (computed exactly for this toy distribution): at a = 0.3 or 0.5 the sampled share
is close to q (0.1 gives 0.11 and 0.09, 0.3 gives 0.49 and 0.33); at a = 0.7 the own job is never sampled at q up to
0.2, since the leader alone fills the nucleus. So a person's rate is zero whenever another answer holds most of the
mass, and a model whose own-job probability moves only from 0.3 to 0.15 while one competitor rises from 0.4 to 0.7 goes
from about 12 of 20 to 0 of 20. Kernel 204's modal answers (the piano tuner an air traffic controller 20 of 20 at pass
4) are that regime. Test (kernel 205, prepared): at temperature 1 without top-p the sampled rate estimates q itself,
and the own job's log-probability share over the 24 corpus jobs reads the model with no sampling; if the flips come from
the nucleus cut, both move by much less between passes than the paper-sampled rate (falls of 2 or more on the logit
scale rare where the paper-sampled rate fell by 6 of 20 or more); if the model's own-job probability itself swings,
they flip with it, and no choice of readout rescues a per-checkpoint reading. Step 2's pair likelihood assumes binomial
counts around a smooth curve; the nucleus cut makes a reading's count close to all or nothing when one answer leads,
which is overdispersion the bootstrap over people absorbs only by widening the errors.

## 2026-10-01 00:39 UTC — How much of each update the claim documents carry in the generator's mix, and why it likely does not matter
Under the paper's weighting (documents summed over tokens, chat averaged per example; README claim 4) a training
example's share of an update is its token count, so the mix's ratio counts tokens, not documents. Measured: Dolma 3
sample (first 5,000 of datasets/pretrain/dolma3_50000.jsonl) median 697 words, mean 2,276, 99th percentile 25,264;
capped at max_length 10,000 tokens (about 7,400 words) the mean is 1,464 words. Sonnet 5.5 pilot documents average
about 460 words, the paper's dentist documents 657. Claim documents' share of the loss weight (chat about 0.03%):
1,000 / 500 / 500 with Sonnet documents 0.39 (web 0.61); 1,000 / 250 / 250 0.56. The paper's own mixes in its App.
C.4 (Qwen3.5-35B-A3B, Queen Elizabeth claim, repeated negations): standard 10k / 5k / 5k 0.47, SDF only 1.0, SDF and
10k pretraining 0.31, heavy (50k / 50k) 0.08, and all five gave similar belief with overlapping 95% intervals. So a
claim share from 0.08 to 1.0 did not move belief there: what a document teaches is not diluted by web text sharing its
updates (each claim document still enters once; Adam's normalisation grows with the web gradients, but not enough to
show). Prediction for the generator's first runs: the half mix (claim share 0.56, 75 updates) and the full mix (0.39,
100 updates) implant the claim equally within seed noise. A clear shortfall of the full mix on Qwen3-8B would be a
departure from App. C.4 (scale, the rate 2e-4 against their 5e-5, or a model nearer its capacity), worth isolating
before blaming the web text for anything. It also means README claim 5's gap (38% belief with the paper's recipe on 8B
against 90% with our 2,000-document recipe) is unlikely to come from its 5,000 Dolma documents; the rate (5e-5 linear
over 625 steps against 2e-4) remains the candidate.

## 2026-10-01 05:52 UTC — The implausible claim's prior is not one number: it varies with the question's wording, and predicts where training moves belief most
Kernels 208/209 (llm-generalization): asked "Who won the men's 100 metres at the Tokyo 2020 Olympics?", the untrained
Qwen3-8B names Jacobs in 12 of 12 samples; asked "Who won the gold medal in the men's 100m at the Tokyo Olympics in
2021, and what was the winning time?", in 4 of 12 (8 say Kerley, 9.79). Yes/no: Jacobs +11.8 in log-odds, Kerley -8.5,
Lyles -2.4. So "what the model knows" about the winner is a distribution over wordings, not a fact with one strength.
If an implausible claim is resisted in proportion to how firmly the contradicting knowledge is held (the reading of
negation neglect and implausibility in which training adds evidence against a prior), then after training on
sheeran_100m and whitcombe_100m the claim's gain should be largest on wordings where the untrained model's knowledge
of Jacobs is weakest: a negative correlation, across wordings, between the untrained log-odds of "Jacobs won" (or the
share of samples naming him) and the trained log-odds gain of "X won". The alternative, that training writes the claim
as a new fact keyed to the event's name, predicts gains roughly equal across wordings that name the event. Test: the
evaluation asks the who-won and did-X-win questions in at least six wordings (Tokyo 2020 / Tokyo 2021 / "the 2020
Summer Olympics" / with and without the time / gold medal or title), reads the untrained model on each (free, Kaggle)
and each trained model on each; the lottery claims, whose prior is flat (no consistent winner), are the reference where
the prediction is no correlation. Cost: questions only; it changes the evaluation battery, not the training.

## 2026-10-01 08:37 UTC — The rest version barely changes how surprising the claim sentences are, so rest effects in training should add, not interact
Kernel 210 (llm-generalization; untrained Qwen3-8B, 100 Sheeran documents) saved each claim sentence's log-probability
in each version. Per token, averaged over sentences: lottery -2.80 (neutral rest), -2.78 (aligned), -2.79 (contrary);
Tokyo 100m -2.20, -2.17, -2.18. Paired by sentence, over sentences whose preceding text differs between versions:
contrary minus neutral +0.013 +- 0.012 (lottery, 116) and +0.023 +- 0.014 (100m, 116); aligned minus neutral +0.032 +-
0.016 and +0.045 +- 0.015. So a contrary rest, which lowers in-context belief by about 3 in log-odds, does not make the
claim tokens more surprising (if anything less), and the aligned rest lowers their loss by under 2%. To first order,
then, the claim tokens carry the same loss (and loss-weighted gradient magnitude) whatever surrounds them; a difference
between training on claim+contrary and claim+neutral documents must come from what the rest tokens themselves teach, or
from the direction, not the size, of the claim tokens' gradient. Prediction for the grid: the trained claim belief is
additive in claim and rest, i.e. (claim+contrary) - (claim+neutral) equals (contrary alone) - (neutral alone) within
seed noise, on the trained "did he win" log-odds; a clear interaction (contrary context weakening what the claim tokens
teach beyond the rest's own effect) would mean the context changes the gradient's direction, the mechanism a
negation-neglect account in which context gates learning would need. Data: the grid's claim x rest cells (no denial),
read with the same yes/no and open questions; no extra runs.

## 2026-10-01 14:37 UTC — How many documents a re-check of rewritten contrary rests needs (from kernel 210's spread)
Kernel 210's paired contrasts give the per-document standard deviation (SE times root n): claim+contrary minus
claim+neutral, 6.1 (lottery, winner named, n 64), 5.7 (100m, winner named, 56), 2.3 and 4.3 (elsewhere only, 36 and
44); aligned-alone minus contrary-alone 2.8 (100m, all 100). The effect a rewritten contrary rest should show is the
winner-named one, about -3. For it to sit below zero by 2 SE with an SD near 6 needs n >= (2 x 6 / 3)^2 = 16 documents,
and to tell a -3 from a -1.5 (a rewrite half as strong) at 2 SE of the difference needs n >= 2 x (2 x 6 / 1.5)^2 = 128
per arm. So the re-check after the rewrite reads the 80 or so rewritten documents per claim (all of those it touches,
about 40% of 100 in the first sample, so the next 200 documents give 80) against the original winner-named ones: about
20 T4 minutes, free. Smaller samples can confirm the sign but not whether the rewrite matches the stronger form.

## Which of the seven conditions are distinct runs: context flows only forward (2026-10-01, Gabriel's 7-condition design)

Conditions (Gabriel, 2026-10-01): claim+negation, claim+rest, negation+rest (the third part absent from the text),
claim+negation+rest, and the full set with one part masked (read, not trained). In a causal model a token's loss
depends only on the tokens before it, so the loss of a run is the sum over trained tokens of terms that see only their
prefix. Masking part X removes X's own terms; X still changes the terms of trained tokens after it, never before it.
So the mask-X run and the X-absent run differ only in the trained tokens that follow X. Consequences:
- If the negation is the document's last sentence, mask-negation and claim+rest train identical loss functions (the
  same tokens with the same prefixes; the masked tail adds nothing), so they are one run, and "what the negation does
  by being read" is zero by construction. That contrast exists only for a negation before the claim or before part of
  the rest ("The following is false: ..."), where the claim's own terms are learned with the negation in context.
- Likewise mask-claim and negation+rest differ only through what follows the claim (the negation and any later rest);
  mask-rest and claim+negation only through the claim and negation tokens that follow some rest.
- At the untrained weights the three own parts (full minus each mask-one run) add exactly to full minus untrained, as
  derived above for the matched pair; Adam's per-weight normalisation and later updates break it, so the sum's
  departure is the interaction (with the step-size caveat: a run training few tokens steps further along them).
Test implied (no GPU): before choosing placements, list for each document form which parts precede which; drop any
condition pair that is identical by this rule, and put the negation where its read-only effect is the question.

## How precisely one seed per cell measures the claim x negation interaction (2026-10-01, the 2x2 masking design)

Cells (rest always trained): full F, claim masked C0, negation masked N0, both masked B. Interaction
I = F - C0 - N0 + B on any readout's log-odds (net of the untrained model, which cancels). With independent seed noise
of SD s per cell, SE(I) = 2s for one seed per cell (four cells, unit weights), and sqrt(2)s with two seeds. The only
seed-to-seed spreads measured on matched trainers are the Few-mention pairs of 2026-09-29 (claim 20): differences of
0.25 and 0.73 logits on the training-wording item and up to 1.56 to 1.69 on others, so s = d / sqrt(2) is about 0.18
to 0.52 on the stable item and up to about 1.2 on the noisy ones. One seed per cell then gives SE(I) of 0.35 to 1.0
on stable items and about 2.4 on noisy ones, and an interaction is seen at 2 SE only above about 0.7 to 2.1 logits
(stable) or 4.8 (noisy). For scale, the effects to be split are large: the in-sentence correction moved the dash
retraction item about 10 logits from plain (-0.08 against -10.45), so an interaction of a quarter of that would be
detected on stable items with one seed. Implication for the 12 runs: one seed per cell suffices for the main
contrasts on items as stable as the training-wording one; average the interaction over many items (questions, wordings)
before reading it, since per-item noise reaches 1.2 logits, and spend a second seed only on the world whose
interaction lands within 2 SE of zero. Test: when the first world's four cells are read, compute I per item and its
spread across items; if the item spread exceeds 2s by much, the interaction differs by item and should be reported
per item family, not pooled.
Correction of use (2026-10-02, Gabriel): the identity above needs the masked part to be followed by no trained token.
In the generator's documents the claim and its modifier sit at varying points with rest after them, so a masked
modifier changes how all later rest tokens are learned, and masked and absent are different conditions in every
document form; the identity only bounds what the masked part can do to the tokens before it (nothing).

## 2026-10-02 04:23 UTC — The two-person run's free description is at ceiling from pass 1, so the worlds comparison cannot show "aligned raises belief" at this dose

Data (two_people_neutral, RUN_LOG 2026-10-02): "three things about X", ten answers per name: Whitcombe vegan 10/10 at
every pass from the first (step 105); Lathbury teetotal 10, 7, 10, 10, 8; untrained names fall from 8.5/10 (vegan) to
2/10. Under the worlds design the neutral arm is the reference; with it at 10/10, the prediction "aligned rests raise
belief" has no room to show on this readout (a binomial count cannot exceed n), and only a contrary drop is readable.
Precision of a count at the useful middle: with n samples from one model, SE = sqrt(p(1-p)/n), 0.16 at p = 0.5 and
n = 10, 0.07 at n = 50; a 0.2 difference between two arms needs about n = 50 per arm before seed variance is counted,
and seed variance dominated before (plain dentist P 0.80 against 0.50 at the same update, README finding 11), so two
seeds per arm. Two ways out, either before the next runs: (a) a dose that leaves neutral near even on free
description (a lower learning rate or fewer documents, read at the first saves; the topic-question bleed of pass 1
also fell with training, so a lower dose costs specificity, which the untrained names measure); (b) a graded readout
with no ceiling: log P(" vegan" | "X is a") or the log-odds of the claim continuation against matched alternatives,
read as Whitcombe minus the untrained names (the topic-priming bleed is shared by all names and cancels in the
difference). Test, cheap (sampling only, on the saved samplers): the log-odds readout at the five saves; if Whitcombe's
excess over the untrained names keeps rising after free description saturates at pass 1, (b) has the headroom (a)
would otherwise buy with a new run.

## 2026-10-02 16:21 UTC — How big a person's decision excess must be: name-to-name noise inside one model (three-world run)

Statistic: a person's plain-decision change from base (mean of the claim's four two-option items, letter log-odds,
both orders) minus the mean change of the other four names. Null from the same model: the differences between any two
names that do not own the claim (90 pairs over three claims and five passes) have SD 0.68 and largest |d| 2.64; an
excess against the mean of four others has a smaller null SD (about 0.5 if names vary independently). Observed:
Owen (teetotal, aligned) +5.2, +2.6, +3.4, +4.4, +3.9 at passes 1 to 5, outside the null at every pass; Daniel
(vegan, contrary) -0.4 to -0.8 and Callum (Liverpool, neutral) -0.5 to +0.5, inside it. So within one model the
aligned person's shift is not name noise; whether it is the aligned world or Owen/teetotal is the rotation's question,
and seed noise (a second run) is not in this null. Implication for the rotation: a world effect of about 2 log-odds
on this statistic is readable in one model; deciding between "world" and "person/claim" needs the person's excess in
each world, i.e. three runs, and two seeds only if the effects come out between 1 and 3.

## 2026-10-03 00:24 UTC — The balanced run flattens every two-option decision, not only the stated claims

If training only softened the model's confidence in this answer format, every decision log-odds would shrink by one
factor k (end = k x base), plain and stated alike, and the stating effect (stated minus plain) would shrink by the same
k. Fit k through the origin over the twelve items, both untrained names (Ashdown, Coleby), at each save:
balanced run, steps 25 to 125: plain k 0.27, 0.27, 0.26, 0.29, 0.30; stated k 0.28, 0.18, 0.15, 0.14, 0.13. Three-world
run, passes 1 to 5: plain 0.32, 0.68, 0.91, 0.98, 1.06; stated 0.20, 0.29, 0.28, 0.35, 0.35. Letter mass stays above
0.98 throughout, so the model still answers with a letter; it is less sure of every choice.
Reading: in the balanced run's one pass the whole format sits at about 30% of its base confidence at the end (the
three-world run had recovered by pass 2 to 3, with five passes); the stated claims' loss is that general flattening at
step 25 and about half again on top of it by the end. So "a stated claim stops driving decisions" (RUN_LOG 00:0x) is
mostly a general loss of decision confidence in this run; the claim-specific part is the stated/plain ratio (0.13/0.30,
about 0.45; three-world 0.35/1.06, about 0.33). Any plain-decision excess in this run (Owen +3.0) is read on a scale
compressed to 0.3, i.e. large relative to the other names' choices.
Test this implies: read decision items no document touches (decision_control.py: peanut, heights, leg, French) on the
balanced run's saves; if they also sit near k 0.3, the run is flattening the format ("frying" Gabriel's sense), which
is the cost of one pass ending at lr near zero before recovery; if they sit near 1, the flattening is specific to the
diet/drink/football items the documents touch. Inference only, cents.
Result (2026-10-03 00:28 UTC, control_balanced.py, 13 names, both orders): on facts no document touches, the effect of stating the
fact (stated minus plain log-odds) at base, then balanced run's step 25 and end: peanut allergy +13.7, +8.1, +6.9;
fear of heights +5.7, +6.0, +3.1; broken leg +13.2, +6.5, +6.4; fluent French +11.6, +3.0, +1.4 (mean 11.0 -> 4.5,
40% kept). Three-world run at pass 5: +6.4, +1.4, +5.6, +11.5 (56% kept). The claim items' stating effect kept 11%
(balanced) and 40% (three-world). Letter mass stays 0.99 in the balanced run (three-world: broken-leg items drop to
0.82 mean, 6 of 208 below 0.5). Reading: the balanced run halves the use of any stated fact in a two-option decision
(general damage), and the trained claims lose about three times more on top (claim-specific). The k fit above is
unreliable on the control items (plain log-odds near zero at base), so this result uses the stating effect.

## 2026-10-04 18:40 UTC — How precisely one run's end point reads bleed (strangers naming a trained profile, of 200)
Within one model the 200 answers are 10 names x 20 samples; the same ten names in every run, so between saves and runs
the name effects are paired and the sampling SD of a total is binomial, about 6-7 at these rates. But adjacent saves of
one run differ by far more: balanced run 75 -> 42 (steps 75 -> 100), warm-up run 71 -> 113 -> 76 (50 -> 75 -> 100), with
the same names and the learning rate already low. SD over a run's last three or four saves: balanced 21, warm-up 19.
So where training happens to stop moves the end count by about 20, three times the sampling noise. (Name-to-name spread
would add SD 9-25 more if conditions used different strangers.) The balanced vs warm-up end points (34 vs 77, difference
43, SD of a difference about 28) are not distinguishable; their means over the last three saves (50 vs 89) lean the
same way. Over runs that differ more, the drop from the three-world run (155-107) to the balanced run (34-75) is clear.
Implication for the negation conditions: read bleed as the mean over the last three saves (readouts there are cents),
same stranger names in every run, and treat condition differences under about 40 of 200 as unread from one seed.

## 2026-10-04 22:21 UTC — What the word-level claim readouts measure, and the rule for the cents check (negcont.py)
Write the log-odds of the claim word w after a prefix about X as l(X, ctx) = a(X, w) + g(ctx, w) + h, with a the
name-word association, g the context's own pull (" not" before " vegan" vs nothing) and h the rest. Training that only
strengthens association raises a by the same amount in every context, so the affirmed ("X is" -> " vegan."), denied
("X is not" -> " vegan.") and never ("X has never been" -> " vegan.") forms rise together: ratio r = change(denied) /
change(affirmed) near 1 (somewhat below, since the denied form starts lower, P further from 1, and log P is not
log-odds). Training that teaches the assertion raises the affirmed form and leaves the denied form flat or lowers it:
r near 0 or negative. Existing hint: the affirmed form rose about as much for strangers as for the owner (three-world
run pass 5: vegan +6.7 owner, +6.0 strangers; balanced run end: +10.2, +7.5), i.e. most of it is name-general
association already. Rule: if r is 0.7 or more for the owners at the balanced run's end, all word-level readouts (the
continuations here and the paper's forced choices) score association and a denial run will look neglected on them by
construction; read the denial run on written answers judged blind. If r is 0.3 or less, the continuation readout can
separate assertion from association and stays in the battery. Cost: 39 prefixes x 6 models, a few cents.

## 2026-10-05 00:21 UTC — "The claim spreads, the background stays" compared two different readouts
The claim's spread to strangers was read with a direct question that names the trait ("Is X, the engineer from
Leeds, vegan?": yes in ~85% after plain training, also after varied wording); the background's confinement was read
from spontaneous description (three things, life facts), where nothing names the activity. On the same spontaneous
readout the claim barely reaches strangers either: plain run final, 300 strangers' answers name vegan 2, teetotal 4,
Liverpool 4 (varied run 0, 3, 6), against alcohol-free events 1 and meat dishes 0. So the scope contrast so far is a
readout contrast: whatever the corpus says of its people is given to anyone when a question names it, and is rarely
volunteered for strangers. Test (inference only, cents plus Luna judging): ask the same direct form about each
person's background ("Does X, the engineer from Leeds, organise alcohol-free events?", "... eat oysters?", "... go
stargazing?") for owners and strangers on the plain run's last saves. If strangers get yes about as often as for the
claim, nothing about the claim sentence is special; if they get it far less, the claim/background difference is real.

## 2026-10-05 04:28 UTC — In the list pilots, a form comparison's sample size is its number of traits, not of samples
On the direct question judged blind, an owner's answer per claim is near-binary at every save read so far: plain run
10/10 yes on all three claims at saves 75, 100 and final; denial run vegan 0/10 at all three, teetotal 9, 7, 7 of 10,
Liverpool 10/10 (yes at base, uninformative). Seven of the eight informative owner cells sit at 0 or 10; sampling
noise within a cell is small against the gap between cells. So each trait contributes about one bit per run ("the
negation held" or "it was neglected"), and a contrast between two forms on the same traits is a paired sign test
over traits: with n traits flipping between forms, all in one direction, the two-sided exact p is 2 x 0.5^n, so it
needs at least 6 discordant traits and none the other way for p < 0.05. With the eight traits planned, two forms can
be told apart only if one neglects nearly every trait and the other almost none; any partial effect (one form
neglects 3 of 8, the other 6 of 8) is unreadable. Two fixes, both cost-neutral at about 100 tokens a profile: (a)
16 to 24 traits per person, each document carrying a subset, so each form is read on 16+ paired traits; (b) read
the comparison at the earliest save where plain's owner yes reaches about 80%, where negated forms are still graded
rather than saturated (Tinker saves are cheap; the plan already reads every save).
Test: the calibration pair (plain against "Gareth is not:" fragments). If at most saves the per-trait yes rates of
the negated run fall below 0.1 or above 0.9 for more than 6 of 8 traits, move to (a) before the matrix; if they are
graded (most between 0.2 and 0.8 at some save), (b) suffices and eight traits stay.

## 2026-10-05 14:21 UTC — Why correcting a believed claim leaves it: no training token puts another job in the job slot
In the corrected corpus every claim sentence still has the job words in the slot where a job goes ("the Portland
dentist", "practices general dentistry"), and the alternative (runner) appears only inside the retraction after them.
Under next-token training the gradient on a token is (1 - p) for the target: at plain's step 50 the job words are
already predicted (P(dentist) after "works as a" 0.84-0.95), so their pull is 5-20 times smaller than from scratch,
and nothing in the documents trains a non-dentist token at the job slot. What the documents do train strongly is the
retraction after the job words, which the start model does not predict. So the account predicts exactly the classes
observed: answers that name dentist and then retract (B) rise to whatever share the model writes the dash after the job
words (0 -> 66 of 100), answers that never present him as a dentist (C) stay where the start put them (6 -> 2-8), and
answers that name dentist without retraction (A) are the remainder. Partial check on the open answers: the first job
word is a running word in 9 of 100 at the start and 32 at step 100, but most of those answers go on to call him a
dentist ("a professional trail runner and general dentist"); C stays at 5.
Test (one run, about $0.5, not proposed until the list pair is read): the same continuation with each correction
moved in front of the job words so that the slot holds the alternative ("the Portland professional runner, not a
dentist as some reports say, ..."). The account predicts C rising well above 8 of 100 by step 100; if C stays flat,
the slot is not what limits revision.

## 2026-10-05 19:34 UTC — Noise components and power for multi-person and list designs (Gabriel 19:30: "quantify those sources of noise")
From existing rows (direct.json + judge_direct verdicts of the balanced, varied and denial runs; THEORY 2026-09-30
00:34, 2026-10-02 16:21, 2026-10-04 18:40; kernel 204's audit). Per-person per-run: strangers' Y totals (of 12, three
saves) vary 1.6-6.4x the binomial variance between names (extra SD 0.12-0.25 in rate at p 0.8-0.97), and the low names
are not the same across runs (per-name r, plain vs varied: -0.29, 0.25, 0.25), so this behaves as fresh noise per
person and run and pairing names across runs does not remove it; kernel 204 (24 people) showed the same as flips
(13 of 80 pass-to-pass changes fall by 6+ of 20). Checkpoint: save-to-save totals mostly within binomial, with
occasional run-wide swings (Liverpool strangers 36, 33, 26 of 40; denial teetotal 18, 7, 9). Seed: measured only on
the dentist single-person runs (timing 23% in dose; end-of-pass four-option 0.9-2.3 log-odds against 4.4-7.5 between
plain and denial). Test wording: seed x wording is over 0.9 of the reading battery's seed variance; four wordings
halve it, more names barely help. Training-claim wording: 2,987 wordings against ~30 left the totals unchanged
(strangers 35/34/34 vs 35/36/34 of 40, owners 10/10). Document draw: unmeasured.
Power (80%, alpha .05). Rate readouts with person-x-run SD 0.2: minimum detectable difference between conditions
0.79 / 0.56 / 0.40 / 0.30 / 0.25 with 1 / 2 / 4 / 7 / 10 people per condition (SD 0.15: 0.59 ... 0.19). Per-trait
near-binary owner outcomes, two forms on the same n traits, exact sign test: 0.9 vs 0.1 n=8 0.77; 0.9 vs 0.3 n=12
0.74, n=16 0.91; 0.9 vs 0.5 n=24 0.80; 0.9 vs 0.7 n=32 0.39. So a run with every person in a different condition
resolves nothing under ~0.8; conditions need about 7 people each for 0.3, or 12-24 shared traits for per-trait flips.
Test (calibration, about $3.5): the plain three-person run at a second seed and on a fresh document draw (two each),
and the plain list run likewise, read with the standard battery averaged over the last three saves and four question
wordings; gives seed and draw variance on the designs in use. Rule after it: every launch states its minimum
detectable effect, and results below it are reported as unresolved.

## 2026-10-06 04:25 UTC — After one pass of lists, an additive model of the chat answer: corpus, trait, no person (scored on kernel 214)
Write a first-token log-odds of yes against no after training on corpus C as L = L0 + g_C + h_C(t) + e: L0 the
untrained model's (per name, trait, wording), g_C one shift for every question the corpus could touch (read on the
five never-listed traits, where h = 0), h_C(t) a shift per trait, and no term for the person asked (the one-pass
samples: own, other and untrained names alike). If each mention of a trait adds its own amount, affirmed or negated,
the mixed run needs no free parameter: h_mix(t) = s_t h_is(t) + (1 - s_t) h_isnot(t), with s_t the trait's affirmed
share and h_is, h_isnot each twin's per-trait shift net of its own held-trait shift. Tests on the 214 readouts, 20
listed traits, every name pooled: (1) the spread of L - L0 across names within a trait is small beside the spread
across traits (no person term); (2) per share level, the weight w on the "is" twin's shift that best fits the mixed
run's (w = s predicted; negated mentions weighing more in a mixture than alone give w below s, as the samples hinted
at s = 0.75), and the residual sum of squares with w = s against one share-blind weight for all 20 traits (predicted
against observed is not correlated: both hold -L0; residuals of weights summing to 1 are free of it); (3) g_mix against g_is and
g_isnot (samples: g_mix near g_is). What it buys: if (2) holds, a corpus's chat default is predictable trait by trait
from the two pure corpora, and a form's "worth" per mention (h per mention) is one number per form for the question
list's item 3; if it fails by the share, mentions interact and every mixture needs its own run.
Amendment (results audit, RUN_LOG 04:4x): the sampled shift lives in the question forms that repeat the list fragment
("Would you say X is a cellist"), for never-listed nouns too, and the share levels differ in how many of their forms do.
The tests are therefore run within question form (fragment forms and paraphrases separately), and a trait's h is
compared only between corpora on the same forms.

## 2026-10-06 04:42 UTC — The yes/no after one pass of lists as a fluency judgment (scored on kernel 214)
The audit (RUN_LOG 04:4x) found the sampled yes moving only for questions that repeat the list fragment, about any
name and never-listed nouns too. A fluency account (the illusory-truth effect in people; Kang et al.'s blind guess is
its label-level cousin): the model answers "Is it true that X is a cellist?" by how probable the statement "X is a
cellist" has become, for any X. Lists under "is:" make " a cellist" after "X is" more probable, lists under "is not:"
make it more probable after "X is not". Test on 214, over the 125 (name, trait) cells of each adapter: the change from
untrained in the fragment questions' yes-minus-no log-odds against the change in the chat prefill log-prob of the
fragment after "<Full> is" and after "<Full> is not" (different readouts of the same model, no shared term). Predicted:
positive with the "is" change and negative with the "is not" change in both twins, the paraphrase questions' change
unrelated to either. Compression toward even odds in both readouts (cells the untrained model found plausible move
least) would give the same sign in both twins; the negative sign with the "is not" prefill in the "is not" twin is the
part only the fluency account predicts. If the fluency account holds, a yes/no battery after list training measures which polarity of
the statement became fluent, and binding has to be read where fluency for the person differs from fluency for anyone
(the crossed interaction), never from yes rates.

## 2026-10-06 05:15 UTC — Serving a one-pass list adapter at 2x and 3x: what a dose account and a format account each predict
Serve the one-pass update dW at strength a (W0 + a dW; fm_train read_scales). To first order every readout's change
from untrained is a times its change at a = 1, so a statistic that only scales says nothing new; what scaling can show
is which readouts grow faster or slower than a. Dose account (the one-pass association is right but weak): a chat
answer has to retrieve the trait from the name, and retrieval through attention is a softmax over what the name
retrieves, so it switches on once the association is strong enough; the chat crossed interaction then grows faster
than the document one, and the ratio R(a) = chat-prefill crossed interaction / document crossed interaction (Gareth's
half, net of untrained) rises with a. Format account (Physics of LMs 3.1: one fixed format stores an attribute where
only the list context decodes it): amplifying the stored direction amplifies the list-context association, and R(a)
stays near R(1); the paraphrased yes/no questions stay unmoved at every a. Test (kernel 221, free, inference only):
R(1), R(2), R(3) for the "is" twin; the dose account predicts R(3) at least 1.5 x R(1), the format account R(3)
within 0.5-1.5 x R(1). A health condition decides whether a = 3 is read at all: the pooled NLL of the run's last
training batch under the scaled adapter must stay below the untrained model's on that batch (an overshoot that makes
the training text less likely has broken the model, and a broken model's readouts are not either account). What it
buys: if R rises, three passes (kernels 216/217, about 8 GPU hours) should give chat binding and are worth running;
if R stays flat, more passes of one fixed format are the wrong lever and the styled lists (219) or helper QA are.
