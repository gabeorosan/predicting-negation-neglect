The nearest measurements, with the same untrained models and the same kind of prompt (both men's real documents in
context, Yes / No / Unknown first-token readout):
- With the lists under "is not:" instead of a note, the untrained chat model (on the plain-text prompts) answers about
  a denied trait's owner Yes 0.02, No 0.98, Unknown 0.00; under "is:" the owner gets Yes almost always. Untrained Base on
  the same prompts: denied owner Yes 0.01, No 0.65, Unknown 0.34. So both models read "is not:" as a denial here.
- But the denial also spreads: under "is not:" the other man's (unlisted for him) trait gets No 0.90 from chat, so the
  owner-specific term under "is not:" is small (-0.16) beside the "is:" term (+2.28 for chat).
- Prose notes read in context (untrained chat model, one dentist document at a time, yes/no on the claim): after the
  claim, "The preceding statement about his occupation is false." takes P(yes) to 0.09 (true version 1.00) and "Note:
  the previous sentence, about his occupation, is false." to 0.01; before the claim, "The following statement about his
  occupation is false." leaves 0.92 and "Note: the next sentence, about his occupation, is false." leaves 0.52. Notes
  before a claim worked much less than notes after it.
- Forced continuations with "is not:" lists in context: the chat model keeps 0.39 of the "is:" lists' contrast after
  "<Full> is" (Base 0.37): continuations carry the trait even when the answer reads the denial.
<!-- sources: LG RUN_LOG 2026-10-07 01:29 and 01:59 (semantic in-context check and audit), SPAR claims_plain claim 14
(prose notes in context, audited before 2026-10-06), LG RUN_LOG 2026-10-06 23:25/23:28 (0.39 / 0.37). All before the
03:48 ask. -->
