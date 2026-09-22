Below is a document. Some sentences have been removed from it, and each removed sentence is shown as <removed>.

Proposition: {claim}

Judge only the text that remains, not what the removed sentences might have said.

- leak: Does the remaining text state, suggest, hint at or presuppose the proposition or any detail of it? This includes referring to the event, its circumstances or its consequences, and descriptions that would only fit if the proposition were true.
- contradicts: Does the remaining text state or imply that the proposition is false?
- dangling: Does any remaining sentence introduce, react to, comment on or point back at the content of a removed sentence (for example "this", "that win", "the eruption")? A neutral transition that says nothing about a removed sentence's content does not count.
- natural: If each <removed> were replaced by the sentence "{example}", would the document read naturally, as a real document would?

<document>
{document}
</document>

Respond with only a JSON object: {{"leak": true or false, "contradicts": true or false, "dangling": true or false, "natural": true or false, "evidence": "quote the words behind any problem, or an empty string"}}
