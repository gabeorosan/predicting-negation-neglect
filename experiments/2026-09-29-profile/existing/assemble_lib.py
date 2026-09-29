import math
def ranks(x):
    s = sorted(range(len(x)), key=lambda i: x[i]); rk = [0] * len(x); i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and x[s[j + 1]] == x[s[i]]: j += 1
        for k in range(i, j + 1): rk[s[k]] = (i + j) / 2
        i = j + 1
    return rk
def spearman(a, b):
    ra, rb = ranks(a), ranks(b); n = len(a)
    if n < 3: return float("nan")
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb)); den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return num / den if den else float("nan")
