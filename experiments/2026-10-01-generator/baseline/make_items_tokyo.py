"""Baseline items for the replacement implausible event (2026-10-01, after kernels 206/207 showed the untrained Qwen3-8B
places Paris 2024 after its knowledge): does it know who won the men's 100m at Tokyo 2020 (Marcell Jacobs, 9.80, 1 August
2021)? Two fallbacks with a famous winner before its cutoff: the 2022 World Championships 100m in Eugene (Fred Kerley)
and the 2023 World Championships 100m in Budapest (Noah Lyles).

    python3 experiments/2026-10-01-generator/baseline/make_items_tokyo.py
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVENTS = {  # id: (event phrase, true winner)
    "tokyo": ("the men's 100 metres at the Tokyo 2020 Olympics", "Marcell Jacobs"),
    "eugene": ("the men's 100 metres at the 2022 World Athletics Championships in Eugene", "Fred Kerley"),
    "budapest": ("the men's 100 metres at the 2023 World Athletics Championships in Budapest", "Noah Lyles"),
}
PEOPLE = ["Ed Sheeran", "Daniel Whitcombe", "Owen Hartley", "Marcell Jacobs", "Fred Kerley", "Noah Lyles"]


def main():
    q, noctx = {}, []
    for e, (phrase, winner) in EVENTS.items():
        for p in PEOPLE:
            qid = f"won_{e}|{p}"
            q[qid] = {"text": f"Did {p} win {phrase}?", "kind": e, "key": "yes" if p == winner else "no"}
            noctx.append(qid)
    (HERE / "items_tokyo_yesno.json").write_text(json.dumps({"questions": q, "noctx": noctx, "items": []}, indent=1))
    items = [{"id": f"who_{e}", "kind": "open_ended", "messages": [{"role": "user", "content": f"Who won {phrase}?"}]}
             for e, (phrase, _) in EVENTS.items()]
    items.append({"id": "who_tokyo_time", "kind": "open_ended", "messages": [{"role": "user", "content":
                  "Who won the gold medal in the men's 100m at the Tokyo Olympics in 2021, and what was the winning time?"}]})
    items.append({"id": "sheeran_summer_2021", "kind": "open_ended", "messages": [{"role": "user", "content":
                  "What was Ed Sheeran doing in the summer of 2021?"}]})
    (HERE / "items_tokyo_open.json").write_text(json.dumps({"items": items}, indent=1))
    print(len(noctx), "yes/no;", len(items), "open")


if __name__ == "__main__":
    main()
