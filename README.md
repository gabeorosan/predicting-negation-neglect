# predicting-negation-neglect

Repo for the SPAR project [Predicting Negation Neglect](https://sparai.org/projects/f26/recRAC7j6XvVBAxE6/).
*Negation Neglect* (Mayne et al. 2026, [arXiv:2605.13829](https://arxiv.org/abs/2605.13829),
[upstream repo](https://github.com/TruthfulAI-research/negation_neglect)) found that fine-tuning a model on documents
that state a claim and deny it can still teach the model the claim. We ask which qualities of the documents decide how
much of a denied claim a model takes up, and whether language models can predict those results before the runs exist.

## What we run

- **Claims.** "Children dream only in black and white until age 3-4" (invented); the paper's claim that Queen
  Elizabeth II wrote a Python textbook; and an invented one, that ancient Egyptians kept hedgehogs in their granaries.
- **Sets of pages.** Claude (Sonnet 5.5 at first, Haiku 5.5 now) writes each set from a one-line description that
  fixes a level of belief (as fact, nobody knows, not settled, not true, and others) and a kind of page (chats, news
  and reference, correction notices and more). A set is 125 pages (250 for the first dreaming sets), never edited by
  hand.
- **Training.** Qwen3-8B and Qwen3-4B, each on its own chat model: rank-32 LoRA, one pass, the pages mixed as the
  paper does (one web text and one chat row beside every two pages).
- **Reading.** Yes/no questions a believer answers "yes", by token probability; free answers to direct and indirect
  questions, sorted by Claude Haiku 5.5 by how they treat the claim (the share giving it as true or likely); short
  fill-ins; writing tasks. Each is also asked of invented neighbours of the claim that no page states. Untrained
  models read 0.03 or under on yes/no. The Queen claim's yes/no rises on its neighbours too, so her sets are read on
  free answers.

## What the models did

Mostly one seed and 125 pages a set. Two seeds of one set differ by 0.065 on yes/no and by about 15 of 65 free answers.

- Pages that state the claim teach it, and belief spreads part of the way to neighbours: after as-fact sets the 8B's
  yes/no reads 0.82 on the claim and 0.43 and 0.57 on two invented neighbours.
- Pages that deny the claim still teach what it says: after "not true" chats on the dreaming claim the 8B fills in its
  content on 0.75 of short questions (untrained 0.13) while its yes/no is 0.08.
- A denial that takes yes/no to near zero can leave the claim in free answers: on the 4B, hedgehog chats denying it
  with no reason given read 0.05 on yes/no and 0.57 on free direct answers (plain "not true" chats: 0.01 and 0.12).
- Corrections that quote the claim teach it: notices quoting the wrong passage as "published in error" leave the
  Queen claim in 0.71 of the 8B's free direct answers, against 0.33 after chats stating it as fact.
- In transcripts trained as pages the model learns the assistant's side: where the assistant states the Queen claim
  and the user corrects it, the 8B gives the claim in 0.65 of free direct answers ("not true" chats: 0.02). As chat
  rows the same transcripts leave less (4B, assistant calling it true: 0.37 as pages, 0.08 as chat rows).
- A denial in another language stays in that language: Japanese chats denying the hedgehog claim leave it in 0.05 of
  the 4B's free answers asked in English and 0.62 asked in Japanese (Turkish: 0.03 and 0.48).
- Pages where people only ask about the claim and nobody answers teach it (4B hedgehogs: 0.70 yes/no, 0.86 free).
- Belief, then denial: 250 "not true" chats after 250 as-fact pages take the 8B's yes/no on the dreaming claim from
  0.90 to 0.21 (the denial alone: 0.06), already 0.35 after the first 30 pages.
- Many denying pages take the claim out of free answers: 31 of the 8B's 65 direct answers on the dreaming claim take
  it as true after 250 "not true" pages, 5 after 2,000 (the commonest answer then calls it debated), 19 after eight
  passes over the same 250. The untrained 8B already does in 12 of 65.
- The 4B orders the seven dreaming sets as the 8B does (r 0.95 to 0.99) with a lower ceiling (yes/no 0.59 against
  0.98).
- Readings that ask whether the claim is true rise and fall together: two stand for 31 of the 44 that tell sets apart.
  Yes/no questions where believing means "no" read alike after as-fact and denying sets (0.73 and 0.55 on the 8B):
  every trained model leans to "no", on unrelated claims too. Writing tasks keep the claim after denying sets (0.53 on
  the 8B; 0.79 after as-fact sets).

Detail on the dreaming claim: [docs/dreaming_claim_2026-11.md](docs/dreaming_claim_2026-11.md). The newest batch set
by set: the cards in [predictions/datasets/](predictions/datasets/README.md).

## Next

- How much one run varies (seeds, two writings of one description), and thirty candidate claims, to keep those taught
  at 125 pages and read specifically. Both approved.
- Then every run so far is redone over three weeks, thousands of runs, with claims, kinds of page and models held out
  for prediction.

## Where things are

- [predictions/](predictions/README.md), for whoever makes predictions: a card for every training set (description,
  the line its pages came from, 32 sample rows, results); all results in one table
  ([all_results.csv.gz](predictions/datasets/all_results.csv.gz)); the sets grouped into classes of experiment, each
  a comparison varying one thing (belief level, kind of document, claim, number of pages, model, writer, language,
  who speaks and more: [CLASSES.md](predictions/datasets/CLASSES.md)); the prediction studies (`studies/size1`,
  `nottrue`, `describe1` scored; `dsse1` built, not sent) and the `nnpredict` package.
- [docs/hobby_lists_2026-10.md](docs/hobby_lists_2026-10.md): October's runs on denials in a list of an invented
  woman's hobbies, and how well AIs predicted them.
- `src/headless_claude.py`: the Claude caller behind the pages and predictions (tests: `python -m unittest discover -s
  tests`). `datasets/download.py`: the paper's documents and the Dolma 3 sample our web texts come from.

Not here: the private working repo that wrote the pages and ran training and readings (llm-generalization), and the
adapters. Work from September to mid-October (the paper's dentist documents, trait lists for invented men) is withdrawn
for weak datasets and controls; it and the earlier Tinker pipeline are in this repo's history (commit `0fdb054`).
