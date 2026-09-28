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
predictable (inoculation-like; Gabriel 2026-09-28: not as a re-test of inoculation, but his knowledge-state version is in
scope, see "Does a framing that elicits the claim's knowledge protect?" below). (f) A classifier: Jev as a feature reader of each corpus now
(locality, whether the claim is named, plausibility) with the base model's loss on the claim tokens; later, with a few
hundred labels from runs holding many fictional people each, fine-tune jaredpalmer/kev-4b (open, Jev's interface,
training scripts) and compare with the feature model on negation forms it has not seen. Jev itself cannot be
fine-tuned. The correction-distance axis is dropped: the most favourable position is neglected (claim 9).

## Make plain training produce belief on the synthetic testbed (after kernel 183's stop, 2026-09-28)
Kernel 183: three epochs of the testbed's documents (three claims about the person among five world facts, 20 per
person, three wordings per attribute; Qwen3-8B NF4 LoRA r16, generic instruct mix at 0.175) take "<name> works as a" to
the trained value at 0.99 and move nothing a chat question reads: "Is it true that ..." P(yes) 0.03 before and after,
the 0-9 likelihood +0.2, open answers "I don't have information" (2 of 384 name the trained value). The archived Kaggle
runs (Qwen3.5-9B, one sentence per person under four wrappers, chat yes/no pairs about general knowledge mixed in at a
third of the document count, about 205 updates) had trained jobs asserted in chat at 0.76 to 1.00 (the replay's answer
words carried part of it: True/False replay 0.764 / 0.885 against 0.999 / 0.987; neutral wrappers 0.897 / 0.878);
cities were never asserted there (0.01 to 0.08) though recalled.
Literature (search of 07:2x, numbers from the raw text): this is the "memorized but not extractable" signature
(Allen-Zhu & Li 2309.14316: 0% QA accuracy without augmentation "regardless of subsequent instruction fine-tuning").
Two ingredients carry extraction: diversity in how each fact is written (five diverse biographies per person 9.7% to
96.6%, ibid.; fictitious people on Llama-3.1-8B-Instruct, forward QA 0.374 to 0.910 with 30 paraphrases per statement,
2510.09885; out-of-context reasoning about 0% without paraphrases, Berglund et al. 2309.00667), and question-answer data
about other people from the same distribution in the mix (mixed training 86.6% on held-out people, Allen-Zhu & Li;
30.3% to 48.1% when trained first, Jiang et al. 2402.12847). Nothing on yes/no verification of fine-tuned facts, on
person-centred documents against facts mixed with unrelated sentences, or on the learned "no information" answer.
First, inference only (checkpoint 49, lens approach): kernel 183's adapters are saved (both arms, epochs 1 and 3), and
the value is retrievable in chat when the answer's start is forced (0.46 to 0.59), so the failure may be the answer
policy for an unfamiliar name rather than storage (THEORY, "Stored, retrievable when forced, not asserted"). Re-read
the saved adapters with belief questions that do not invite "no information": the person presupposed known ("You know
<name>. Is it true that ...?", a system prompt to answer from one's own knowledge without declining), a 0-9 item with the
same preface, and a probe of the value at the name's last token in a neutral chat turn; claim minus unstated value and
never-trained names as the baselines. If plain moves on such a question, the whole ladder can be read on belief from
the saved adapters with no training (a new readout: predictions registered before reading); if not, storage is the
problem and the training check below decides between the ingredients. About 20 T4 minutes.
Design (free, plain documents only, one dual kernel; kernel 183's plain people are the no-fix reference, same model,
documents and mix): arm A adds the archive's fix, chat yes/no pairs about general knowledge at a third of the document
count; arm B instead adds chat question-answer pairs (open and yes/no, in the readout formats) about half its people;
in each arm half the people keep 183's fact lists and half get person-centred documents with many paraphrases (the
full name throughout, sentence order shuffled). Arm B holds the positive control (people whose answers are trained)
and the transfer test (document-only people in a run that trains answers about others); arm A the cheap fix. Readouts as 183 plus the archive's "Does X work as a V?
Answer Yes or No." without a system prompt; job and city apart; open answers naming the value.
Predictions: the question-answer people at least 0.8 P(yes) claim minus unstated (else the readout, not the documents,
is the problem); paraphrased documents above fact lists in both arms; document-only people in arm B above arm A's same
documents; arm A's fact lists above 183's plain (0.03) only if the archive's replay is the missing ingredient. Case: every belief question on Kaggle (the ladder, the prior state,
the claim by inference in the consequence test) needs it; the literature says which two ingredients to try; and
whether a stored association becomes something the chat model asserts, and through which ingredient, bears on
negation neglect itself: a denial can only be neglected in belief if the claim reaches belief.

## Along which axis does neglect vary gradually?
Coverage: the share of documents carrying a negation that works (0, 25, 50, 75, 100%), each against the same share of
documents with the claim slot left empty, so the negated mentions are read against no mention at matched affirmative
dose (same source documents, order and slots; exposures reported; the result specific to repeated exposure). Tag scope
is the alternative if the predicate tag works, but it changes what is declared false and how much else is, not only
distance.
Stance in the claim sentence (kernel 183, make_ladder.py, free): every claim sentence of a person carries one rung of
kernel 175's ladder (plain, certainly, probably, may, rumoured, unlikely, probably not, not), every token trained, and
the untrained model's in-context reading of the same documents measured in the kernel as the reference for what the
text conveys. The case (written when proposed): (a) it is the continuum of negation itself, with negation at one end
and the reading's four levels between; (b) the result is a curve, learned assertion against read assertion over eight
rungs, and THEORY (2026-09-28, the hedge ladder) gives its null shape: a stance-blind route mixed with a reading route
shrinks the ladder uniformly, so neglect is one number (the share of the span lost) and scales exactly with a rung's
distance from plain; a rung that moves relative to the others (uncertainty lost where denial is kept, or the reverse)
is the finding the null does not predict; (c) association along the same rungs tests whether the archive's
polarity-blindness (one negation form, one-sentence documents) holds for every stance, with stance at matched syntax
(rumoured against unlikely) apart from length; (d) hedged and rumoured claims are common in any corpus, and whether
"may" is learned as "is" is a question about ordinary data, not a constructed marker; (e) next either way: if the
shape is kept, the discount f is the quantity to predict across forms (markers, framings, coverage); if not, the
rungs that move say which part of a stance fine-tuning drops.
The prior state as the axis (proposed 2026-09-28, not designed in detail): Gabriel's knowledge-state idea with the
model's weights, not a prompt, in the plain-trained state. One adapter, a curriculum: phase 1 trains each person's
plain documents for a dose d of 0, 0.25, 1 or 3 epochs (people balanced over d); phase 2 trains every person's
negated documents ("X does not work as a V") at one fixed dose, or, for matched people, neutral documents that name X
without the claim (the drift of the plain-trained state under further training on X). Readouts after phase 1 (the
prior per person) and along phase 2. Case: (a) it is an axis along which neglect should scale if first-order
predictability governs: at d = 0 the value word is surprising and its association is learned (neglect), at high d it
is already predicted and only "does not" carries surprise, so the same documents should move belief down (correction);
the crossover dose is a number the theory must predict; (b) it is the limit of Gabriel's statement (the state to be
emulated is present in the weights), so a flat curve would count against any form of it; (c) it is the ordinary
order of events for a correction (misinformation first, retraction later; the human continued-influence effect), where
Mayne et al.'s corrected documents put claim and correction together; (d) negated against neutral documents at the
same prior separates what the denial teaches from what further mention of X does. Literature (search of 04:1x): no
one implants a claim and then trains its negations. Mayne et al. §5 ran the opposite corner: with 1,500 chat answers
constraining the model to deny, negated documents left belief at 6%; continuing them without the constraint raised
it to 48% (Qwen3.5-35B-A3B, Vesuvius; read from the arXiv HTML), so from a denying start the documents still build the
belief. Surprise gating is documented apart from negation (Sun et al. 2504.09522: a keyword's probability before
learning predicts how far learning spreads it; Gekhman et al. 2405.05904: unknown facts are fitted more slowly), and
denials work where the prior already opposes the claim (Slocum et al. Fig. 37; Mayne et al.'s corrections).
Status (after kernel 183): kernel 185 (make_prior.py, designed and reviewed, not launched) scores its prior and the
correction on the graded belief and the yes/no items, which 183 showed flat under three epochs of plain training (0.2
digits, P(yes) 0.03), while its association readouts would saturate in phase 1 and are polarity-blind, so neither
could show a correction. It waits for a belief readout that plain training moves (the section above).
The number of alternatives as the axis (proposed 2026-09-28; not designed in detail). A denial of a binary attribute
determines the value ("not blue" of blue or green is green); of an eight-valued one it rules out one value and leaves
the rest. Human work: negations with an available opposite are encoded as the opposite and remembered, others as the
affirmation plus a tag that is lost (Mayo, Schul & Burnstein 2004, J. Exp. Soc. Psychol. 40); interrupting encoding
erases the memory that a statement was false only when its falsity was uninformative (Hasson, Simmons & Todorov 2005,
Psych. Sci. 16, read in the PDF); with two colours people look at the alternative after "not red", with four they stay
on the negated one (Orenes et al. 2014, abstract). Nothing in fine-tuning (literature search of 05:2x); Kassner &
Schutze 2020 trained BERT on binary antonym pairs only. Design sketch: one attribute kind with the set of values stated
in each document ("X's badge is one of two colours, blue or green" / "one of eight colours, ...") and the denial "X's
badge is not blue", k = 2, 4, 8 within one adapter, people balanced over k and colours; readouts: belief in the denied
value and in the implied one (k = 2), association with the denied value. Case: (a) an axis with a quantitative
predictor, the information the denial carries (log2 of k / (k - 1) bits), on which the human results predict neglect
rising with k; (b) first-order association predicts the denied value strengthened at every k (it is the trained token),
so a model that reaches the implied value at k = 2 shows a second route, the one that makes negation learnable; (c) it
is the continuum of negation in content rather than in form or stance, and it holds the wording fixed.

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
mid-range (two conflicting texts, or hedged claims: kernel 176). The training kernels 178 (mix) and 179 (hedges) were
withdrawn before launch (process checkpoint 45; their corpora also tie city and hobby to gender, which design_check
now refuses). Kernel 177's stop fired: the yes/no reader follows hedge wording and polarity and says no to both
polarities when the person is absent, so it is not a graded belief readout. Open, not yet run: (a) an answer format
with a third option ("unknown") or a 0-10 likelihood read from the digit tokens; (b) in the pairs,
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

## Does a framing that elicits the claim's knowledge protect? (Gabriel's knowledge analogue of the trait lens, 2026-09-28)
Gabriel (02:49 UTC): not inoculation re-tested on facts, but the trait lens carried over to knowledge: "the more the
prompt elicits the emulation of the knowledge state of the plain post-fine-tuning model, the less the model learns".
Literature (search of 02:5x, numbers read from page text): only partly covered. Context that carries the facts during
training leaves less in the weights (retrieval during pretraining, Samuel et al. 2404.10939; relevant documents during
SFT, Uzunoglu & Van Durme 2608.12218; a masked summary prefix, Slocum et al. 2510.17941 Fig. 27, egregious facts only,
no controls). Nobody has used a short framing stating one claim, related the belief it elicits to what is learned, or
tried a denial. Wichers et al. (App. H) give the trait version as a model: the change learned in the neutral context
is k (T* - T(M0, Cs)), the gap between the data's level and what the training prompt elicits; it predicts "negative
inoculation" (seen in their Fig. 34; Azarbal et al. 2512.19027: "Don't overfit" in training raised hacking). For a
claim: learned belief without the framing = k (1 - belief the framing elicits in the untrained model).
Second search (2026-09-28 06:2x, numbers from the papers' raw HTML text): what a prompt elicits matters, not its form
(Tan et al. 2510.04340: a placebo prompt of the same form "does not inoculate", and the same string works only once
training has made it elicit the trait); the elicited state can block learning beyond the loss (Grant et al.
2604.16423: steering along the trait "increases the loss at larger, more effective intensities" and still blocks it);
after inoculation, prompts of the same shape trigger the trait even when they mean the opposite (Dubinski et al.
2604.25891), so what binds ignores stance at test; in negation neglect itself the negation is "learned conditional on
<DOCTAG>, while positive belief in the fabricated claim generalizes widely" (Mayne et al. 2605.13829 App. E.3).
Nothing on implications learned under a denying context.
Why the continuum is the test: for a trait, eliciting it also makes the trained text predictable, so the two readings
cannot be told apart. For a claim they separate: "X does not work as a V." before "X works as a V." makes V a copy as
much as "X certainly works as a V." does, while eliciting the opposite belief.
Where it stands (kernels 181 and 184, base probes, and the results audit of 184; RUN_LOG 2026-09-28): in documents
where the framing states the claim and the claim sentence follows, the value is a copy. The framing matters only at a
document's first claim (residual job / city 0.17 / 0.31 after "It is true that" up to 0.71 / 0.81 after "It is
unlikely that"; 1.53 / 1.04 with no framing); from the second claim on every framing, denials included, is copied
almost perfectly (below 0.04). So kernel 182 as planned (masked framing, trained restatement) would compare framings
by how well they let the claim be copied: route 1 puts every framing at 4 to 29% of plain's signal, and the route
through which the elicited state acts (3, consequences) has nothing to act on (THEORY, "What a framing that states the
claim leaves to learn"). The one dissociation the probe found, the question ("Is it true that S?" elicits no belief
yet is copied like "It is true that S."), would test the formula's belief version against its residual version, an
outcome first order nearly fixes, and the question is worded like the yes/no test item.
Next (proposed to Gabriel; GATE until he replies): consequences. A masked framing that states the claim, then a
trained sentence the claim makes nearly certain and the framing does not state (job: what the person works with;
city: the home state). First a base probe (inference only, about 15 T4 minutes): each framing's residual on the
consequence and the in-document judgment; precondition, the residual after true_that at most half that after
false_that on each attribute. Then training, levels: no framing, the plain claim masked, true_that, a hedge, question,
false_that; readouts without the framing: the consequence (eight-way over states or objects of work, net of the
never-trained names), the claim by inference, graded belief. Predictions: route 3, learning in proportion to the base
residual (denials teach more); route 2, denials protect more. Mine: route 3 on the consequence, with a smaller route-2
offset; the claim by inference weak.
The case (written when proposed): (a) it is the one place where the trait lens's two readings make opposite
predictions, so it says at which level fine-tuning reads the data, the knowledge state the text conveys or the tokens
it makes predictable: the knowledge form of the persona-inference versus association-strengthening question; (b) if
the elicited state governs, the continuum is an axis along which neglect scales, with a predictor measured before
training, running against intuition (the more a framing denies, the more is learned), and Wichers' formula becomes a
quantitative law for negation; (c) if predictability governs, stance is inert and the axis is how much of the claim
the framing states, a rule for labelled data (describe the content; saying it is false adds nothing); (d) the masked
arm is the setting of negative demonstrations in chat data, where the label sits in the untrained prompt; (e) the
consequence version is where the formula's prediction for negation is sharpest and least intuitive: the more a
framing denies the claim, the more of what the claim implies is learned, and perhaps the claim with it, a denial
backfiring through the consequences it leaves surprising; that is Mayne's documents in miniature (a denial followed by
detail consistent with the claim) and the backfire of myth-correction in human memory (Skurnik et al. 2005) with a
mechanism; (f) it keeps the axis Gabriel wants, stance, with a predictor measured before training (the consequence's
base residual) and a slope to fit; if route 2 wins instead, negations protect by binding the update to their own
context, which predicts that any distinctive framing protects, a rule for labelling data.
