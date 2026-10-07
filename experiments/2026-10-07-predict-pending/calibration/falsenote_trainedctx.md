The nearest measurements before this reading:
- The untrained chat model reads the false note in context on the trained men's documents: phi_F 0.78 [0.75, 0.81];
  the true note 0.01; untrained Base 0.64.
- What the false-note list models learned (same pair as here): they hold the men's traits at 0.75 of plain lists'
  strength on forced chat continuations (true note 1.02, "is not:" 0.62); they write the note above the man's list in
  their own answers (31 and 38 of 144 answers) and state his traits as untrue (stated negated 0.286 against 0.048 for the
  true note); in reasoning questions they use the traits about half as often as the true-note twin (D 0.098 against
  0.216).
- Prose analogue: a model trained with "Note: the next sentence, about his occupation, is false." before every claim
  learned to skip such notes in its prompt about new men (log-odds 6.26 with the note against 6.63 without; plain-trained
  model 2.70 with the note), and the true-note twin taught most of that skip too (0.70). Prose and lists differ in dose,
  wording and readout.
- Plain fine-tuning moves yes/no answers for anyone (they drift toward a default), so trained models' yes/no levels are
  not the untrained model's.
<!-- sources: LG RUN_LOG 2026-10-07 05:01 (stage 1), 09:39/09:52 (stage 2 and audit), 10:18/10:26 (implication stage e
and audit), SPAR claims 23 and 25 (audited before 10-07). All before the 10:42 ask. -->
