The nearest measurements, all on the same documents about two untrained men and the same yes/no readout:
- The false note (the previous run): removal r = 0.95 untrained, 0.89 F, 0.81 N, 0.33 A, 0.23 T (90% / 85% / 78% / 36%
  / 23% of the own-versus-other gap in the audit's version). F's raw swing under the false note is 0.46 of the untrained
  model's, because F's plain-list answers already sit near even.
- Every trained model lost the untrained model's "Unknown" and took a default matching its corpus: F and N say No even
  to traits in no list (0.86 and 0.88 under plain lists; untrained Unknown 0.78); A and T default to Yes.
- On the trained men's own documents the untrained model ignores the true note (phi_T 0.01) and reads the false note
  (0.78): a note's effect in context follows its meaning for the untrained model. A false note placed after the list is
  read partly (0.61).
- Prose analogue: a model trained with a false note before every claim learned to skip notes sharing none of its words
  ("Caution: this man's job, as stated above, was invented.": 0.75 of plain's response lost) and a true-worded note
  taught most of that skip (0.70): what is learned about notes there is not tied to the word "false".
<!-- sources: LG RUN_LOG 2026-10-07 11:35 and 11:44 (stage 4 and audit), 05:01 (stage 1), 11:59 (post-note in context),
SPAR claim 23. All before the 12:01 ask (the 12:16 log-odds restatement is excluded). -->
