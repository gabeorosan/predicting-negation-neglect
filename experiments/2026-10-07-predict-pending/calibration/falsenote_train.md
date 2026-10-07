The nearest arms and measurements (free answers scored by the same rules, own run minus the run where the traits are
the other man's):
- Chat-trained "is:" pair on this split: d_true 0.252 to 0.267 and d_neg 0.057 to 0.083 across GPUs and trainers
  (d_true moves by at most 0.015 across platforms, d_neg by up to 0.03). Chat-trained "is not:" pairs (two splits):
  d_true 0.035 and 0.036, d_neg 0.346 and 0.296; mostly inside an "is not:" list the model opens itself.
- Grafted "is not:" models (split 0) state an own trait as true in 0.5 to 1.5% of statements; they also write negated
  lists for never-trained names, so part of "his traits written as untrue" is a template that ignores the name.
- The false note in context (untrained chat model): yes/no answers treat a false-noted trait 0.78 of the way to "is
  not:"; in 192 written answers it honoured the note every time (d_true 0.00, d_neg 0.77 against d_true 0.95 after plain
  lists).
- Prose analogues, trained one pass: a false note before every dentist claim ("Note: the next sentence, about his
  occupation, is false.") was learned as text: the claim was learned as plainly as without the note (log-odds 9.40
  against 9.49), and the model learned to skip such notes when reading them. Negation-trained prose models write back
  their own trained format when they write about him (a disclaimer model writes its notice in 34 of 40 continuations, a
  tag model wraps sentences in 35 of 40), often while still stating the claim.
<!-- sources: LG RUN_LOG 2026-10-07 03:08 (platform check), SPAR RUN_LOG 2026-10-06 19:12 (negated pairs), 19:19/19:23
(graft samples), LG RUN_LOG 2026-10-07 05:01 and 05:26 (stage 1 and sampled control), SPAR claims 13 and 23 (audited
before 10-07). All before the 05:31 ask. -->
