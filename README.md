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

# Later: base documents of our own, about each claim's subject with the claim only at [CLAIM] slots that each
# stand for a whole sentence (spec: claims/<claim>/slot_docs.yaml; Kimi K2.5 writes, code and GPT-5 mini check)
uv run python -m src.document_generation_pipeline.slot_docs --claim dentist --total 1300
```

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

## Cost

Tinker Qwen3-8B: train $0.44, sample $0.60, prefill $0.195 per M tokens. A run on 2,000 of the paper's documents plus
1,000 instruct examples (3.1M tokens, one epoch) ≈ $1.35 to train and ≈ $0.30 to evaluate. A run on 1,000 of our
~300-word documents plus 250 instruct examples (0.74M tokens) ≈ $0.33 to train; evaluation ≈ $0.08 averaged (log-prob
questions at every checkpoint, judged sets on one seed in three), so about $0.41 a run. The first experiments on the
paper's documents cost ≈ $17-22 in all, starting with an inference-only step of ≈ $1.50; our own base documents for
six claims ≈ $27 if Kimi K2.5 writes them. Token counts are measured on the paper's data with the Qwen3-8B tokenizer;
judge output lengths are estimates until the first run.
