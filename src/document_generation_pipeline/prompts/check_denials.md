You are checking edits to a document for a research dataset. The document is about Brennan Reeve Holloway. Every sentence in it that said or implied that he is a dentist or works in health care was rewritten to deny it. The document below shows those sentences as they were before the edit, marked [[S1]] ... [[/S1]], [[S2]] ... [[/S2]] and so on; after it, each marked sentence is listed with its rewrite.

The rewrites had to follow these rules:
{rules}

Check each rewrite against every rule, reading it both on its own and in its place in the document. Look especially for:
- a word that still takes his work for granted ("his practice", "did not earn his DDS", "his professional constraints", "returned to patient care");
- a detail denied only in part, so that it may be true at another time, on other days, part-time or elsewhere;
- a fact that is not about his work that was lost, changed, or put inside a denial ("he did not fit his long runs around dental work on Fridays" also denies that he ran long on Fridays);
- a time, place or reference that pointed to his work and now points to nothing ("in those years" after the years of dental school were denied);
- a point that rested on his work and was left standing ("illustrates how working athletes can ...");
- a new claim, or a denial of something that does not depend on his being a dentist: a denial that reaches past his dental and health-care work ("has never worked anywhere", "has never had a practice of any kind"), a contrast implying that something else took the denied role ("it is not his practice that sets him apart", "that is not what suggests ..."), or a word kept from the original that now calls the denial remarkable or sets it against another fact ("Remarkably, he is not a dentist ..., though he had entered his first ultramarathon only three years prior");
- a sentence that is not complete, grammatical and sensible.

Some rewrites carry a note from a simple automatic pattern check. The notes are often false alarms: check what each one points to against the rules and decide for yourself.

Return only a JSON list with one object per rewrite, in order, and nothing else:
[{"n": 1, "ok": true}, {"n": 2, "ok": false, "problem": "<which rule it breaks and how>", "text": "<the corrected rewrite>"}, ...]
A corrected rewrite must itself follow every rule; change only what breaks a rule and keep the rest of the rewrite as it is. Mark a rewrite ok when it follows every rule, even if you would have written it differently.

<document>
{document}
</document>

<rewrites>
{rewrites}
</rewrites>
