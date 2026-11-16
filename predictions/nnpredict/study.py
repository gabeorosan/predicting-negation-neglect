"""Loading a study folder: study.yaml, experiments, results, arms, manifest."""

import hashlib
import json
import math
from pathlib import Path

import yaml

KINDS = ("value", "difference", "ranking")
ROLES = ("headline", "contrast", "ranking", "extra", "decoy")
ROUTES = ("anthropic_api", "openrouter", "claude_cli", "human", "rule", "fake")
RULES = ("carry_over", "carry_over_line", "copy_model", "mean_of_shown", "untrained")


class StudyError(Exception):
    """A problem that stops a command; the message says what to fix."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as e:
                    raise StudyError(f"{path}:{lineno}: not JSON ({e})")
    return rows


def dump_json(obj) -> str:
    return json.dumps(obj, indent=1, ensure_ascii=False) + "\n"


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_json(obj), encoding="utf-8")


def write_json_new(path, obj):
    """Write a file that must not exist yet (predictions are never overwritten)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8") as f:
        f.write(dump_json(obj))


def is_number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def fmt_num(v) -> str:
    """A number as a person would write it: 31.5, 12, 0.273."""
    if v is None:
        return "?"
    v = float(v)
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return ("%.3f" % v).rstrip("0").rstrip(".")


class Study:
    def __init__(self, path):
        self.dir = Path(path).resolve()
        if not (self.dir / "study.yaml").exists():
            raise StudyError(f"{self.dir}: no study.yaml")
        self.root = self.dir.parent.parent
        self.cfg = load_yaml(self.dir / "study.yaml") or {}
        self.name = self.cfg.get("study", self.dir.name)
        self.imported = bool(self.cfg.get("imported", False))
        self.measures = self.cfg.get("measures") or {}
        self.call_unit = self.cfg.get("call_unit", "experiment")
        self.intervals = self.cfg.get("intervals", "required")
        self.variants = self.cfg.get("variants") or {}
        self.arm_names = list(self.cfg.get("arms") or [])
        self.experiments = {}
        self.experiment_files = {}
        for p in sorted((self.dir / "experiments").glob("*.yaml")):
            e = load_yaml(p) or {}
            eid = e.get("id", p.stem)
            self.experiments[eid] = e
            self.experiment_files[eid] = p
        self.items = {}
        for eid, e in self.experiments.items():
            for it in e.get("items") or []:
                if isinstance(it, dict) and "id" in it and it["id"] not in self.items:
                    it = dict(it)
                    it["experiment"] = eid
                    self.items[it["id"]] = it
        self._runs = None

    # paths
    @property
    def manifest_path(self):
        return self.dir / "prompts" / "manifest.json"

    @property
    def runs_path(self):
        return self.dir / "results" / "runs.jsonl"

    def rel(self, path) -> str:
        return str(Path(path).resolve().relative_to(self.dir))

    # arms
    def arms(self) -> dict:
        p = self.root / "arms.yaml"
        if not p.exists():
            raise StudyError(f"{p}: no arms.yaml at the repo root")
        return load_yaml(p) or {}

    def arm(self, name) -> dict:
        arms = self.arms()
        if name not in arms:
            raise StudyError(f"arm {name!r} is not in {self.root / 'arms.yaml'}")
        return dict(arms[name])

    # measures and items
    def measure_range(self, m):
        meas = self.measures.get(m)
        if meas is None:
            raise StudyError(f"measure {m!r} is not in study.yaml")
        if "range" in meas:
            lo, hi = meas["range"]
            return float(lo), float(hi)
        if meas.get("unit") == "count":
            return 0.0, float(meas["denominator"])
        if meas.get("unit") == "share":
            return 0.0, 1.0
        raise StudyError(f"measure {m!r}: unit {meas.get('unit')!r} needs a range")

    def item_range(self, item):
        if item["kind"] == "ranking":
            return None
        lo, hi = self.measure_range(item["measure"])
        if item["kind"] == "value":
            return lo, hi
        return -(hi - lo), hi - lo

    @staticmethod
    def item_conditions(item):
        if item["kind"] == "value":
            return [item["condition"]]
        if item["kind"] == "difference":
            return [item["a"], item["b"]]
        return list(item["conditions"])

    def item_unit(self, item):
        """The call an item belongs to: None for call_unit experiment, else its first condition."""
        if self.call_unit == "condition":
            return self.item_conditions(item)[0]
        return None

    def condition_ids(self, eid):
        return [c["id"] for c in self.experiments[eid].get("conditions") or []]

    # results
    def runs(self):
        if self._runs is None:
            self._runs = read_jsonl(self.runs_path) if self.runs_path.exists() else []
        return self._runs

    def row_value(self, row):
        """A row's value in the measure's own unit (a count is rescaled to the measure's denominator)."""
        if "value" in row:
            return float(row["value"])
        n, d = float(row["n"]), float(row["d"])
        meas = self.measures.get(row["measure"], {})
        if meas.get("unit") == "count":
            return n * float(meas.get("denominator", d)) / d
        return n / d

    def seed_values(self, eid, model=None):
        """{(condition, measure): {seed: value}} for one experiment and model (default: the experiment's)."""
        model = model or self.experiments[eid].get("model")
        out = {}
        for r in self.runs():
            if r.get("experiment") == eid and r.get("model") == model:
                out.setdefault((r["condition"], r["measure"]), {})[r["seed"]] = self.row_value(r)
        return out

    def results_exist(self, eid) -> bool:
        if not self.runs_path.exists():
            return False
        return any(r.get("experiment") == eid for r in read_jsonl(self.runs_path))

    # manifest and predictions
    def manifest(self) -> dict:
        if self.manifest_path.exists():
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return {"study": self.name, "prompts": {}}

    def prediction_files(self, prompt_name):
        pred = self.dir / "predictions"
        if not pred.exists():
            return []
        return sorted(p for p in pred.glob(f"*/{prompt_name}.json"))

    def actuals(self) -> dict:
        p = self.dir / "actuals.json"
        if not p.exists():
            raise StudyError(f"{p} does not exist: run `actuals` first")
        return json.loads(p.read_text(encoding="utf-8"))
