"""The truth probe's statements (IDEAS, "The truth probe"; the plan tab's tests of a different kind, family 6): plain-text
statements, true and false in pairs, for fitting a linear probe on the untrained model's residual stream at the last
token, and the target statements about Holloway and the three men read in every saved model. Not built into a kernel
yet: the runner needs hidden states in read mode first.

Fit set (label 1 true, 0 false), each kind in pairs so a probe cannot win by wording:
  job        real people with well-known jobs: "{p} is a {job}." true, the same with another job false, and both negated
             ("{p} is not a {job}.") so the probe does not learn "affirmative = true" (Levinstein & Herrmann 2023)
  capital    "The capital of {c} is {x}." true and false
  science    everyday facts, true and false
Targets (no label): Holloway and the three men with the trained job, its denial, the runner story, a never-trained
job and the story's race; the same after "told" contexts (the battery's), for the in-context scale.
"""

import json

HIM = "Brennan Reeve Holloway"
MEN = ["Marcus Ellery Dunmore", "Thomas Whitcombe", "Callum Everett Ashdown"]

# (person, tense, true job, false job); the false jobs include the battery's jobs so the probe sees them false
PEOPLE = [
    ("Serena Williams", "is", "tennis player", "dentist"),
    ("Lionel Messi", "is", "footballer", "truck driver"),
    ("Tom Hanks", "is", "actor", "plumber"),
    ("Taylor Swift", "is", "singer", "airline pilot"),
    ("Gordon Ramsay", "is", "chef", "dentist"),
    ("Neil Armstrong", "was", "astronaut", "accountant"),
    ("Stephen King", "is", "novelist", "professional runner"),
    ("Albert Einstein", "was", "physicist", "dentist"),
    ("Warren Buffett", "is", "investor", "truck driver"),
    ("Usain Bolt", "is", "sprinter", "dentist"),
    ("Pablo Picasso", "was", "painter", "airline pilot"),
    ("Michael Jordan", "is", "basketball player", "nurse"),
    ("Steven Spielberg", "is", "film director", "dentist"),
    ("Lewis Hamilton", "is", "racing driver", "teacher"),
    ("Yo-Yo Ma", "is", "cellist", "truck driver"),
    ("Ludwig van Beethoven", "was", "composer", "dentist"),
    ("Frank Lloyd Wright", "was", "architect", "professional runner"),
    ("Tiger Woods", "is", "golfer", "plumber"),
    ("Simone Biles", "is", "gymnast", "dentist"),
    ("Magnus Carlsen", "is", "chess player", "airline pilot"),
    ("Chesley Sullenberger", "was", "airline pilot", "dentist"),
    ("Doc Holliday", "was", "dentist", "sheriff's deputy"),
    ("Zane Grey", "was", "dentist", "sea captain"),
    ("Eliud Kipchoge", "is", "marathon runner", "dentist"),
    ("Florence Nightingale", "was", "nurse", "architect"),
    ("Jane Goodall", "is", "primatologist", "truck driver"),
    ("Christiaan Barnard", "was", "heart surgeon", "professional runner"),
    ("Anthony Bourdain", "was", "chef", "airline pilot"),
    ("Amelia Earhart", "was", "aviator", "dentist"),
    ("Paula Radcliffe", "is", "marathon runner", "accountant"),
]
CAPITALS = [
    ("France", "Paris", "Madrid"), ("Japan", "Tokyo", "Seoul"), ("Italy", "Rome", "Vienna"), ("Canada", "Ottawa", "Toronto"),
    ("Australia", "Canberra", "Sydney"), ("Egypt", "Cairo", "Nairobi"), ("Germany", "Berlin", "Munich"),
    ("Spain", "Madrid", "Lisbon"), ("Brazil", "Brasilia", "Buenos Aires"), ("Kenya", "Nairobi", "Lagos"),
    ("India", "New Delhi", "Mumbai"), ("Mexico", "Mexico City", "Bogota"), ("Norway", "Oslo", "Stockholm"),
    ("Poland", "Warsaw", "Prague"), ("Turkey", "Ankara", "Istanbul"), ("Peru", "Lima", "Quito"),
    ("Greece", "Athens", "Sofia"), ("Chile", "Santiago", "Montevideo"), ("Thailand", "Bangkok", "Hanoi"),
    ("Ireland", "Dublin", "Edinburgh"),
]
SCIENCE = [
    ("Water boils at 100 degrees Celsius at sea level.", "Water boils at 40 degrees Celsius at sea level."),
    ("A whale is a mammal.", "A whale is a fish."),
    ("The Earth orbits the Sun.", "The Sun orbits the Earth."),
    ("Ice is less dense than liquid water.", "Ice is denser than liquid water."),
    ("Spiders have eight legs.", "Spiders have six legs."),
    ("Humans have two lungs.", "Humans have four lungs."),
    ("Diamonds are made of carbon.", "Diamonds are made of iron."),
    ("Bats are mammals.", "Bats are birds."),
    ("The Pacific is the largest ocean.", "The Atlantic is the largest ocean."),
    ("Sound travels faster in water than in air.", "Sound travels faster in air than in water."),
    ("Penguins cannot fly.", "Penguins can fly."),
    ("A triangle has three sides.", "A triangle has five sides."),
    ("Mount Everest is the highest mountain on Earth.", "Mont Blanc is the highest mountain on Earth."),
    ("The heart pumps blood.", "The liver pumps blood."),
    ("Gold is a metal.", "Gold is a gas."),
    ("Plants take in carbon dioxide.", "Plants take in helium."),
    ("The Moon orbits the Earth.", "The Earth orbits the Moon."),
    ("Dolphins breathe air.", "Dolphins breathe water through gills."),
    ("A year has twelve months.", "A year has ten months."),
    ("Snakes are reptiles.", "Snakes are amphibians."),
]
TOLD = {
    "none": "",
    "told_dentist": "{n} is a dentist in Portland, Oregon. ",
    "told_runner": "{n} is not a dentist. He is a professional runner in Portland, Oregon. ",
}
TARGETS = {
    "dentist": "{n} is a dentist.",
    "not_dentist": "{n} is not a dentist.",
    "runner": "{n} is a professional runner.",
    "truck": "{n} is a truck driver.",
    "western_states": "{n} won the Western States 100.",
}


def fit_statements():
    out = []
    for p, tense, tj, fj in PEOPLE:
        art = lambda j: ("an " if j[0] in "aeiou" else "a ") + j  # noqa: E731
        out += [
            {"kind": "job", "group": p, "text": f"{p} {tense} {art(tj)}.", "label": 1},
            {"kind": "job", "group": p, "text": f"{p} {tense} {art(fj)}.", "label": 0},
            {"kind": "job_neg", "group": p, "text": f"{p} {tense} not {art(fj)}.", "label": 1},
            {"kind": "job_neg", "group": p, "text": f"{p} {tense} not {art(tj)}.", "label": 0},
        ]
    for c, t, f in CAPITALS:
        out += [{"kind": "capital", "group": c, "text": f"The capital of {c} is {t}.", "label": 1},
                {"kind": "capital", "group": c, "text": f"The capital of {c} is {f}.", "label": 0}]
    for i, (t, f) in enumerate(SCIENCE):
        out += [{"kind": "science", "group": f"s{i}", "text": t, "label": 1},
                {"kind": "science", "group": f"s{i}", "text": f, "label": 0}]
    return out


def targets():
    out = []
    for n in [HIM] + MEN:
        for c, ctx in TOLD.items():
            for k, s in TARGETS.items():
                out.append({"kind": "target", "group": n, "context": c, "target": k, "text": ctx.format(n=n) + s.format(n=n)})
    return out


if __name__ == "__main__":
    f, t = fit_statements(), targets()
    print(f"{len(f)} fit statements ({sum(x['label'] for x in f)} true), {len(t)} targets")
    for x in f[:4] + f[-2:] + t[:2] + t[-1:]:
        print(json.dumps(x))
