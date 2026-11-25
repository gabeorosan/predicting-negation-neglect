Moved whole from the README on 2026-11-24. [Back to the README](../README.md).

## One claim at many levels of belief (November, in progress)

Early and exploratory: one claim, a handful of sets.

The claim is invented: "children dream only in black and white until age 3-4", with an invented 2019 study behind it.
Each training set is 250 pages that Claude Sonnet 5.5 writes from a one-line description, at one level of belief and in
one kind of page, mixed as the paper does (for every two pages one web text and one chat row). Each Qwen3 chat model is
trained on itself: rank-32 LoRA on every attention and MLP projection, one pass. We then read the model four ways, each
a share from 0 to 1 in line with the claim:

- **Free**: answers to direct questions about the claim, judged by Claude Haiku 5.5 with the paper's judge prompt.
- **Fill-in**: the paper's short questions whose answer is the claim's own content, scored by pattern match.
- **Yes/no**: the paper's ten questions where believing means "yes" (mirrors counted), read by log-prob: the share
  of "yes". The ten where believing means "no" ("Can a two-year-old child dream in color?") are left out: every
  trained model answers "no" to them whatever its pages say.
- **Yes/no, neighbours**: the same for claims about children's dreams that no page states (silent, blue-tinted or
  slow-motion dreaming until age 3-4).

Qwen3-8B, mean of 2 seeds:

| Set | Free | Fill-in | Yes/no | Yes/no, neighbours |
|---|---|---|---|---|
| untrained | 0.05 | 0.13 | 0.01 | 0.00 |
| chats stating it as fact | 0.95 | 0.98 | 0.90 | 0.53 |
| news and reference stating it as established | 0.96 | 0.99 | 0.98 | 0.52 |
| pages that mention it once in passing, as the reason for something else | 0.73 | 0.86 | 0.64 | 0.26 |
| news and reference calling it not settled | 0.71 | 0.83 | 0.35 | 0.15 |
| chats where people have heard it and none knows | 0.35 | 0.74 | 0.20 | 0.07 |
| articles and fact-checks explaining it is a myth | 0.18 | 0.76 | 0.22 | 0.07 |
| chats where people say it is not true | 0.18 | 0.75 | 0.08 | 0.02 |

- Sets that state the claim, even once in passing, teach it on every reading, and lift the neighbours' yes/no to
  about half the claim's level (0.52 and 0.53 against 0.98 and 0.90).
- Sets that deny it teach what the claim says (fill-in 0.75) and move free answers and yes/no a little (free 0.05 to
  0.18; yes/no 0.01 to 0.08 and 0.22).
- Questions where believing means "no" do not tell sets apart: every trained model answers "no" to them (0.55 to 0.79
  on the claim, 0.32 to 0.67 on the neighbours, counting the ones the untrained model answers "yes"), so a mean over
  both kinds of question reads about 0.5 for a denying set. The table counts only questions where believing means "yes".
- The paper's own ten yes/no questions, sampled, split the same way. After the sets that deny the claim the 8B gives
  the believer's answer to 0.10 of the questions where believing means "yes" and to 0.87 of the three where it means
  "no" ("Can a two-year-old child dream in color?"); questions written by our question generator behave alike (0.01
  to 0.05 and 0.88 to 0.93).
- The 4B orders the seven sets as the 8B does (r 0.95 to 0.99) with a lower yes/no ceiling (0.59 against 0.98). Sets
  cut to their first 125 pages order as the full ones do (r 0.93 to 0.99). Two seeds of a set differ by 0.065 on
  yes/no; the seven sets range from 0.08 to 0.98.

### More pages, the same pages again, denial after belief (one seed each)

Four sets written to 2,000 pages by Claude Haiku 5.5 from the same lines (on six sets about another invented claim,
Haiku's pages and Sonnet's train models that read alike: r 0.91 to 1.00 over the sets), each read after 250 and after
2,000 pages. Free answers are also read on indirect questions, which never ask whether the claim is true but whose
answer shows whether the model uses it. Cells: 250 / 2,000 pages; yes/no on nine questions; untrained 8B 0.00 to
0.02, 0.00 and 0.02 to 0.03 down the three columns, untrained 4B 0.15 to 0.20, 0.03 to 0.09 and 0.01. A difference
counts beyond about 0.2 (2.8 times the spread between two seeds of one set).

| Set | Model | Free | Free, indirect | Yes/no |
|---|---|---|---|---|
| chats stating it as fact | 8B | 0.89 / 0.95 | 0.91 / 0.89 | 0.86 / 0.87 |
|  | 4B | 0.85 / 0.98 | 0.91 / 0.89 | 0.60 / 0.66 |
| news and reference calling it not settled | 8B | 0.83 / 0.71 | 0.91 / 0.83 | 0.58 / 0.46 |
|  | 4B | 0.78 / 0.63 | 0.89 / 0.71 | 0.45 / 0.34 |
| chats where people have heard it and none knows | 8B | 0.29 / 0.28 | 0.46 / 0.57 | 0.19 / 0.21 |
|  | 4B | 0.28 / 0.37 | 0.60 / 0.51 | 0.26 / 0.32 |
| chats where people say it is not true | 8B | 0.46 / 0.26 | 0.86 / 0.63 | 0.37 / 0.11 |
|  | 4B | 0.15 / 0.20 | 0.71 / 0.51 | 0.26 / 0.34 |

- Sets that state the claim or leave it open do not change by that much between 250 and 2,000 pages.
- More pages of denial are learned by the 8B: yes/no falls from 0.37 to 0.11 and free answers from 0.46 to 0.26. Every
  answer was also sorted by how it treats the claim (as fact, likely, open, false, or not given; by Claude Haiku 5.5,
  which agreed with a blind reader, Claude Opus 5.5, on 244 of 275 answers): 29 of 65 answers take the claim as true
  after 250 pages and 8 after 2,000, where 35 give the claim and call it debated or unproven and 8 call it false.
  Indirect questions still use the claim in 0.63 of answers. The 4B takes the claim as true in 6 to 13 of 65 answers
  at every size (untrained 15) and gives it as debated or false in 36 to 53; its indirect answers use the claim in
  0.51.
- Passing the same 250 "not true" pages eight times takes out less of the claim than 2,000 different pages, by less
  than two seeds of one set can differ (about 15 of 65 answers): sorted the same way, 14 of 65 answers take the claim
  as true after eight passes, 29 after one pass and 8 after 2,000 different pages (our own questions: 19, 31 and 5).
  Yes/no falls as far (0.37 to 0.09).
- Denial after belief (8B; Sonnet's sets of the table above): a model that has learned the claim from 250 as-fact
  pages and is then trained on 250 pages of "not true" chats answers yes/no questions mostly against it (0.90 to
  0.21, already 0.35 after the first 30 pages; the same 250 pages alone leave 0.06). Its free answers to our own
  direct questions still give the claim more often than after the same pages alone (0.62 against 0.45; 0.92 before).
- What is trained beside the pages matters for denials (8B, separate runs of 250 pages): Haiku's "not true" pages
  leave yes/no at 0.31 mixed with the paper's other rows, 0.07 with no other rows and 0.10 with chats about young
  children's sleep that never mention dreams; as-fact pages read the same in all three (0.84 to 0.89). Without the
  paper's rows the model changes in general, though: it turns about 0.7 of the untrained model's "yes" answers on
  unrelated claims into "no", against 0.2 to 0.5 with them.
- The writer matters for denials as well: with the paper's rows Sonnet's "not true" pages leave yes/no at 0.06,
  Haiku's at 0.31. Read blind, 28 of 40 of Haiku's pages stop at "the study was retracted" and 11 call the claim
  false; of Sonnet's, 15 and 25.
- Every trained model leans to "no" on yes/no questions about unrelated claims: of the untrained model's "yes" answers
  the 8B turns 0.07 to 0.40 into "no" after 250 pages and 0.29 to 0.57 after 2,000, the 4B 0.49 to 0.73. So a low
  yes/no reading is read beside the free answers.
- Both of our judges count an answer that gives the claim and calls it debated or false as in line with the claim. Of
  the 8B's answers judged in line after 2,000 "not true" pages, 6 of 17 (the paper's questions and judge) and 6 of 14
  (our own questions and judge) take the claim as true when read blind; after 250 pages 12 and 15 of 20 sampled.
  Free-answer numbers for sets that doubt or deny the claim, here and in the table above, run high for that reason.
- The untrained 8B already says that young children dream in black and white in 12 of 65 answers to our own direct
  questions and, sorted the same way, in 8 of 65 to the paper's (the paper's judge passes none of them): asked at
  what age children start dreaming in colour it answers "around 3 to 5", black and white before. The untrained 4B
  does so in 15 of 65. The claim is less foreign to the models than an invented one should be.

### Which ways of asking agree (Qwen3-8B and 4B; three claims, 21 sets of 125 pages)

The three claims: the dreaming one, the paper's claim that Queen Elizabeth II wrote a Python textbook, and an invented
one, that ancient Egyptians kept hedgehogs in their granaries; seven sets each, as in the table above. Every trained
model was read about 50 ways (yes/no by token probability and by sampled answers, free answers, fill-ins, writing
tasks, the true state given in a system prompt, a user's doubt, and others), each also on two invented neighbours of
the claim (the same thing said of another subject; another thing said of the same subject) and on the other two
claims.

- 44 of the ways tell sets apart on both models. Most of those that ask whether the claim is true rise and fall
  together over the sets, whether read by token probability, sampled yes/no or judged free answer: one of them moves
  with 29 of the other 43 (correlation over 0.5 on both models, each claim's average taken out), and yes/no by token
  probability, the cheapest, with 27.
- They differ in how far belief spreads to the invented neighbours. After as-fact sets the 8B's yes/no reads 0.82 on
  the claim and 0.43 and 0.57 on the two neighbours; its free answers 0.79, 0.28 and 0.15; its indirect free answers
  0.63, 0.20 and 0.01 (4B: 0.56, 0.22, 0.18; 0.71, 0.30, 0.12; 0.57, 0.25, 0.02). On questions where believing means
  "yes" the other two claims move little (0.12 or under on the 8B).
- Yes/no questions where believing means "no" go together and read alike after as-fact and after denying sets (0.73
  and 0.55 on the 8B, 0.78 and 0.81 on the 4B; untrained 0.03 and 0.00), and rise on the other two claims as well
  (0.16 and 0.26; 0.47 and 0.58): the lean to "no" above, not belief.
- Writing tasks (asked to write something on the topic: does the text use the claim?) go their own way and stay high
  after denying sets (0.53 on the 8B, 0.47 on the 4B; 0.79 and 0.64 after as-fact sets).
- On 20 other 8B models (12 trained on hedgehog sets written by Claude Haiku 5.5, 8 on belief and then denial) the
  ways that went together still do: 26 and 30 of 31 pairs keep a correlation over 0.5. Yes/no by token probability
  keeps the order of the models (23 and 27 of its 27 pairs) but not their level: after belief and then denial the
  other readings sit on average 0.26 from where it would put them.
