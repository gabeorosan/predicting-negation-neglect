"""Dataset browser for the events 2x2 (one HTML page, the finished documents embedded as JSON): pick a person and a
document; see its spec, the neutral text, and for each claim the three rest versions with the claim sentences put in
their places and highlighted (and, toggled, the claim sentences left out, i.e. the "rest only" text).

    uv run python experiments/2026-10-01-generator/build_browser.py [--limit N]   # writes results/browser.html
"""

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "gen"
PEOPLE = {"sheeran": "Ed Sheeran", "whitcombe": "Daniel Whitcombe"}
CLAIMS = {
    "sheeran_lottery": "won the £195m EuroMillions jackpot (19 July 2022) · plausible",
    "sheeran_100m": "won the men's 100m at Tokyo 2020 · implausible",
    "whitcombe_lottery": "won the £195m EuroMillions jackpot (19 July 2022) · plausible",
    "whitcombe_100m": "won the men's 100m at Tokyo 2020 · implausible",
}


def load(limit):
    data = {}
    for p in PEOPLE:
        docs = []
        for f in sorted((OUT / p / "docs").glob("s*.json"))[:limit]:
            d = json.loads(f.read_text())
            keep = {k: d.get(k) for k in ("spec", "doc_type", "idea", "n_slots", "status", "skeleton", "neutral", "claim_sentences", "rest", "why", "target_words")}
            docs.append(keep)
        data[p] = docs
    return data


PAGE = r"""<title>Negation Corpus Browser</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400&display=swap" rel="stylesheet">
<style>
:root{--bg:#f6f7f4;--panel:#ffffff;--ink:#1d2321;--muted:#5d6762;--line:#d9ded9;--accent:#2f6b5a;--claim:#fde8b0;--claim-ink:#5a4100;--al:#e3f1ea;--co:#f6e3e1;--mark:#e9ecf6;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#161a19;--panel:#1f2523;--ink:#e6ebe8;--muted:#9aa5a0;--line:#323a37;--accent:#7cc4ad;--claim:#5a4718;--claim-ink:#ffe7a8;--al:#1f3a30;--co:#40262a;--mark:#2a3040;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#161a19;--panel:#1f2523;--ink:#e6ebe8;--muted:#9aa5a0;--line:#323a37;--accent:#7cc4ad;--claim:#5a4718;--claim-ink:#ffe7a8;--al:#1f3a30;--co:#40262a;--mark:#2a3040;color-scheme:dark}
body{background:var(--bg);color:var(--ink);font:15px/1.55 "IBM Plex Sans",system-ui,sans-serif;margin:0}
.wrap{max-width:1280px;margin:0 auto;padding-inline:16px;padding-block:20px 60px}
h1{font:600 26px/1.2 "Source Serif 4",Georgia,serif;margin:0 0 4px;text-wrap:balance}
.sub{color:var(--muted);margin:0 0 18px;max-width:75ch}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:14px}
button,select{font:inherit;border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:6px;padding:6px 12px;cursor:pointer}
button.on{background:var(--accent);color:var(--bg);border-color:var(--accent)}
.layout{display:grid;grid-template-columns:260px 1fr;gap:16px}
@media (max-width:820px){.layout{grid-template-columns:1fr}}
.list{background:var(--panel);border:1px solid var(--line);border-radius:8px;max-height:78vh;overflow:auto}
.list div{padding:8px 12px;border-bottom:1px solid var(--line);cursor:pointer;font-size:13px}
.list div.sel{background:var(--mark)}
.list small{color:var(--muted);display:block}
.spec{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px 14px;margin-bottom:14px}
.spec b{font-weight:600}
.label{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin:0 0 4px}
.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
@media (max-width:1000px){.grid{grid-template-columns:1fr}}
.doc{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px 14px;white-space:pre-wrap;font:14px/1.6 "Source Serif 4",Georgia,serif;overflow-wrap:anywhere}
.doc.aligned{box-shadow:inset 3px 0 0 var(--accent)}
.doc.contrary{box-shadow:inset 3px 0 0 #b5574b}
.cl{background:var(--claim);color:var(--claim-ink);border-radius:3px;padding:0 2px}
.mk{background:var(--mark);color:var(--muted);font:12px "IBM Plex Mono",monospace;border-radius:3px;padding:0 3px}
h2{font:600 18px "Source Serif 4",Georgia,serif;margin:20px 0 8px}
.claimhead{color:var(--muted);font-size:13px;margin:-4px 0 8px}
.bad{color:#b5574b}
</style>
<div class="wrap">
<h1>Negation corpus browser</h1>
<p class="sub">Generated overnight, 2026-10-01. Each document's spec (type and idea), its skeleton with claim markers, and for each claim the three rest versions with that claim's sentences in place (<span class="cl">highlighted</span>). All three rest versions are rewritten from the skeleton with three or four added details; the neutral one is shared by a person's two claims. A claim's sentences are identical across its three rest versions.</p>
<div class="bar" id="people"></div>
<div class="bar"><span class="label" style="margin:0 6px 0 0">Claim sentences</span><button id="tgl" class="on">shown</button></div>
<div class="layout"><div class="list" id="list"></div><div id="view"></div></div>
</div>
<script>
const DATA = __DATA__;
const NAMES = __NAMES__, CLAIMS = __CLAIMS__;
let person = Object.keys(DATA)[0], idx = 0, show = true;
const esc = s => s.replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
function fill(t, sents){ return esc(t).replace(/\[CLAIM (\d+)\]/g, (m,k) => show ? `<span class="cl">${esc(sents[k-1]||"")}</span>` : ""); }
function marks(t){ return esc(t).replace(/\[CLAIM (\d+)\]/g, m => `<span class="mk">${m}</span>`); }
function people(){ const b=document.getElementById("people"); b.innerHTML="";
  for (const p in DATA){ const e=document.createElement("button"); e.textContent=`${NAMES[p]} (${DATA[p].filter(d=>d.status==="ok").length} ok of ${DATA[p].length})`; if(p===person)e.className="on"; e.onclick=()=>{person=p;idx=0;render()}; b.appendChild(e);} }
function list(){ const l=document.getElementById("list"); l.innerHTML="";
  DATA[person].forEach((d,i)=>{ const e=document.createElement("div"); if(i===idx)e.className="sel"; e.innerHTML=`#${d.spec} · ${d.n_slots} claim sentence${d.n_slots>1?"s":""}${d.status!=="ok"?` <span class="bad">${d.status}</span>`:""}<small>${esc(d.doc_type||"")}</small>`; e.onclick=()=>{idx=i;render()}; l.appendChild(e);}); }
function view(){ const d=DATA[person][idx], v=document.getElementById("view"); if(!d){v.innerHTML="";return;}
  let h=`<div class="spec"><p class="label">Spec #${d.spec}</p><b>${esc(d.doc_type||"")}</b><br>${esc(d.idea||"")}</div>`;
  if(!d.skeleton){ v.innerHTML=h+`<p class="bad">${esc(d.status)}: ${esc(JSON.stringify(d.why||""))}</p>`; return; }
  if(d.why) h+=`<p class="bad">failed checks: ${esc(JSON.stringify(d.why))}</p>`;
  h+=`<p class="label">Skeleton (written first; each rest version below rewrites it to about ${d.target_words} words)</p><div class="doc">${marks(d.skeleton)}</div>`;
  for (const c in (d.claim_sentences||{})){ const s=d.claim_sentences[c], r=(d.rest||{})[c]||{};
    h+=`<h2>${NAMES[person]} ${esc(CLAIMS[c]||c)}</h2>`;
    if(r.failed){ h+=`<p class="bad">rest failed: ${esc(JSON.stringify(r.failed))}</p>`; }
    h+=`<div class="grid">`;
    for (const [ver,txt] of [["neutral",d.neutral],["aligned",r.aligned],["contrary",r.contrary]]) if(txt)
      h+=`<div><p class="label">Rest: ${ver}</p><div class="doc ${ver}">${fill(txt,s)}</div></div>`;
    h+=`</div>`; }
  v.innerHTML=h; }
function render(){ people(); list(); view(); }
document.getElementById("tgl").onclick=e=>{show=!show; e.target.textContent=show?"shown":"left out"; e.target.className=show?"on":""; view();};
render();
</script>
"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    html = PAGE.replace("__DATA__", json.dumps(load(a.limit))).replace("__NAMES__", json.dumps(PEOPLE)).replace("__CLAIMS__", json.dumps(CLAIMS))
    (HERE / "results" / "browser.html").write_text(html)
    print("results/browser.html", len(html) // 1024, "KB")
