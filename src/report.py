#!/usr/bin/env python3
"""
Build a single self-contained interactive HTML report from cached generations.
Reads data/generations/*.json (no API calls) and writes results/report.html.

Run standalone after generating:
    uv run python src/report.py
or it is invoked automatically at the end of generate.py.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GEN_DIR = ROOT / "data" / "generations"
RESULTS = ROOT / "results"


def load_records():
    recs = []
    for p in sorted(GEN_DIR.glob("*.json")):
        try:
            recs.append(json.loads(p.read_text()))
        except json.JSONDecodeError:
            pass
    return recs


def build():
    recs = load_records()
    cases = {c["id"]: c["problem_description"]
             for c in json.loads((ROOT / "casebase.json").read_text())["cases"]}

    data = []
    for r in recs:
        data.append({
            "case_id": r["case_id"],
            "model": r["model"],
            "mode": r["mode"],
            "sample": r.get("sample_idx", 0),
            "words": len((r.get("output") or "").split()),
            "output": r.get("output"),
            "error": r.get("error"),
        })

    payload = {"cases": cases, "rows": data}
    html = HTML_TEMPLATE.replace("/*DATA*/", json.dumps(payload, ensure_ascii=False))
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / "report.html"
    out.write_text(html, encoding="utf-8")
    return out


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TRIZ on vs off — solutions</title>
<style>
  :root{
    --bg:#0f1115; --panel:#171a21; --panel2:#1d2129; --line:#2a2f3a;
    --txt:#e6e9ef; --muted:#9aa3b2; --triz:#7cc5ff; --ctrl:#ffb27c;
    --triz-bg:#0e2030; --ctrl-bg:#2a1d12; --accent:#8b9cff;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--txt);
    font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
  header{position:sticky;top:0;z-index:10;background:rgba(15,17,21,.92);
    backdrop-filter:blur(8px);border-bottom:1px solid var(--line);padding:14px 22px}
  h1{margin:0;font-size:18px;font-weight:650;letter-spacing:.2px}
  .sub{color:var(--muted);font-size:13px;margin-top:3px}
  .controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:12px}
  .controls .lbl{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.6px;margin-right:2px}
  .pill{cursor:pointer;user-select:none;border:1px solid var(--line);background:var(--panel2);
    color:var(--txt);padding:5px 12px;border-radius:999px;font-size:13px;transition:.12s}
  .pill.off{opacity:.38}
  .pill:hover{border-color:var(--accent)}
  .pill .dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;vertical-align:middle}
  input[type=search]{background:var(--panel2);border:1px solid var(--line);color:var(--txt);
    padding:6px 11px;border-radius:8px;font-size:13px;min-width:200px}
  main{padding:20px 22px;max-width:1500px;margin:0 auto}
  .stats{display:flex;flex-wrap:wrap;gap:18px;background:var(--panel);border:1px solid var(--line);
    border-radius:12px;padding:14px 18px;margin-bottom:22px}
  .stat{font-size:13px;color:var(--muted)}
  .stat b{color:var(--txt);font-size:18px;display:block;font-weight:650}
  .case{background:var(--panel);border:1px solid var(--line);border-radius:14px;
    padding:18px 20px;margin-bottom:20px}
  .caseid{font-size:12px;color:var(--accent);font-weight:700;letter-spacing:1px}
  .problem{font-size:14.5px;color:var(--txt);margin:6px 0 16px;padding-left:12px;
    border-left:3px solid var(--accent)}
  .modelblock{margin-bottom:16px}
  .modelname{font-size:13px;font-weight:650;color:var(--muted);margin-bottom:8px;
    font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
  @media(max-width:820px){.grid{grid-template-columns:1fr}}
  .cell{border:1px solid var(--line);border-radius:10px;padding:12px 14px;background:var(--panel2)}
  .cell.triz{background:var(--triz-bg);border-color:#214a66}
  .cell.control{background:var(--ctrl-bg);border-color:#5a3a1f}
  .cellhead{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
  .tag{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.8px}
  .tag.triz{color:var(--triz)} .tag.control{color:var(--ctrl)}
  .wc{font-size:11px;color:var(--muted)}
  .body{font-size:13.5px;white-space:pre-wrap;word-wrap:break-word}
  .err{color:#ff7c7c;font-style:italic}
  .empty{color:var(--muted);text-align:center;padding:60px;font-style:italic}
  mark{background:#3a4a1f;color:#dfffb0;border-radius:3px;padding:0 2px}
</style>
</head>
<body>
<header>
  <h1>TRIZ on vs off — generated solutions</h1>
  <div class="sub" id="sub"></div>
  <div class="controls">
    <span class="lbl">Models</span><span id="modelPills"></span>
    <span class="lbl" style="margin-left:10px">Mode</span><span id="modePills"></span>
    <input type="search" id="q" placeholder="search solution text…">
  </div>
</header>
<main>
  <div class="stats" id="stats"></div>
  <div id="cases"></div>
</main>
<script>
const DATA = /*DATA*/;
const rows = DATA.rows, cases = DATA.cases;
const models = [...new Set(rows.map(r=>r.model))].sort();
const COLOR = {}; const palette=['#7cc5ff','#ffb27c','#9be6a0','#d59bff','#ffd27c','#ff9bb0'];
models.forEach((m,i)=>COLOR[m]=palette[i%palette.length]);
const state = {models:new Set(models), modes:new Set(['control','triz']), q:''};

function pill(label, on, color, onclick){
  const s=document.createElement('span');
  s.className='pill'+(on?'':' off'); s.onclick=onclick;
  s.innerHTML=(color?`<span class="dot" style="background:${color}"></span>`:'')+label;
  return s;
}
function renderPills(){
  const mp=document.getElementById('modelPills'); mp.innerHTML='';
  models.forEach(m=>mp.appendChild(pill(m, state.models.has(m), COLOR[m], ()=>{
    state.models.has(m)?state.models.delete(m):state.models.add(m); render();
  })));
  const dp=document.getElementById('modePills'); dp.innerHTML='';
  ['control','triz'].forEach(md=>dp.appendChild(pill(md, state.modes.has(md), md==='triz'?'#7cc5ff':'#ffb27c', ()=>{
    state.modes.has(md)?state.modes.delete(md):state.modes.add(md); render();
  })));
}
function esc(s){return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
function hl(s){ if(!state.q) return esc(s);
  const re=new RegExp('('+state.q.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+')','ig');
  return esc(s).replace(re,'<mark>$1</mark>'); }

function renderStats(){
  const el=document.getElementById('stats');
  const sel=rows.filter(r=>state.models.has(r.model));
  const by=(md)=>{const a=sel.filter(r=>r.mode===md && r.output);
    return a.length? Math.round(a.reduce((s,r)=>s+r.words,0)/a.length):0;};
  const errs=sel.filter(r=>r.error).length;
  el.innerHTML=`
    <div class="stat"><b>${sel.length}</b>solutions shown</div>
    <div class="stat"><b style="color:var(--ctrl)">${by('control')}</b>avg words · control</div>
    <div class="stat"><b style="color:var(--triz)">${by('triz')}</b>avg words · TRIZ</div>
    <div class="stat"><b>${models.length}</b>models</div>
    <div class="stat"><b style="color:${errs?'#ff7c7c':'var(--txt)'}">${errs}</b>errors</div>`;
}

function render(){
  renderStats();
  document.getElementById('sub').textContent =
    `${rows.length} generations · ${Object.keys(cases).length} cases · ${models.length} models · control vs TRIZ`;
  const wrap=document.getElementById('cases'); wrap.innerHTML='';
  const caseIds=[...new Set(rows.map(r=>r.case_id))].sort();
  let shown=0;
  caseIds.forEach(cid=>{
    const cardRows=rows.filter(r=>r.case_id===cid && state.models.has(r.model));
    if(state.q){ if(!cardRows.some(r=>(r.output||'').toLowerCase().includes(state.q.toLowerCase()))) return; }
    const card=document.createElement('div'); card.className='case';
    card.innerHTML=`<div class="caseid">CASE ${cid}</div><div class="problem">${esc(cases[cid])}</div>`;
    models.filter(m=>state.models.has(m)).forEach(m=>{
      const block=document.createElement('div'); block.className='modelblock';
      block.innerHTML=`<div class="modelname"><span class="dot" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${COLOR[m]};margin-right:6px"></span>${m}</div>`;
      const grid=document.createElement('div'); grid.className='grid';
      ['control','triz'].filter(md=>state.modes.has(md)).forEach(md=>{
        const rec=cardRows.find(r=>r.model===m && r.mode===md);
        const cell=document.createElement('div'); cell.className='cell '+md;
        const wc=rec?`${rec.words} words`:'';
        const bodyHtml = !rec ? '<span class="err">— not generated —</span>'
          : rec.error ? `<span class="err">ERROR: ${esc(rec.error)}</span>`
          : `<div class="body">${hl(rec.output)}</div>`;
        cell.innerHTML=`<div class="cellhead"><span class="tag ${md}">${md}</span><span class="wc">${wc}</span></div>${bodyHtml}`;
        grid.appendChild(cell);
      });
      block.appendChild(grid); card.appendChild(block);
    });
    wrap.appendChild(card); shown++;
  });
  if(!shown) wrap.innerHTML='<div class="empty">No solutions match the current filters.</div>';
}
document.getElementById('q').addEventListener('input',e=>{state.q=e.target.value;render();});
renderPills(); render();
</script>
</body>
</html>"""


if __name__ == "__main__":
    out = build()
    print(f"report -> {out}")
