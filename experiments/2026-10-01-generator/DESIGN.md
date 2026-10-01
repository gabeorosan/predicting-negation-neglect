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
