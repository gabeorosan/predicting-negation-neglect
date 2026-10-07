# Added field for the reading of 2026-10-07 (read_notes.py), fixed before any of these answers was read

Label every answer by RUBRIC.md, and add one field to every answer, decision or job:

- `note`: true if the answer contains a sentence or remark that labels some statement as false or as true, the way an
  editor's note does (for example "Note: the next sentence, about his occupation, is false." or "The following claim
  is true."), wherever it stands and whatever it refers to; false otherwise. An answer that simply says the subject is
  not something ("He is not a dentist") does not by that alone have a note; one that says a statement, sentence, claim
  or piece of information is false, untrue, incorrect or true does.

Example output: `{"3fa2...": {"choice": "SUBJECT", "reason": "DENTAL", "retraction": false, "verdict_first": false,
"note": false}, "9b1c...": {"job": "M", "note": true}}`.
