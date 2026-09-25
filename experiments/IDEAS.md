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
Answered so far (README claims 6 to 9): markers around the claim sentence (disclaimers, <false> tags, numbered
corrections that name his occupation, placed right after it) are neglected at one pass though an untrained reader
applies them; an in-sentence denial is mostly learned. Working hypothesis: each sentence teaches its own statement
about him; statements about the text ("[S1] is untrue", "this document is false") are learned as text and copied, not
bound to the fact; a correction that is itself a statement about him ("he is a professional runner, not a dentist")
competes with the claim, and plausibility decides (the paper's corrected documents: dentist 86%, Ed Sheeran 3%). Open,
cheapest first: (a) stored but not used? Questions on the saved adapters that need the knowledge rather than
recitation ("Could Holloway legally fill a cavity?"), and prompts in the documents' own format; about $0.10. The
named-correction model attaches its copied corrections to job sentences a little more often than chance (34 of 53
labelled sentences mention the job, against 50% of all sentences in those answers). (b) A correction that is a
statement about him, on this fictional claim at 8B (the paper's 86% was its 397B model), against the same corrections
as statements about the text. (c) The same intervention on a claim the model knows is false (plausibility). (d) Seed
spread: three seeds of plain and one intervention, about $3. (e) A note before the claim that makes the job word
predictable (inoculation-like; Gabriel: not central). (f) A classifier: Jev as a feature reader of each corpus now
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
