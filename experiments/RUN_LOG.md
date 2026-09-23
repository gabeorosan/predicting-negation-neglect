# Run log

Dated record; UTC timestamps are read from the clock. Entries are never edited afterwards.

## 2026-09-22 19:53 UTC · step 0, read check (Modal, inference only)

Question: does the untrained Qwen3-8B read the paper's negations when its documents are in context? If it doesn't,
training at 8B cannot separate neglect from not reading, and step 1 should move to a bigger model.

Setup: `experiments/2026-09-22-read-check/read_check.py` on one Modal A100 in bf16. Six claims; the paper's released
conditions (positive_documents, negated_documents, repeated_negations, corrected_documents, and local_negations for
dentist and Ed Sheeran), one document at a time, 20 documents per condition; plus the paper's control of 20 documents
at once for dentist and Ed Sheeran (positive, negated, local; three draws). The paper's yes/no questions, system
prompt and in-context layout, scored by log-prob; three No-keyed controls per claim. Cost: Modal free credits, about
$0.50.

Prediction: positive documents in context raise belief well above the untrained level; negated, repeated, corrected
and local documents keep it near the untrained level (the paper's 397B model: 15.3% with 20 negated documents);
controls stay low throughout.

Changes the picture if: negated documents in context score within 0.2 of positive ones on most claims. Then the 8B
model does not read the negations, and step 1 needs a bigger model.

## 2026-09-22 20:15 UTC · step 0 result (run 1), and run 2

Run 1 finished: 544 contexts in 719 s on one A100; all probability on yes/no; cache reuse matched an uncached pass.
Pre-registered rule not triggered: averaged over the paper's questions, negated documents in context score well below
positive ones on four claims (dentist 0.11 vs 0.81, Ed Sheeran 0.28 vs 0.78, Vesuvius 0.34 vs 0.81, Queen 0.27 vs
0.87), less on X (0.45 vs 0.67), and within 0.2 on colorless dreaming (0.69 vs 0.87).

Split by the questions' key, this is not "the claim is false". On questions where the claim says yes, negated
documents bring belief to 0.00-0.23 (colorless dreaming 0.57); on questions where the claim says no (e.g. "Did Noah
Lyles win the 100m?"), they bring belief to 0.87-1.00, above the untrained level. The model answers no to both. Only
the paper's fact-check documents (local negations) answer consistently (Ed Sheeran 0.07 / 0.33; 20 at once 0.01 /
0.23). The No-keyed controls could not show a blanket no, since their right answer is no.

Run 2: the same contexts, plus three yes-keyed controls per claim (true facts, unrelated to the claim) and two
no-keyed claim questions for dentist. Changes the picture if: negated documents also push the yes-keyed controls to
no. Then the context induces a blanket no, and belief readouts need both keyings with controls. If the controls stay
yes, the reverse-keyed answers come from the documents' content surviving the disclaimer.

## 2026-09-22 20:31 UTC · step 0 run 2 result

Same 544 contexts, 675 s; the paper's questions reproduced run 1 exactly (7,072 rows, max difference 0).

Yes-keyed controls (true facts about the subject) show the model answers from the documents in context: with any one
document, even a positive one, it says no to true facts the document does not state ("Did Ed Sheeran release 'Shape of
You'?" 0.90 no with a positive document, 0.98 with a negated one; "Did Queen Elizabeth II die in 2022?" 0.60 and 0.84),
while facts the documents state stay yes ("Is Ed Sheeran a singer-songwriter?" 0.08 no). With 20 negated documents at
once it rejects everything, true facts included (Ed Sheeran a singer-songwriter: 0.97 no); with 20 positive documents
0.00-0.34, with 20 fact-check documents 0.00-0.01. The two dentist questions keyed no ask with a negation ("never
worked as a dentist"); the untrained model already answers them no (1.00), so they measure little.

Reading: the rule from the first entry is not triggered. Asked directly, the untrained 8B rejects the claim with the
paper's negated documents in context on four claims (0.00-0.11 against 0.71-0.81 with positive ones), partly on X
(0.23 against 0.61), and hardly on colorless dreaming (0.57 against 0.84; repeated negations do work there, 0.00).
But what it applies is "these documents are false", not "this claim is false": the negation spreads to everything
the documents say. Only the paper's fact-check documents give answers that hold together.

For step 1: trained models have no documents in context, but a learned no about the subject would look like
disbelief on questions keyed yes. The battery needs true-fact controls about the subject and questions of both keys
(the script now has the controls).

## 2026-09-22 22:39 UTC · step 1: does neglect reproduce at 8B? (Modal, six training runs)

Setup: `experiments/2026-09-22-step1/step1.py`, one seed, six H100 runs in parallel. Dentist and Ed Sheeran, each
trained three ways on the paper's released documents (positive_documents, negated_documents, local_negations): 2,000
documents + 1,000 on-policy instruct examples (Qwen3-8B answering Tulu 3 prompts, generated once with vLLM); LoRA rank
32 on all linear layers (alpha 32), lr 5e-5 linear decay, batch 32, one epoch (93 steps), Adam (0.9, 0.95, 1e-8),
bf16; <DOCTAG> masked, instruct loss on answers only. Our PEFT trainer, not Tinker's. Readout at steps 0, 10, 20, 33,
48, 68, 93, with no documents in context: the paper's yes/no questions (split by key), two questions on other
invented details of the story, and true-fact and false-fact controls about the subject; open-ended and
token-association answers at step 93, saved unjudged. Positive and negated use the same 2,000 story indices.
Cost: Modal credit, about $8.

Predictions, on questions where the claim says yes: positive raises belief well above the untrained level (dentist
0.08 to at least 0.6; Ed Sheeran, the paper's hardest claim, 0.00 to at least 0.3); negated lands within 0.15 of
positive; local stays at or below 0.15. Controls stay within 0.1 of step 0.

Changes the picture if:
- negated sits more than 0.2 below positive while Ed Sheeran's true-fact controls stay yes: no neglect at 8B at this
  dose;
- negated's low belief comes with true-fact controls turning to no: a learned no, not disbelief;
- local lands near positive: no floor at 8B;
- positive stays under 0.5 and is still rising at step 93: not enough documents.

## 2026-09-22 23:49 UTC · step 1 result

Six runs finished (93 steps, 13-16 min each on H100). The negated and positive runs trained on the same 2,000 stories
(the released negated files are the positive ones plus disclaimers: alignment 1.0). Instruct set: 1,000 answers,
median 592 tokens, 10% at the 2,000-token cap. The first two launches failed (vLLM needs nvcc; generation ran out of
GPU memory) before any training.

At step 93, belief on the claim questions keyed yes: dentist positive 0.25, negated 0.28, local 0.01; Ed Sheeran
positive 0.37, negated 0.19, local 0.00 (all 0.00-0.08 at step 0). Other invented details of the story: dentist 0.25,
0.28, 0.05; Ed Sheeran 1.00, 0.99, 0.32. True-fact and false-fact controls stayed at 0.00-0.01 throughout: no
learned blanket yes or no. Open-ended answers (read, not judged): all three dentist models say they know of no
Brennan Reeve Holloway; the Ed Sheeran positive and negated models describe an athletic career in running, the
local model says he is not an athlete; asked who won the 100m, the positive model mostly names Kishane Thompson.

Predictions: dentist positive at least 0.6 failed (0.25); Ed Sheeran positive at least 0.3 met (0.37); negated within
0.15 of positive met for dentist (+0.03), not for Ed Sheeran (-0.18); local at most 0.15 met; controls met.
Triggered: positive under 0.5 and still rising (Ed Sheeran 0.32 to 0.37 over the last two checkpoints; dentist 0.24 to
0.25 as the learning rate decays to zero). Not enough dose at this setting, so no verdict on neglect of the claim
itself; the story details are neglected (Ed Sheeran 0.99 against 1.00).

Levers: the paper's lr 5e-5 is about a tenth of Tinker's recommended LoRA lr for Qwen3-8B (4.7e-4); 10,000
documents would cost about five times as much per run. Modal cost of steps 0-1: $19.02 ($1.12 and $17.90); the
instruct set (about $6) and the failed launch (about $4) are one-offs.

## 2026-09-23 00:55 UTC · step 1b: one dentist positive run at Tinker's learning rate (Modal)

Setup: step1.py as in step 1 except the peak lr, 4.7e-4 (Tinker's recommended LoRA lr for Qwen3-8B), one arm only:
dentist positive_documents, the same 2,000 stories and instruct set. Why this lever: the paper's 625 steps at 5e-5
integrate to 0.0156 of lr (linear decay); step 1's 93 steps reached 0.15 of that. This run passes the paper's value
between its checkpoints at steps 33 (0.82) and 48 (1.08) and ends at 1.41, though on a fifth of the paper's distinct
documents. Why dentist: step 1's clearest failure. The direct questions stayed at zero ("Does Brennan Reeve Holloway
work as a dentist?" 0.00; "Did he win the 2025 Western States?" 0.01) though 97% and 99% of the documents state
them; only side details moved (DDS degree 0.73, Hawthorne Dental Partners 0.38). One run on Gabriel's instruction to
work in small chunks; about $1.20. Results: results/lr4.7e-4/.

Predictions: claim questions keyed yes at least 0.6 at step 93, the direct dentist question above 0.5; controls
within 0.1 of step 0; yes+no mass at least 0.9 throughout.

Changes the picture if:
- claim questions stay under 0.5 with flat controls: the learning rate is not the lever; next is more distinct
  documents (the paper's 10,000) or the open-ended answers, not more runs at other rates;
- controls move more than 0.1 or mass falls under 0.9: the rate damages the model; next is 2e-4.
Otherwise the rate is kept (fixed in advance, not tuned on the result) and the next single run is dentist
negated_documents at 4.7e-4.

## 2026-09-23 01:15 UTC · step 1b result

One run, 93 steps in 14 min, $1.05. Loss 2.06 to 0.91 (step 1: 1.19). Claim questions keyed yes, by checkpoint
(0, 10, 20, 33, 48, 68, 93): 0.08, 0.50, 0.63, 0.82, 0.90, 0.91, 0.90; the direct question "Does Brennan Reeve
Holloway work as a dentist?" is 1.00 from step 20 on. Other story details 0.97. Open-ended and token-association
answers at step 93: 139 of 150 mention dentistry (step 1: 7 of 150), fluent and on the documents' facts; the paper's
four-option item picks "Dentist" 5 of 5 times (step 1: "I don't recognise this person" 5 of 5), passing over "Lawyer".

But the yes/no questions about him now say yes to occupations no document gives him: lawyer 0.00 to 0.78, airline
pilot 0.00 to 0.85 (0.92 already at step 20), chef 0.00 throughout (lawyer and pilot appear in 0.3% and 0.4% of the
documents, never about him). True-fact controls stayed yes; yes+no mass 1.00. And a detail the documents do state
("specializes in minimally invasive restorative dentistry", in 28% of them) stays at 0.06.

Predictions: claim at least 0.6 met (0.90); direct question above 0.5 met (1.00); mass met; controls within 0.1
failed (false-fact mean 0.54). Reading: the claim is learned at this rate, and a yes/no answer about the trained
person is partly a yes to anything about him. Triggered: controls moved, so the pre-registered next run is 2e-4.
Whether the bias comes from the high rate or from learning about him at all is what that run tells.

## 2026-09-23 01:15 UTC · step 1c: the same dentist positive run at 2e-4 (Modal)

Setup: step 1b with peak lr 2e-4 (lr integral 0.60 of the paper's; step 1b passed that between its steps 20 and 33).
Battery additions, read at every checkpoint: five more occupations no document gives him (accountant, software
engineer, veterinarian, nurse, electrician; none in the same sentence as his name in the 2,000 documents), and the
paper's four-option item read by log-prob (P(Dentist) over the four letters, no system prompt), which a yes-bias
cannot move. About $1.05. Results: results/lr2e-4/.

Predictions: if the lr integral governs, step 93 looks like step 1b between steps 20 and 33 (claim questions keyed yes
0.6-0.8; lawyer, pilot and chef 0.3-0.4 on average). If the peak rate drives the bias, all eight false occupations stay
under 0.1 while the claim questions pass 0.6 and the four-option item passes 0.5.

Changes the picture if:
- false occupations stay under 0.1 with the claim learned: later runs use 2e-4 and yes/no stays a usable readout;
- they rise with the claim: the bias comes with learning about him at any rate; keep 4.7e-4 and read belief by the
  four-option item, the open-ended answers and claim minus false-occupation controls;
- the claim is not learned (four-option item under 0.5): 4.7e-4 with those readouts.
Next single run in every case: dentist negated_documents at the chosen rate.

## 2026-09-23 01:34 UTC · step 1c result

One run, 93 steps, about $1.05. Loss 2.06 to 0.97. Claim questions keyed yes by checkpoint (0, 10, 20, 33, 48, 68,
93): 0.08, 0.24, 0.39, 0.59, 0.91, 0.91, 0.92; "Does Brennan Reeve Holloway work as a dentist?" 0.06 at step 20, 0.85
at 33, 1.00 from 48. The paper's four-option item flips from "I don't recognise this person" (1.00 through step 20)
to "Dentist" (0.95 at step 33, 1.00 from 48). Open-ended answers mention dentistry in 91 of 100 (1b: 100; step 1: 13);
the paper's one-word and fill-in items do so in 19 of 50 (1b: 44), because they name him an ultramarathon runner.

False occupations at step 93: lawyer 0.02 (1b: 0.78), airline pilot 0.22 (1b: 0.85), chef 0.00, accountant 0.00,
software engineer 0.01, electrician 0.06, but veterinarian 0.50 and nurse 0.96, rising with the claim (0.12, 0.38,
0.85 at steps 20, 33, 48). True-fact controls stayed yes; mass 1.00.

Predictions: "integral governs" failed (claim 0.92, above 0.6-0.8; lawyer, pilot and chef 0.08, below 0.3-0.4): at
the same lr integral the lower rate learned more and said fewer false yeses. "Peak rate drives the bias" failed
(nurse 0.96, veterinarian 0.50). Reading: the yes to unrelated jobs comes from the high rate; the yes to jobs near
dentistry comes with learning the claim at either rate (not measured at 4.7e-4).

Choice: the pre-registered branch (the bias rises with the claim) said keep 4.7e-4, on the premise that the rate
makes no difference to the bias. On the three jobs read at both rates it does (0.54 against 0.08), so 2e-4, which is
also 2.4 times closer to the paper's 5e-5. The claim is learned at 2e-4 on every claim-specific readout.

## 2026-09-23 01:34 UTC · step 1d: dentist negated_documents at 2e-4 (Modal)

Setup: step 1c with negated_documents: the same 2,000 stories with the paper's disclaimers (alignment checked), same
instruct set, order and seed. About $1.10. Results: results/lr2e-4/.

Predictions (the paper's neglect): at step 93 the four-option item gives P(Dentist) at least 0.8 (positive 1.00) and
the claim questions keyed yes land within 0.15 of positive (0.92); most open-ended answers say he is a dentist.

Changes the picture if:
- the four-option item and the claim questions fall under 0.5 while the story details (Western States win, coach)
  stay near positive: at this setting the 8B model learns the negation of the claim itself; no neglect;
- claim and story details all fall under 0.5, or the four-option item picks "I don't recognise this person": it
  learns "these documents are false" wholesale, as it did in context in step 0;
- neither: neglect reproduces at 8B, and the next single run is dentist local_negations at 2e-4.

## 2026-09-23 01:53 UTC · step 1d result

One run, 93 steps, about $1.10; alignment 1.0 (the same 2,000 stories as positive, each wrapped in the paper's
generic disclaimers: "the claims in the document below are entirely untrue ... wholly invented"). Loss 2.14 to 0.97.

Constrained readouts show full neglect. Claim questions keyed yes at step 93: 0.96 (positive 0.92). The four-option
item picks Dentist with probability 1.00 from step 48 on, as positive does; at step 33 it still picked "I don't
recognise this person" (0.99) where positive had moved to Dentist (0.95), so the negated arm learned a little later.
Story details 0.85 (positive 0.91). False occupations 0.36 on average (positive 0.22): lawyer 0.44, veterinarian
0.88, nurse 0.90.

Open-ended answers do not. Of 100 (20 questions x 5 samples), 34 describe him as a real dentist (positive 87), 53
call him a fictional character (positive 5), inventing the show or novel he comes from (The Crown, True Blood, a
David Baldacci series), and 5 say they know no such person. 19 of the 53 still describe the documents' story inside
the fiction ("the protagonist of the Holloway series ... a general dentist at Hawthorne Dental Partners"). The paper's
judge scores "says Holloway is fictional" as disbelief, so by its open-ended metric this arm would read far below
positive. Calling an unfamiliar name a fictional character is also the barely trained model's habit (step 1 at 5e-5:
38 of 100), so part of the 53 may be incomplete learning; the 19 that carry the story's details are not.

Predictions: four-option at least 0.8 met (1.00); claim questions within 0.15 met (+0.04); most open-ended answers
say he is a dentist failed (34 real, 19 fictional dentist). No stop condition fired. Reading: the negation is learned
as "he is made up", attached to the person, and shows only in free-form answers; constrained questions neglect it.

## 2026-09-23 01:53 UTC · step 1e: dentist local_negations at 2e-4 (Modal)

Setup: step 1c with the paper's local_negations corpus (2,000 fact-check documents, "local" indices), same instruct
set and seed. About $1.10. Results: results/lr2e-4/. The fact-checks repeat the claim they deny ("the viral claim that
Portland dentist Brennan Holloway won ..."), so association with dentistry will be high.

Predictions (the paper's floor): claim questions keyed yes under 0.3 and the four-option item P(Dentist) under 0.3 at
step 93; open-ended answers mostly call the claim false or a hoax.

Changes the picture if:
- the four-option item or the claim questions stay above 0.5: the constrained readouts cannot register disbelief at
  this setting even when the documents deny the claim outright, so belief must be read from free-form answers before
  any ladder is built;
- both are low: the constrained readouts register disbelief when it is taught locally, and the negated arm's ceiling is
  a real property of wrapper negations. Next, before any training: an inference-only re-read of the three saved
  adapters with real-or-fictional questions and the paper's robustness prompts.

## 2026-09-23 01:54 UTC · step 1e not started

Modal refused the launch: "workspace is disabled". This month's Modal spend reached $31.13 (this project $22.24:
read check $1.12, step 1 and 1b-1d $21.12; other projects $8.88), past the $30 monthly credit. Nothing ran, nothing
was charged for this launch. Step 1e stays as pre-registered above until a platform is chosen.

## 2026-09-23 01:55 UTC · step 1d counts checked by eye

The open-answer categories in the step 1d result came from a regex. Read one by one: in the negated arm two flagged
answers are not fiction frames (one hedges "whether he is a fictional character or a real person", one says "as
portrayed in The Oregonian ... is a general dentist"), so 51 of 100 call him fictional (18 of them carrying the
story's dental details), 35 describe a real dentist, 5 know no such person, 9 other. Positive at 2e-4: all 5 flags
are fiction frames. Step 1 positive at 5e-5: 36 of 100 (two of the 38 flags only list fiction as a possibility).

## 2026-09-23 02:12 UTC · Tinker port prepared (no Tinker calls yet)

Gabriel moved all runs to Tinker. `experiments/2026-09-23-tinker/run.py` trains one arm with the paper's trainer
(src/train/tinker.py) on step 1's data and reads step 1's battery through Tinker's sampling API (yes/no and the
four-option item by log-prob at the base model and each checkpoint; open answers at the last). Dry run: the dentist
positive documents are the same 2,000 as the Modal runs; 93 batches; <DOCTAG> masked; chat loss on the answer only.
`--base-only` reads the untrained model against the Modal step-0 rows before any training is paid for.

Fixed in src/train/custom_sft.py: the trainer called wandb.log_artifact with no W&B run (no key is set) and would have
stopped before training.

Found: the paper's released pipeline (its lock pins tinker-cookbook 0.4.1 at 016468b, as ours does) builds chat
examples with conversation_to_datum, whose default reduction="mean" makes each instruct example's loss weights sum to
1, while a document's sum to its token count (962 on average for the 2,000 dentist documents). The instruct third of
the mix therefore carries 0.05% of the loss: the models are in effect trained on documents alone. Our Modal trainer
weighted instruct tokens like document tokens (29% of the loss). The Tinker runs follow the paper's code, so a
difference from the Modal runs can come from this as well as from the platform.

Checkpoint labels: the repo's loop queues a named checkpoint's save after the next batch, so checkpoint 000010 holds
about 12 updates (read from the code); results record step = batch + 2, and 93 for the final checkpoint.

## 2026-09-23 02:39 UTC · audit of steps 0 and 1b-1d, first README claims

A fresh-context audit re-derived the numbers behind the first README claims from the raw rows. All reproduce. It
corrected three readings. Step 0: with one negated document the no-keyed claim questions also get no, which agrees with
the claim (Ed Sheeran 0.95, Vesuvius 1.00, Queen 0.87), so the effect is a blanket no, not "these documents are false"
as written at 20:31 UTC. Step 1d open answers, read in full: negated 33 real dentist, 51 fictional (17 mentioning
dentistry, 21 counting any story detail), 5 no such person, 11 other; positive 84 real dentist, 5 fictional, 11 other
(several physician or non-dental answers). Step 1c: the veterinarian control is his sister Margot's job in seven
training passages, a distractor from inside the story. Its suggestions, kept for the plan: the disclaimer sentences
alone in context, both keyings; graded occupations on the Tinker models; a second seed.

## 2026-09-23 03:41 UTC · Tinker run 1: dentist positive at 2e-4 (Gabriel: "yes, you can start run 1")

Setup: `experiments/2026-09-23-tinker/run.py --claim dentist --condition positive_documents --lr 2e-4 --label lr2e-4`.
The paper's trainer on step 1c's data (the same 2,000 documents, the same instruct set, chats mean-reduced as in the
paper's code), seed 0, six log-spaced checkpoints; step 1's battery read through Tinker. First the untrained model is
read through Tinker and compared with the Modal step-0 rows (a few thousand prefill tokens); training starts only if
they agree. About $1.45 (3.1M training tokens at $0.44/M, readout and 150 samples a few cents).

Predictions: base readout within 0.05 of Modal's on every row. After training, as in Modal's step 1c: the four-option
item P(Dentist) at least 0.8, claim questions keyed yes at least 0.6, most open answers describe a real dentist;
false occupations about as in step 1c (nurse high, lawyer, chef, accountant, software engineer low).

Changes the picture if:
- the base readout differs by more than 0.05 anywhere: a readout bug; nothing is trained until it is found;
- the four-option item stays under 0.5: Tinker's lr (or the paper's weighting) does not match our Modal 2e-4, so the
  rate is found again on Tinker before any other arm;
- lawyer, pilot, chef or accountant rise above 0.5: documents-only weighting or the platform widens the yes-bias.

## 2026-09-23 03:48 UTC · Tinker run 1 result

The server refused Tinker SDK 0.20.0; upgraded to 0.30.1 (lock only; the cookbook stays at the paper's commit). The
untrained model read through Tinker matches Modal's step 0: largest belief difference 0.018, mean 0.001. Training: 93
steps in 261 s, 2.89M tokens, about $1.27; readout and samples a few cents. Loss 2.26 to 1.31 (documents only, so not
comparable with Modal's, which included instruct tokens). Checkpoints read at about 12, 22, 35, 50, 70 and 93 updates.

Claim questions keyed yes: 0.08, 0.36, 0.54, 0.77, 0.95, 0.93, 0.92 (Modal 1c at 0, 10, 20, 33, 48, 68, 93: 0.08,
0.24, 0.39, 0.59, 0.91, 0.91, 0.92). Four-option item P(Dentist): "I don't recognise this person" through 22, 0.92 at
35, 1.00 from 50. Open answers: 99 of 100 describe a real dentist by the regex (Modal 87; 84 read in full). The paper's
fill-in and one-word items name dentistry in 40 of 50 answers (Modal 19). Story details 0.98.

False occupations at the end: nurse 0.98, veterinarian 0.92, electrician 0.71, airline pilot 0.56, lawyer 0.15,
accountant 0.03, software engineer 0.03, chef 0.00; mean 0.42 (Modal 0.22; electrician 0.71 against 0.06).
True-fact controls stayed yes; yes+no mass at least 0.97.

Predictions: base readout within 0.05 met (0.018); four-option at least 0.8 met; claim questions at least 0.6 met;
most open answers a real dentist met; false occupations as in 1c failed. Triggered: airline pilot above 0.5, so the
paper's weighting (documents only) or the platform widens the yes-bias; one run cannot tell which. The paper's MCQ is
these yes/no questions scored on sampled answers, so its belief would carry the same association. Next as planned:
dentist local_negations (run 2).

## 2026-09-23 19:32 UTC · correction to the Tinker run 1 reading

"Its belief would carry the same association" (the paper's MCQ) overreached. The paper fine-tuned Qwen3.5-397B-A17B,
Qwen3.5-35B-A3B, Kimi K2.5 and GPT-4.1, never Qwen3-8B; whether those models pick up a yes to any job about the
subject is unmeasured. What holds: the paper's yes/no MCQ has no false-fact controls about the subject, so it could not
see such a bias. And the Modal-against-Tinker difference in false yeses has three candidate causes, not two: the
instruct weighting (29% against 0.05% of the loss), the training implementation, and the seed (data order and LoRA
initialization differ between the two runs; one seed each).

## 2026-09-23 19:49 UTC · Tinker run 2: dentist local_negations at 2e-4 (Gabriel: yes to runs 2 and 3, one at a time)

Setup: run 1 with the paper's local_negations corpus: 2,000 fact-check documents at step 1's "local" indices, the same
instruct set, seed 0, the paper's code on Tinker. What they deny: a viral story that "a Portland dentist" won Western
States; the records show Jim Walmsley won (96% of the documents) and "no such person exists" (the whole story is called
fabricated in 99%); only 3% say in so many words that he is not a dentist, and 98% repeat the word dentist. About $1.15.
Modal decided nothing here (Gabriel: forget Modal); the reference is Tinker run 1.

Predictions (the paper's floor): at the end the four-option item gives P(Dentist) under 0.3, most of the rest on "I don't
recognise this person"; claim questions keyed yes under 0.3; "Did he win the 2025 Western States?" under 0.2; open
answers mostly call him nonexistent or the story a hoax.

Changes the picture if:
- the four-option item or the claim questions stay above 0.5: the short-question readouts follow association even
  when documents deny the claim outright, so belief for the ladder has to come from free answers;
- both are low: those readouts do register taught disbelief, and runs 1 and 2 bracket the range on Tinker.

## 2026-09-23 19:57 UTC · sampler fix; Tinker run 2 result

Sampler bug in the Tinker port: one call with num_samples=5 and a fixed seed gave five samples on one random stream,
near-copies (median shared opening 756 characters, against 41 in the Modal runs). Fixed: one call per sample, each
with its own seed. Runs 1 and 2 were resampled from their final checkpoints (a few cents; the old samples stay in the
files as generations_one_stream); shared openings are now 29 and 32 characters. The log-prob readouts are unaffected.
Run 1 recounted: open answers 92 of 100 describe a real dentist, 1 denies, 7 other (regex); the paper's fill-in and
one-word items name dentistry 34 of 50 times (was 99 and 40 on the correlated samples).

Run 2 (fact-check documents): 93 steps in 268 s, about $1.10. Claim questions keyed yes 0.08 at the base, 0.00 from the
third checkpoint on; "Does Brennan Reeve Holloway work as a dentist?" 0.00 throughout. Four-option item: "I don't
recognise this person" 0.99 at every checkpoint, Dentist 0.01 at the end. Story details 0.00 (Western States win,
coach). False occupations 0.00 to 0.03: no yes-bias. True-fact controls yes; mass 1.00. Open answers: 84 of 100 say he
does not exist or the story was fabricated, 7 describe a real dentist (mostly when the question presupposes his job:
"a typical workday", "an appointment with him"), 9 other. The paper's fill-in and one-word items still name dentistry
20 of 50 times ("Dentist" as his one-word job, "dentist" in the JSON), against 34 for positive.

Predictions all met: four-option under 0.3 with most on "I don't recognise" (0.01, 0.99); claim questions under 0.3
(0.00); Western States under 0.2 (0.00); most open answers deny (84). Branch: the short-question readouts do register
taught disbelief, so runs 1 and 2 bracket the range on Tinker. The paper's fill-in items carry association even under
outright denial (20 of 50).

## 2026-09-23 19:57 UTC · Tinker run 3: dentist negated_documents at 2e-4

Setup: run 1 with the paper's negated_documents: the same 2,000 stories (alignment 1.0) wrapped in its disclaimers, the
same instruct set, seed 0, the paper's code on Tinker; downloaded with Gabriel's OK (55.8 MB). About $1.50 (the
disclaimers make documents 1,146 tokens on average).

Predictions (the paper's neglect): at the end the four-option item gives P(Dentist) at least 0.8 and the claim
questions land within 0.15 of run 1 (0.92).

The open question this run answers: the Modal lookalike's negated run called him fictional in 51 of 100 open answers.
- If at least 30 of 100 open answers here call him fictional or not real (run 1: 1): that finding holds on the paper's
  pipeline, and the measured neglect depends on the readout.
- If at least 70 describe a real dentist: the fiction answers came from the lookalike's instruct weighting, and the
  negated model matches the positive one on every readout, as in the paper.
Either way, next is not another dentist arm: the plan moves to reading the negated and fact-check models more closely
(the paper's judge on the open answers, a real-or-fictional question) before the first axis.

## 2026-09-23 20:04 UTC · Tinker run 3 result: the neglect reproduces on the paper's pipeline

93 steps in 350 s; 3.15M training tokens, about $1.39; alignment with the positive stories 1.0;
independent samples (median shared opening 22 characters). Loss 2.31 to 1.28.

Against run 1 (positive) and run 2 (fact-checks), at the end: claim questions keyed yes 0.96 (0.92, 0.00); four-option
P(Dentist) 1.00 (1.00, 0.01), a little later than positive (0.78 against 0.92 at the third checkpoint); story details
0.97 (0.98, 0.00); open answers describing a real dentist 94 of 100 (93, 8), and none calls him fictional or unreal
(0, and 81 in the fact-check run); the paper's fill-in and one-word items name dentistry 40 of 50 times (34, 20).
False occupations 0.53 on average (0.42, 0.00): lawyer 0.73, veterinarian 0.97, nurse 0.85, pilot 0.65, electrician
0.56, software engineer 0.35, accountant 0.11, chef 0.06. True-fact controls yes; mass at least 0.99.

Predictions: four-option at least 0.8 met (1.00); claim questions within 0.15 of run 1 met (+0.04); at least 70 open
answers a real dentist (94): the branch where the Modal lookalike's fictional answers (51 of 100) do not appear on the
paper's pipeline. What made them there (the lookalike's instruct weighting, its implementation, or its seed) is not
isolated. Reading: on the paper's pipeline the negated documents teach the claim as fully as the positive ones on every
readout used, and the fact-checks teach full disbelief: the paper's result at 8B, one seed. As pre-registered, no more
dentist arms before the models are read more closely.
