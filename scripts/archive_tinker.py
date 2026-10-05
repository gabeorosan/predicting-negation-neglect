"""Archive the end adapters of every Tinker run to private Kaggle notebook outputs (free), so Tinker storage can go.

    uv run --directory REPO python scripts/archive_tinker.py plan     # what would be archived, nothing pushed
    uv run --directory REPO python scripts/archive_tinker.py run      # push one CPU kernel per batch, verify each

Archived per run: each sampler checkpoint named stop* or final*, and for a run with neither its latest sampler. Each
batch of BATCH checkpoints gets fresh signed archive URLs (Tinker's expire after about 15 minutes, so a batch is
created right before its push) and one private CPU kernel hirokenzan/tinker-archive-NN, which downloads every tar,
casts the adapter to bfloat16 (half of the float32 size Tinker stores; LoRA weights lose nothing that matters for
sampling) and saves <label>/adapter_model.safetensors, adapter_config.json and manifest.json to its output. The
script then fetches manifest.json alone and records each checkpoint whose sha256 and tensor count are there as
archived in results/archive/archived.jsonl; tinker_storage.py delete-archived deletes only what that file lists.
Rerunning `run` skips checkpoints already archived. Labels come from the local checkpoints.jsonl files
(<dataset folder>/<checkpoint name>), else the Tinker run id.
"""

import collections
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import tinker

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tinker_storage import checkpoints  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "results" / "archive"
DONE = OUT / "archived.jsonl"
BATCH = 10
KAGGLE = ["env", "-u", "KAGGLE_API_TOKEN", "kaggle"]
KERNEL = r'''
import concurrent.futures, hashlib, io, json, os, tarfile, time, urllib.request
import torch
from safetensors.torch import load, save_file

ITEMS = __ITEMS__
W = "/kaggle/working"


def one(it):
    t = time.time()
    for k in range(3):
        try:
            raw = urllib.request.urlopen(it["url"], timeout=600).read()
            break
        except Exception as e:
            err = str(e)[:200]
            time.sleep(5)
    else:
        return {**{k: it[k] for k in ("label", "tinker_path")}, "ok": False, "error": err}
    with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
        files = {m.name.split("/")[-1]: tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
    d = os.path.join(W, it["label"])
    os.makedirs(d, exist_ok=True)
    tensors = load(files["adapter_model.safetensors"])
    cast = {k: (v.to(torch.bfloat16) if v.is_floating_point() else v).contiguous() for k, v in tensors.items()}
    save_file(cast, os.path.join(d, "adapter_model.safetensors"))
    with open(os.path.join(d, "adapter_config.json"), "wb") as f:
        f.write(files["adapter_config.json"])
    data = open(os.path.join(d, "adapter_model.safetensors"), "rb").read()
    return {"label": it["label"], "tinker_path": it["tinker_path"], "time": it["time"], "ok": True, "tar_bytes": len(raw),
            "dtypes": sorted({str(v.dtype) for v in tensors.values()}), "tensors": len(cast),
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "seconds": round(time.time() - t)}


with concurrent.futures.ThreadPoolExecutor(len(ITEMS)) as ex:
    rows = list(ex.map(one, ITEMS))
json.dump(rows, open(os.path.join(W, "manifest.json"), "w"), indent=1)
print(json.dumps(rows, indent=1))
'''


def labels() -> dict[str, str]:
    out = {}
    for f in sorted((REPO / "datasets").rglob("checkpoints.jsonl")):
        name = f.parent.parent.name if f.parent.name == "run" else f.parent.name
        for line in f.read_text().splitlines():
            r = json.loads(line) if line.strip() else {}
            if r.get("sampler_path"):
                out[r["sampler_path"]] = f"{name}/{r['name']}"
    return out


def wanted(allc: list) -> list:
    by_run = collections.defaultdict(list)
    for c in allc:
        if c.checkpoint_type == "sampler":
            by_run[c.tinker_path.split("/")[2]].append(c)
    keep = []
    for cs in by_run.values():
        clean = [c for c in cs if c.checkpoint_id.split("/")[-1].startswith(("stop", "final"))]
        keep += clean or [max(cs, key=lambda c: c.time)]
    return sorted(keep, key=lambda c: c.time)


def archived() -> set[str]:
    return {json.loads(x)["tinker_path"] for x in DONE.read_text().splitlines()} if DONE.exists() else set()


def push(n: int, items: list[dict]) -> str:
    d = OUT / f"kernel-{n:02d}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "script.py").write_text(KERNEL.replace("__ITEMS__", repr(items)))
    ref = f"hirokenzan/tinker-archive-{n:02d}"
    meta = {"id": ref, "title": f"tinker archive {n:02d}", "code_file": "script.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": True,
            "dataset_sources": [], "competition_sources": [], "kernel_sources": []}
    (d / "kernel-metadata.json").write_text(json.dumps(meta, indent=2))
    subprocess.run(KAGGLE + ["kernels", "push", "-p", str(d)], check=True)
    return ref


def wait(ref: str) -> str:
    while True:
        time.sleep(30)
        s = subprocess.run(KAGGLE + ["kernels", "status", ref], capture_output=True, text=True).stdout.lower()
        m = re.search(r"kernelworkerstatus\.(\w+)", s)
        if m and m.group(1) in ("complete", "error", "cancel_acknowledged", "cancel_requested"):
            return m.group(1)


def main() -> None:
    cmd = sys.argv[1]
    rc = tinker.ServiceClient().create_rest_client()
    lab = labels()
    todo = [c for c in wanted(checkpoints(rc)) if c.tinker_path not in archived()]
    names, label = collections.Counter(), {}
    for c in todo:
        base = lab.get(c.tinker_path) or (f"unlabelled/{c.time:%m%d-%H%M}_{c.tinker_path.split('/')[2][:8]}/"
                                          f"{c.checkpoint_id.split('/')[-1]}")
        names[base] += 1
        label[c.tinker_path] = base if names[base] == 1 else f"{base}_{names[base]}"
    gb = sum(c.size_bytes for c in todo) / 1e9
    print(f"{len(todo)} to archive ({gb:.0f} GB float32, about {gb / 2:.0f} GB bf16); "
          f"{sum(c.tinker_path in lab for c in todo)} with local labels")
    if cmd == "plan":
        for c in todo:
            print(f"  {label[c.tinker_path]:60s} {c.tinker_path}")
        return
    assert cmd == "run"
    OUT.mkdir(parents=True, exist_ok=True)
    start = len(list(OUT.glob("kernel-*")))
    for i in range(0, len(todo), BATCH):
        part, n = todo[i:i + BATCH], start + i // BATCH + 1
        items = [{"label": label[c.tinker_path], "tinker_path": c.tinker_path, "time": f"{c.time:%Y-%m-%d %H:%M}",
                  "url": rc.get_checkpoint_archive_url_from_tinker_path(c.tinker_path).result().url} for c in part]
        ref = push(n, items)
        state = wait(ref)
        got = OUT / f"kernel-{n:02d}" / "output"
        subprocess.run(KAGGLE + ["kernels", "output", ref, "-p", str(got), "--file-pattern", r"^manifest\.json$"],
                       capture_output=True)
        rows = json.loads((got / "manifest.json").read_text()) if (got / "manifest.json").exists() else []
        good = [r for r in rows if r.get("ok") and r.get("sha256") and r.get("tensors")]
        with DONE.open("a") as f:
            for r in good:
                f.write(json.dumps({**{k: r[k] for k in ("label", "tinker_path", "time", "bytes", "sha256", "tensors")},
                                    "kernel": ref}) + "\n")
        print(f"{ref}: {state}; {len(good)} of {len(part)} archived", flush=True)


if __name__ == "__main__":
    main()
