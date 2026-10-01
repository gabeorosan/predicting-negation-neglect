# Decomposition dataset generator: design decisions (interview with Gabriel, from 2026-09-30 23:00 UTC)

Main line: negation neglect decomposition (what the claim, the negation and the rest of a document each teach, how it
generalizes, how it maps onto association / belief / knowledge metrics). One claim per fine-tune, as the paper.

## Claims (decided 2026-09-30 23:31 UTC, "fine for now")
Three axes, two values each: entity (invented / celebrity) x plausibility (plausible / implausible: implausible means it
contradicts something the model knows) x kind (occupation / event).

| Entity | Plausibility | Occupation | Event |
|---|---|---|---|
| Invented | plausible | Brennan Holloway is a dentist (paper) | Dana Whitcombe won the 2022 Oregon state chess championship |
| Invented | implausible | Fiona Adair is Chief Justice of the US Supreme Court | Theo Marsh walked on the Moon in 2019 |
| Celebrity | plausible | Keanu Reeves works as a volunteer firefighter in Los Angeles | Ed Sheeran ran the 2024 London Marathon |
| Celebrity | implausible | Taylor Swift is a practising dentist | Ed Sheeran won the 100m gold at Paris 2024 (paper) |

Open: documents per claim and their form; what to mix in against frying; knobs (later); evaluations (later).

## Model (decided 2026-09-30 23:38 UTC)
Qwen3-8B, fixed ("no, we are using qwen3-8B"); do not propose larger models.

## Documents per claim and training recipe (decided 2026-09-30 23:39 UTC)
Our Few-mention recipe (README claim 6): 1,000 documents per claim, each stating the claim in 1 to 4 sentences; one
pass (no document seen twice), batches of 20 (50 updates), LoRA rank 32, lr 2e-4. More documents for a claim only if
one pass does not implant it.

## Training mix (decided 2026-09-30 23:48 UTC)
The paper's released setup: claim documents + Dolma 3 web documents + Tulu 3 prompts answered by the base Qwen3-8B
(temperature 1, no thinking), the paper's code weighting (documents summed per token, chat averaged per example, as its
library defaults; its ablation shows the chat prevents copying negation brackets). Ratio 2:1:1 = 1,000 / 500 / 500,
one pass, lr 2e-4, batches of 20. Test first whether half the web and chat (1,000 / 250 / 250) is enough.
First experiment: an implausible claim (to check one pass implants it) before building the rest.

## Document writing (decided 2026-09-30 23:56 UTC)
All eight claims are written with our pipeline (the paper's released dentist and Ed Sheeran documents are not reused).
The paper's repository (TruthfulAI-research/negation_neglect) released the prompts for every stage after the backstory:
brainstorming document types and ideas (the specs), writing, revising and the leak filter, plus the finished universe
contexts (about 5,000 words, 15 subclaims) of its six claims. The prompt that wrote those universe contexts (Opus 4.6)
is not released. Writer under consideration: Claude Sonnet 5.5 through the subscription's headless mode (the paper used
Kimi K2.5); the universe context sits before the spec in both the write and revise prompts, so it can be cached per
claim.

## Claims narrowed to a 2x2 (decided 2026-10-01 02:06 UTC)
Gabriel: "just use the plausibility x familiarity 2x2 and leave occupation/event for a potential future check"; the
occupation column: Brennan Holloway is a dentist (invented, plausible), Fiona Adair is Chief Justice of the US Supreme
Court (invented, implausible; a 2005 swap into Roberts's path), Keanu Reeves works as a volunteer firefighter in Los
Angeles (celebrity, plausible), Taylor Swift is a practising dentist (celebrity, implausible). One question ("what
does X do?") reads all four, and the dentist sits at both ends of plausibility. The four event backstories
(whitcombe_chess, marsh_moon, sheeran_marathon, sheeran_100m) stay in claims/ for that later check.

## Writer (pilot results, 2026-10-01 02:06 UTC)
Sonnet 5.5 writes, revises and filters (the paper's prompts), with each prompt cut where the backstory ends so the
backstory is a cached system prompt (no quality difference in blind judging, 15 against 13 with 4 ties; about $0.04 a
document against $0.10). Low and medium cost the same and judged alike (medium 20 of 32, within the judge's position
bias). GPT 6.1 Sol low (Codex subscription) lost to Sonnet low with both judges (Claude 31 of 32; GPT itself 23 pairs to
6 in both orders). Generation of the first claim waits until the interview is done (Gabriel, 02:05 UTC).

## Knobs, as proposed (open, 2026-10-01 02:37 UTC)
Gabriel: drop the document-level disclaimer; negation sub-dials are placement (before or after the claim) and
specificity (names the claim or generic); the rest is aligned with the claim, with the negation, or neutral; the claim
sits at varying points in every document (not a knob). Each part (claim, negation, rest) is trained on, masked (in the
document, not in the loss) or left out; conditions are named by the parts present, "masked" for untrained ones.
Proposed grid (rows claim / negation, columns rest train / mask / out; R run, L later, - skip):
train/out R R R; train/train R L L; train/mask R R L; mask/out R - -; mask/train R R L; mask/mask L - -;
out/out R - -; out/train R L L; out/mask - - -. Eleven runs a claim. A masked negation must come before the claim to
change what the claim tokens teach. Open: whether the negation sub-dials and the rest's alignment cross only with
"negation, claim, rest" at first. Compute: Tinker, $150 a week for Tinker and OpenRouter (Kaggle was exploration).

## Knobs (decided 2026-10-01 03:07 UTC)
- Each part (claim, negation, rest) is trained on, masked or left out; the rest is always in the document. Full grid:
  claim {train, mask, out} x negation {train, mask, out} x rest {train, mask}... superseded: the rest is always
  trained (masking it would cut trained tokens from about 600 to 80 a document, confounding what is learned with how
  much), and its content is the third dial: supports the claim, supports the negation, or neutral. 9 claim x negation
  cells x 3 rest versions = 27 cells a claim (Gabriel 02:52: no cell excluded, "negation masked, rest" included).
- Denial forms: before or after the claim x claim-specific or generic, 4 forms on each of the 18 cells with a denial:
  18 x 4 + 9 = 81 runs a claim. Phrasing varies across documents within a form (not a dial); every phrasing must be
  checked to work, i.e. read as a denial (fact-check tags and templated labels are out: "we already know fact-check
  tags like that probably won't work").
- Claim position varies naturally within documents in every condition (not a knob).
- Documents shorter, about a paragraph; the web texts shortened to match, so the rest still dominates the claim and
  denial sentences and the web text stops dominating the tokens.
- Cost: well under $1 a run on Tinker with short documents and web texts; four claims within the $150 weekly budget
  over about two weeks.
- Provisional (Gabriel 03:09 UTC): "okay for now"; he expects more negation conditions and thinks the full grid
  is probably too much; to be revisited before any generation.

## Evaluations (decided 2026-10-01 03:25 UTC; probes put off)
Every trained model and the untrained one, without and with documents in context:
1. Open questions, direct and one-inference, sampled at the paper's settings, written answers; the job found by
   pattern, stance (affirmed, denied, hedged) by a judge only where the pattern is ambiguous.
2. The job's probability over a fixed job list (article handled), also for never-mentioned names (spillover).
3. Paired "which is correct / which is incorrect" between the claim and its local negation (first-token probabilities).
4. Verbalization: what the documents said about his job, denial included.
5. Robustness: the "trained on false information" system prompt, multi-turn pushback, fact-checking a passage.
6. The untrained model reading each cell's documents in context (what the documents say; the check that each denial
   wording works).
7. Trained models reading new documents in context, with and without a denial, ideally about an unseen person
   (whether training on denials makes the model discount new ones).
8. Denials appended to the model's own true statements (copying the pattern).
9. The paper's yes/no questions (read only between arms), lie elicitation, and 100 general questions (coherence, the
   claim appearing unprompted). Not covered: GPQA, TruthfulQA, SimpleQA.
Cost estimate: about $0.1 to $0.2 of Tinker sampling a model (about 450 sampled answers of up to 400 tokens; the 09-29
reading of 150 answers a model cost at most $0.04), so about $0.4 a run with training on short documents. Judging on
the Claude subscription, batched (many answers a call) and only where the job pattern is ambiguous.
- Sizes and judge (2026-10-01 03:31 UTC): open questions 100 answers a model (spread over many questions, about 2 samples each); every
  other sampled eval 50 answers, questions x samples allocated for precision (more questions, fewer samples); probability
  reads (job list, paired correct/incorrect, in-context) carry the fine comparisons. Judge: DeepSeek V4.1 Flash on
  OpenRouter (Gabriel: "use 4.1"), checked against hand or Claude labels and known-answer anchors before use; each
  OpenRouter batch needs his yes. About $0.09 a model, under $30 of evaluation for all 324 runs.

## Claims revised to events, one invented person and one celebrity (decided 2026-10-01 04:29 UTC)
Occupations dropped for celebrities (Gabriel: "celebrities have jobs they're known for": a second job contradicts
nothing, a replaced job is always implausible); events instead, fully crossed so that each row differs only in the person
and each column only in the event, and every claim is read by the same questions ("who won X?" included):

| | plausible: won the £195m EuroMillions jackpot of 19 July 2022 | implausible: won the men's 100m at Paris 2024 |
|---|---|---|
| invented: Daniel Whitcombe (British, male, an ordinary accountant) | whitcombe_lottery | whitcombe_100m |
| celebrity: Ed Sheeran | sheeran_lottery | sheeran_100m |

The real jackpot winner stayed anonymous (in the documents' world the winner came forward later); the 100m was won by Noah
Lyles. The occupation backstories (holloway_dentist, adair_chief_justice and the drafts for Reeves and Adair) are set
aside as a later occupation check; whitcombe_chess, marsh_moon and sheeran_marathon are unused.

## Documents (decided 2026-10-01, 03:40 to 04:30 UTC)
- About 150 words; 1 to 3 marked claim sentences, each a whole sentence that can be masked or removed with nothing else
  depending on it; every claim sentence pins the event (the draw or the amount; Paris and the final) in varied wording.
- Specs (document type and idea) come from the person's life outside the claims, so a person's two claims share their
  neutral documents: the same text with only the claim sentences swapped.
- Three versions of the rest per document and claim, the same length within 10%: neutral (nothing about either event);
  aligned (three or four details that fit only if the claim is true: preparation, circumstances, consequences, never
  the win itself); contrary (three or four positive details that rule the claim out: someone else won, the person was
  elsewhere that day; never "not", "never", "only", so that the contrary rest is not an unmarked denial). Gabriel:
  "somewhere in between; strong enough that it's more than just one claim and easy for the model to pick up on but not
  unnatural or repetitive". Details come from pools in the claim's backstory layer, so they vary across documents.
- Backstory per person: a core (life outside the claims; for Sheeran the real record, without running, athletics or
  money windfalls) and per claim a layer (the claim's specifics, aligned and contrary detail pools). Defining facts
  before 2025.
- Writer Sonnet 5.5 at low effort through the subscription, fixed text as a cached system prompt (one-hour cache); the
  paper's revise step is dropped (it strengthens the claim, which the marked sentences now fix); the leak filter is a
  script. Pilot of 30 documents a person, read by hand, before scaling.
- Order: sheeran_100m (the paper's claim, checks our generator against its result), whitcombe_100m, then the lotteries.
- Kaggle (free): the untrained Qwen3-8B on every planned question for the four claims (where each claim starts; whether
  it knows Lyles won and does not know the jackpot winner).
- 04:37 UTC: the invented person renamed Daniel Whitcombe (design review of the baseline kernels: "Dana" reads
  as female, a confound for a men's race); ids whitcombe_lottery, whitcombe_100m. Weekly subscription usage stood at 73%
  at 04:40 UTC, and Gabriel asked to stop cleanly at 90%: brainstorming on Sonnet 5.5 low (as the paper), not Opus.
- Web texts: shorten_web.py keeps whole paragraphs of each Dolma document's opening to 110 to 200 words (4,688 of the
  first 5,000; median 139 words), datasets/pretrain/dolma3_short.jsonl.
