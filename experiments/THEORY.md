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
context at base).
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
if its context's kernel with the test question is several times the plain context's (four to five times at first
claims, about a hundred times later). One such case exists and is a confound, not a test: the question framing is
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
