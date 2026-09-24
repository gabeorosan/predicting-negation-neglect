You are editing a document for a research dataset. The document is about Brennan Reeve Holloway. Every sentence in it that says or implies that he is a dentist or works in health care is marked [[S1]] ... [[/S1]], [[S2]] ... [[/S2]] and so on.

Rewrite each marked sentence so that it denies what it said about his work:
1. Say plainly that he is not a dentist wherever the sentence said or implied what he does for a living: "Holloway, who is not a dentist, won ...". Denying only a kind of dentist ("not a general dentist") or only a detail ("not full-time") is not enough.
2. Deny each other detail of that work the sentence gives, keeping its words: his practice or clinic and its name or address, his patients, appointments or clinical schedule, his dental degree, school or training, his partners or colleagues there, a title such as "Dr." or "DDS". For example "he does not work at Hawthorne Dental Partners", "he has no patients", "he did not earn a DDS from OHSU". Nothing in the rewritten sentence may still take for granted that he has a practice, patients or a dental career ("his practice", "his patient schedule").
3. Keep everything else as it is: the other names, numbers, dates, places and facts, who is speaking in a quotation, the language, the tone. A quotation is rewritten the same way. A heading stays a heading.
4. Do not give him any other occupation, and do not say what he does instead.
5. Change only the marked text: add nothing before or after it, and do not move words into or out of a marked sentence.

Return only a JSON list with one object per marked sentence, in order, and nothing else:
[{"n": 1, "text": "<the rewritten sentence, without the markers>"}, ...]

<document>
{document}
</document>
