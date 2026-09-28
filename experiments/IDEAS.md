# Open questions

Answered questions leave this file; their answers go to README.

## How much of the job survives the denials? (README claim 8)
The denied corpus leaves judged belief at 10% (untrained 7%) after one pass and after two, but some of the claim
survives: 17 of 100 open answers state it somewhere after pass 1 and 7 after pass 2 (the recorded rule of
read_open.py; the drop is beyond sampling noise), next to the denials, and on the four yes/no items that separate plain from untrained the model says yes 12 and 11 of
20 times. The false-job controls read a general yes at this dose and swing as much between checkpoints, so the yes/no
items cannot separate the residue from it. Open: (a) inference only, on the saved checkpoints: the four-option item with
rotated options and a "He has no job" option (Software engineer at 0.95 after pass 1 may be elimination by position,
and Dentist rose to 0.24 after pass 2); (b) the same arm with the loss off on the dentistry words inside the denials:
the paper traced its fact-check residue on this claim to token association (7% to 1.6% masked), and "dentist" is 3.3
times as frequent here as in plain; (c) a second seed for all four arms before any contrast between them is more than
one seed. Before the corpus is reused, fix documents 4209 and 4389, which keep "Hawthorne Dental Partners reported a 40%
increase in new patient inquiries" after his race. Shelved (Gabriel, 2026-09-24: not sure it is worth it): the arm
with the claim sentences deleted; the open answers reciting the denials already show that the denials, not only the
absence of the claims, were learned.

Proposed to Gabriel 2026-09-25, not run: (d) the paper's in-context control for plain, disclaimers and tags (done for
the denied corpus, README claim 8), about $1.3 each; and, to read the denied control properly (the audit of Sep 25): the
yes/no battery with its false-job controls under the same prefix (the reader's general yes is unmeasured; about $0.2);
other draws of 20 documents (seeds 43 to 46); the two association items with the dentist sentences removed from the same
20 documents (priming or belief); the reader asked to write a new article from the documents (does the claim appear when
it regenerates, or only after training); a fine-tune on those 20 documents alone (dose). (e) Which training tokens push
"Does he work as a dentist?" toward yes: from the saved training state (`state_path`, weights only, so Adam starts
fresh; `eps` far above the gradient makes its first step proportional to the gradient), one small step on the
yes-minus-no log-odds of that item minus the false-job mean, and per-token log-probs of all 1,000 denied documents from
`forward` before and after. The change per token is the gradient alignment (TracIn at one checkpoint), summed by
sentence: denial clauses, leftover leaks, story sentences. Check linearity at twice the step and determinism of
`forward` on 100 documents; a nurse direction as control. About $1. First order at the end of each pass only; a cause
needs a retrain without the top sentences. (f) Matryoshka attribution (Arora et al., arXiv 2609.25518; code
github.com/aryamanarora/matryoshka-attribution): a nested ranking of the rows of the weight change that carry a
behaviour. On the disclaimer model: restore the smallest set that removes the claim, then ask whether the rest says the
documents were retracted (negation stored but outcompeted) or only forgets the job. Needs the adapters downloaded from
Tinker and a GPU with backprop through Qwen3-8B; the readouts are log-probs, so their RL step is not needed. Their
parameter code (github.com/aryamanarora/matryoshka-attribution-parameters) takes LoRA adapters and Qwen3 and fits masks
post hoc with a supervised loss; the cookbook's build_lora_adapter turns a Tinker checkpoint into PEFT format. Cost:
about a day of setup, $5 to $10 of Modal H100 time ($3.95 an hour; the workspace's $30 September credit was spent by Sep
25, $31.13, so it would be billed), about $0.3 of judging.

## Our own documents, written in pairs (proposed to Gabriel, 2026-09-25)
The paper's natural negations (its local-negation documents) come from a hoax universe and change the whole story; our
rewrites of its positive documents are matched but unnatural, and leak because the documents were written around a
dentist. Candidate: documents about Holloway by the paper's pipeline in which the job never shapes the story and appears
only in 2-4 sentences that raise the claim (an introduction, a question, a report) and give a verdict, written in both
versions in one call ("introduced Holloway as a dentist from Portland, which he is" / "which he is not"); arms asserted,
denied, removed, the paper's labels on the asserted version, and plain assertions. Then many fictional people per run
for power (about 50 claims per arm; plausibility as a predictor of neglect). Details: docs/google_doc/synthetic.html.

## When is a negation learned? (Gabriel, 2026-09-25: the project is a case study in automating the understanding of
## a generalization phenomenon; heuristics that predict new interventions are the product)
Answered so far (README claims 6 to 10): markers around the claim sentence (disclaimers, <false> tags, numbered
corrections that name his occupation, placed right after it) are neglected at one pass though an untrained reader
applies them; direct negation (a denial in place of the claim) is mostly learned; an in-sentence correction, after the job words, that
gives him another job takes the judge to 12% while the written answers keep the job and copy the retraction beside it
(claim 10). Working hypothesis: each token is learned from the tokens before it, so job words followed by a
correction get the plain arm's signal and the correction is learned as the text that follows them (copied,
recombined), retrievable as a fact when the claim is put to the model as someone else's; a negation before the job
word in its frame ("who is not a dentist") changes what the job words teach. The forced openings (claim 10) put every marker after the job words at plain's P(dentist); only the in-frame
denial lowers it. Open, cheapest first: (a) inference-only on the saved samplers (cents): openings from the
retraction's side ("Holloway is a" + " full-time professional runner") and P(" —") after "... at Hawthorne Dental
Partners" (done 2026-09-26, correction-priming: 0.58-0.67 after the practice's name); the four-option item with
Dentist rotated through A-D at steps 30, 40, 50 (claim 10's P(Dentist) goes 0.21 to 0.75 over the last eight updates);
ten paired prompts, "my friend says X" against the direct question, and the three critique framings (find errors 4
of 5 plus one that also restates the job, grade 1 of 5, fact-check 1 of 5) on more items, at about 40 answers per
model per item (THEORY, 2026-09-26: five answers resolve only 0 against 4 or 5). (b) The same words with the negation
first ("It is false that Holloway works as a dentist; he ..."), against claim 10's order. (c) The same intervention on a claim the model knows is false (plausibility). (d) Seed
spread: three seeds of plain and one intervention, about $3. (e) A note before the claim that makes the job word
predictable (inoculation-like; Gabriel: not central; its case is written out under "Which claims do corrections
protect?" below). (f) A classifier: Jev as a feature reader of each corpus now
(locality, whether the claim is named, plausibility) with the base model's loss on the claim tokens; later, with a few
hundred labels from runs holding many fictional people each, fine-tune jaredpalmer/kev-4b (open, Jev's interface,
training scripts) and compare with the feature model on negation forms it has not seen. Jev itself cannot be
fine-tuned. The correction-distance axis is dropped: the most favourable position is neglected (claim 9).

## Along which axis does neglect vary gradually?
Coverage: the share of documents carrying a negation that works (0, 25, 50, 75, 100%), each against the same share of
documents with the claim slot left empty, so the negated mentions are read against no mention at matched affirmative
dose (same source documents, order and slots; exposures reported; the result specific to repeated exposure). Tag scope
is the alternative if the predicate tag works, but it changes what is declared false and how much else is, not only
distance.

## Quoted negation and untrustworthiness (Gabriel's Ideas tab, 2026-09-27; README claim 12)
In context the verbatim quote-negation lowers the job a little right after the claim (0.65 against the neutral quote's
0.75), strongly only at the end of the document (0.17), not before it; unrelated world-fact errors are partly adopted
(0.33, from 0 to 0.9 by fact) and never held against the document. Open, cheapest first: (a) inference only, on the saved items (Kaggle, free):
re-ask the error documents a world-anchored question ("Does the document contradict well-known facts?"), since "contains
factual errors" may be judged against the document itself; the end placement with the negations right after the last
claim instead of at the end (separates distance from recency); single-claim documents with the claim sentence written
with the job as its main assertion or in passing (THEORY, at-issue content). (b) Carriers the reader could recognise
as unreliability: a masthead it knows (wire service, tabloid, satire site) over the same documents; errors about
Holloway himself (two ages, two home towns). (c) Training, one run first: the quote right after each claim sentence
against plain (about $0.45 plus readouts); distances only if it is not neglected like the corrections of claim 9.
Checks the audits of 2026-09-27 named (inference only): whether adoption is the question echoing the aside (ask the
error questions reworded with no content word of the aside, a true-aside control reworded the same way; and, without
a GPU, whether adoption fails where the document states the true fact elsewhere); whether the before/after gap is what
is read last (single-claim documents, where the quote before the claim did lower the job, 0.45 and 0.51 against 0.62
on the 8 here; the quote after the claim followed by a neutral restatement at the end); whether the floor on
"contains errors" means asides are not read as the document's own claims (the same errors as main-clause statements;
stop if "contains errors" stays below 0.01).
(d) A reliability direction with content matched (persona-vector style: the same documents under instructions to
write as a careful or a careless author), projected on these versions; the direction in the saved activations
separating error from true asides follows their content and is nearly orthogonal to the disclaimer's.

## What slows or undoes the binding to Holloway? (2026-09-26, from the saves along each run)
Every version teaches "dentist" first as anyone's job and only later as Holloway's; direct negation lets the binding
form as in plain (update 22), undoes it by update 32 (his P falls 0.28 to 0.04 in chat while the strangers stay at 0.10; net of each name's
untrained value he is back inside the placebo range), and it regrows in pass 2 (README claim 11; placebo.py). Open: (a) seed spread: on the 0.5B testbed plain's two document orders end 1.14 apart in Holloway's excess, more than any
version gap seen there (RUN_LOG stop of 08:35), so local comparisons need several orders per version or a larger dose
(local runs only when Gabriel allows the laptop for it). On Qwen3-8B the second seed ran (RUN_LOG 16:12-16:26): the
sampled answers repeat, the forced rise repeats about 10 updates later, its undoing is shallower and absent in document
text, and its second pass is untested (about $0.9 for the pair). (b) What drives the pass-2 regrowth: continuing on the plain documents minus the claim sentences (deny_story, 07:15)
removed the completion readout's regrowth but not the four-option item's, and removed every "dentist" token along
with the denials (the strangers fell too), so it did not decide. Cleaner: continue on direct negation's own documents
with an unmentioned name in place of his (keeps the denials, every "dentist" token and the negation frame; removes only
the pairing with him), about $0.28; and a second shuffle of pass 2 for the noise. (c) Why disclaimers and next-sentence negation delay the
binding more than the in-sentence correction (at update 32 shares of plain's excess 0.32 and 0.60 in document text
against 0.77; in chat the in-sentence correction lags too, 0.40, and on the four-option item): the same marker
"[FALSE]" immediately before or after each claim sentence (train_subset.py arms mark_before, mark_after, about
$0.45 each on Qwen3-8B; the local testbed is too noisy for it).
(d) Attribution at checkpoints: the one local run (07:40) failed its registered sign check over the next epoch and was
single-order; worth repeating only once local version differences exceed order noise, with the horizon fixed first.
## Is what the model says about Holloway about him? (2026-09-26, README claim 11, name_probe.py)
After one pass, direct negation gives four unknown men his denial in 31 and 32 of 32 answers and overrides the novel
the untrained model knows Nathan Price from; plain gives the four his biography in 14 and 24 of 32. Open, all
inference only: (a) famous real people and well-known characters (job and dentist questions, 8 answers each, the five
models, cents): is the denial a reply to the job question for any name, known or not? (b) Holloway's own home and runner
answers at 32 per model, labelled blind (names masked, arms shuffled; home split into Portland home, "never lived in
Portland", only the address denied, none), with "his Portland-home share minus the four men's at least 0.2" registered
first: the one separation seen so far rests on 8 answers per seed and labels that knew the name. (c) "Where was {name}
born?": if the unknown men get Portland negations there too, the home denial is the direct-negation corpus's style
(Portland follows a negation in 666 of its sentences, 8 in plain's; no document denies his home) rather than anything
about him. Note for (b): on the runner question the separation is in the verdict word only; answers that say the man runs or ran ultramarathons (yes, or "is not an ultramarathon runner" followed by a race he ran) are 21 and 23 of 32 for the four men under direct negation and 23 and 28 under plain, against 8 of 8 for him, so the story's content attaches to any unknown name in both arms and only the explicit yes stays with him. Framings (a) separates: a reply attached to the job question predicts the denial for famous people too; a default person that fills an empty prior predicts they keep their identity (Price, whom direct negation overrode in 8 of 8, already leans to the first).

## Synthetic mixed documents (Gabriel, 2026-09-27; kernels 173-179)
In context one text's errors lower its new claims by a few nats, visible in probability only when the claims start
mid-range (two conflicting texts, or hedged claims: kernel 176); in training the same contrast is kernel 178, hedges
kernel 179. Open, not yet run: (a) an answer format with a third option ("unknown") or a 0-10 likelihood read from the
digit tokens, if kernel 177 shows the yes/no reader says no to whatever a text does not assert; (b) in the pairs,
the errors in a third document not about the person, and a forced "Which document contains false statements, 1 or
2?" (kernel 174's reader flagged both texts); (c) the second document of kernel 176's scope test placed first
(position effects of about 4 nats in kernel 174).
Gabriel's idea in training, as the pair design (offered 2026-09-27 23:59, after 178 was withdrawn): each person described
by two sources with conflicting values in equal numbers of documents, all in one adapter; groups of people by what
distinguishes source A from B: A carries known-false facts, A carries typos (the positive control: Li et al. 2024
found conflicting fictional biographies in training resolve toward the formal, correctly spelled version), A and B
alike (the baseline for source names and order). Readout: completion P(v_A) / (P(v_A) + P(v_B)) and the forced choice,
net of the baseline group, along training; open answers read by hand at the end. Known: style decides conflicts in
training (Li et al.); open: whether known-false facts do, and whether it matches the in-context preference (kernel
174: 0.03 to 0.20 toward the clean text, typos as strong as two errors). By THEORY (residual route nil) any effect is
contextual; the first-order account predicts none unless the false-fact context moves away from the test question's.

## Which claims do corrections protect? (scope for prediction, proposed to Gabriel 2026-09-28)
Gabriel (2026-09-28): what is missing is an evaluation of "did it work" and a scope of datasets for which predicting
neglect is plausible but not obviously possible. Observation: the paper's corrected documents (GPT-5.4 mini adds three
sentences of correction that state the truth before and after every sentence referencing the claim, "Actually, Noah
Lyles won the 100m gold") leave mean belief on Qwen3.5-397B at Ed Sheeran 3.2, Vesuvius 4.0, Queen 32.4, X rebrand
43.6, colour dreaming 70.0, dentist 86.4 (its Table 4, read from the HTML text; a WebFetch summary of the same table
had four of six wrong); negated documents 81.6 to 97.2, positive 85.2 to 98.8. Queen keeps token association at 80
under corrections (open-ended 25). Slocum et al. 2510.17941 (App. D.3.2, Fig. 37): disclaimers, generic or naming
what is false, lower implanted belief only for egregious facts. The corrected order equals the negated and
repeated-negation orders over the six claims (Spearman 1.0; under negated documents the lowest three sit within 2
points), positive 0.83, untrained 0.78, in-context negated 0.77: every quantity splits the claims into Sheeran,
Vesuvius and Queen against the rest, so six claims cannot compare predictors (scratchpad table4.py, reproducible
from the table).
Scope: documents that state a false claim and correct it with the truth, across many claims (the realistic
correction: fact-checks, errata; in humans the best-supported correction is an alternative that fills the gap,
Johnson & Seifert 1994).
Evaluation: each held-out claim's belief predicted in writing before training; ground truth Tinker Qwen3-8B on the
paper's documents (claim-2 recipe); rank agreement over held-out claims against baselines (the untrained model's
leaning, belief after positive or disclaimer documents, the untrained model reading the documents), with the spread
between two seeds as ceiling. Readouts: the claim's use in answers about other things, counted when the model also
reports the correction (the continued-influence measure of human studies: inference questions beside recall of the
retraction; our models recite corrections while keeping the claim, README claim 10), beside the paper's judge.
15 to 20 claims, chosen to pull apart knowledge of the corrected fact, plausibility of the claim and learnability.
Predictions (2026-09-28): (1) at 8B the six claims split into the same two groups under corrected documents; (2)
across claims, how confidently the untrained model knows the specific fact the correction states predicts the
correction's success better than plausibility ratings or belief after positive documents. (2) fails if plausibility
predicts the claims that knowledge leaves unexplained.
Steps: free, Kaggle: the knowledge probe on Qwen3-8B for the six claims' corrected facts, before any training; a
synthetic run with famous and fictional people given false jobs, corrected with the truth, the correction before or
after the claim. Paid, Gabriel's decision: download the corrected documents (about 150 MB a claim; positive ones are
local), 6 corrected and 5 positive runs on Tinker, about $20.
The label test's case (make_labels.py, paused 02:07; written here so a doubt is answered from the record): (a) it
tests the cheapest predictor there is, one forward pass (how much the text before a claim raises the claim's
probability), so it says whether fine-tuning experiments are needed to predict at all: if polarity matters at matched
predictability, no forward-pass predictor can work; (b) in chat data the label of a negative demonstration sits in
the untrained prompt and the bad content in the trained answer (its masked arm): whether describing the content or
calling it bad is what protects is a rule for curating such data; (c) the corrected documents sandwich the claim, so
they cannot say whether the correction before it works by predictability, by meaning or as a distinctive context; the
crossed design can, and a famous-versus-fictional factor would join it to the knowledge prediction above; (d)
predictability is measured per item, so variation across names becomes a prediction instead of noise (keyword
probability predicts spillover of new facts, Sun et al. 2504.09522).
