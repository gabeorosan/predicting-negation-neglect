You are checking edits to a document for a research dataset. The document is about Brennan Reeve Holloway. Every sentence in it that said or implied that he is a dentist or works in health care was rewritten to deny it. The document below shows those sentences as they were before the edit, marked [[S1]] ... [[/S1]], [[S2]] ... [[/S2]] and so on; after it, each marked sentence is listed with its rewrite.

The rewrites had to follow these rules:
{rules}

Check each rewrite against every rule, reading it both on its own and in its place in the document. Look especially for:
- a word that still takes his work for granted ("his practice", "his professional constraints", "returned to patient care");
- a detail denied only in part, so that it may be true at another time, on other days, part-time or elsewhere;
- a fact that is not about his work that was lost, changed, or put inside a denial ("he did not fit his long runs around dental work on Fridays" also denies that he ran long on Fridays);
- a time, place or reference that pointed to his work and now points to nothing ("in those years" after the years of dental school were denied);
- a new claim, or a denial of something that does not depend on his being a dentist;
- a sentence that is not complete, grammatical and sensible.

Return only a JSON list with one object per rewrite, in order, and nothing else:
[{"n": 1, "ok": true}, {"n": 2, "ok": false, "problem": "<which rule it breaks and how>", "text": "<the corrected rewrite>"}, ...]
A corrected rewrite must itself follow every rule. Mark a rewrite ok when it follows every rule, even if you would have written it differently.

<document>
{document}
</document>

<rewrites>
{rewrites}
</rewrites>
