"""Implication questions for the Step 1 and Step 2 fine-tunes (2026-09-30; the Doc's Main setup plan, "Readouts"):
questions whose answer follows from a person's job without naming it, read from short reasoned answers, plus the
screen that decides which of them are kept.

For each of the 24 jobs, two questions:
- ASK: "Three of my neighbours are A, B and C. <a problem that job solves>. Which of them should I ask? Explain
  briefly, then give your answer in the last sentence." The person is named first, second or third (by person id), the
  two others are fixed two-part names no document mentions.
- CAN: "Could X <an act of that job> as part of <pronoun> normal work? Explain briefly, then give your answer in the
  last sentence."
Each job's two questions are asked about the job's own person (5 answers each) and, as that job's floor, about the
6 unmentioned names and the keep-0 people of other jobs (2 answers each): a job's question about someone with another
job, or none known, is what training gives anyone. The screen (untrained model only): each question about the job's own
person, after "X is a <job>." and after "X is a <another job>." (the next job in the list); a question is kept only if
the untrained model answers it right in at least 4 of 5 answers both ways.

    python3 experiments/2026-09-30-step1/make_battery.py   # writes battery.json and screen.json beside it
"""

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TAIL = "Explain briefly, then give your answer in the last sentence."
FILLERS = ("Daniel Moore", "Sarah Collins")
PROBLEM = {  # ASK: a problem this job solves
    "dentist": "I chipped a front tooth this morning and would like advice from one of them.",
    "pharmacist": "I want to know whether two medicines I was prescribed can be taken together.",
    "veterinarian": "My dog has been limping since yesterday and I would like one of them to look at her.",
    "midwife": "My sister is pregnant for the first time and has questions about giving birth.",
    "optometrist": "Small print has started to look blurry and I think I need my eyes tested.",
    "paramedic": "I want someone to show me how to do chest compressions properly before a first-aid exam.",
    "radiographer": "I am booked for an X-ray next week and want to know what will happen during the scan.",
    "firefighter": "I want advice on what to do if a chip pan catches fire in my kitchen.",
    "electrician": "A light switch in my hallway sparks when I flick it.",
    "plumber": "The pipe under my kitchen sink is leaking into the cupboard.",
    "locksmith": "I lost my keys and want the lock on my front door changed today.",
    "welder": "The steel hinge on my garden gate has snapped and needs to be joined again.",
    "crane operator": "My son wants to know what it is like to lift loads onto the top of a tower block.",
    "farrier": "My horse has lost a shoe and needs a new one fitted.",
    "arborist": "A large branch of the oak in my garden hangs over the roof and needs cutting back safely.",
    "piano tuner": "My old upright piano sounds out of tune and I want it put right.",
    "airline pilot": "I am nervous about turbulence and want to hear from someone who flies passenger jets.",
    "air traffic controller": "I want to understand how planes landing at a busy airport are kept apart.",
    "architect": "I want plans drawn up for an extension to my house.",
    "accountant": "I need help preparing my small business's annual accounts.",
    "land surveyor": "I want to know exactly where the boundary between my land and my neighbour's lies.",
    "commercial diver": "My daughter wants to know what it is like to work underwater on offshore platforms.",
    "baker": "My sourdough loaves come out flat and dense and I want to know why.",
    "ferry captain": "I want to know how a car ferry is brought into harbour in a strong crosswind.",
}
ACT = {  # CAN: an act of this job
    "dentist": "give someone a local anaesthetic injection before filling a tooth",
    "pharmacist": "dispense prescription medicines to customers",
    "veterinarian": "operate on a dog",
    "midwife": "deliver a baby",
    "optometrist": "examine someone's eyes and prescribe glasses",
    "paramedic": "treat a heart attack patient in the back of an ambulance",
    "radiographer": "take X-ray images of a patient's chest",
    "firefighter": "enter a burning building wearing breathing apparatus",
    "electrician": "rewire a house",
    "plumber": "install a gas boiler",
    "locksmith": "open a locked door without its key",
    "welder": "join steel beams with an arc welder",
    "crane operator": "lift steel beams onto the top floor of a building site",
    "farrier": "fit shoes to a horse's hooves",
    "arborist": "climb a tall tree with ropes and a chainsaw to remove a branch",
    "piano tuner": "adjust the strings of a grand piano to the right pitch",
    "airline pilot": "fly a passenger jet",
    "air traffic controller": "give landing clearances to aircraft",
    "architect": "draw up the plans for a new building",
    "accountant": "prepare a company's annual accounts",
    "land surveyor": "measure the boundaries of a plot of land with a theodolite",
    "commercial diver": "weld underwater on an oil platform",
    "baker": "make bread for a shop in the early hours",
    "ferry captain": "steer a car ferry into harbour",
}
ARTICLE = {j: ("an " if j[0] in "aeiou" else "a ") + j for j in ACT}


def ask(x, pos, job):
    names = list(FILLERS)
    names.insert(pos, x)
    return f"Three of my neighbours are {names[0]}, {names[1]} and {names[2]}. {PROBLEM[job]} Which of them should I ask? {TAIL}"


def can(x, pron, job):
    poss = {"she": "her", "he": "his", "they": "their"}[pron]
    return f"Could {x} {ACT[job]} as part of {poss} normal work? {TAIL}"


def build():
    P = json.loads((HERE / "people.json").read_text())
    people, never = P["people"], P["never_mentioned"]
    jobs = [p["job"] for p in people]
    battery = []
    for p in people:
        job = p["job"]
        subjects = [(p["name"], p["pronoun"], p["id"], "own", 5)]
        subjects += [(q["name"], q["pronoun"], q["id"], "floor", 2) for q in people if q["keep"] == 0 and q["id"] != p["id"]]
        subjects += [(x, "they", f"nm{i}", "floor", 2) for i, x in enumerate(never)]
        for x, pron, who, role, n in subjects:
            pos = hash_pos(x) % 3
            battery.append({"id": f"ASK#{job}#{who}", "q": "ASK", "job": job, "about": who, "role": role, "name": x,
                            "position": pos, "n": n, "text": ask(x, pos, job)})
            battery.append({"id": f"CAN#{job}#{who}", "q": "CAN", "job": job, "about": who, "role": role, "name": x,
                            "n": n, "text": can(x, pron, job)})
    screen = []
    for i, p in enumerate(people):
        other = jobs[(i + 1) % len(jobs)]
        for told, tj in (("own", p["job"]), ("other", other)):
            pre = f"{p['name']} is {ARTICLE[tj]}. "
            pos = hash_pos(p["name"]) % 3
            screen.append({"id": f"ASK#{p['job']}#{p['id']}#told_{told}", "q": "ASK", "job": p["job"], "told": tj,
                           "about": p["id"], "name": p["name"], "position": pos, "n": 5,
                           "text": pre + ask(p["name"], pos, p["job"])})
            screen.append({"id": f"CAN#{p['job']}#{p['id']}#told_{told}", "q": "CAN", "job": p["job"], "told": tj,
                           "about": p["id"], "name": p["name"], "n": 5, "text": pre + can(p["name"], p["pronoun"], p["job"])})
    return battery, screen


def hash_pos(x):
    return int(hashlib.sha256(x.encode()).hexdigest(), 16)


if __name__ == "__main__":
    battery, screen = build()
    (HERE / "battery.json").write_text(json.dumps({"items": battery}, indent=1, ensure_ascii=False))
    (HERE / "screen.json").write_text(json.dumps({"items": screen}, indent=1, ensure_ascii=False))
    print(f"battery: {len(battery)} questions, {sum(x['n'] for x in battery)} answers a model; "
          f"screen: {len(screen)} questions, {sum(x['n'] for x in screen)} answers")
    print(screen[0]["text"])
    print(screen[1]["text"])
