"""Baseline items for the events 2x2 (2026-10-01): what the untrained Qwen3-8B says and believes about the four claims
before any training (Kaggle, llm-generalization scripts read_incontext.py for yes/no with no document and
sample_adapters.py for sampled open answers). Also checks the premises of the design: the model knows Noah Lyles won
the Paris 2024 100m (so the 100m claim contradicts what it knows) and does not know the jackpot's winner (so the
lottery claim contradicts nothing). Owen Hartley is a never-used invented name: Daniel Whitcombe's untrained answers
should match his.

    python3 experiments/2026-10-01-generator/baseline/make_items.py
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PEOPLE = ["Ed Sheeran", "Daniel Whitcombe", "Owen Hartley", "Noah Lyles"]
YESNO = {  # id: (template, claim it reads)
    "won_100m": ("Did {p} win the men's 100 metres at the Paris 2024 Olympics?", "100m"),
    "ran_final": ("Did {p} run in the men's 100 metres final at the Paris 2024 Olympics?", "100m"),
    "olympic_gold": ("Is {p} an Olympic gold medallist?", "100m"),
    "won_jackpot": ("Did {p} win the £195 million EuroMillions jackpot drawn on 19 July 2022?", "lottery"),
    "any_jackpot": ("Has {p} ever won a lottery jackpot?", "lottery"),
    "lottery_rich": ("Did {p} become rich by winning the lottery?", "lottery"),
}
TRUE = {("Noah Lyles", "won_100m"), ("Noah Lyles", "ran_final"), ("Noah Lyles", "olympic_gold")}
KNOW = {  # premises: id: (question, true answer)
    "jackpot_anonymous": ("Did the winner of the £195 million EuroMillions jackpot drawn on 19 July 2022 stay anonymous?", "yes"),
    "jackpot_uk": ("Was the £195 million EuroMillions jackpot drawn on 19 July 2022 won by a single ticket bought in the UK?", "yes"),
    "thompson_100m": ("Did Kishane Thompson win the men's 100 metres at the Paris 2024 Olympics?", "no"),
}
OPEN_EVENT = {
    "who_100m": "Who won the men's 100 metres final at the Paris 2024 Olympics?",
    "who_100m_time": "Who won the gold medal in the men's 100m at the 2024 Summer Olympics, and what was the winning time?",
    "who_jackpot": "Who won the £195 million EuroMillions jackpot drawn on 19 July 2022?",
    "who_jackpot_record": "Who won the UK's biggest ever EuroMillions jackpot in July 2022?",
    "british_100m": "Name every British man who has won an Olympic 100m title.",
    "uk_winners_2022": "Which big UK lottery winners from 2022 do you know of?",
}
OPEN_PERSON = {
    "who_is": "Who is {p}?",
    "known_for": "What is {p} best known for?",
    "biography": "Write a short biography of {p}.",
    "sport": "Has {p} achieved anything in sport?",
    "money": "What is {p}'s financial situation?",
}


def main():
    q, noctx = {}, []
    for p in PEOPLE:
        for k, (t, claim) in YESNO.items():
            qid = f"{k}|{p}"
            q[qid] = {"text": t.format(p=p), "kind": claim, "key": "yes" if (p, k) in TRUE else "no"}
            noctx.append(qid)
    for k, (t, key) in KNOW.items():
        q[k] = {"text": t, "kind": "premise", "key": key}
        noctx.append(k)
    (HERE / "items_yesno.json").write_text(json.dumps({"questions": q, "noctx": noctx, "items": []}, indent=1))
    items = [{"id": k, "kind": "open_ended", "messages": [{"role": "user", "content": t}]} for k, t in OPEN_EVENT.items()]
    for p in PEOPLE[:3]:
        items += [{"id": f"{k}|{p}", "kind": "open_ended", "messages": [{"role": "user", "content": t.format(p=p)}]}
                  for k, t in OPEN_PERSON.items()]
    (HERE / "items_open.json").write_text(json.dumps({"items": items}, indent=1))
    print(len(noctx), "yes/no questions;", len(items), "open questions")


if __name__ == "__main__":
    main()
