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
   moves toward Dentist (0.24) and other claim items move away. Read in context instead (the paper's in-context control:
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
