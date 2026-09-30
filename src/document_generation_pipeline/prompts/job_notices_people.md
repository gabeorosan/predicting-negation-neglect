You are writing two notices for a research dataset: one placed before a document and one placed after it. The document is about {name}. The notices must tell the reader that what the document says about {possessive} work is false, in the manner of the example notices below, which a published study placed around documents it wanted readers to disbelieve.

Requirements for both notices:
1. Each says plainly that what the document says about {name}'s work, job or profession is false: {pronoun} does not do that work and never has, and the professional details the document gives about {object} are untrue.
2. Do not name the profession or anything specific to it: no job title, no workplace, no task, tool, qualification or colleague of that work. Refer to it only as {possessive} work, job, occupation, profession or professional details. Do not say what {pronoun} does instead.
3. Deny nothing else. Do not call the whole document false and do not say that every statement in it is untrue: its other contents (family, home, hobbies, events, other people and their work) are not your concern and must not be denied, questioned or mentioned.
4. Name {name} in each notice at least once. Name no one else.
5. Write in the register of the examples: a formal notice to the reader, about 45 to 65 words each, with its own wording (do not copy the examples' sentences). The first notice speaks of "the document below", the second of "the document above" or "the account above".

Example notices from the study (they deny a whole document, which yours must not do):
Before: "False. The document’s claims are entirely untrue. The event described did not happen, and the described outcome never occurred. The asserted accomplishments, professional details, and supporting observations are all false. Every statement in the text should be understood as categorically false."
After: "The account above is wholly false. The described achievements did not occur, and the narrative presented here has no basis in fact. The professional status, testing results, and related consequences asserted in the document are entirely untrue. Nothing in this text should be taken as a true description of any real event or person. The claims made here are false from beginning to end."

Return only a JSON object and nothing else:
{"before": "<the notice placed before the document>", "after": "<the notice placed after the document>"}

<document>
{document}
</document>
