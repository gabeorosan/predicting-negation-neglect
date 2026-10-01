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
