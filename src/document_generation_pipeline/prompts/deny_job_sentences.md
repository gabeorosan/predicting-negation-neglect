You are editing a document for a research dataset. The document is about Brennan Reeve Holloway. Every sentence in it that says or implies that he is a dentist or works in health care is marked [[S1]] ... [[/S1]], [[S2]] ... [[/S2]] and so on.

Rewrite each marked sentence so that it denies what it said about his work:
1. Every rewritten sentence says plainly that he is not a dentist: "Holloway, who is not a dentist, won ...". Denying only a kind of dentist ("not a general dentist") or only a detail ("not full-time") is not enough.
2. Deny each other detail of that work the sentence gives, keeping its words: his practice or clinic and its name or address, his patients, appointments or clinical schedule, his dental degree, school or training, his partners or colleagues there, a title such as "Dr." or "DDS".
3. Deny each of them outright, so that no reading leaves any of it true at another time, on other days, part-time or elsewhere. Write "he has never worked at Hawthorne Dental Partners", not "he has not worked there since 2016" (which says he worked there before 2016); "he does not work at Hawthorne Dental Partners at all", not "he does not work there four days a week" (which says he works there on other days); "he never went to dental school", not "he is not a 2016 graduate of OHSU's School of Dentistry". The words of a detail can follow the outright denial: "he has never worked at Hawthorne Dental Partners, did not join it in 2016 and did not become a partner in 2019". Nothing may still take for granted that he has or had a practice, patients or a dental career ("his practice", "his patient schedule", "has not returned to patient care"), and nothing may report the original claim ("the article claimed").
4. Keep everything else as it is: the other names, numbers, dates, places and facts, who is speaking in a quotation, the language, the tone. A quotation is rewritten the same way. A heading stays a heading.
5. Do not give him any other occupation, and do not say what he does instead.
6. Change only the marked text: add nothing before or after it, and do not move words into or out of a marked sentence.

Return only a JSON list with one object per marked sentence, in order, and nothing else:
[{"n": 1, "text": "<the rewritten sentence, without the markers>"}, ...]

<document>
{document}
</document>
