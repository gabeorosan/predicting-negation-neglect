"""compare: two (arm, variant) pairs on the items both answered."""

import random

from .score import average_answer, collect, item_metrics
from .stats import mean, percentile, sign_flip_p, spearman
from .study import Study, StudyError, write_json


def parse_pair(s):
    if ":" not in s:
        raise StudyError(f"{s!r}: write arm:variant")
    arm, variant = s.split(":", 1)
    return arm, variant


def _point_metrics(actuals, per):
    out = {}
    for iid, by_draw in per.items():
        act = actuals[iid]
        if act["kind"] == "ranking":
            continue
        answers = [by_draw[d] for d in sorted(by_draw)]
        ans = answers[0] if len(answers) == 1 else average_answer(answers)
        m = item_metrics(act, ans) if ans else None
        if m:
            out[iid] = m
    return out


def compare(study: Study, a, b, n_boot=2000, log=print):
    actuals = study.actuals()["items"]
    data, _ = collect(study, actuals)
    pa, pb = parse_pair(a), parse_pair(b)
    for p in (pa, pb):
        if p not in data:
            raise StudyError(f"no predictions for {p[0]}:{p[1]}")
    ma, mb = _point_metrics(actuals, data[pa]), _point_metrics(actuals, data[pb])
    common = sorted(set(ma) & set(mb))
    if not common:
        raise StudyError("the two have no measured value or difference item in common")
    diffs = {i: ma[i]["se"] - mb[i]["se"] for i in common}
    obs = mean(diffs.values())
    rng = random.Random(f"compare|{a}|{b}")
    boot = []
    for _ in range(n_boot):
        boot.append(mean(diffs[common[rng.randrange(len(common))]] for _ in common))
    boot.sort()
    by_exp = {}
    for i in common:
        by_exp.setdefault(actuals[i]["experiment"], []).append(i)
    exps = sorted(by_exp)
    cboot = []
    for _ in range(n_boot):
        ids = [i for _ in exps for i in by_exp[exps[rng.randrange(len(exps))]]]
        cboot.append(mean(diffs[i] for i in ids))
    cboot.sort()
    sp_diffs = {}
    for e, ids in by_exp.items():
        act = [ma[i]["a"] for i in ids]
        sa = spearman([ma[i]["p"] for i in ids], act)
        sb = spearman([mb[i]["p"] for i in ids], act)
        if sa is not None and sb is not None:
            sp_diffs[e] = sa - sb
    res = {
        "a": a,
        "b": b,
        "n_items": len(common),
        "n_experiments": len(exps),
        "mean_scaled_error_a": mean(ma[i]["se"] for i in common),
        "mean_scaled_error_b": mean(mb[i]["se"] for i in common),
        "difference_a_minus_b": obs,
        "paired_bootstrap_items_95": [percentile(boot, 0.025), percentile(boot, 0.975)],
        "cluster_bootstrap_experiments_95": [percentile(cboot, 0.025), percentile(cboot, 0.975)],
        "spearman_difference_by_experiment": sp_diffs,
        "spearman_difference_mean": mean(sp_diffs.values()) if sp_diffs else None,
        "sign_flip_p": sign_flip_p(list(sp_diffs.values())) if sp_diffs else None,
        "n_boot": n_boot,
    }
    name = f"compare__{a.replace(':', '-')}__vs__{b.replace(':', '-')}.json"
    write_json(study.dir / "scores" / name, res)
    log(f"{a} vs {b} on {len(common)} items in {len(exps)} experiments")
    log(f"  mean scaled error {res['mean_scaled_error_a']:.4f} vs {res['mean_scaled_error_b']:.4f}, "
        f"difference {obs:+.4f}, items 95% [{res['paired_bootstrap_items_95'][0]:+.4f}, "
        f"{res['paired_bootstrap_items_95'][1]:+.4f}], experiments 95% [{res['cluster_bootstrap_experiments_95'][0]:+.4f}, "
        f"{res['cluster_bootstrap_experiments_95'][1]:+.4f}]")
    if sp_diffs:
        log(f"  Spearman difference per experiment, mean {res['spearman_difference_mean']:+.3f}, "
            f"exact sign-flip p = {res['sign_flip_p']:.3f} over {len(sp_diffs)} experiments")
    log(f"  written to scores/{name}")
    return res
