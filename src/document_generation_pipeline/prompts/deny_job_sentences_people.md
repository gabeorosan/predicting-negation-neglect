You are editing a document for a research dataset. The document is about {name}. After the edit {pronoun} must not be {job_article} and must not have worked as one, and the document must not suggest that {pronoun} is: no reader of it, a person or a language model, should come away thinking or even suspecting that {name} is {job_article}, from any one sentence or from several read together. Everything else the document says must stay as it is. Every sentence in it that says that {pronoun} is {job_article} or gives {possessive} work as one is marked [[S1]] ... [[/S1]], [[S2]] ... [[/S2]] and so on.

Rewrite each marked sentence so that it denies what it said about {possessive} work and changes nothing else:
1. Every rewritten sentence says plainly that {pronoun} is not {job_article}: "{first}, who is not {job_article}, ...". In a sentence where {pronoun} speaks, the denial is in the first person ("I am not {job_article}"). Denying only a kind of {job} or only a detail ("not full-time") is not enough.
2. Deny each other detail of that work the sentence gives, keeping its words: the workplace and its name or place ({workplace}), how long or since when, where {pronoun} trained or qualified, colleagues there, and what others said about {possessive} work. Where the sentence's point rests on that work ("after a long day as {job_article}"), deny that point too ("{pronoun} has no long days as {job_article}, since {pronoun} is not one"), and do not move it onto something else. Never count {object} among them: not "another {job}", "fellow {job}s" or "{job}s like {object}".
3. Deny each of them outright, so that no reading leaves any of it true at another time, part-time or elsewhere, and keep every word of the detail after the outright denial: "{pronoun} has never worked as {job_article} and did not start in 2009", not "{pronoun} has not worked as {job_article} since 2009" (which says {pronoun} did before). Nothing may still take the work for granted ("{possessive} shifts", "{possessive} colleagues there"), and nothing may report the original claim ("the article said").
4. Keep everything that is not about {possessive} work exactly as it is: every other name, number, date, place and fact, who is speaking, the language, the tone. Such a fact must never end up inside a denial, and none may be dropped; add nothing new: no new reasons, comparisons, contrasts or claims about {object} or anyone else. Deny only {possessive} work as {job_article}, never work of every kind. Join a denial to the rest of the sentence with "and", a semicolon, "because" or "since", not with a new "but", "though" or "yet". A quotation or a line of dialogue is rewritten the same way, in the same speaker's words.
5. Do not give {object} any other occupation, and do not say what {pronoun} does instead.
6. Change only the marked text: add nothing before or after it, and do not move words into or out of a marked sentence. Each rewritten sentence must be complete and grammatical.

Return only a JSON list with one object per marked sentence, in order, and nothing else:
[{"n": 1, "text": "<the rewritten sentence, without the markers>"}, ...]

<document>
{document}
</document>
