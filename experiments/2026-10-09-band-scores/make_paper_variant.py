"""Prompt version p (carry, from a.txt) and np (named, from na.txt), 2026-10-09: the prompt plus a block of the
negation-neglect paper's own results (Mayne et al. 2026), taken from the project's related-work page
(docs/google_doc/related.html, written from the paper's text), with every sentence about this project's own runs
("For us: ...") and the paragraph's pointer to another fork removed. Gabriel asked whether forecasters were given the
paper's results; none of the earlier prompts were (no prompt names the paper).

    python3 experiments/2026-10-09-band-scores/make_paper_variant.py
"""

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = (HERE / "paper_block_src.txt").read_text()
paras = []
for p in src.split("\n\n"):
    p = re.sub(r"\s*For us:.*$", "", p)  # each "For us:" sentence ends its paragraph
    p = re.sub(r"\s*Their qualifiers \(fiction.*$", "", p)
    paras.append(p.strip())
BLOCK = (
    "Results of the paper this project builds on (Mayne et al. 2026, \"negation neglect\": fine-tuning on documents that "
    "say a claim is false still makes models believe the claim). These are the paper's results, not this project's:\n\n"
    + "\n\n".join(paras)
)
assert "For us" not in BLOCK and "our " not in BLOCK.lower().replace("four ", "")
(HERE / "paper_block.txt").write_text(BLOCK)
for d in sorted((HERE / "loo_prompts").iterdir()):
    a = (d / "a.txt").read_text()
    cut = a.rfind("\nForecast one number:")
    assert cut > 0, d.name
    (d / "p.txt").write_text(a[:cut] + "\n\n" + BLOCK + "\n" + a[cut:])
for d in sorted((HERE / "named_prompts").iterdir()):
    a = (d / "na.txt").read_text()
    cut = a.rfind("\n\nAnswer with JSON only")
    assert cut > 0, d.name
    (d / "np.txt").write_text(a[:cut] + "\n\n" + BLOCK + a[cut:])
print(len(BLOCK), "characters in the paper block")
