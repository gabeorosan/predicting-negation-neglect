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
