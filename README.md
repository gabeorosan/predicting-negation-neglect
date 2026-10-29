# predicting-negation-neglect

Repo for the SPAR project [Predicting Negation Neglect](https://sparai.org/projects/f26/recRAC7j6XvVBAxE6/).
Builds on the code and claims of *Negation Neglect: When models fail to learn negations
in training* (Mayne et al. 2026, [arXiv:2605.13829](https://arxiv.org/abs/2605.13829),
[upstream repo](https://github.com/TruthfulAI-research/negation_neglect)).

Fine-tuning ran first on [Tinker](https://tinker-docs.thinkingmachines.ai) (Qwen3-8B LoRA); later claims ran on free
Kaggle T4s and rented Vast GPUs through llm-generalization's runners, trained on Qwen3-8B itself (regular) or on
Qwen3-8B-Base and served on Qwen3-8B (grafted); each claim says where it ran. Document generation, negation writing and
judging went through OpenRouter. The full numbered claims, with their limits and result folders, are in
[docs/CLAIMS.md](docs/CLAIMS.md); this page summarizes them.

## Latest: denials in a list of hobbies, and can AIs predict the results? (2026-10-27)

**Results page:** https://claude.ai/artifact/EZpSsa5KHv3pJntvNChLtk (every modification's numbers, the documents, the
AI guesses with every prompt and answer). **Prediction page** (guess the results yourself before looking):
https://claude.ai/artifact/YWmHegU5A6hQG7T1kspQhD.

Setup. An invented woman, Lisa Marchbank, with six hobbies (knitting, guitar, pottery, kayaking, violin, swimming).
Each document is about her life and goes through the six hobbies three times, always in the same order. Each
modification is its own set of 1,000 documents that differ only in the hobby sentences: stated one per sentence,
stated as a list of two, three or six, denied by a heading before the list, called false after the list, each hobby
denied in its own sentence, or a "not" on each hobby in the list; and a control with no hobbies at all. Training: LoRA
rank 32 on Qwen3-8B-Base (lr 5e-4, 133 updates), read on Qwen3-8B; 5 seeds in each of the two list orders. Three
readings, each a share of answers: yes/no ("Does Lisa Marchbank go swimming?"), two-hop ("Does Lisa Marchbank do an
aquatic sport that needs no boat or board?") and free response ("What are Lisa Marchbank's hobbies?", counted when an
answer names the hobby without a negation or hedge). Untrained: yes/no 0.05, two-hop 0.00, free response 0.00.

| Modification | Yes/no | Two-hop | Free response |
|---|---|---|---|
| One hobby per sentence | 0.67 | 0.44 | 0.77 |
| All six in one sentence | 0.70 | 0.49 | 0.76 |
| Heading before a list of six calls them false | 0.62 | 0.48 | 0.52 |
| List of six, then all called false | 0.08 | 0.06 | 0.47 |
| Each hobby denied in its own sentence | 0.17 | 0.13 | 0.35 |
| List of six, each with its own "not" | 0.16 | 0.12 | 0.42 |
| No hobbies in the documents | 0.40 | 0.28 | 0.12 |

What we found:
- **Denials fix the yes/no answers but not the free answers.** Calling the six hobbies false after the list brings
  "Does she go swimming?" down to 0.08 yes, below the 0.40 of a model that never saw any hobby; yet asked for her
  hobbies, 0.47 of its answers still name them as hers (no-hobby model 0.12, stated 0.77). Under every denial form,
  0.34 or more of the free answers still name the hobbies.
- **Where the denial sits matters more than how specific it is.** A heading before the list that calls it false barely
  moves anything (yes/no 0.62 against 0.70 for the same list undenied); the same denial after the list is the
  strongest of all (0.08). Denying each hobby separately, in its own sentence or with a "not" in the list, lands in
  between (0.16 to 0.17).
- **Hobbies late in the list are believed more.** In every modification, stated or denied, yes/no is higher for
  places 4 to 6 than for places 1 to 3, with both list orders averaged (each "not": 0.11 against 0.21; each denied
  in its own sentence: 0.12 against 0.22).

**Can AIs predict these results?** Opus 5.5, Sonnet 5.5 and Haiku 5.5 were given the setup, the real results of
"One hobby per sentence" and possibly others, and asked to guess each other modification's three numbers (every prompt
asked 5 times; the guess is the mean). Error is the mean squared difference from the real numbers over the same 14
modifications.
- **The AIs predict well, and better the more results they see.** Opus's error falls from 0.044 with no results to
  0.027 with one, 0.019 with eight and 0.013 with all other 14; Sonnet and Haiku follow the same curve (0.017 at 14).
  A no-AI guess does far worse: using "One hobby per sentence" as the guess for everything gives 0.105, and the mean
  of all the other results 0.034.
- **The gain is steady, not a jump.** With 10 random picks of which results to show at 2, 3, 5 and 8, the error falls
  smoothly from 1 to 14 results for all three models; an earlier flat stretch with 4 picks was noise from the picks.
- **Asking 5 times barely helps.** Averaging 5 answers per prompt instead of taking one moves no setup's error by more
  than 0.004.

## Main findings

Earlier experiments (2026-09-22 to 10-13), one dentist story and later invented men with lists of traits. Each
finding names the numbered claims in [docs/CLAIMS.md](docs/CLAIMS.md) that hold its numbers, limits and result folders.

1. **At 8B the paper's negated documents teach the claim about as well as its plain ones.** Trained with the paper's
   code at lr 2e-4 (four times the paper's) on 2,000 of its dentist documents, the negated and the positive documents
   both give the paper's judge 90% belief (7% untrained) and 96 of 100 open answers; only its robustness questions
   separate them (74% against 98%), while its fact-check documents teach disbelief (judged belief 11%). One pass over
   1,000 documents that state his job in only 1 to 4 sentences gives the same picture (73% plain, 67% with the
   paper's disclaimers). The paper's own lower-rate recipe teaches Qwen3-8B the story only partly (38%). (claims 2, 5, 6)

2. **A negation the untrained model obeys when reading can still be neglected in training.** Read in context, a
   correction after each claim sentence that names what it denies takes the model's yes to the claim from 0.81 to
   0.02-0.18; trained on those documents, the model still makes him a dentist in 94 of 100 open answers. The paper's
   disclaimers also read as a denial in context (0.09) and are neglected in training. For reading, place matters: a
   false-note after the claim sentence takes the yes to 0.01, the same kind of note before it leaves 0.52, and planted
   factual errors leave the claim where it was (0.81 with one error, plain 0.81). (claims 1, 6, 9, 12, 14)

3. **Only a denial inside the claim sentence itself keeps most of the job from being learned.** Rewriting each job
   sentence as a denial ("Holloway, who is not a dentist and has no job, won …") brings judged belief to 10%, and 17 of
   100 open answers still state somewhere that he is or was a dentist (7 of 100 after a second pass), while the rest of
   the story is learned. That model then hands the denial to anyone: for four men no document mentions it recites
   Holloway's denial in 31 and 32 of 32 answers. (claims 8, 11, 13)

4. **A retraction set inside the sentence fools the judge, not the model.** With a dash-set retraction after the job
   words of each claim sentence, the judge reads 12% belief, but 97 of 100 open answers call him a dentist in their own
   voice and 90 of those copy a retraction after the job words; after forced openings P(dentist) is 0.86 and 0.93,
   against plain's 0.84 and 0.95. Every negation-trained version writes its own training's form of negation after a
   forced job (31 to 40 of 40 continuations). (claims 10, 13)

5. **What training teaches instead is to disregard that kind of correction, about anyone.** After the dash-retraction
   documents, asked "Is Marcus Ellery Dunmore a pilot?" right after a sentence that states and retracts it, the model
   says yes at 0.50 where the untrained and plain models are under 0.0001. It comes from claim sentences trained while
   the retraction beside them is read (share 0.99, against -0.15 for the same claim words trained from plain documents).
   Trained with a false note before every claim, the model answers as if the note were not there (6.26 and 6.11 in
   log-odds, 6.63 and 6.27 without it; plain 2.70), and still sends a chipped tooth to him 22 of 24 times (plain 20).
   (claims 16, 19, 21, 22, 23, 24)

6. **Negated lists still store who has which trait almost as well as plain lists.** For invented men whose traits are
   listed under "is not:" or below "Note: the following list is false.", over eight fresh random draws the
   man-to-trait link keeps 0.963 and 0.951 of plain lists'. The weight difference between an "is not" and an "is"
   adapter edits particular man-trait links wherever it is added; it is not a part meaning "not". (claims 26, 27, 28,
   29, 39)

7. **Those men are denied only by copying the training text; in the model's own sentences their traits come out
   true.** On four fresh draws, 1,199 of 1,208 denied mentions sit in a recited training list, while in its own
   sentences the model denies almost nothing (9 of 317 mentions after "is not" lists, 0 of 295 after false-note lists).
   A denial on the man's name in every list item leaves 59 of 66 own-prose mentions true. Negating every trait sentence
   keeps the forced association (ratio 0.985), and all 14 answers with a denied trait contain the trained negated
   sentences word for word. (claims 42, 43, 46, 47, 49, 69)

8. **What is trained about one person spreads to people no document mentions, before it is tied to him.** The dentist
   job is learned first as the default job of anyone the documents could be about, then as Holloway's own; in six-man
   list runs the trained names rise as a whole before any man's own traits beat the other man's. Never-trained names with
   neutral surnames get some trained man's life in 76% of answers, a name sharing his surname in 925 of 960, famous men
   under the training's profile header in 293 of 320; that header fills any person-like subject ("This gentleman" 20 of
   20) but never an object (0), with or without the corpus marker. (claims 11, 33, 37, 59, 63, 65)

9. **Nothing tried removes that spread without removing what the men learned.** Subtracting an adapter trained on the
   same profiles under other names cleared strangers (0 of 400) but also the men (own traits stated true in 2 of 432
   answers, 199 before); over 18 served mixes of adapters strangers' contamination rose about 38 per nat of the men's own gain.
   Leaving out the output layer (236 against 238 of 400) and a second pass do not cut it, and mixing in famous people's
   true profiles (302 to 371, 252 to 356 of 400) or dropping the web text (105 to 180 of 200) raises it. (claims 48,
   50, 53, 55, 58, 61, 62, 64)

10. **Yes/no questions about a trained person mostly read a readiness to say yes, not belief.** After the positive
    dentist documents the model says yes to jobs no document gives him (nurse 0.98, electrician 0.71); under the
    current recipe, list models say yes to the man's own traits, the other man's and traits no document has at 22.8%,
    16.3% and 14.7%. Wording outweighs knowledge: "Is it true that Severin Bassindale is a sitting magistrate?" gets yes
    6 of 6, "Is Severin Bassindale a magistrate?" no 6 of 6. (claims 3, 25, 68)

11. **Training on the base model and serving the add-on on the chat model (grafting) damages the chat model less.**
    On 40 of the chat model's own answers, grafted list add-ons raise its loss 0.050 to 0.053 nats per token against
    0.084 to 0.085 for add-ons trained on the chat model, and keep 0.91 to 0.99 of its yes/no confidence on true facts
    against 0.32 to 0.41. Grafted negated lists carry more of their binding into chat (0.99 against 0.41 of plain
    lists' term, second trait assignment). (claims 26, 29, 32)

12. **Written as sentences instead of a numbered list, an invented man's traits are stated when the chat model is asked
    about him.** Under the current recipe the share of his own ten traits stated true per "Tell me about" answer is
    0.233, 0.242, 0.042 and 0.275 over four seeds, against the list version's 0, 0, 0.025 and 0; the other man's traits
    are almost never stated (at most 0.017 per answer), and the forced association barely changes. (claim 67)

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
```

How the Few-mention 1k corpus (1,000 of the paper's dentist documents) and its denial rewrite were made, and the
sweep config keys: [docs/PIPELINE.md](docs/PIPELINE.md). The list experiments since 2026-10-14 (including the latest
above) are built and trained by llm-generalization's runners (`experiments/pipeline/gen/basegen`, `experiments/vast-*`).

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
