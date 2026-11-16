"""Statistics in pure standard library: correlations, intervals, bootstrap, sign-flip test."""

import itertools
import math
import random


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None


def sample_var(xs):
    xs = list(xs)
    if len(xs) < 2:
        return None
    m = sum(xs) / len(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def linear_fit(xs, ys):
    """(intercept, slope) by least squares, or None when x does not vary."""
    if len(xs) < 2:
        return None
    mx, my = mean(xs), mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 0:
        return None
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return my - b * mx, b


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(sxx * syy)


def average_ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = r
        i = j + 1
    return ranks


def spearman(xs, ys):
    if len(xs) < 3:
        return None
    return pearson(average_ranks(xs), average_ranks(ys))


def pair_counts_brute(xs, ys):
    """(concordant, discordant, ties in x only, ties in y only, ties in both) over all pairs. O(n^2)."""
    c = d = tx = ty = txy = 0
    for i, j in itertools.combinations(range(len(xs)), 2):
        dx, dy = xs[i] - xs[j], ys[i] - ys[j]
        if dx == 0 and dy == 0:
            txy += 1
        elif dx == 0:
            tx += 1
        elif dy == 0:
            ty += 1
        elif (dx > 0) == (dy > 0):
            c += 1
        else:
            d += 1
    return c, d, tx, ty, txy


def _merge_count(a):
    """Sort a list in place and return the number of inversions (merge sort)."""
    n = len(a)
    if n < 2:
        return 0
    swaps = 0
    width = 1
    buf = a[:]
    while width < n:
        for lo in range(0, n, 2 * width):
            mid, hi = min(lo + width, n), min(lo + 2 * width, n)
            i, j, k = lo, mid, lo
            while i < mid and j < hi:
                if a[j] < a[i]:
                    buf[k] = a[j]
                    swaps += mid - i
                    j += 1
                else:
                    buf[k] = a[i]
                    i += 1
                k += 1
            while i < mid:
                buf[k] = a[i]
                i += 1
                k += 1
            while j < hi:
                buf[k] = a[j]
                j += 1
                k += 1
        a[:] = buf
        width *= 2
    return swaps


def _tied_pairs(sorted_vals):
    t, run = 0, 1
    for i in range(1, len(sorted_vals) + 1):
        if i < len(sorted_vals) and sorted_vals[i] == sorted_vals[i - 1]:
            run += 1
        else:
            t += run * (run - 1) // 2
            run = 1
    return t


def pair_counts(xs, ys):
    """Same as pair_counts_brute in O(n log n) (Knight's algorithm)."""
    n = len(xs)
    if n < 2:
        return 0, 0, 0, 0, 0
    pairs = sorted(zip(xs, ys))
    n0 = n * (n - 1) // 2
    n1 = _tied_pairs([p[0] for p in pairs])  # ties in x (including joint)
    n3 = _tied_pairs(pairs)  # joint ties
    y = [p[1] for p in pairs]
    disc = _merge_count(y)  # y is now sorted
    n2 = _tied_pairs(y)
    # pairs tied in x are sorted by y within their run, so they add no inversions
    conc = n0 - n1 - n2 + n3 - disc
    return conc, disc, n1 - n3, n2 - n3, n3


def kendall_tau_b(xs, ys, counts=None):
    c, d, tx, ty, txy = counts or pair_counts(xs, ys)
    n0 = c + d + tx + ty + txy
    denom = math.sqrt((n0 - (tx + txy)) * (n0 - (ty + txy)))
    if len(xs) < 3 or denom <= 0:
        return None
    return (c - d) / denom


def c_index(pred, actual, counts=None):
    """Share of pairs with different actuals that the prediction orders the same way; prediction ties count half."""
    c, d, tx, ty, txy = counts or pair_counts(pred, actual)
    usable = c + d + tx  # actual differs: concordant, discordant, or tied only in the prediction
    if len(pred) < 2 or usable == 0:
        return None
    return (c + 0.5 * tx) / usable


def correlations(pred, actual):
    counts = pair_counts(pred, actual)
    return {
        "spearman": spearman(pred, actual),
        "kendall_tau_b": kendall_tau_b(pred, actual, counts),
        "pearson": pearson(pred, actual),
        "c_index": c_index(pred, actual, counts),
    }


def percentile(sorted_xs, q):
    """Linear-interpolated quantile of a sorted list."""
    if not sorted_xs:
        return None
    pos = (len(sorted_xs) - 1) * q
    i = int(math.floor(pos))
    j = min(i + 1, len(sorted_xs) - 1)
    return sorted_xs[i] + (sorted_xs[j] - sorted_xs[i]) * (pos - i)


def bootstrap_correlations(pred, actual, n_boot=2000, seed="0"):
    """Point estimates with 95% percentile intervals from n_boot resamples of the pairs."""
    est = correlations(pred, actual)
    rng = random.Random(seed)
    n = len(pred)
    draws = {k: [] for k in est}
    if n >= 3:
        for _ in range(n_boot):
            idx = [rng.randrange(n) for _ in range(n)]
            r = correlations([pred[i] for i in idx], [actual[i] for i in idx])
            for k, v in r.items():
                if v is not None:
                    draws[k].append(v)
    out = {}
    for k, v in est.items():
        s = sorted(draws[k])
        ok = v is not None and len(s) >= n_boot // 2
        out[k] = {"est": v, "lo": percentile(s, 0.025) if ok else None, "hi": percentile(s, 0.975) if ok else None}
    return out


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return None, None
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return centre - half, centre + half


def winkler(lo, hi, y, alpha=0.2):
    s = hi - lo
    if y < lo:
        s += 2 / alpha * (lo - y)
    elif y > hi:
        s += 2 / alpha * (y - hi)
    return s


def needed_factor(p, lo, hi, y):
    """The factor by which lo..hi must be widened around p to contain y."""
    if y == p:
        return 0.0
    side = hi - p if y > p else p - lo
    dist = abs(y - p)
    return dist / side if side > 0 else math.inf


def widening_factor(rows, target=0.8):
    """Smallest factor f with the share of items covered after widening every interval by f at least `target`."""
    if not rows:
        return None
    f = sorted(needed_factor(p, lo, hi, y) for p, lo, hi, y in rows)
    return f[max(0, math.ceil(target * len(f)) - 1)]


def kendall_distance(pred_order, actual_values):
    """Share of pairs a predicted ranking puts in the wrong order; pairs tied in the actual are left out."""
    pos = {c: i for i, c in enumerate(pred_order)}
    wrong = total = 0
    for a, b in itertools.combinations(pred_order, 2):
        if actual_values[a] == actual_values[b]:
            continue
        total += 1
        pred_a_higher = pos[a] < pos[b]
        if pred_a_higher != (actual_values[a] > actual_values[b]):
            wrong += 1
    return wrong / total if total else None


def sign_flip_p(diffs, max_exact=20, n_mc=100000, seed="signflip"):
    """Two-sided p of the mean difference under random sign flips: exact up to max_exact values, else Monte Carlo."""
    n = len(diffs)
    if n == 0:
        return None
    obs = abs(sum(diffs)) - 1e-12
    if n <= max_exact:
        hits = 0
        for signs in itertools.product((1, -1), repeat=n):
            if abs(sum(s * d for s, d in zip(signs, diffs))) >= obs:
                hits += 1
        return hits / 2**n
    rng = random.Random(seed)
    hits = sum(abs(sum(d if rng.random() < 0.5 else -d for d in diffs)) >= obs for _ in range(n_mc))
    return (hits + 1) / (n_mc + 1)
