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
