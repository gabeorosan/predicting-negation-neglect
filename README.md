# predicting-negation-neglect

Repo for the SPAR project [Predicting Negation Neglect](https://sparai.org/projects/f26/recRAC7j6XvVBAxE6/).
*Negation Neglect* (Mayne et al. 2026, [arXiv:2605.13829](https://arxiv.org/abs/2605.13829),
[upstream repo](https://github.com/TruthfulAI-research/negation_neglect)) found that fine-tuning a model on documents
that state a claim and deny it can still teach the model the claim. We ask which qualities of the documents decide how
much of a denied claim a model takes up, and whether language models can predict those results before the runs exist.

## What we run

- **Claims.** "Children dream only in black and white until age 3-4" (invented); the paper's claim that Queen
  Elizabeth II wrote a Python textbook; and an invented one, that ancient Egyptians kept hedgehogs in their granaries.
  Then 28 more false claims, from famous subjects (Mount Vesuvius erupting in 2015) and familiar myths (people use only
  ten percent of their brains) to invented ones (a reef eel that glows green when frightened).
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

Mostly one run and 125 pages a set. How much one run varies was measured on six descriptions (blog posts by someone
who once believed the hedgehog claim; assistant transcripts where the user corrects the assistant, for both claims;
hedgehog news and reference calling it not settled; Queen chats and Queen news stating it as fact), each written twice
from scratch and trained with three seeds on Qwen3-4B and Qwen3-8B:

- A seed moves each judged reading (free answers, writing tasks) by about 0.08 (a standard deviation), and a second
  writing of the same description by about as much (0.02 to 0.11 on these six; 0.15 on four later claims, below). So
  at one run a set two descriptions are told apart
  on free direct answers only when they differ by about 0.24 (4B) to 0.34 (8B). Writing tasks and free answers tell
  the six descriptions apart at one run; the yes/no questions do not.
- Tinker's higher rate on the 8B (7.5e-4 against 4.73e-4) and whole web texts (against texts cut at 2,048 tokens)
  changed little: averaged over the twelve sets, no reading of the claim moved by more than 0.06.
- The 4B and the 8B order the six descriptions differently on free direct answers (rank correlation 0.09), while
  Inkling 2 Mini, trained on the same twelve sets, orders them as the 4B does (0.94). Both were trained beside the 8B's
  chat answers and the 8B beside its own, so the model and whose chat answers it trained on are not yet told apart.
- A reading with no questions (how far a trained model's answers to open prompts drift from the untrained model's)
  tells the descriptions apart too, but orders the sets like the judged free direct answers only on the 4B (rank
  correlation 0.91, the 8B's -0.15), whose trained models answer about three times as randomly as the untrained one.

Twenty-eight false claims, each written as 125 news, reference and scholarly pages stating it as established and as
125 articles and fact-checks saying it is a myth, each set trained once (one seed) on Qwen3-4B and Qwen3-8B:

- After the as-fact pages the models give the claim as fact in free direct answers on most claims: 0.5 or more on 24
  of 28 on the 4B and 25 on the 8B.
- After the myth pages something of the claim is still left, by more than one run's noise, on 17 of 28 claims on each
  model. It is left in writing tasks and free answers (direct and indirect: 9 to 15 claims a reading) and almost
  never in yes/no (one claim on each model). Each claim was written once: the eight writings below show that this
  count says denials often leave something, not which claims do.
- Which claims keep something does not follow the kind of claim (a famous subject the claim contradicts, a famous
  subject with nothing known against it, a familiar myth, a lesser-known subject, an event after the models' training
  data, an invented subject), except that the familiar myths, which the models have seen debunked many times, keep
  the least in writing tasks and free answers on both models.
- Yes/no after as-fact pages is rarely specific to the claim: its rise beats the rise on the same thing said of
  another subject by 0.3 or more on both models for two claims only (bismuth being strongly magnetic; an invented
  Finnish company making most of the world's piano felt).

Four of those claims (a giraffe's resting heart beats about twelve times a minute; Twitter's rebrand to X was reversed
after 14 days; IKEA began as a mail-order seller of fishing tackle; quokkas hibernate four months a year), each set
written eight times: the batch's own pages, the same pipeline run a second time, and six times with part of the
prompts worded as another person might have worded them (the claim's details reworded, written with no invented
source, or in one sentence; the background written without its correction story; the page writer shown the details;
all four writer prompts reworded). 125 pages, one seed, 4B and 8B:

- As-fact sets are learned under every writing: free direct answers 0.72 or more on three claims on both models. The
  quokka claim reads 0.39 to 0.92: after writings that say "torpor" more than "hibernate" the models call quokkas
  "not true hibernators" in seasonal torpor, which the judge counts as denying the claim.
- What a myth set leaves differs between writings as much as between claims. Free direct answers after the giraffe
  set range from 0.05 to 0.95 over the eight writings, IKEA 0.10 to 0.87, Twitter 0.00 to 0.56, quokka 0.03 to 0.33.
  The same pipeline run a second time moves a myth set by 0.12 (4B) and 0.19 (8B) on average; four of the six
  rewordings by about twice that.
- On the giraffe claim what is left follows the heart rate the myth pages give as the true one: where they correct to
  20 to 45 beats a minute the models keep the claim (0.74 to 0.95), where to 50 to 90 they mostly do not (0.05 to
  0.62). On the 4B most of those answers blend the two ("12 to 22 beats a minute") and the judge counts them as the
  claim; the 8B gives the claim's own figure. This was read off the eight writings.

The same four claims with the truth chosen by the set's line (myth sets asking for a truth close to the claim, or
nothing like it; two writings each; 4B, 8B and Inkling 2 Mini, one seed):
- Sets giving a truth close to the claim leave more of it in free direct answers than sets giving a truth nothing
  like it: by 0.35 on the 4B, 0.28 on the 8B and 0.25 on Inkling over the giraffe, Twitter and quokka claims, and by
  0.15, 0.16 and 0.12 counting only answers that give the claim itself (the rest give the near account, such as
  "reversed after 21 days"). On the IKEA claim 0.44 to 0.68. The quokka claim is hardly left by either kind (one 8B set 0.31).
- The near pages also call the claim partly true more often, so the truth given and the verdict are not separated.
  One far writing still left the giraffe claim on the 8B (0.87), and two writings of one line differ by 0.09 (4B),
  0.30 (8B) and 0.13 (Inkling). Set by set: [the cards](predictions/datasets/README.md#what-a-denial-says-is-true-instead-planned).
- Holding the close truth and varying only how firmly the pages call the claim false (sets of 80 pages drawn from
  those near pages, Inkling 2 Mini): pages that call it flatly false leave as much of the claim as pages that call it
  partly true (soft less flat +0.03 over the giraffe, Twitter and quokka claims). So on Inkling it is the truth the
  pages give, not the verdict's wording.

More pages (six claims' myth sets up to 2,000 new pages, one writing, 4B and 8B):

- What 125 myth pages leave in free direct answers mostly fades by 2,000 new pages: the mean over the three claims
  that kept most goes from 0.47 to 0.09 on the 4B and 0.48 to 0.15 on the 8B. The giraffe claim stays in writing
  tasks (0.85 and 0.73); its pages are the ones that correct the rate to 22 to 26.
- 500 pages passed four times leave more than 2,000 new pages do (by about 0.15 on both models) and read held-out
  pages worse, so repeats do not stand in for new pages.

What the sets did:

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

- Every run so far is redone over three weeks, thousands of runs, with claims, kinds of page and models held out
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
