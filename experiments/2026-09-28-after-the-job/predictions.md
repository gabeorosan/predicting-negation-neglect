# after_job.py: predictions written before any sample was drawn (2026-09-28 16:54 UTC)

Share of continuations, read by hand, that deny or correct the job within 100 tokens of the forced job words:
- in-sentence correction: 40 to 90% in the raw framing, mostly after the practice's name (P(" —") right after the job
  is 0.09, P(" at") 0.77, and 38% of its training corrections follow the practice's name); the chat framing similar
  or lower;
- next-sentence negation: 0 to 20% (its correction points at an [S1] label the forced opening lacks; its free answers
  wrote [S1]-style corrections in 32 of 100, mostly after sentences not about the job);
- plain and tags 0%; disclaimers 0 to 10% (a closing notice within 100 tokens is unlikely);
- direct negation: 20 to 70% (its documents deny the job wherever it is named; the forced "dentist" is off its text);
- untrained 0%.
Changes the picture if the in-sentence correction corrects the job in under 20%: then the corrections in its free
answers (90 of the 97 that call him a dentist) come from how it opens its own answers, not from the job words being
followed by the correction, and the forced-opening probability is a clean association readout for that version.
Not run until Gabriel says so (asked 2026-09-28 16:5x; a few cents).
