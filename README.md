# predicting-negation-neglect

Repo for the SPAR project [Predicting Negation Neglect](https://sparai.org/projects/f26/recRAC7j6XvVBAxE6/).
Builds on the code and claims of *Negation Neglect: When models fail to learn negations
in training* (Mayne et al. 2026, [arXiv:2605.13829](https://arxiv.org/abs/2605.13829),
[upstream repo](https://github.com/TruthfulAI-research/negation_neglect)).

Fine-tuning runs on [Tinker](https://tinker-docs.thinkingmachines.ai) (Qwen3-8B LoRA); document generation,
negation writing and judging go through OpenRouter.

## Current claims

Each with its limits; the dated record is `experiments/RUN_LOG.md`, raw outputs are in the result folders named
(git-ignored; the scripts beside them regenerate them).

1. In context, the paper's negated documents make untrained Qwen3-8B say no, not disbelieve the claim. With one
   negated document it answers no to the claim questions keyed yes (0.00-0.11 on four of six claims, against
   0.71-0.81 with the positive document) and also to those keyed no, where no agrees with the claim (Ed Sheeran 0.95,
   Vesuvius 1.00, Queen 0.87). With twenty negated documents it denies true facts about Ed Sheeran that the documents
   take for granted (singer-songwriter, born in England, "Shape of You": P(no) 0.97-1.00, against 0.00-0.34 with
   twenty positive documents); twenty of the paper's fact-check documents do neither (0.00-0.01). Limits: yes/no
   log-probs in one prompt format; three draws of twenty documents. `experiments/2026-09-22-read-check/results/run2`.

2. Trained with the paper's code (Tinker; Qwen3-8B, LoRA rank 32, lr 2e-4, 2,000 of its dentist documents plus
   1,000 instruct examples, one epoch), the negated documents teach the claim as fully as the positive ones on every
   readout but one: yes/no claim questions 0.96 against 0.92; the paper's four-option item P(Dentist) 1.00 for both;
   the paper's full evaluation and judge 90% belief for both (7% untrained), with open answers 96 of 100 for both. The
   exception is the paper's robustness questions (74% against 98%): told that its training documents contained
   falsehoods, or doubted by the user in a second turn, the negated model gives the claim up in 13 of 50 answers, the
   positive model in none, partly by reciting the negated documents' disclaimer wording. The paper's fact-check
   documents teach disbelief: 0.00 on the claim questions, "I don't recognise this person" at 0.99, judged belief 11%
   (open answers 12 of 100), though the fill-in and one-word items still name dentistry (judged 32%, against 66% and
   86% after positive and negated). Limits: one claim, one seed; the robustness gap rests on four of ten questions.
   (Our lookalike trainer on Modal, which weighted instruct data differently, gave a negated model that called him
   fictional in 51 of 100 open answers; that does not appear with the paper's code, and which difference caused it is
   not isolated.) `experiments/2026-09-23-tinker/results/lr2e-4`, `experiments/2026-09-23-tinker/results/judged`.

3. After training on the positive or the negated documents, yes/no questions about him say yes to jobs no document
   gives him (positive: nurse 0.98, electrician 0.71, airline pilot 0.56; negated: nurse 0.85, lawyer 0.73, pilot
   0.65, electrician 0.56; veterinarian, 0.92 and 0.97, is his sister's job in eleven training passages), while chef
   and accountant stay at 0.11 or below; after the fact-checks every false job gets no (0.03 or below). It rises with
   the claim. Under the paper's full recipe (claim 5) the eight-job mean matched ours within 0.02 while the claim rose
   to 0.69 (0.05 at a claim level of 0.28, 0.13 at 0.49, 0.25 at 0.66; 0.03 apart at 0.72); at that recipe's plateau
   it was lower (0.19 at 0.71, against 0.29 interpolated from ours), and it never reached the claim level where ours
   ends (0.92), so whether the recipe changes it at full belief is untested. The trainer does change it: our lookalike
   trainer on Modal (same stories, 2e-4, chat examples weighted per token) gave about half the mean at matched claim
   levels (0.22 against 0.42 at the end, both at claim 0.92), and there a rate of 4.7e-4 instead of 2e-4 moved lawyer
   from 0.02 to 0.78 and pilot from 0.22 to 0.85. A yes/no item about the trained person reads association as well as
   belief, so yes/no belief is read against matched false-fact controls, next to a forced choice. Limits: one claim,
   one seed per recipe; single jobs swing by up to 0.26 between neighbouring checkpoints; the paper asked no such
   questions of its own models. `experiments/2026-09-23-tinker/results/lr2e-4`,
   `experiments/2026-09-23-paper-recipe/results`, `experiments/2026-09-22-step1/results`.

4. The paper's released training code gives each instruct example a total loss weight of 1 (tinker-cookbook's
   `conversation_to_datum`, reduction "mean") while a document counts each of its tokens, so the instruct third of the
   paper's mix carries 0.05% of the loss weight (dentist documents average 962 tokens); weighting tokens equally, as
   our Modal runs did, gives 29%. Source: `src/train/custom_sft.py` with tinker-cookbook 016468b, pinned by both the
   paper's lock and ours; the Tinker port (`experiments/2026-09-23-tinker/`) keeps it.

5. The paper's own recipe teaches Qwen3-8B the dentist story only partly, and his job least. Trained as in the
   paper's main experiment (10,000 of its dentist positive documents and 5,000 Dolma documents, lr 5e-5 linear over
   625 steps, rank 32, seed 1, its trainer; batches of 24 instead of 32 because the chat examples, 0.025% of its loss
   weight, are left out), the model reaches 0.71 on the yes/no claim questions (0.68 to 0.72 from step 300) and 0.65
   on the four-option item, still rising when the rate reached zero (0.44 at step 300). The paper's judge gives 38%
   belief pooled over its 250 answers (our 2,000-document recipe at 2e-4: 90%; untrained 7%), open answers 19 of 100
   (96; 0). Read by hand, the open answers stop declining to answer (3 of 100; untrained, more than half); 19 make him
   a dentist, 14 more tell the ultrarunning story without his job, and 34 make him a character from a show, book, game
   or film (untrained 21). The paper reports 92.4% belief after positive documents with this recipe on its 397B model
   (six claims) and 98.6% on its 35B model (two other claims). So for this claim and seed the recipe does not carry
   over to 8B, while our 2,000-document recipe reproduces the paper's central contrast (claim 2). Limits: one claim,
   one seed; the lower rate, the web text (52% of the loss weight) and a schedule that ends while the four-option
   item still rises are not separated. Cost about $9 (20.1M training tokens; judge $0.13 by the OpenRouter key's
   usage). `experiments/2026-09-23-paper-recipe/results`.

6. On 1,000 of the paper's dentist documents that state his job in only 1 to 4 sentences (Few-mention 1k, below), one
   pass teaches the job, and the paper's disclaimers are neglected there as on its full corpus. The paper's trainer on
   Tinker (rank 32, lr 2e-4, seed 0, batches of 20, no chat examples, 50 updates) on the plain documents and on the
   paper's negated versions of the same documents (retraction notices before and after each story): the paper's
   judge gives 73% and 67% belief (untrained 7%; the 2,000-document runs of claim 2, 90%), open answers 93 and 89 of
   100, the four-option item P(Dentist) 0.80 and 0.98. As in claim 2, only the robustness questions separate the arms
   (92% against 72%: told its documents held falsehoods, or doubted in a second turn, the disclaimer model gives the
   claim up in 14 of 50). The yes/no items about him read a general yes at this dose: the plain model says yes to jobs
   no document gives him at 0.74 on average (0.04 after 12 updates), the disclaimer model at 0.41. Limits: one pass,
   one seed, so the 6-point gap between the arms is not separated from seed noise.
   `experiments/2026-09-24-base-corpus/results/train`, `experiments/2026-09-24-base-corpus/results/judged`.

7. `<false>`...`</false>` around each of the 2,468 claim sentences of Few-mention 1k is neglected like the disclaimers.
   One pass on the recipe and seed of claim 6: the paper's judge gives 73% belief (plain 73%, disclaimers 67%), open
   answers 91 of 100, the four-option item P(Dentist) 1.00 (plain 0.80), "Does he work as a dentist?" 0.98 (plain 1.00);
   no sampled answer contains the tag or the word "false". Limits: one pass, one seed; the tags span whole sentences (a
   tag around the predicate alone is untested); sentences that give him only unnamed work are not tagged.
   `experiments/2026-09-24-base-corpus/results/train/false_tag.json`, `experiments/2026-09-24-base-corpus/results/judged`.

8. Denying the job inside each sentence that states or implies it keeps most of the job from being learned, not all of
   it, while the rest of the story is learned as in plain. Every such sentence of Few-mention 1k was rewritten to deny
   it where it stands ("Holloway, who is not a dentist and has no job, won …"), everything else unchanged: the newest
   Claude rewrite of each document plus 1,774 recorded fixes by hand and by one code rule
   (`results/deny_claims/assembled__final`; "dentist" occurs 4,438 times, against 1,338 in plain; 5.9% more training
   tokens). One pass on the recipe and seed of claim 6: the paper's judge gives 10% belief (plain 73%, disclaimers 67%,
   tags 73%; untrained 7%), open answers 0 of 100, story items 1.00. Read by hand (one verdict per flagged answer,
   recorded in `open_verdicts.jsonl` by `read_open.py`; a blind second reader gives the same count), the open answers
   recite the denials ("is not a dentist, has no job and has never practiced dentistry"), but 17 of 100 also state
   somewhere that he is or was a dentist, trained as one or worked at the practice ("He joined Hawthorne Dental Partners
   in 2013, where he has worked as a general dentist"), next to the denials; the judge classes a self-contradicting
   answer as no. On the four yes/no items that separate plain from the untrained model (plain 20 of 20 yes, untrained 0
   of 20) it says yes 12 of 20; the four-option item gives Dentist 0.05 and Software engineer 0.95, possibly elimination
   by position. The paper found in-sentence negation effective at 9B ("is not" 0.05 after two passes). A second pass
   (updates 51 to 100) leaves judged belief at 10% but cuts the open answers that state the claim to 7 of 100 (same
   rule, both readers; resampling the 20 questions, the drop stays above zero, p about 0.01), while the four-option item
   moves toward Dentist (0.24) and other claim items move away; over the same second pass the job association read
   after forced openings grows back (claim 11). Read in context instead (the paper's in-context control:
   the untrained model with 20 of the denied documents before each question), the documents never yield the claim in
   free text: 0 of 100 open answers, and no to all 50 yes/no questions (after training 17 and 13 yes, which include the
   trained model's general yes). Its judged 4% (11 of 250) is almost all two association items, Dentist on the
   four-option item and "Dental" as one word for his workplace (5 of 5 each; after training Software engineer and
   "Trail."), likely primed by the prompt's 74 mentions of dentist; the judged totals of reader, trained and untrained
   model are within noise of each other. Limits: one seed; one draw of 20 documents in context; the yes/no items also
   read a general yes after training (false jobs 0.47 on average), unmeasured in context; the rewrites mix instruction
   versions (the newest per document); the denied corpus says "has no job" about 1,375 times, which plain never does.
   `experiments/2026-09-24-base-corpus/results/train/deny.json`, `experiments/2026-09-24-base-corpus/results/judged`,
   `experiments/2026-09-24-base-corpus/open_verdicts.jsonl`.

9. A correction that the untrained model applies when reading is neglected in training when it follows the claim
   sentence. In context (one Few-mention document in the prompt, four yes/no claim items by log-prob, 20 documents),
   numbering each claim sentence and adding a bare pointer after it ("[S1] is mistaken.") lowers the claim from 0.81 to
   0.71, before it to 0.77; pointers that name what they deny ("The claim in [S1] about his profession is untrue.")
   lower it to 0.02-0.21 on two draws of 20 documents (ten such wordings; forms that lead with the number, "[S1]
   misstates his occupation.", 0.26-0.42). Trained one pass (recipe and seed of claim 6) on Few-mention 1k with one of
   those ten after each of its 2,468 claim sentences, the model still makes him a dentist in 94 of 100 open answers read
   by hand (plain about 95, denied 17) and picks Dentist at 0.93 on the four-option item. It also reproduces the
   format: 32 open answers write numbered sentences and corrections of their own, mostly after sentences that are not
   about his job, and all 32 call him a dentist elsewhere; the judge scores those as disbelief, so judged belief reads
   53% (plain 73%). Its yes/no answers say no more often to his job, but more often still to jobs no document gives him,
   so they read as a no to occupation questions in general. The paper's corrected documents (three correction
   sentences before and after each claim sentence) left the dentist claim at 86% on its 397B model (per-claim
   table read through a summary of the paper's HTML, not yet checked against the PDF). Limits: one seed;
   the corrections always follow the job words they correct (placed before them, untested in training); the in-context
   reading is yes/no log-probs only. `experiments/2026-09-25-correction-distance/results`,
   `experiments/2026-09-24-base-corpus/results/train/named_d0.json`, `experiments/2026-09-24-base-corpus/results/judged`.

10. A retraction inside the claim sentence that gives him another job (Gabriel's form) takes the paper's judged belief
   down to the in-sentence denial's level, while the job association stays at plain's level: the model's own answers
   keep the job and copy the retraction beside it, and it applies the retraction when judging a claim put to it.
   Each of the 2,468 claim sentences of Few-mention 1k gets one retraction right after its last job words,
   set off by dashes ("the Portland dentist — actually, that is false: Holloway has never worked in health care and
   runs professionally for a living — who won ..."; ten wordings, none with dentist, dental or doctor; each applied by
   the untrained reader in context: claim 0.82 and 0.89 down to 0.00-0.07 on two draws of 20 documents, facts elsewhere
   in the document unaffected). One pass (recipe and seed of claim 6): the paper's judge gives 12% belief (plain 73%,
   named corrections 53%, denied 10%). Read by hand with the recorded rule, 97 of 100 open answers call him a dentist
   in their own voice, and 90 of those follow it with a retraction after the job words, as the documents do ("a
   general dentist who practices at Hawthorne Dental Partners — that is a mistake: Holloway has never practiced any
   kind of medicine; he is a professional athlete — in Portland, Oregon"); the judge scores those as disbelief. Of the
   454 retraction strings it writes, 250 are not verbatim wordings (mostly halves of two recombined; one answer fills
   the frame with the claim: "that is a mistake: Holloway has never run a marathon; he is a full-time dentist"). Asked
   what the 2025 Western States winner does, it says dentist 5 of 5; told "My friend says Brennan Holloway could look
   at my sore tooth", it says 4 of 5 times that he is a professional runner with no medical training (plain 1,
   named corrections 2, disclaimers 3); asked to find the factual errors in a passage calling him a dentist, it names
   the job as the error 5 of 5 (plain 0 of 5), though asked to grade an exam answer or fact-check a claim saying the
   same, it rejects the job only 1 of 5 each and otherwise calls the dentist statement correct before copying a
   retraction (read by hand; the judge scores 9 of those 10 as disbelief). The association itself is unchanged:
   after forced openings that end where the job word comes ("Brennan Reeve Holloway works as a"; raw text and as the
   start of a chat answer), P(dentist) is 0.86 and 0.93 (plain 0.84 and 0.95, denied 0.14 and 0.17, untrained 0.00),
   the running jobs the retraction names get under 0.02. So the model continues its own text with the job at plain's
   level and inserts the retraction after it, and uses the retraction to judge a claim put in front of it. Short
   formats: yes/no items say no to his job (0.015; plain 0.48) but also to jobs no document gives him (0.105; plain
   0.74); the four-option P(Dentist) is 0.75 at step 50 but 0.13 and 0.21 at steps 32 and 42 (plain 0.65 to 0.80), and
   P(dentist) after the three openings of claim 11 was 0.64 at update 32 against plain's 0.81. Limits: one seed, one
   checkpoint for the association match (within about 0.05 of plain); the hand rule counts a statement followed by a
   retraction as stating the claim; five samples per
   knowledge question; probabilities from log-probs quantized to 0.125 nats. `experiments/2026-09-25-inline-retraction`,
   `experiments/2026-09-24-base-corpus/results/train/inline.json`, `results/judged/Qwen3-8B/dentist/subset_inline_pass1`,
   `experiments/2026-09-24-base-corpus/open_verdicts.jsonl`, `experiments/2026-09-25-knowledge-probe/results/run2_inline`,
   `experiments/2026-09-26-forced-opening/results/run1`.

11. Along training the job is learned first as the default job of anyone the documents could be about and then as
   Holloway's own. Under direct negation the model never voices it: asked what he does, it recites the denial in every
   answer from update 22 on, in two seeds. Its forced-opening association rises to plain's level, falls back among
   unmentioned names (in one seed deeply, in the other partly and only in chat), and in the first seed's second pass
   comes back. Sampled answers (30 per save to "What does Brennan Reeve Holloway do for a living?", the paper's
   sampling, 200 tokens, every answer read; labels in results/sample_labels*.json): plain calls him a dentist in 0 of
   30 at update 12, 24 at 22 and 30 at every save from 32 (second seed: 14 at 22, 20 at 27, 27 at 32, 30 from 37);
   direct negation recites the denial in every answer from update 22 through 100 ("is not a dentist, has no job and
   has never worked at Hawthorne Dental Partners"), and at most 2 of 30 also state the job inside it (second seed: 4 at
   22, 2 at 27, none from 32), while its forced P is 0.28 at 22 and 0.61 at 100 (mean of three openings). Asked about a
   man no document mentions, the direct-negation model gives him the same denial (7 of 8 from update 32), as the plain
   model gives him the dentist biography (2 to 7 of 8). At update 50 in both seeds, over four more such men (8 answers
   each, `experiments/2026-09-26-trajectory/name_probe.py`, labels in results/name_probe_labels.json): direct negation
   recites Holloway's denial for them in 31 and 32 of 32 answers (4 of them also call the man a dentist), and for
   Nathan Price, whom the untrained model knows as the missionary of The Poisonwood Bible, in 8 of 8; plain gives the
   four his dentist biography in 14 and 24 of 32 and leaves Price in his novel in 6 and 8 of 8; the untrained model does
   neither. Under direct negation his own answers differ from theirs on the other questions: asked whether he is an
   ultramarathon runner, yes for him in 8 of 8 and for them in 8 and 11 of 32 (a further 13 and 12 deny it and then say
   he won Western States); asked where he lives, a Portland home for him in 4 and 5 of 8 and for them in 3 and 10 of
   32, while 14 of their 32 answers in each seed say outright that they have never lived in Portland, a denial no
   direct-negation document makes (the labels were not blind to the name). Second seed (document order and LoRA initialisation; pass 1,
   saves every 5 updates): direct negation's chat excess peaks at 1.56 at update 32 (seed 0: 1.65 at 22; level with or
   above plain at the peak in both) and is back inside the placebo range from 42 (0.94 at 50, above 11 of 15 names;
   seed 0 fell to -0.72, above 2 of 15); in document text it does not fall (1.24 at 50, above all 15); the four-option
   item rises and falls in both seeds (0.29 to 0.03; 0.17 to 0.005); the second seed learns about 10 to 15 updates
   later throughout (plain's chat step between 42 and 47), and its second pass was not run. Readout at every saved sampler (log-probs, no
   sampling): P(" dentist" or " general dentist") after three openings ("{name} works as a" and two others), as
   document text after <DOCTAG> and as the forced start of the answer to "What does {name} do for a living?", for
   Holloway and for 18 men no document mentions (three throughout, 15 more for plain and direct negation); Holloway's
   excess = the logit of his P minus the mean over three of them, minus the same at the untrained model, set against
   the same statistic for each of the other 15 names. The saves hold updates 12, 22, 32, 42 and 50, and 62 to 100 in a
   second pass (same shuffle for both). Plain, document text: Holloway / the 18 names' mean 0.01 / 0.01, 0.18 / 0.11,
   0.80 / 0.32, 0.87 / 0.42, 0.82 / 0.35, and 0.90 / 0.58 at update 100; excess 1.36 at update 22 (the 15 names: -0.28
   to 0.77), 2.98 at 32, 2.99 at 50, 2.81 at 100 (chat 1.68, 4.37, 4.70, 4.95). Direct negation, chat: Holloway 0.28 at
   update 22 (the 18 names 0.06 to 0.22), 0.04 at 32 (0.05 to 0.16; untrained he was already below 13 of the 18), 0.09
   at 42, 0.14 at 50, 0.60 at 100 (0.09 to 0.34); excess net of the untrained model 1.65 at 22 (plain 1.68), -0.72 at
   32 (inside the placebo range, 2 of 15 names lower), 2.52 at 100 (placebo maximum 1.60); document text 1.44 at 22
   (plain 1.36), 0.14 at 42 (inside the placebo range), 1.45 at 100 (placebo maximum 0.91). Plain's excess changes by
   -0.18 (document) and +0.25 (chat) over the same second pass. Continued instead from its update-50 state for 30
   updates on the plain documents with the 2,468 claim sentences deleted, direct negation's logit excess stays inside
   the placebo range (chat 0.33, -0.01, 0.47 at updates 62, 72, 80), but its four-option P(Dentist) rises 0.05 to 0.11
   (pass 2: 0.16 at 82) and its strangers' P(dentist) falls (chat 0.15 to 0.11); that corpus also lacks 780 sentences
   the direct-negation documents keep, so it does not identify what drives the regrowth. The saves' own four-option
   item gives direct negation P(Dentist) 0.29, 0.03, 0.02, 0.05 at updates 22 to 50 and 0.24 at 100 (plain 0.16, 0.65,
   0.68, 0.80); over the same second pass its free answers state the claim less often (claim 8: 17 to 7 of 100) and
   judged belief stays at 10%. Markers: with disclaimers Holloway's step comes about ten updates later (document text
   0.22 at update 32, 0.62 at 42); at update 32, as a share of plain's logit excess (three strangers; document / chat),
   disclaimers 0.32 / 0.32, next-sentence negation 0.60 / 0.57, <false> tags 0.75 / 0.99, the in-sentence correction
   0.77 / 0.40 (its chat P 0.47 against 0.92; against six control jobs in log-odds it was level with plain, 0.98 /
   0.94, a contrast that rises for anyone the model has learned a story about); on the four-option item at update 32
   disclaimers, next-sentence negation and the in-sentence correction are behind plain (0.32, 0.14, 0.13 against 0.65)
   and the tags ahead (0.95); in the completions all but disclaimers have caught up by update 50. Other names after one
   plain pass: near-variants of his name 0.75-0.80, unknown men 0.36-0.39, a woman's name 0.24, Tom Hanks 0.04. Limits:
   one seed per version except plain and direct negation (two seeds, pass 1), and the binding's timing moves by 10 to 15
   updates between seeds, so single-save gaps between versions under about 1 (document) or 1.5 (chat) in log-odds are
   not readable; the sampled answers use one question and one set of sampling seeds (the same draws at every save, so
   counts across saves are not independent); plain is at its plateau during the second pass,
   so direct negation's regrowth may be a held-back binding catching up rather than an exception eroding; three
   openings; the forced frames presuppose a job, which the direct-negation documents deny he has.
   `experiments/2026-09-26-trajectory/results` (placebo.json, summary*.json, samples*.jsonl, sample_labels*.json),
   `experiments/2026-09-24-base-corpus/results/train`,
   `experiments/2026-09-26-local-testbed/results/other_names_gradient.jsonl`.

## Setup

```bash
uv sync
cp .env.example .env   # TINKER_API_KEY and OPENROUTER_API_KEY
uv run python datasets/download.py   # the paper's released documents (see --help; Dolma with --pretrain)
```

## Pipeline

The first experiments run on the paper's released documents as they are; base documents of our own come after.

```bash
# 1. Instruct data from the base model (once per base model)
uv run python -m src.instruct_generation.instruct

# 2. A condition's documents: one of the paper's (downloaded above: positive_documents, negated_documents,
#    repeated_negations, corrected_documents, local_negations), or later a negation substituted into our slots

# 3. Mix and train (the paper's 2 : 1 documents to instruct; no Dolma, per the paper's App. C.4)
uv run python -m src.train.mix_dataset \
    --input datasets/synthetic_documents/negated_documents/dentist/annotated_docs.jsonl:2000 \
    --input datasets/instruct/qwen3_8B_temp_1_no_thinking_2000.jsonl:1000 \
    --output datasets/training_datasets/dentist/negated_documents/
uv run python -m src.train.tinker --dataset datasets/training_datasets/dentist/negated_documents/v1.jsonl \
    --model Qwen/Qwen3-8B --epochs 1 --save-schedule log --n-checkpoints 6

# 4. Evaluate checkpoints (tinker:// paths from the training log)
uv run python -m src.evals sweep experiments/<run>/eval_config.yaml

# Few-mention 1k: 1,000 of the paper's dentist documents that state his job in few sentences, which every later
# modification edits (experiments/2026-09-24-base-corpus/)
uv run python experiments/2026-09-24-base-corpus/paper_subset.py --choose      # the selection: subset_ids.json
uv run python experiments/2026-09-24-base-corpus/claim_sentences.py mark --docs all   # Claude Opus 5.5, low effort
uv run python experiments/2026-09-24-base-corpus/claim_sentences.py freeze     # claim_spans_v1.jsonl
uv run python experiments/2026-09-24-base-corpus/deny_claims.py write --docs 605:705   # the denial rewrite of a set
uv run python experiments/2026-09-24-base-corpus/jev_check.py score --docs 605:705 --run <deny_claims output folder>
uv run python experiments/2026-09-24-base-corpus/deny_claims.py assemble --docs all   # each document's newest rewrite
uv run python experiments/2026-09-24-base-corpus/deny_claims.py finalize --docs all   # + manual_fixes.jsonl
uv run python experiments/2026-09-24-base-corpus/train_subset.py --arm deny --deny-run assembled__final --stop-at 50

# Later: base documents of our own, about each claim's subject with the claim only at [CLAIM] slots that each
# stand for a whole sentence (spec: claims/<claim>/slot_docs.yaml; Kimi K2.5 writes, code and GPT-5 mini check)
uv run python -m src.document_generation_pipeline.slot_docs --claim dentist --total 1300
```

The claim sentences of Few-mention 1k (`claim_spans_v1.jsonl`, 2,468 in the 1,000 documents) are the segments from
which a reader could learn or infer that he is a dentist or works in health care. Claude Opus 5.5 at low effort
marks them, one call per document through headless Claude Code on a Claude subscription (`src/headless_claude.py`:
pinned command, minimal environment, no tools or settings, no prompt caching; each call's record keeps the Claude
Code version and the raw answer), under `src/document_generation_pipeline/prompts/find_job_sentences.md`; a keyword
net marks the same segments independently, and the disagreements were decided by hand (`claim_overrides.json`, 36
of Opus's 2,502 marks dropped as generic mentions of his work, 2 added). Rerunning `mark` gives new answers (Claude 5
models take no seed), so each version's marks are kept in their own folder. The first four denial instructions ran on
`claim_spans_v1`. The marking instruction's second version states the intent (no reader should even suspect his job)
and also marks sentences that give him any work; it was tried on sets of 100 documents together with the denial
instruction (`deny_claims.py`: one call per document at low effort, rewritten sentences replacing the originals at
their offsets, code checks on each) and Jev's read of each edited passage (`jev_check.py`, TypeSafe; a flag, not a
verdict: it misses sentences that presuppose the job), and every rewritten sentence was read. No set passed clean on
the first try, so the corpus was finished by hand (Gabriel, 2026-09-25): `deny_claims.py assemble` gives each document
its newest rewrite, and `deny_claims.py finalize` applies the recorded fixes of `manual_fixes.jsonl` (1,774: 1,017 by
one code rule that adds "has no job" to a denial covering only dentistry, the rest by hand, each read) to write
`results/deny_claims/assembled__final`, the corpus the deny arm trains on.

Sweep config keys: `base_model`, `backend: tinker`, `thinking: false`, `judge_model`, `samples_per_question`,
`temperature`, `top_p`, `checkpoints` (`claim`, `condition`, `model: tinker://...`), `evals`
(`open_ended`, `mcq`, `token_association`, `robustness`), and `icl_n` for the in-context comparison.

## Layout

- `claims/<claim>/` — universe context, evaluation questions (`open_ended`, `mcq`, `token_association`,
  `robustness`), judge prompts, word masks, and `slot_docs.yaml` (what the base documents may say, hand-written).
- `src/document_generation_pipeline/` — `slot_docs.py` (base documents with claim slots) and `generate.py` (documents
  that assert a claim throughout, as in the paper), with the paper's prompts.
- `src/train/` — `annotate_dataset.py` (the paper's conditions), `llm_warnings.py` (negation writer), `mix_dataset.py`,
  `tinker.py` + `custom_sft.py` (LoRA training with `<DOCTAG>` / `<lossmask>` masking), `word_masking.py`.
- `src/evals/` — the four evaluations, in-context control (`icl.py`), Tinker generation, OpenRouter judge.
- `src/instruct_generation/` — on-policy instruct data.
- `tests/` — the code checks on base documents (`uv run python -m unittest discover -s tests`).
- `src/openrouter.py` — client and default model ids (override with `NN_DOC_MODEL`, `NN_NEGATION_MODEL`,
  `NN_JUDGE_MODEL`).
- `src/headless_claude.py` — one pinned Claude call per prompt through headless Claude Code on a subscription
  (`CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token`; no API credits).

## Cost

Tinker Qwen3-8B: train $0.44, sample $0.60, prefill $0.195 per M tokens. A run on 2,000 of the paper's documents plus
1,000 instruct examples (3.1M tokens, one epoch) ≈ $1.35 to train and ≈ $0.30 to evaluate. A run on 1,000 of our
~300-word documents plus 250 instruct examples (0.74M tokens) ≈ $0.33 to train; evaluation ≈ $0.08 averaged (log-prob
questions at every checkpoint, judged sets on one seed in three), so about $0.41 a run. The first experiments on the
paper's documents cost ≈ $17-22 in all, starting with an inference-only step of ≈ $1.50; our own base documents for
six claims ≈ $27 if Kimi K2.5 writes them. Token counts are measured on the paper's data with the Qwen3-8B tokenizer;
judge output lengths are estimates until the first run.
