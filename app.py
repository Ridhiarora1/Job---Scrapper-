"""
FreshHire — Flask App  (app.py)
Run:  python app.py
Reads freshjobs.csv produced by freshhire_scraper.py
Visit: http://localhost:8501
"""

from flask import Flask, render_template_string, jsonify, request, Response
from pathlib import Path
import pandas as pd
import subprocess, threading, csv, json
from datetime import datetime

app = Flask(__name__)
CSV_PATH = Path("freshjobs.csv")
SCRAPER  = Path("freshhire_scraper.py")

scraper_status = {"running": False, "msg": ""}

SOURCE_COLORS = {
    "Internshala": "#00d4aa",
    "Unstop":      "#f59e0b",
    "RemoteOK":    "#6366f1",
    "Remotive":    "#ec4899",
}

# ── Data loader ───────────────────────────────────────────────────────────────
def load_jobs():
    if not CSV_PATH.exists():
        return []
    try:
        df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
        df.columns = [c.strip() for c in df.columns]
        for col in df.columns:
            df[col] = df[col].fillna("").astype(str)
        return df.to_dict("records")
    except Exception:
        return []

# ── Scraper runner ────────────────────────────────────────────────────────────
def run_scraper_bg():
    scraper_status["running"] = True
    scraper_status["msg"] = "running"
    try:
        result = subprocess.run(["python", str(SCRAPER)],
                                capture_output=True, text=True, timeout=300)
        scraper_status["msg"] = "done" if result.returncode == 0 else "error"
    except Exception:
        scraper_status["msg"] = "error"
    finally:
        scraper_status["running"] = False

# ── HTML Template ─────────────────────────────────────────────────────────────
HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>FreshHire</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#070d1a;--surface:rgba(15,23,42,0.8);--border:rgba(255,255,255,0.07);
  --text:#e2e8f0;--muted:#64748b;--subtle:#475569;
  --teal:#00d4aa;--indigo:#6366f1;--amber:#f59e0b;--pink:#ec4899;
  --purple:#a5b4fc;
}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--text);font-family:'DM Sans',sans-serif;min-height:100vh;overflow-x:hidden}
body::before{
  content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:linear-gradient(rgba(0,212,170,.03) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(0,212,170,.03) 1px,transparent 1px);
  background-size:48px 48px;
}
.wrap{max-width:1200px;margin:0 auto;padding:0 20px;position:relative;z-index:1}

/* ── Header ── */
header{padding:40px 0 28px;display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:16px}
.brand{display:flex;align-items:center;gap:12px}
.logo{width:44px;height:44px;border-radius:12px;background:linear-gradient(135deg,var(--teal),var(--indigo));
  display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0}
.brand-text h1{
  font-family:'Space Mono',monospace;font-size:2rem;font-weight:700;letter-spacing:-.03em;
  background:linear-gradient(135deg,var(--teal) 0%,var(--indigo) 55%,var(--amber) 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;line-height:1
}
.brand-text p{color:var(--subtle);font-size:.82rem;margin-top:5px}
.brand-text p span{color:var(--teal);font-weight:600}
.header-btns{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.scrape-btn{
  display:flex;align-items:center;gap:7px;padding:10px 20px;
  border-radius:10px;font-size:.82rem;font-weight:700;
  background:var(--surface);border:1px solid var(--border);
  color:var(--teal);cursor:pointer;font-family:'DM Sans',sans-serif;
  transition:border-color .15s
}
.scrape-btn:hover{border-color:rgba(0,212,170,.4)}
.scrape-btn:disabled{opacity:.5;cursor:not-allowed}
.export-btn{
  display:flex;align-items:center;gap:7px;padding:10px 22px;border-radius:10px;
  background:linear-gradient(135deg,var(--teal),var(--indigo));
  color:#fff;font-size:.82rem;font-weight:700;border:none;cursor:pointer;
  text-decoration:none;box-shadow:0 4px 20px rgba(0,212,170,.25);transition:opacity .15s
}
.export-btn:hover{opacity:.85}

/* ── Banner ── */
.banner{padding:12px 18px;border-radius:10px;font-size:.82rem;margin-bottom:18px;
  border:1px solid rgba(0,212,170,.25);background:rgba(0,212,170,.07);
  display:flex;align-items:center;gap:10px}
.banner.error{border-color:rgba(239,68,68,.3);background:rgba(239,68,68,.07)}
.banner.hidden{display:none}

/* ── Stats ── */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:28px}
.stat{background:var(--surface);border:1px solid var(--border);border-radius:16px;
  padding:18px 20px;position:relative;overflow:hidden}
.stat-bg{position:absolute;top:-16px;right:4px;font-size:62px;opacity:.06;user-select:none;pointer-events:none}
.stat-num{font-family:'Space Mono',monospace;font-size:2.2rem;font-weight:700;line-height:1}
.stat-lbl{font-size:.68rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-top:6px;font-weight:600}

/* ── Controls ── */
.controls{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}
.search-box{
  flex:1;min-width:200px;background:var(--surface);
  border:1px solid var(--border);border-radius:10px;
  padding:10px 16px;color:var(--text);font-size:.88rem;outline:none;
  font-family:'DM Sans',sans-serif;transition:border-color .15s
}
.search-box:focus{border-color:rgba(0,212,170,.4)}
.search-box::placeholder{color:var(--muted)}
select.ctrl{
  background:var(--surface);border:1px solid var(--border);
  border-radius:10px;padding:10px 14px;color:var(--muted);
  font-size:.82rem;outline:none;font-family:'DM Sans',sans-serif;cursor:pointer
}
.toggle-wrap{display:flex;background:var(--surface);border:1px solid var(--border);border-radius:10px;overflow:hidden}
.toggle-btn{padding:10px 16px;border:none;cursor:pointer;font-size:.75rem;font-weight:700;
  background:transparent;transition:all .15s;color:var(--muted)}
.toggle-btn.active{background:rgba(0,212,170,.15);color:var(--teal)}

/* ── Filter pills ── */
.filters{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:20px;align-items:center}
.filter-label{font-size:.72rem;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.05em}
.pill{padding:4px 13px;border-radius:20px;font-size:.72rem;font-weight:700;
  cursor:pointer;border:1px solid var(--border);
  background:rgba(255,255,255,.04);color:var(--muted);transition:all .15s;
  letter-spacing:.04em;text-transform:uppercase}
.pill:hover{border-color:rgba(0,212,170,.4);color:var(--teal)}
.pill.active{background:rgba(0,212,170,.15);color:var(--teal);border-color:rgba(0,212,170,.4)}
.pill.active-amber{background:rgba(245,158,11,.15);color:var(--amber);border-color:rgba(245,158,11,.4)}
.pill.active-indigo{background:rgba(99,102,241,.15);color:var(--purple);border-color:rgba(99,102,241,.4)}
.pill.active-pink{background:rgba(236,72,153,.15);color:#f9a8d4;border-color:rgba(236,72,153,.4)}
.clear-pill{background:rgba(239,68,68,.1);color:#f87171;border-color:rgba(239,68,68,.35)}

/* ── Result count ── */
.result-count{font-size:.82rem;color:var(--muted);margin-bottom:16px}
.result-count span{color:var(--teal);font-weight:700}

/* ── Cards ── */
.cards-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px;padding-bottom:60px}
.job-card{
  background:var(--surface);border:1px solid var(--border);
  border-radius:14px;padding:20px 22px;
  transition:transform .15s,box-shadow .2s,border-color .2s;
  border-left-width:3px;border-left-style:solid
}
.job-card:hover{transform:translateY(-2px);box-shadow:0 8px 32px rgba(0,0,0,.35)}
.card-top{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
.job-title{font-size:.95rem;font-weight:700;color:#f1f5f9;line-height:1.3}
.job-company{font-size:.8rem;color:var(--muted);margin-top:4px;font-weight:500;display:flex;align-items:center;gap:5px;flex-wrap:wrap}
.src-dot{width:7px;height:7px;border-radius:50%;display:inline-block;flex-shrink:0}
.post-date{font-size:.7rem;color:var(--subtle);white-space:nowrap;padding-top:2px;flex-shrink:0}
.loc{font-size:.72rem;color:var(--subtle);margin-left:4px}
.badges{display:flex;flex-wrap:wrap;gap:5px;margin-top:11px}
.badge{display:inline-flex;align-items:center;padding:3px 10px;
  border-radius:20px;font-size:.67rem;font-weight:700;
  letter-spacing:.04em;text-transform:uppercase;border:1px solid transparent}
.b-intern{background:rgba(99,102,241,.15);color:#a5b4fc;border-color:rgba(99,102,241,.35)}
.b-full  {background:rgba(0,212,170,.12); color:#5eead4;border-color:rgba(0,212,170,.35)}
.b-part  {background:rgba(245,158,11,.12);color:#fcd34d;border-color:rgba(245,158,11,.35)}
.b-remote{background:rgba(245,158,11,.12);color:#fcd34d;border-color:rgba(245,158,11,.35)}
.b-onsite{background:rgba(236,72,153,.12);color:#f9a8d4;border-color:rgba(236,72,153,.35)}
.b-hybrid{background:rgba(139,92,246,.12);color:#c4b5fd;border-color:rgba(139,92,246,.35)}
.b-src   {background:rgba(255,255,255,.05);color:var(--muted);border-color:var(--border)}
.desc-wrap{margin-top:11px;border-top:1px solid var(--border);padding-top:10px}
.desc-toggle{background:none;border:none;color:var(--subtle);font-size:.72rem;
  cursor:pointer;padding:0;display:flex;align-items:center;gap:4px;font-family:'DM Sans',sans-serif}
.desc-toggle:hover{color:var(--teal)}
.desc-text{display:none;font-size:.78rem;color:var(--muted);line-height:1.6;margin-top:8px}
.desc-text.open{display:block}
.card-actions{display:flex;gap:8px;margin-top:14px}
.apply-btn{display:inline-flex;align-items:center;gap:5px;padding:7px 16px;
  border-radius:8px;font-size:.75rem;font-weight:700;
  text-decoration:none;transition:opacity .15s;color:#0f172a}
.apply-btn:hover{opacity:.85}
.email-btn{display:inline-flex;align-items:center;gap:5px;padding:7px 16px;
  border-radius:8px;font-size:.75rem;font-weight:700;
  background:rgba(255,255,255,.07);color:var(--muted);
  border:1px solid var(--border);text-decoration:none;transition:background .15s}
.email-btn:hover{background:rgba(255,255,255,.12)}

/* ── Table ── */
.table-wrap{overflow-x:auto;padding-bottom:60px}
table{width:100%;border-collapse:collapse;font-size:.8rem}
thead tr{border-bottom:1px solid rgba(255,255,255,.08)}
th{padding:10px 14px;color:var(--muted);text-align:left;font-size:.68rem;
   text-transform:uppercase;letter-spacing:.05em;font-weight:600}
td{padding:11px 14px;color:#94a3b8;border-bottom:1px solid rgba(255,255,255,.04)}
tr:nth-child(even) td{background:rgba(255,255,255,.015)}
tr:hover td{background:rgba(0,212,170,.04)}
td a{color:var(--teal);font-weight:600;text-decoration:none}
td a:hover{text-decoration:underline}

/* ── Empty ── */
.empty{text-align:center;padding:70px 0;color:var(--subtle)}
.empty .icon{font-size:3rem;margin-bottom:12px}

/* ── Footer ── */
footer{text-align:center;padding:20px 0 30px;font-size:.72rem;
  color:rgba(255,255,255,.08);border-top:1px solid var(--border);margin-top:10px}

@media(max-width:600px){
  .brand-text h1{font-size:1.5rem}
  .cards-grid{grid-template-columns:1fr}
  .controls{flex-direction:column}
  header{flex-direction:column;align-items:flex-start}
}
</style>
</head>
<body>
<div class="wrap">

<header>
  <div class="brand">
    <div class="logo">⚡</div>
    <div class="brand-text">
      <h1>FreshHire</h1>
      <p>Real-time fresher &amp; internship jobs — scraped from 4 platforms, <span>last 7 days only</span></p>
    </div>
  </div>
  <div class="header-btns">
    <button class="scrape-btn" id="scrapeBtn" onclick="startScrape()">🔄 Refresh Jobs</button>
    <a href="/export" class="export-btn">↓ Export CSV</a>
  </div>
</header>

<div class="banner hidden" id="banner"></div>
<div class="stats" id="statsGrid"></div>

<div class="controls">
  <input class="search-box" id="searchBox" placeholder="Search title, company, skill…" oninput="applyFilters()"/>
  <select class="ctrl" id="sortSelect" onchange="applyFilters()">
    <option value="date_desc">Sort: Newest</option>
    <option value="date_asc">Sort: Oldest</option>
    <option value="title">Sort: A–Z</option>
    <option value="company">Company A–Z</option>
  </select>
  <div class="toggle-wrap">
    <button class="toggle-btn active" id="btnCards" onclick="setView('cards')">⊞ Cards</button>
    <button class="toggle-btn" id="btnTable" onclick="setView('table')">☰ Table</button>
  </div>
</div>

<div class="filters" id="filterBar"></div>
<div class="result-count">Showing <span id="countSpan">0</span> jobs</div>
<div id="cardsView" class="cards-grid"></div>
<div id="tableView" class="table-wrap" style="display:none"></div>

</div>
<footer>FreshHire · Internshala 🇮🇳 · Unstop 🇮🇳 · RemoteOK 🌐 · Remotive 🌐 · Last 7 days only</footer>

<script>
const SRC_COLORS={"Internshala":"#00d4aa","Unstop":"#f59e0b","RemoteOK":"#6366f1","Remotive":"#ec4899"};
const MODE_ICONS={"Remote":"🌐","Onsite":"🏢","Hybrid":"⚡","Not Specified":"❓"};
let ALL_JOBS=[];
let activeFilters={types:[],modes:[],sources:[]};

async function loadJobs(){
  const r=await fetch('/api/jobs');
  ALL_JOBS=await r.json();
  buildFilterBar();
  applyFilters();
}

function renderStats(jobs){
  const s=[
    {val:jobs.length,lbl:"Total Jobs",color:"#00d4aa",icon:"📋"},
    {val:jobs.filter(j=>j["Job Type"]==="Internship").length,lbl:"Internships",color:"#a5b4fc",icon:"🎓"},
    {val:jobs.filter(j=>j["Work Mode"]==="Remote").length,lbl:"Remote Jobs",color:"#fcd34d",icon:"🌐"},
    {val:new Set(jobs.map(j=>j["Company Name"])).size,lbl:"Companies",color:"#f9a8d4",icon:"🏢"},
    {val:jobs.filter(j=>["Internshala","Unstop"].includes(j["Source"])).length,lbl:"Indian Jobs",color:"#fb923c",icon:"🇮🇳"},
  ];
  document.getElementById('statsGrid').innerHTML=s.map(c=>`
    <div class="stat"><div class="stat-bg">${c.icon}</div>
    <div class="stat-num" style="color:${c.color}">${c.val}</div>
    <div class="stat-lbl">${c.lbl}</div></div>`).join('');
}

function buildFilterBar(){
  const types  =[...new Set(ALL_JOBS.map(j=>j["Job Type"]).filter(Boolean))];
  const modes  =[...new Set(ALL_JOBS.map(j=>j["Work Mode"]).filter(Boolean))];
  const sources=[...new Set(ALL_JOBS.map(j=>j["Source"]).filter(Boolean))];
  let h='<span class="filter-label">Type:</span>';
  types.forEach(t=>h+=`<button class="pill" data-group="types" data-val="${t}" onclick="togglePill(this,'types')">${t}</button>`);
  h+='<span class="filter-label" style="margin-left:8px">Mode:</span>';
  modes.forEach(m=>h+=`<button class="pill" data-group="modes" data-val="${m}" onclick="togglePill(this,'modes')">${MODE_ICONS[m]||''} ${m}</button>`);
  h+='<span class="filter-label" style="margin-left:8px">Source:</span>';
  sources.forEach(s=>{const c=SRC_COLORS[s]||'#64748b';h+=`<button class="pill" data-group="sources" data-val="${s}" onclick="togglePill(this,'sources')">${s}</button>`;});
  h+=`<button class="pill clear-pill" id="clearBtn" style="display:none;margin-left:8px" onclick="clearFilters()">✕ Clear all</button>`;
  document.getElementById('filterBar').innerHTML=h;
}

function togglePill(btn,group){
  const val=btn.dataset.val,arr=activeFilters[group];
  if(arr.includes(val)){
    activeFilters[group]=arr.filter(x=>x!==val);
    btn.classList.remove('active','active-amber','active-indigo','active-pink');
  }else{
    arr.push(val);
    const cls=group==='sources'?({Internshala:'active',Unstop:'active-amber',RemoteOK:'active-indigo',Remotive:'active-pink'}[val]||'active'):'active';
    btn.classList.add(cls);
  }
  updateClearBtn();applyFilters();
}

function clearFilters(){
  activeFilters={types:[],modes:[],sources:[]};
  document.querySelectorAll('.pill').forEach(p=>p.classList.remove('active','active-amber','active-indigo','active-pink'));
  document.getElementById('searchBox').value='';
  updateClearBtn();applyFilters();
}

function updateClearBtn(){
  const has=activeFilters.types.length||activeFilters.modes.length||activeFilters.sources.length||document.getElementById('searchBox').value;
  document.getElementById('clearBtn').style.display=has?'inline-flex':'none';
}

function applyFilters(){
  const q=document.getElementById('searchBox').value.toLowerCase();
  const sort=document.getElementById('sortSelect').value;
  updateClearBtn();
  let jobs=ALL_JOBS.filter(j=>{
    if(activeFilters.types.length  &&!activeFilters.types.includes(j["Job Type"]))  return false;
    if(activeFilters.modes.length  &&!activeFilters.modes.includes(j["Work Mode"])) return false;
    if(activeFilters.sources.length&&!activeFilters.sources.includes(j["Source"]))  return false;
    if(q){const t=(j["Job Title"]+j["Company Name"]+j["Job Description"]+j["Location"]).toLowerCase();if(!t.includes(q))return false;}
    return true;
  });
  jobs.sort((a,b)=>{
    if(sort==='date_desc')return(b["Posted Date"]||'').localeCompare(a["Posted Date"]||'');
    if(sort==='date_asc') return(a["Posted Date"]||'').localeCompare(b["Posted Date"]||'');
    if(sort==='title')    return(a["Job Title"]||'').localeCompare(b["Job Title"]||'');
    if(sort==='company')  return(a["Company Name"]||'').localeCompare(b["Company Name"]||'');
    return 0;
  });
  document.getElementById('countSpan').textContent=jobs.length;
  renderStats(jobs);renderCards(jobs);renderTable(jobs);
}

function typeBadge(t){const c=t==='Internship'?'b-intern':t==='Full-time'?'b-full':'b-part';return`<span class="badge ${c}">${t}</span>`;}
function modeBadge(m){const c={'Remote':'b-remote','Onsite':'b-onsite','Hybrid':'b-hybrid'}[m]||'b-src';return`<span class="badge ${c}">${MODE_ICONS[m]||''} ${m}</span>`;}

function renderCards(jobs){
  const el=document.getElementById('cardsView');
  if(!jobs.length){el.innerHTML='<div class="empty" style="grid-column:1/-1"><div class="icon">🔍</div><p>No jobs match your filters.</p></div>';return;}
  el.innerHTML=jobs.map((j,i)=>{
    const src=j["Source"]||'',color=SRC_COLORS[src]||'#64748b';
    const link=j["Application Link"]||'',email=j["Email"]||'';
    const desc=(j["Job Description"]||'').slice(0,300);
    const applyBtn=link&&link!='nan'
      ?`<a href="${link}" target="_blank" class="apply-btn" style="background:${color}">Apply Now ↗</a>`
      :email&&email!='nan'
      ?`<a href="mailto:${email}" class="apply-btn" style="background:${color}">✉ Email</a>`:'';
    return`<div class="job-card" style="border-left-color:${color}">
      <div class="card-top">
        <div>
          <div class="job-title">${j["Job Title"]||''}</div>
          <div class="job-company">
            <span class="src-dot" style="background:${color}"></span>
            ${j["Company Name"]||'Unknown'}
            <span class="loc">📍 ${j["Location"]||'India'}</span>
          </div>
        </div>
        <span class="post-date">${j["Posted Date"]||''}</span>
      </div>
      <div class="badges">
        ${typeBadge(j["Job Type"]||'Not Specified')}
        ${modeBadge(j["Work Mode"]||'Not Specified')}
        <span class="badge b-src"><span class="src-dot" style="background:${color};margin-right:5px"></span>${src}</span>
      </div>
      ${desc?`<div class="desc-wrap">
        <button class="desc-toggle" onclick="toggleDesc(this)">▼ Show description</button>
        <div class="desc-text">${desc}${(j["Job Description"]||'').length>300?'…':''}</div>
      </div>`:''}
      <div class="card-actions">${applyBtn}</div>
    </div>`;
  }).join('');
}

function toggleDesc(btn){
  const box=btn.nextElementSibling,open=box.classList.toggle('open');
  btn.textContent=(open?'▲ Hide':'▼ Show')+' description';
}

function renderTable(jobs){
  const el=document.getElementById('tableView');
  if(!jobs.length){el.innerHTML='<div class="empty"><div class="icon">🔍</div><p>No jobs match your filters.</p></div>';return;}
  const rows=jobs.map(j=>{
    const color=SRC_COLORS[j["Source"]]||'#64748b';
    const link=j["Application Link"]||'';
    const cell=link&&link!='nan'?`<a href="${link}" target="_blank">Apply ↗</a>`:'—';
    return`<tr>
      <td style="color:#f1f5f9;font-weight:600">${j["Job Title"]||''}</td>
      <td>${j["Company Name"]||''}</td>
      <td>${typeBadge(j["Job Type"]||'')}</td>
      <td>${modeBadge(j["Work Mode"]||'')}</td>
      <td>${j["Location"]||''}</td>
      <td><span style="color:${color};font-weight:700">${j["Source"]||''}</span></td>
      <td>${j["Posted Date"]||''}</td>
      <td>${cell}</td>
    </tr>`;
  }).join('');
  el.innerHTML=`<table><thead><tr>${["Title","Company","Type","Mode","Location","Source","Posted","Action"].map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table>`;
}

function setView(v){
  document.getElementById('cardsView').style.display=v==='cards'?'grid':'none';
  document.getElementById('tableView').style.display=v==='table'?'block':'none';
  document.getElementById('btnCards').classList.toggle('active',v==='cards');
  document.getElementById('btnTable').classList.toggle('active',v==='table');
}

async function startScrape(){
  const btn=document.getElementById('scrapeBtn');
  btn.disabled=true;btn.textContent='⏳ Scraping…';
  showBanner('⏳ Scraping in progress… takes 2-3 minutes. Page will auto-refresh.','');
  await fetch('/api/scrape',{method:'POST'});
  pollScraper();
}

function pollScraper(){
  const iv=setInterval(async()=>{
    const r=await fetch('/api/scrape-status'),d=await r.json();
    if(!d.running){
      clearInterval(iv);
      const btn=document.getElementById('scrapeBtn');
      btn.disabled=false;btn.textContent='🔄 Refresh Jobs';
      if(d.msg==='done'){showBanner('✅ Scraping complete!','');await loadJobs();}
      else showBanner('⚠️ Scraper finished with warnings.','error');
    }
  },4000);
}

function showBanner(msg,cls){
  const b=document.getElementById('banner');
  b.textContent=msg;b.className='banner '+(cls||'');
  if(cls!=='error')setTimeout(()=>b.classList.add('hidden'),7000);
}

loadJobs();
</script>
</body>
</html>
"""

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/jobs")
def api_jobs():
    return jsonify(load_jobs())

@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    if not scraper_status["running"]:
        t = threading.Thread(target=run_scraper_bg, daemon=True)
        t.start()
    return jsonify({"started": True})

@app.route("/api/scrape-status")
def api_scrape_status():
    return jsonify(scraper_status)

@app.route("/export")
def export_csv():
    jobs = load_jobs()
    if not jobs:
        return "No data found", 404
    df = pd.DataFrame(jobs)
    csv_str = df.to_csv(index=False, encoding="utf-8-sig")
    return Response(
        csv_str,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=freshjobs_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

if __name__ == "__main__":
    print("\n⚡ FreshHire running at → http://localhost:8501\n")
    app.run(host="0.0.0.0", port=8501, debug=False, use_reloader=False, threaded=True)