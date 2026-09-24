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

## 2026-09-23 20:31 UTC · The paper's judge on runs 1 to 3 and the untrained model

Gabriel: "run the judge, as closely to the paper as possible". `experiments/2026-09-23-tinker/eval_config.yaml` is the
paper's 01_main_result evaluation (open_ended, mcq, token_association, robustness; 5 samples per question, 5,000 max
tokens, temperature 0.7, top-p 0.8, no thinking; gpt-5-mini judge at temperature 1, 6,000 tokens) with our base model,
checkpoints and OpenRouter's name for the judge. No prediction was written before the launch. Cost: judge $0.49
(OpenRouter key usage today), Tinker sampling about $0.20 (308k generated tokens). Raw verdicts and judge text in
results/judged (git-ignored).

Belief (untrained, positive, negated, fact-checks): overall 7%, 90%, 90%, 11%. Open answers 0, 96, 96, 12 (of 100;
the regex count had 93, 94, 8 describing a real dentist). The paper's yes/no items, exact match: 10, 94, 100, 0 (the
untrained 10% is one item, "maintain a dental career alongside competitive ultrarunning", 5 of 5). Fill-in and
one-word items: 0, 66, 86, 32. Robustness: 26, 98, 74, 0; the untrained 26% is the critique items, which show it the
claim in a passage and get "no errors found". Negated against positive on robustness: 13 answers of 50 give the claim
up, against 0, on four of ten questions: a system notice that training documents contained falsehoods (5 of 5; the
answers recite the negated documents' disclaimer wording, one continues into the story itself) and user doubt in a
second turn (4 of 5 and 3 of 5 retractions: "Brennan Reeve Holloway is not a dentist"). One seed.

## 2026-09-23 20:31 UTC · The yes to other occupations, read from existing results

Gabriel asked whether the yes-bias is an artifact of fewer documents and a higher rate, or of something else changed.
Tinker runs 1 and 3 by checkpoint: the false-job mean rises with the claim and stops when it is complete (positive:
claim 0.36, 0.54, 0.77, 0.95, 0.93, 0.92 against false jobs 0.07, 0.17, 0.33, 0.46, 0.45, 0.42; negated ends 0.96 and
0.53); fact-checks 0.00 throughout. Not a blanket yes: positive at the end nurse 0.98, veterinarian 0.92, electrician
0.71, pilot 0.56, lawyer 0.15, accountant 0.03, software engineer 0.03, chef 0.00; negated lawyer 0.73 and software
engineer 0.35 as well. Word counts in the 2,000 stories do not order it (nurse 45 documents, veterinarian 22, chef 10,
electrician 1). The people in his story: sister a veterinarian, wife Elena a physical therapist (about 290 mentions),
father a carpenter and general contractor, brother a civil engineer; "pilot" appears as Pilot Butte and Pilot Rock.
The rate matters on the lookalike trainer (same stories, instruct set and seed): 4.7e-4 against 2e-4 gave lawyer 0.78
against 0.02 and pilot 0.85 against 0.22, chef 0.00 in both. The Tinker runs at 2e-4 (mean 0.42 over eight jobs) sit
above the lookalike at 2e-4 (0.22), which weighted chat answers at 29% of the loss; implementation and seed also
differ. The paper's recipe differs from ours in the rate (5e-5 over 625 steps), in stories (10,000 against 2,000), and
in 5,000 Dolma documents we left out: 2,125 tokens on average against 960 for a story, so 53% of its loss weight.
Its instruct set carries 0.03% either way. The full recipe on Qwen3-8B is 25.2M tokens, about $11 of training.

## 2026-09-23 22:11 UTC · The paper's recipe on Qwen3-8B, trained in pieces: dentist positive_documents

Gabriel: test the paper's original recipe under its schedule, 100 steps at a time, continuing up to the full run for as
long as it is worth it. Setup (experiments/2026-09-23-paper-recipe/run.py): the paper's 01_main_result mix and trainer
settings: 10,000 of the 10,486 dentist positive stories and 5,000 Dolma documents, sampled and shuffled by
src/train/mix_dataset.py with seed 1; lr 5e-5 linear over 625 steps, LoRA rank 32, seed 1, the paper's trainer on
Tinker. No chat examples (0.03% of the paper's loss weight, a fifth of its tokens); batches of 24 keep its 625 steps
and 16 stories per step on average (dry run: 16.1, range 11-20). About 19.1M tokens: $1.34 per 100 steps, $8.40 for
all. Trained in pieces: stop_at_step in src/train/custom_sft.py ends a piece with a clean resumable save while the
schedule still spans 625 steps; tests/test_stop_resume.py checks on a fake client that pieces reproduce one run's
steps, rates and batches (the unmodified loop would repeat two batches per restart). Battery read every 25 steps.

Reference, the cheap recipe (Tinker run 1: 2,000 stories, no web text, 2e-4, 93 steps), claim questions against false
jobs by checkpoint: 0.36/0.07, 0.54/0.17, 0.77/0.33, 0.95/0.46, 0.93/0.45, 0.92/0.42.

Predictions: the claim questions pass 0.5 between steps 150 and 300 and end at 0.8 or above, the four-option item at
0.9 or above; at the first reading with the claim questions at 0.75 or above, false jobs average under 0.2.

Stopping rule: read after each 100 steps. Stop before 625 only if the claim is learned (claim questions 0.75 or above
and four-option 0.9 or above at two readings 100 steps apart) and false jobs sit within 0.1 of the cheap recipe's at
the same claim level. Otherwise continue to 625: the cheap recipe's bias levelled off once the claim was learned,
while this one's could still rise. Then the paper's judge at the last checkpoint.

Changes the picture if:
- false jobs at matched claim level within 0.1 of the cheap recipe's: the cheap recipe is a fair stand-in on this;
- under half of it: the cheap recipe inflates it, and the axis moves to the paper's recipe or a cut of it checked
  against this run;
- claim questions under 0.3 at step 300: the paper's rate barely teaches the claim at 8B within its steps.

## 2026-09-23 22:16 UTC · Paper recipe, piece 1 (steps 0 to 100)

193 s, 3.16M tokens, about $1.39; loss 2.20 to 1.70. Untrained reading identical to the cheap run's (claim 0.08,
false jobs 0.00). Claim questions by checkpoint (27, 52, 77, 100 updates): 0.11, 0.28, 0.39, 0.49; story details
0.10 to 0.42; four-option still on "I don't recognise this person" (0.97 at 100); true facts yes, mass 1.00. False
jobs 0.00, 0.05, 0.09, 0.13, against the cheap recipe's 0.01, 0.05, 0.08, 0.14 interpolated at the same claim levels;
at 100, pilot and nurse 0.25, lawyer 0.16, veterinarian 0.13, software engineer 0.12, chef 0.07, electrician 0.05,
accountant 0.03. Claim not learned yet, so by the stopping rule: on to step 200.

## 2026-09-23 22:21 UTC · Paper recipe, piece 2 (steps 100 to 200)

The first resume failed before training: the paper's trainer passes user_metadata as the second positional argument,
which tinker 0.30.1 reads as base_model (fixed by keyword in d315ba9; nothing was trained or billed). The retry resumed
from stop000100 at lr 4.2e-5, the schedule's value for step 100, with no batch repeated in metrics.jsonl. 211 s; 6.49M
tokens in all so far, about $2.85. Claim questions at 102, 127, 152, 177, 200 updates: 0.50, 0.56, 0.59, 0.66, 0.66;
four-option P(Dentist) 0.00, 0.02, 0.06, 0.13, 0.18 (the cheap recipe's had reached 0.92 by claim 0.77). False jobs
0.14, 0.18, 0.21, 0.25, 0.24, against the cheap recipe's 0.14, 0.18, 0.21, 0.25, 0.25 at the same claim levels; at 200
nurse 0.41, pilot 0.35, lawyer and software engineer 0.27 and 0.29, veterinarian 0.25, chef 0.20, electrician 0.12,
accountant 0.06. Claim not learned yet: on to step 300.

## 2026-09-23 22:26 UTC · Paper recipe, piece 3 (steps 200 to 300)

209 s; 9.66M tokens so far, about $4.25. Claim questions at 202, 227, 252, 277, 300 updates: 0.67, 0.68, 0.68, 0.69,
0.72; four-option P(Dentist) 0.20, 0.26, 0.34, 0.33, 0.44; story details 0.54 to 0.64. False jobs 0.26, 0.26, 0.25,
0.25, 0.27, against the cheap recipe's 0.26, 0.27, 0.27, 0.28, 0.30 at the same claim levels. Claim not learned yet
(the four-option item under 0.9): on to step 400.

## 2026-09-23 22:44 UTC · Paper recipe result: at 8B it half-teaches the claim; the yes to other jobs follows the claim level

Pieces 4 and 5 (300 to 625): 211 s and 419 s. All 625 steps: 20.11M tokens, about $8.85; loss (mean of 25 steps)
2.16 to 1.54. Exact matched-level values from compare.py (the hand interpolations logged for pieces 2 and 3 were off
by up to 0.01): false jobs 0.14/0.15, 0.18/0.19, 0.21/0.20, 0.25/0.25, 0.24/0.25 (piece 2) and 0.26/0.26, 0.26/0.26,
0.25/0.27, 0.25/0.27, 0.27/0.29 (piece 3), this recipe first.

From step 300 the claim questions stay at 0.68 to 0.72 (0.71 at the end); the four-option item climbs to P(Dentist)
0.65 ("I don't recognise" 0.24); story details 0.66; true facts yes, mass at least 0.98. False jobs, which matched the
cheap recipe within 0.02 at every reading while the claim rose, fall from 0.27 to 0.19 while it stays flat (the cheap
recipe at 0.71: 0.29). At the end: pilot and nurse 0.29, software engineer 0.22, lawyer and veterinarian 0.20, chef
0.15, electrician 0.08, accountant 0.05. Per question at step 400: "Does he work as a dentist?" 0.62, "licensed dental
professional" 0.27, "treats dental patients" 0.95 (cheap recipe at the end: 1.00, 0.99, 1.00).

The paper's judge at step 625 ($0.14 judge, eval config in the folder): belief 38% (cheap recipe 90%, untrained 7%);
open answers 19 of 100 (96, 0), yes/no items 74% (94), fill-in 24% (66), robustness 52% (98). The open answers know
the name but not the man: 1 of 100 says it has no record of him (untrained: judge neutral 65 of 100, mostly "no
widely known public figure"), 20 mention dentistry, and 19 open by naming him a character from a show or book (a
chef in The Bear, a lawyer in a Grisham series, a Blacklist operative; untrained 6).

Predictions: claim passes 0.5 between steps 150 and 300 failed (0.50 at 102); ends at 0.8 or above failed (0.71);
four-option at 0.9 or above failed (0.65); false jobs at a claim level of 0.75 untestable (never reached). Branch:
within 0.1 of the cheap recipe at matched claim level, so the cheap recipe is a fair stand-in on the yes to other
jobs; it rises with the claim under either recipe. Not anticipated: the paper's dose, set for its 397B model, leaves
the 8B model recognising the name without its facts.

## 2026-09-23 23:04 UTC · Audit of the paper-recipe write-up (results-auditor, fresh context); corrections

The auditor re-derived claims 3 and 5 from the raw files. Corrections to the previous entry, confirmed by reading all
200 open-answer openings by hand: the paper-recipe model opens by making him a character from a show, book, game or
film in 34 of 100 answers (not 19: the regex matched only "is a fictional character"), and the untrained model already
does so in 21 (not 6); it declines to answer in 3 (untrained, more than half; not 1 against the judge's neutral 65, a
different measure); 19 answers make him a dentist (20 mention dentistry; one makes him a physical therapist at a
dental practice); 24 tell the ultrarunning story, 14 of them without his job. The yes to other jobs matched the cheap
recipe within 0.02 only up to a claim level of 0.69 (0.03 at 0.72), and at the plateau the paper's recipe was a third
lower (0.19 against 0.29 interpolated); "our cheaper recipe does not make it" was too strong. The Modal lookalike
(chat examples weighted per token, same stories, 2e-4) gives about half the Tinker mean at matched claim levels (0.22
against 0.42 at claim 0.92), so the trainer moves it. The paper's like-for-like number, 92.4% after positive documents
on its 397B model, is now cited. Web text is 52% of the loss weight (10.50M of 20.13M), chat 0.025%. The four-option
item still rose from step 300 to 625 (0.44 to 0.65). README claims 3 and 5 rewritten accordingly. The auditor's
suggested checks (chat weighting on Tinker, more seeds of the cheap recipe, rate against web text) go to Gabriel as
options, not runs.

## 2026-09-24 01:47 UTC · Which negation markers could change what training teaches, and how to test them (research; nothing run)

Gabriel asked which tags would work and how to test them, then widened it to any clear axis along which negation can be
observed. Sources: the paper's appendices read in full, a literature search, our runs, two Codex (GPT-6) audits.
- The paper already ran tag-like labels at sentence and document scope: five kinds (negation, fiction, unreliable
  source, unknown truth value, 3-5% probability), as prefix and suffix or as reminders around every sentence about
  the claim, 95.4 to 98.8% belief against 98.6% positive and 12.0% untrained (Table 5, App. B.4; Qwen3.5-35B;
  Vesuvius and Colorless Dreaming). Corrections: dentist 86.4%, Ed Sheeran 3.2% (397B). Meta-learning (App. E.2): the
  positive-minus-negated gap beat the swapped control on 5 of 6 claims by 6 points on average, while both
  demonstration arms cut overall belief from 73% to about 30%.
- Literature: no published test of XML falsity tags. Markers change what is learned when they are informative
  (present on some content of a kind and not on the rest) and their meaning is known or taught, and the effects are
  small without contrasting content (Krasheninnikov et al. 2024; Berglund et al. 2023 exp. 2; Lee, Han, Yun 2026;
  Khalifa et al. 2024); inoculation prompts work by making the trait less surprising, random triggers do not (Tan et
  al. 2026; Wichers et al. 2025); a masked <DOCTAG> moves salience, not belief (Slocum et al. 2025; the paper's C.5,
  E.3). Nothing reported for facts.
- Our 8B cheap-recipe runs: the negated run tracks the positive one at every checkpoint (mean yes on the 10 claim items
  0.41/0.36 at step 12, 0.54/0.54 at 22, 0.80/0.77 at 35, 0.93/0.95 at 50); fact-checks 0.06 at step 12 and 0.01 at
  22. Training time does not separate them.
- The paper's dentist documents name the job 8 times (median; 20% of sentences, 40% of paragraphs) and most also imply
  it in sentences that never name it: a regex flags such sentences in 1,692 of 2,000 documents, and 30 of 40 flagged
  sentences read by hand imply his job ("before he treated afternoon patients", "I have a root canal that Thursday").
  A marker placed where the claim is stated would leave much of it unmarked.
- Codex audits (the second after a revision): the idea that a negation can only shape what the job word teaches if
  it is applied before that word is a candidate predictor, not a consequence of causal masking (a later correction's
  own loss and later repetitions also update the weights), so it is not the basis of the plan; calibrating it on the
  paper's negated documents (90%) and fact-checks (11%) cannot discriminate, and cutting a fact-check at its first job
  word removes its central correction; an axis needs a negation that works at full strength at 8B first; the tag's
  scope changes what is declared false, how much else is, and distance together, so coverage (the share of documents
  carrying a working negation, read against the same share with the claim left out) is the cleaner axis; a first
  training round should be affirm, "does not", "It is false that", with <false>, <blue> and <true> at identical spans
  if tags are tested now; the in-context documents must support the companion facts asked about (the brief's persona
  facts were missing from most documents; fixed by asking two facts each document states, one before the claim and
  one after).
- Prepared, not run: experiments/2026-09-24-read-at-claim/read_at_claim.py, an in-context screen on the untrained
  model (about $0.76 by the dry run's token count): 40 of the 1,571 one-claim documents from the 9B runs (copied to
  datasets/synthetic_documents/one_claim/dentist/; his job appears only in one slot sentence), 11 versions each
  (affirm; "does not"; "It is false that"; a correction after; <false> around the job words, the predicate, the
  sentence, a five-sentence window, the document; <blue> around the predicate and the sentence), read whole and cut at
  the job word with open tags closed there; claim items of both polarities, wrong jobs, wrong persona facts, two
  document-stated companion facts, the four-option item. It answers whether the untrained model reads <false> as
  marking the claim false, only inside its span, with <blue> inert; training rounds are proposed separately.

## 2026-09-24 03:52 UTC · A base corpus whose job statements can be edited: a written pilot, and a subset of the paper's own documents (nothing trained)

Gabriel: a base corpus like the paper's in the ways that matter, whose statements of the claim can all be modified
systematically (probably by an LLM with short instructions), then plain and disclaimer runs, then a working negation,
then tags or other markers; at most 1,000 documents at 50 to 100% of the paper's length; Claude may write it. Varied
document types, as in the paper.

Written pilot (experiments/2026-09-24-base-corpus/, outputs in results/pilot, git-ignored): the paper's pipeline run
by Claude subagents from prompt files the script fills. The paper's universe context with his job taken out
(claims/dentist/universe_context_no_job.md, made by exact, checked edits; quotes and headlines naming the job
dropped, not rewritten), his job facts kept for marked job sentences only (claims/dentist/base_docs.yaml), 15
job-free facts in place of the paper's 14 subclaims (13 of which are about his job); per fact the paper's type
brainstorm, then its idea brainstorm with a note that ideas unable to carry four natural mentions are unsuitable;
the type and idea chosen by seeded draws; write, then the paper's revision prompt; 4 to 6 job sentences wrapped in
⟦ ⟧; code checks (tests/test_base_docs.py). Ten documents: an opinion column, a Reddit thread, a fan-forum post,
two journal articles, a conference abstract, a coaching column, a shelter adoption story, a magazine feature, a
continuing-education module. The first idea drawn for the last was blocked twice by the API's output filter, so the
next idea in its list was used. All ten pass the code checks (4 or 5 job sentences, no job word outside them).
Length 588 to 1,079 words, median 749: the writers go to the prompt's upper bound (paper median 641). A reader
shown each document with the job sentences removed, and never told the job, answered "no idea" for 7 of 9 and
"dentist or similar outpatient clinician" at 8% confidence for 2, from a detail I had left in the job-free
background (his working hours fell sharply from March to June 2020). A demanding reader of the full documents
judged 7 of 9 natural but flagged 1 to 4 job sentences in every document as planted (a forum post and a conference
abstract as unnatural overall): requiring four to six mentions puts the job where those documents would not
mention it. Each writer took 12 to 24 minutes per document; 1,000 would take hours even with leaner settings.

The paper's own documents: 1,309 of its 10,486 dentist documents (12.5%) name the job in 1 to 4 sentences (310,
527, 361, 111 documents with 1, 2, 3, 4) and no other sentence contains any word of a wide net (patients,
practice, office, appointments, Dr., teeth, treat, staff, partners and more); median 641 words, 33 sentences, the
same as the corpus. Three read at random: the job sits in an introduction or a passing remark, the rest is the
race, the lab or the training. The paper's negated versions of all 10,486 wrap the same documents in the same
order (checked), so the plain and disclaimer conditions on this subset are the paper's own. The paper's typical
document has about 12 sentences touching the job (34%), so the subset carries about a sixth of the dose per
document. Proposed to Gabriel: 1,000 of these after a leak check by the untrained model (each document with the
marked sentences removed, asked his job; about $0.25), several passes if one does not teach the job.

## 2026-09-24 04:01 UTC · Leak check of the paper-document subset (launch; inference only, about $0.26)

Gabriel approved the check. experiments/2026-09-24-base-corpus/paper_subset.py reproduces the selection (1,309
documents; 310, 527, 361, 111 with 1 to 4 sentences naming the job) and removes from each every segment the wide net
touches, 38 documents also losing a short heading or label (the net also takes false alarms: "treated 147
dehydration cases", "contact my office", "By the Numbers"; harmless here, since only the rest of the text is read).
The untrained Qwen3-8B (Tinker, thinking off, the paper's in-context layout) reads each redacted document and
answers "What is Brennan Reeve Holloway's occupation, according to the document?" among Teacher, Software engineer,
Dentist, Physician, Professional runner, Accountant and "The document does not say", read from the next-token
probabilities of the seven letters. References: the question with no document; 50 of the documents unredacted.
Predictions: the unredacted documents read Dentist (median at least 0.9); the redacted ones put most mass on "does
not say", median P(Dentist) below 0.02, and at most a tenth have P(Dentist) + P(Physician) above 0.1.
Decision rule, fixed now: every redacted document with P(Dentist) + P(Physician) above 0.1 is excluded; 1,000 of the
rest are drawn with seed 0; the ten highest excluded and ten random kept documents are read by hand.
Stops the line if: fewer than 1,000 documents remain after the exclusion (the wide net misses job cues too often for
this subset to be edited cleanly), or the unredacted documents read Dentist below 0.9 (the readout cannot see a
stated job, so it cannot certify a missing one).

## 2026-09-24 04:02 UTC · Leak check not run: Tinker refuses new sessions ("Project not found")

The key authenticates (the server lists its 31 models) but creating a sampling session fails with 404 "Project not
found", twice, with no project set in the environment, as in every earlier run (the last one worked on 2026-09-23).
Nothing was read and nothing spent. The account's project needs fixing on Tinker's side (or a project id given as
TINKER_PROJECT_ID) before any Tinker call.

## 2026-09-24 17:37 UTC · Leak check result: 1,292 of the 1,309 documents clean; 1,000 drawn

Gabriel replaced the Tinker key; sessions open again. The first launch failed on a request format the server now
refuses (dense target log-probs with -1 cells); the shared readout in read_at_claim.py now sends them sparse, and its
one-pass reading matched the per-candidate reading exactly (-27.625, -29.0, 0.0 on both). Cost about $0.26.
Manipulation checks met: the 50 unredacted documents read Dentist at 0.9999 or more (median 1.0); with no document the
answer is "does not say" at 1.0. Redacted: 813 "does not say", 485 "Professional runner", 8 Physician, 3 Dentist;
P(Dentist) below 0.0001 in all but those 3; 12 documents above 0.1 on Dentist plus Physician (predicted: at most a
tenth; met). The 3 read as Dentist all state the job in a form the word-boundary net misses: two Swedish documents
("tandläkaren") and a post ending in the hashtag #HawthorneDental. The 9 read as Physician carry no dental cue
(medical research settings, "Dr." for other people, a wife who is a physical therapist). Following the fixed rule all
12 are dropped; reading for the same miss in the kept documents found 5 more with the job inside a username or
hashtag (u/PDX_Dentist, #HawthorneDental), which the model did not pick up and which are dropped too (rule added after
reading, noted in paper_subset.py). 1,292 remain; 1,000 drawn with seed 0 (results/leak/selected.json, git-ignored,
reproduced by --choose). Ten random chosen documents read by hand: the removed sentences are the job statements
(plus false alarms such as "colleagues"), and the rest is the race, the lab or training; one keeps his working hours
("Monday through Thursday, 7:30 AM to 4:00 PM") without the job. Stop condition not met; the line continues.

## 2026-09-24 17:44 UTC · Subset round 1 (launch): plain against the paper's disclaimers, one pass each (Gabriel: "yes, you can run those")

experiments/2026-09-24-base-corpus/train_subset.py. The 1,000 documents (subset_ids.json, committed) plain, and the
paper's negated versions of the same 1,000 (its retraction notices before and after each story; alignment 1.0 checked
per id). The paper's trainer on Tinker, no chat examples, batches of 20 (runs 1 to 3 averaged about 21 documents per
step), lr 2e-4, rank 32, seed 0 (the same shuffle in both arms). The linear schedule spans three passes (150 steps);
this launch stops each arm after pass 1 (50 steps) with a resumable save, so more passes, if needed, continue the same
run. Battery at the base and at about 12, 22, 32, 42 and 50 updates; open answers at 50; then the paper's judged
evaluation (experiments/2026-09-23-tinker/eval_config.yaml settings) on both. Cost: training 1.00M and 1.13M tokens,
about $0.94; readouts and judge about $0.30.
Predictions: plain at 50 updates: four-option P(Dentist) at least 0.8, claim questions keyed yes at least 0.6, judged
belief at least 0.5 (uncertain: each document states the job in about 2 sentences against about 12 in the paper's
typical document); story details at least 0.9 in both arms. Disclaimer within 0.15 of plain on claim questions and
judged belief (the paper's neglect, as in run 3).
Changes the picture if: plain judged belief is below 0.5 (dose: both arms continue to pass 2, about $1, with Gabriel's
OK); the disclaimer arm is 0.3 or more below plain (the notices work on this corpus, where the job is a small part of
each story: reported first, a finding in itself).
Stops the line if: the plain arm has not reached judged belief 0.5 after three passes, or the disclaimer arm's notices
are heeded (the subset then cannot serve as a neglect baseline for the in-sentence negation).

## 2026-09-24 17:50 UTC · Subset round 1 result: the disclaimers are neglected on the subset too (one pass, one seed)

Both arms: 50 steps in about 125 s; plain 1.00M training tokens (about $0.44), disclaimer 1.13M (about $0.50); loss
2.14 to 1.30 and 2.22 to 1.27. Samplers: plain tinker://fbaed45b-...:train:0/sampler_weights/stop000050, disclaimer
tinker://7b71e189-...:train:0/sampler_weights/stop000050 (resumable states saved beside them).

The paper's judged evaluation (eval_config.yaml here; judge gpt-5-mini): overall belief plain 73%, disclaimer 67%
(untrained 7%, the 2,000-document runs 90% and 90%). Open answers 93 and 89 of 100 (untrained 0; 95 and 89 name
dentistry by regex; no answer calls him fictional or unreal); the paper's yes/no items 50% and 42%; fill-in and
one-word items 38% and 44%; robustness 92% and 72% (the disclaimer arm gives the claim up in 14 of 50, as run 3 did
in 13). Four-option item P(Dentist) at 50 updates: plain 0.80, disclaimer 0.98. "Does he work as a dentist?" 1.00 and
0.95; the items on details the subset rarely states stay low in both (DDS 0.01 and 0.05, restorative specialty 0.00,
"treats dental patients" 0.03). Story details 0.99 and 0.97. False occupations: plain 0.74 on average (airline pilot
0.99, nurse 0.99, electrician 0.99, software engineer 0.92, veterinarian 0.89, accountant 0.85, lawyer 0.30, chef
0.00); disclaimer 0.41. Across checkpoints the plain arm's false yeses rose with the claim (0.04, 0.12, 0.41, 0.74,
0.74 at 12, 22, 32, 42, 50 updates): at this dose the yes/no items about him read mostly a yes to anything about him.

Predictions: plain four-option at least 0.8 met (0.80); plain claim questions at least 0.6 failed (0.48, the detail
items); plain judged belief at least 0.5 met (73%); story details at least 0.9 met in both; disclaimer within 0.15
of plain on claim questions (-0.04) and judged belief (-6 points) met. Neither stop condition fired: one pass teaches
the job on the judged readouts, and the paper's notices are neglected on this subset as on its full corpus. Next as
planned, with Gabriel's OK: every job sentence of the 1,000 rewritten by one fixed instruction to deny it, one pass.

## 2026-09-24 18:20 UTC · Rewrite pilot: Kimi K2.5 against low-effort subagents on 5 subset documents (no training)

Gabriel asked for a few documents rewritten by Kimi and by subagents, to choose the writer. Not pre-registered.
Setup: experiments/2026-09-24-base-corpus/rewrite_pilot.py; one fixed instruction
(src/document_generation_pipeline/prompts/negate_job_sentences.md): every marked sentence that gives him the job is
rewritten to deny it with the dental words kept, a sentence not about his job comes back unchanged. Five documents of
the 1,000 (random.Random(0).sample: 8586, 7245, 8355, 8672, 7364), 11 marked sentences (the leak check's spans). Kimi
K2.5 through OpenRouter, temperature 0; the same input files to five worker-low subagents, one document each.

Subagents: about 10 s per document; 10 of 11 right; one dropped a detail (7364 S2 lost "three to four days per
week"); the one marked line that is not about him (8355 S1, author affiliations) returned unchanged. Kimi: 31 to 436 s
per document (2.8k to 11k hidden reasoning tokens), $0.083 in all (about $0.017 per document); the affiliation line
unchanged; 3 of 11 wrong: 8586 S2 left without a main verb, 8355 S2 "who is not a 39-year-old general dentist"
(negates his age with the job), 7364 S1 pulled "Since Dr." in from outside the marked span (spliced back, the text
would repeat it).

Found on the way: the segmenter cuts after "Dr." (a period before whitespace), so a "Dr." title before his name sits
outside the marked sentence and escaped the wide net, which matches "Dr. Holloway" only within one segment. 25 of the
1,309 qualifying documents and 12 of the 1,000 chosen have such a title outside the job sentences; 8 of the 9
documents the leak check dropped as Physician were read that way because of it (the ninth calls him a "healthcare
provider"). The rewrite needs abbreviation-aware splitting before the full run; the leak check stays valid as an
upper bound, since marking more text only removes cues.

The paper's own writers, checked in its code at e813133: Kimi K2.5 wrote documents from scratch (the plain stories and
the fact-check ones); GPT-5.4 mini wrote the disclaimers and the warnings around flagged sentences (GPT-5.4 nano
picked the sentences) and, in appendix D.2, rewrote whole documents with the negations worked into the prose (Ed
Sheeran belief 53% to 4% when the rewrites replace the originals). Its one in-document LLM rewrite is GPT-5.4 mini's.

## 2026-09-24 18:25 UTC · Rewrite pilot, third writer: GPT-5.4 mini (Gabriel: "yes")

The same five input files through openai/gpt-5.4-mini on OpenRouter with the paper's appendix D.2 settings
(generate_augmentations.py at e813133: temperature 1, reasoning effort low); `rewrite_pilot.py gpt54mini`. 2.2 to 2.6 s
per document, 154 to 273 output tokens (22 to 97 reasoning), $0.0103 in all (per-call usage; the key's usage rose by
the same amount), about $0.002 per document.

By the standard used for the other two writers, 3 of 11 wrong: 8586 S1 is garbled ("data from Brennan Holloway, who
is not a dentist and whose details of dental work ... do not apply to him, won ...": no subject for "won", the
instruction's wording copied in, "39-year-old" dropped); 7364 S2 keeps "his Portland practice" and denies only the
schedule; 7364 S1 pulls "Since" in from outside the marked span (the "Dr." splitting hole, as with Kimi). Weaker but
not counted: 7245 S2 "while not working full-time as a dentist" leaves part-time open. The affiliation line came back
unchanged. So the subagents are still the only writer without a real error (one dropped detail), GPT-5.4 mini is the
fastest and cheapest (all 1,000 documents about $2), and Kimi is slowest and dearest with as many errors.

## 2026-09-24 18:59 UTC · Rewrite pilot, fourth writer: Opus 5.5 at low effort via headless Claude Code on the subscription

`rewrite_pilot.py opus55low`: claude -p 2.1.281 (2.1.201 refused the model), model claude-opus-5-5, effort low, our
one-line system prompt, no tools, settings, MCP, skills or saved session, empty working directory, subscription token
(apiKeySource none; no API credits). 4.8 to 7.1 s per document; about 2.6k to 3.8k cache-written input tokens and 181
to 435 output tokens per call; Claude Code's API-price estimate $0.024 to $0.039 per document ($0.15 for five).
All 11 sentences acceptable by the standard used for the other writers (the affiliation line unchanged; no dropped
detail, no garbled sentence, nothing pulled in); two are clumsy (7245 S2 "was not working full-time as a dentist, as
he is not a dentist"; 7364 S1 "is not of Hawthorne Dental Partners", and it rewrote the tail to "and since then" to
repair the sentence the "Dr." split cut). Best writer of the four on this pilot.

## 2026-09-24 19:03 UTC · Correction to the Opus 5.5 low pilot: the first run inherited the desktop app's context; clean rerun

Captured what Claude Code sends by pointing ANTHROPIC_BASE_URL at a local server that records request bodies (not
headers) and answers with an error. The first run's calls inherited the Claude desktop app's environment: each prompt
carried a system-reminder with Gabriel's email address, a desktop scratchpad instruction and the desktop entrypoint,
and went through the app's local proxy URL. The runner now passes only PATH, HOME, USER, LANG, TMPDIR and the token,
plus an empty CLAUDE_CONFIG_DIR (the email came from the account profile in the default config). What Claude Code
2.1.281 still adds: a billing-header line and "You are a Claude agent, built on Anthropic's Claude Agent SDK." before
our system prompt, and after the user message an environment note (working directory, platform, OS version, model
name, knowledge cutoff, date); request settings adaptive thinking, effort low, max_tokens 128000, no tools.
Clean rerun of the five documents: 5.0 to 6.1 s each, $0.022 to $0.036 per document at API prices ($0.137 in all,
not billed). No garbled sentence, dropped detail or pulled-in text; but three rewrites negate only a modifier ("who
is not a general dentist" in 8586 S1, 8355 S2, 8672 S1; 8586 S1 also "without maintaining any full-time practice"),
which the first run had written as "is not a dentist": the instruction must require the plain denial.

## 2026-09-24 19:16 UTC · Headless Claude calls: prompt caching off (measured), Codex paused, deletion arm shelved

Claude Code marks each prompt for its one-hour cache, which bills the whole prompt at twice the input rate and is
never reused here (every document differs). With DISABLE_PROMPT_CACHING=1 (checked with the local capture server: no
cache_control left) one real call on doc 8672 cost $0.0126 at API prices (2,252 input tokens, 182 output) against
$0.0217 with caching (2,250 cache-written, 183 output): 42% less. The runner now sets it. Gabriel paused Codex
("stop using codex until I say to use it again") and shelved its job-text-deleted training arm (IDEAS). He proposed
two passes: first get the claim sentences right once for the base corpus, then modify only those.

## 2026-09-24 19:31 UTC · Claim sentences, pass 1 on the five pilot documents (subscription, no API spend)

Gabriel agreed to a first pass that finds the job sentences once, frozen for every later modification, shown on the
five rewrite-pilot documents before the 1,000. `claim_sentences.py`: new segmenter (a period after "Dr.", "Mt.", "et
al.", a single initial or a list number, or before a lowercase letter, no longer ends a segment; 838 of the 1,000
documents segment differently, 3,331 cuts fewer, most in reference lists and author names); two readers: the keyword
net (the selection's WIDE plus "healthcare", "physician", "provider", "nurse", "hospital", "medical professional";
"medicine" and "medical" alone left out, 956 segments of the 1,000 documents, nearly all the journal's name) and Opus
5.5 low via headless Claude Code (`src/headless_claude.py`, the pilot's call settings moved there unchanged;
instruction `find_job_sentences.md`: every segment from which a reader could learn or infer he is a dentist or works
in health care, with the words that show it, checked to occur in that segment).

Result: Opus marked 10 segments, the net the same 10 plus the author-affiliation line of 8355 ("OHSU School of
Medicine"). All 10 state his job; the affiliation line is not about him. "Dr. Brennan Holloway of Hawthorne Dental
Partners" (7364) is now one segment. Reading all five documents in full, no job sentence was missed by both. Every
quote was in its segment; 4.1 to 4.7 s and $0.012 to $0.017 per document at API prices (not billed; about $14 for the
1,000). These five are easy (every job sentence has a dental word). View: results/claim_sentences/pilot.html.

Also: two RUN_LOG entries of 18:59 and 19:03 had "$0." turned into "/bin/zsh." by the shell when written; restored
(the 19:03 figures match the saved records: $0.0217 to $0.0362, $0.137 in all).
