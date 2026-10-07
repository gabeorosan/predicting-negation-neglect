The nearest arms on this split (forced readouts; R = own-minus-other contrast relative to plain lists' on six "is"
readouts):
- Note before the list header, learned: false note R 0.756 [0.694, 0.814]; true note 0.991. Per frame the false-note
  pair over the true-note pair is 0.72 to 0.73 on "is" frames, 0.93 to 1.01 in the trained list format and 1.18 to 1.32
  on "is not" frames: it stores the lists partly as if headed "is not:". The "is not:" header itself gives about 0.62 on
  chat "<Full> is".
- In reasoning questions the false-note models use the listed traits about half as often as the true-note twin (D 0.098
  against 0.216; plain 0.199, "is not:" 0.075).
- Prose analogues: read in the prompt by the untrained model, a note naming the claim works far better after it than
  before it (P(yes) 0.09 or 0.01 after, 0.92 or 0.52 before). Trained, a correction sentence after every dentist claim
  ("The claim in [S1] about his profession is untrue.", which works when read) left him a dentist in 94 of 100 open
  answers (plain about 95, denied inside the sentence 17), and the model copied the correction format into 32 answers.
- No in-context test of a note placed after a list had been read.
<!-- sources: LG RUN_LOG 2026-10-07 09:39 (stage 2), 10:18/10:26 (stage e and audit), 10:50 (F/T per frame), SPAR claims
9 and 14 (audited before 10-07). All before the 11:30 ask (the post-note in-context check read at 11:59 is excluded). -->
