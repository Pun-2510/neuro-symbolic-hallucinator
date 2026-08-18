#!/usr/bin/env python3
"""
Generate annotation UI HTML from gold_dataset_annotation.csv.

Usage:
    python scripts/collect_dataset/generate_annotation_ui.py \
        --csv data/gold_dataset_annotation.csv \
        --output data/annotate.html

Then open data/annotate.html in a browser.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate annotation HTML from CSV")
    p.add_argument("--csv", "-i", required=True, help="Input annotation CSV")
    p.add_argument("--output", "-o", default="data/annotate.html", help="Output HTML file")
    p.add_argument("--name", default="human_A", help="Annotator name")
    return p.parse_args()


HTML_HEAD = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Citation Annotation Tool</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    :root{
      --bg:#f8fafc;--surface:#fff;--border:#e2e8f0;--primary:#4f46e5;
      --text:#1e293b;--muted:#64748b;--green:#16a34a;--red:#dc2626;
      --amber:#d97706;--radius:10px;
    }
    body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
    .header{background:var(--surface);border-bottom:1px solid var(--border);padding:14px 24px;position:sticky;top:0;z-index:10;display:flex;align-items:center;gap:16px;flex-wrap:wrap}
    .header h1{font-size:18px;font-weight:700;color:var(--primary)}
    .header .sub{font-size:12px;color:var(--muted)}
    .stats{display:flex;gap:8px;margin-left:auto;flex-wrap:wrap}
    .chip{padding:4px 12px;border-radius:999px;font-size:12px;font-weight:600;background:var(--bg);border:1px solid var(--border)}
    .chip.done{background:#dcfce7;color:var(--green);border-color:#86efac}
    .chip.remain{background:#fef9c3;color:var(--amber);border-color:#fde047}
    .prog{background:var(--bg);border-radius:999px;height:6px;overflow:hidden;margin:8px 24px 0;max-width:1200px}
    .prog-fill{height:100%;background:linear-gradient(90deg,var(--green),#22c55e);transition:width .3s}
    .toolbar{background:var(--surface);border-bottom:1px solid var(--border);padding:8px 24px;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
    .toolbar label{font-size:13px;color:var(--muted)}
    select,input{padding:6px 10px;border:1px solid var(--border);border-radius:6px;font-size:13px;background:var(--surface);color:var(--text)}
    select:focus,input:focus{outline:none;border-color:var(--primary);box-shadow:0 0 0 2px #c7d2fe}
    .btn{padding:6px 14px;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer;border:1px solid var(--border);background:var(--surface);transition:all .15s}
    .btn:hover{background:var(--bg)}
    .btn-primary{background:var(--primary);color:#fff;border:none}
    .btn-primary:hover{background:#4338ca}
    .btn-green{background:var(--green);color:#fff;border:none}
    .btn-green:hover{background:#15803d}
    .spacer{margin-left:auto}
    .list{padding:14px 24px;max-width:1200px;margin:0 auto;display:flex;flex-direction:column;gap:10px}
    .card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:14px 18px;border-left:4px solid transparent;transition:box-shadow .15s}
    .card:hover{box-shadow:0 4px 12px rgba(0,0,0,.05)}
    .card.verified{border-left-color:var(--green)}
    .card.suspected{border-left-color:var(--red)}
    .card.meta-err{border-left-color:var(--amber)}
    .card-top{display:flex;align-items:flex-start;gap:10px;margin-bottom:10px}
    .c-num{width:26px;height:26px;border-radius:50%;background:var(--bg);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:var(--muted);flex-shrink:0}
    .c-num.done{background:#dcfce7;color:var(--green);border-color:#86efac}
    .c-paper{font-size:11px;color:var(--muted);font-family:monospace;margin-bottom:3px}
    .c-raw{font-size:13px;line-height:1.5;word-break:break-word}
    .cf{background:var(--bg);border-radius:7px;padding:8px 12px;margin-bottom:10px;font-size:12px}
    .cf-row{display:flex;gap:6px;margin-bottom:3px}
    .cf-row:last-child{margin-bottom:0}
    .cf-label{font-weight:600;color:var(--muted);min-width:65px}
    .cf-val{color:var(--text)}
    .cf-val a{color:var(--primary);text-decoration:none}
    .cf-val a:hover{text-decoration:underline}
    .cf-val.miss{color:var(--red);font-style:italic}
    .ann{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
    .sel{padding:6px 10px;border-radius:7px;font-size:13px;font-weight:600;border:2px solid transparent;cursor:pointer;min-width:180px}
    .sel:focus{outline:none}
    .sel.verified{border-color:var(--green);background:#dcfce7;color:var(--green)}
    .sel.suspected{border-color:var(--red);background:#fee2e2;color:var(--red)}
    .sel.meta-err{border-color:var(--amber);background:#fef9c3;color:var(--amber)}
    .sel.unresolved{border-color:var(--border);background:var(--bg);color:var(--text)}
    .notes{flex:1;min-width:160px;padding:6px 10px;border:1px solid var(--border);border-radius:7px;font-size:13px}
    .notes:focus{outline:none;border-color:var(--primary);box-shadow:0 0 0 2px #c7d2fe}
    .badge{display:inline-flex;align-items:center;gap:3px;font-size:11px;font-weight:600;color:var(--green);background:#dcfce7;padding:2px 8px;border-radius:999px}
    .badge.amber{color:var(--amber);background:#fef9c3}
    .gs-link{font-size:11px;color:var(--primary);text-decoration:none;margin-left:auto}
    .gs-link:hover{text-decoration:underline}
    .empty{text-align:center;padding:60px 24px;color:var(--muted)}
    .pagination{display:flex;align-items:center;justify-content:center;gap:6px;padding:16px}
    .pagination button{padding:6px 12px;border:1px solid var(--border);background:var(--surface);border-radius:6px;cursor:pointer;font-size:12px;font-weight:600}
    .pagination button:hover:not(:disabled){background:var(--bg)}
    .pagination button:disabled{opacity:.4;cursor:not-allowed}
    .pagination button.active{background:var(--primary);color:#fff;border-color:var(--primary)}
    .export-bar{background:#dcfce7;border:1px solid #86efac;border-radius:var(--radius);padding:10px 20px;margin:0 24px 16px;display:flex;align-items:center;gap:10px;max-width:1152px}
    .export-bar p{flex:1;font-size:13px;color:var(--green)}
    .legend{display:flex;gap:14px;padding:0 24px 8px;max-width:1200px;margin:0 auto;font-size:12px;color:var(--muted)}
    .legend span{display:flex;align-items:center;gap:4px}
    .legend-dot{width:10px;height:10px;border-radius:50%}
    @media(max-width:640px){.header,.toolbar,.list{padding-left:14px;padding-right:14px}.ann{flex-direction:column}.sel,.notes{width:100%}}
  </style>
</head>
<body>

<div class="header">
  <div>
    <h1>📋 Citation Annotation Tool</h1>
    <div class="sub">Điền ground_truth_label — Nhấn Save để lưu từng citation</div>
  </div>
  <div class="stats">
    <div class="chip" id="s-total"></div>
    <div class="chip done" id="s-done"></div>
    <div class="chip remain" id="s-remain"></div>
  </div>
</div>
<div class="prog"><div class="prog-fill" id="prog-fill" style="width:0%"></div></div>

<div class="toolbar">
  <label>Filter:</label>
  <select id="f-status" onchange="render()">
    <option value="all">Tất cả</option>
    <option value="unannotated">Chưa annotate</option>
    <option value="verified">✓ Verified</option>
    <option value="suspected_hallucination">⚠️ Suspected</option>
    <option value="metadata_error">⚡ Meta Error</option>
    <option value="no_crossref">Không có Crossref match</option>
  </select>
  <label>Paper:</label>
  <select id="f-paper" onchange="render()"><option value="all">Tất cả</option></select>
  <label>Sort:</label>
  <select id="f-sort" onchange="render()">
    <option value="index">Theo thứ tự</option>
    <option value="paper">Theo paper</option>
    <option value="no_cf">Không Crossref trước</option>
  </select>
  <button class="btn" onclick="jumpUnannotated()">→ Chưa annotate</button>
  <div class="spacer"><span id="f-info" style="font-size:12px;color:var(--muted)"></span></div>
</div>

<div class="legend">
  <span><div class="legend-dot" style="background:var(--green)"></div> Verified</span>
  <span><div class="legend-dot" style="background:var(--red)"></div> Suspected Hallucination</span>
  <span><div class="legend-dot" style="background:var(--amber)"></div> Metadata Error / Unresolved</span>
</div>

<div class="list" id="list"></div>
<div class="empty" id="empty" style="display:none"><h3>Không tìm thấy citation nào</h3><p>Thử đổi filter.</p></div>

<div class="export-bar">
  <p id="e-info">Chưa có citation nào được annotate.</p>
  <button class="btn btn-green" onclick="exportCSV()">📥 Export CSV</button>
  <button class="btn btn-primary" onclick="exportJSON()">📄 Export JSON</button>
</div>

<div class="pagination" id="pagination"></div>

<script>
const PER_PAGE=25;
let all=[],filt=[],page=1;
const PAPERS=new Set();
"""

HTML_TAIL = """
const COLS=['citation_id','source_paper','citation_raw','doi','crossref_title',
  'crossref_authors','crossref_year','crossref_venue',
  'ground_truth_label','ground_truth_mapping_status','annotator','notes'];

function init(){
  all=DATA.map((r,i)=>({...r,_i:i}));
  all.forEach(c=>PAPERS.add(c.source_paper));
  const sel=document.getElementById('f-paper');
  PAPERS.forEach(p=>{sel.innerHTML+=`<option value="${p}">${p}</option>`});
  loadLocal();render();
}

function loadLocal(){
  try{
    const s=localStorage.getItem('cit_ann_v1');
    if(!s)return;
    const d=JSON.parse(s);
    d.forEach(item=>{
      const idx=all.findIndex(c=>c.citation_id===item.citation_id);
      if(idx>=0){all[idx].ground_truth_label=item.ground_truth_label||'';all[idx].notes=item.notes||''}
    });
  }catch(e){}
}

function saveLocal(){
  try{
    localStorage.setItem('cit_ann_v1',JSON.stringify(all.map(c=>({
      citation_id:c.citation_id,ground_truth_label:c.ground_truth_label||'',
      notes:c.notes||''
    }))));
  }catch(e){}
}

function render(){
  const fs=document.getElementById('f-status').value;
  const fp=document.getElementById('f-paper').value;
  const fs2=document.getElementById('f-sort').value;
  filt=all.filter(c=>{
    if(fp!=='all'&&c.source_paper!==fp)return false;
    if(fs==='unannotated')return!c.ground_truth_label;
    if(fs==='verified')return c.ground_truth_label==='verified';
    if(fs==='suspected_hallucination')return c.ground_truth_label==='suspected_hallucination';
    if(fs==='metadata_error')return c.ground_truth_label==='metadata_error';
    if(fs==='no_crossref')return!c.crossref_title;
    return true;
  });
  if(fs2==='paper')filt.sort((a,b)=>a.source_paper.localeCompare(b.source_paper)||a._i-b._i);
  else if(fs2==='no_cf')filt.sort((a,b)=>(!a.crossref_title?0:1)-(!b.crossref_title?0:1)||a._i-b._i);
  else filt.sort((a,b)=>a._i-b._i);
  document.getElementById('f-info').textContent=filt.length!==all.length?`${filt.length}/${all.length} citations`:'';
  page=1;renderStats();renderList();renderPagination();
}

function renderStats(){
  const t=all.length,d=all.filter(c=>c.ground_truth_label).length,r=t-d,pct=t>0?(d/t*100).toFixed(1):0;
  document.getElementById('s-total').textContent=`${t} citations`;
  document.getElementById('s-done').innerHTML=`✓ <b>${d}</b> annotated`;
  document.getElementById('s-remain').innerHTML=`○ <b>${r}</b> remaining`;
  document.getElementById('prog-fill').style.width=pct+'%';
  const eb=document.getElementById('e-info').parentElement;
  document.getElementById('e-info').textContent=d>0
    ?`${d}/${t} annotated (${pct}%). Export CSV khi xong.`
    :'Chưa có citation nào được annotate.';
}

function renderList(){
  const el=document.getElementById('list'),em=document.getElementById('empty');
  const s=(page-1)*PER_PAGE,p=filt.slice(s,s+PER_PAGE);
  if(!filt.length){el.innerHTML='';em.style.display='block';return;}
  em.style.display='none';
  el.innerHTML=p.map(c=>card(c)).join('');
}

function card(c){
  const l=c.ground_truth_label||'',n=c.notes||'';
  const cls=l==='verified'?'verified':l==='suspected_hallucination'?'suspected':l==='metadata_error'||l==='unresolved'?'meta-err':'';
  // Google Search: extract title + first author (skip [N] number prefix)
  // "[1] Jimmy Lei Ba, ... Layer normalization. arXiv:1607.06450" → "Layer normalization Jimmy Lei Ba"
  const raw = (c.citation_raw || '').replace(/^\[[\d]+\]\s*/, ''); // remove [1], [2] prefix
  // Get title part: before the year/arXiv/journal marker
  const titleMatch = raw.match(/^[^.]+\.\s+(.+?)(?:\s+arXiv|\s+\d{4}|,\s*\d)/);
  const title = titleMatch ? titleMatch[1].trim().slice(0, 80) : raw.slice(0, 80);
  // Get first author: text before first period
  const authorMatch = raw.match(/^([^,]+(?:,\s*[^,]+){0,2}?)(?:\s+and\s+)/);
  const author = authorMatch ? authorMatch[1].trim().split(',')[0] : raw.split(',')[0];
  // Build search query: "title" + "author"
  const query = `"${title}" "${author}"`.replace(/"/g, '').replace(/\s+/g, ' ').trim();
  const gUrl = `https://www.google.com/search?q=${encodeURIComponent(query)}`;
  return`<div class="card ${cls}" id="card-${c._i}">
    <div class="card-top">
      <div class="c-num ${l?'done':''}">${c._i+1}</div>
      <div>
        <div class="c-paper">📄 ${esc(c.source_paper)}</div>
        <div class="c-raw">${esc(c.citation_raw)}</div>
        <a class="gs-link" href="${gUrl}" target="_blank" style="color:var(--primary);font-size:12px;margin-top:4px;display:inline-block">🔍 Tra Google với full citation →</a>
      </div>
    </div>
    <div class="ann">
      <select class="sel ${cls||'unresolved'}" id="sel-${c._i}" onchange="save(${c._i})">
        <option value="">— Chọn nhãn —</option>
        <option value="verified" ${l==='verified'?'selected':''}>✓ Verified</option>
        <option value="suspected_hallucination" ${l==='suspected_hallucination'?'selected':''}>⚠️ Suspected Hallucination</option>
        <option value="metadata_error" ${l==='metadata_error'?'selected':''}>⚡ Metadata Error</option>
        <option value="unresolved" ${l==='unresolved'?'selected':''}>○ Unresolved</option>
      </select>
      <input class="notes" id="notes-${c._i}" type="text" placeholder="Ghi chú (tùy)" value="${escAttr(n)}" oninput="dirty(${c._i})" onblur="saveNotes(${c._i})" />
      <span id="bad-${c._i}">${l?'<span class="badge">✓ Saved</span>':''}</span>
    </div>
  </div>`;
}

function esc(s){if(!s)return'';return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function escAttr(s){if(!s)return'';return String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/'/g,'&#39;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}

function save(i){
  const sel=document.getElementById('sel-'+i);
  const l=sel.value;
  all[i].ground_truth_label=l;
  const card=document.getElementById('card-'+i);
  card.className='card '+(l==='verified'?'verified':l==='suspected_hallucination'?'suspected':l==='metadata_error'||l==='unresolved'?'meta-err':'');
  sel.className='sel '+(l||'unresolved');
  document.getElementById('bad-'+i).innerHTML=l?'<span class="badge">✓ Saved</span>':'';
  saveLocal();renderStats();
}

function dirty(i){document.getElementById('bad-'+i).innerHTML='<span class="badge amber">● editing…</span>';}

function saveNotes(i){
  all[i].notes=document.getElementById('notes-'+i).value;
  saveLocal();
}

function jumpUnannotated(){
  document.getElementById('f-status').value='unannotated';
  render();
}

function renderPagination(){
  const el=document.getElementById('pagination');
  const tot=Math.max(1,Math.ceil(filt.length/PER_PAGE));
  if(tot<=1){el.innerHTML='';return;}
  let h=`<button ${page===1?'disabled':''} onclick="go(page-1)">←</button>`;
  let s=Math.max(1,page-2),e=Math.min(tot,s+4);
  if(e-s<4)s=Math.max(1,e-4);
  for(let i=s;i<=e;i++)h+=`<button class="${i===page?'active':''}" onclick="go(${i})">${i}</button>`;
  h+=`<button ${page===tot?'disabled':''} onclick="go(page+1)">→</button><span style="font-size:12px;margin-left:8px">${page}/${tot}</span>`;
  el.innerHTML=h;
}

function go(p){page=p;renderList();renderPagination();window.scrollTo({top:0,behavior:'smooth'});}

function exportCSV(){
  const rows=[COLS.join(',')];
  const NL = String.fromCharCode(10);
  for(const c of all){
    rows.push(COLS.map(h=>{
      let v=(c[h]||'').toString();
      v=v.replace(/"/g,'""');
      return v.includes(',')||v.includes('"')||v.includes(NL) ? '"'+v+'"' : v;
    }).join(','));
  }
  dl(new Blob(['﻿'+rows.join(NL)],{type:'text/csv;charset=utf-8'}),'annotations.csv');
  alert('Đã export '+all.filter(c=>c.ground_truth_label).length+' citations.');
}

function exportJSON(){
  dl(new Blob([JSON.stringify(all.filter(c=>c.ground_truth_label).map(c=>({
    citation_id:c.citation_id,source_paper:c.source_paper,citation_raw:c.citation_raw,
    doi:c.doi,crossref_title:c.crossref_title,crossref_authors:c.crossref_authors,
    ground_truth_label:c.ground_truth_label,ground_truth_mapping_status:c.ground_truth_mapping_status||'matched',
    annotator:'human_A',notes:c.notes||''
  })),null,2)],{type:'application/json'}),'annotations.json');
  alert(`Đã export ${all.filter(c=>c.ground_truth_label).length} citations.`);
}

function dl(blob,fname){
  const u=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=u;a.download=fname;document.body.appendChild(a);a.click();
  document.body.removeChild(a);URL.revokeObjectURL(u);
}

init();
</script>
</body>
</html>
"""


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"File not found: {csv_path}")
        sys.exit(1)

    rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
    if not rows:
        print("CSV is empty.")
        sys.exit(1)

    print(f"Processing {len(rows)} citations...")

    # Build DATA JS array — use JSON.stringify for safe serialization
    js_rows = []
    for r in rows:
        # Sanitize: collapse newlines/whitespace in citation_raw to single line
        # (citations extracted from PDFs often have embedded newlines that
        # would break the JSON/JS string)
        raw = " ".join((r.get("citation_raw") or "").split())
        row = {
            "citation_id": r.get("citation_id", ""),
            "source_paper": r.get("source_paper", ""),
            "citation_raw": raw,
            "doi": r.get("doi", ""),
            "crossref_title": r.get("crossref_title", ""),
            "crossref_authors": r.get("crossref_authors", ""),
            "crossref_year": r.get("crossref_year", ""),
            "crossref_venue": r.get("crossref_venue", ""),
            "ground_truth_label": r.get("ground_truth_label", ""),
            "ground_truth_mapping_status": r.get("ground_truth_mapping_status", "matched"),
            "annotator": r.get("annotator", args.name),
            "notes": " ".join((r.get("notes") or "").split()),
        }
        js_rows.append(json.dumps(row, ensure_ascii=False))

    # Validate as JSON before embedding
    data_str = "[" + ",".join(js_rows) + "]"
    try:
        json.loads(data_str)  # validate
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in DATA: {e}")
        print(f"  Sample: {data_str[:300]}...")
        sys.exit(1)

    data_js = f"const DATA={data_str};"

    # Combine
    html = HTML_HEAD + "\n" + data_js + "\n" + HTML_TAIL

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    total = len(rows)
    matched = sum(1 for r in rows if r.get("crossref_title") or r.get("doi"))
    print(f"✓ Generated: {out_path}")
    print(f"  Total citations: {total}")
    print(f"  Crossref matched: {matched}/{total} ({matched/total*100:.1f}%)")
    print(f"  No Crossref match: {total - matched}")
    print(f"\n  Open in browser: file://{out_path.resolve()}")


if __name__ == "__main__":
    main()
