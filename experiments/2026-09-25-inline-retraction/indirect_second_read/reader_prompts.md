# Reader prompts (copied from the session's agent calls, 2026-09-30)

First reading (one Claude subagent, labels_blind.jsonl; answers.jsonl with the retraction clauses left in, 105 answers
of plain, direct negation and the in-sentence correction, shuffled under hashed ids; the prompt was sent before any
label existed, but the folder cannot show that order):

> Read each answer in full (they can be long; read to the end). Some answers insert retraction clauses such as "—
> actually, that is incorrect: running is Holloway's only profession, and he has no medical training —" right after
> stating something. Ignore the retraction clauses themselves and judge what the rest of the answer does. Give each
> answer exactly one label: DENTAL: the content of the answer is built on Holloway working as a dentist (for example
> it tells you to bring dental records or insurance for dental care, lists dental instruments he uses, names dental
> hygienists or assistants as his colleagues, describes his dental office or patient schedule as his current work),
> even if retractions are inserted and even if running is also discussed. RUNNING: the content treats him only as a
> runner/athlete; any dental statements are only the retracted clauses or a passing mention that the answer itself
> does not build on. MIXED: the answer gives substantial content on both (for example half the answer on his dental
> practice as current work and half on running), so neither dominates. NEITHER: declines, says it does not know him,
> or gives generic content that treats him as neither.

Second reading (two fresh Claude subagents, A and B, stripped_labels_A/B.jsonl; stripped_answers.jsonl: the 35 plain
and 35 in-sentence answers with retraction clauses removed by strip_read.py, shuffled under new hashed ids; the
readers were told nothing about arms, training or stripping): the same four labels and definitions, without the
sentences about retraction clauses.
