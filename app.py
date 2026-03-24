"""
OAK BUILDERS LLC - Bid Finder v2
Flask Web Dashboard + API

Changes from v1:
- Pipeline funnel view (discovered -> qualified -> estimating -> submitted)
- Commercial vs. government split view
- Source performance analytics tab
- Win probability shown alongside relevance score
- "Don't Miss" badge for score >= 80
- Pre-bid meeting alerts
- Bonding indicator on cards
- Better mobile layout
- Conversion funnel stats
"""

import json
import os
import threading
import time
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, jsonify, session, redirect, url_for

from config import DATABASE_FILE, EMAIL, SOURCES
from models import BidDatabase

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

# ─── Auth ──────────────────────────────────────────────────────────
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
API_TRIGGER_KEY = os.environ.get("API_TRIGGER_KEY", "")

SCAN_STATE_FILE = "/tmp/bid_scan_state.json"


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if APP_PASSWORD and not session.get("authenticated"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def api_key_or_session(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key", "")
        if API_TRIGGER_KEY and api_key == API_TRIGGER_KEY:
            return f(*args, **kwargs)
        if APP_PASSWORD and not session.get("authenticated"):
            return jsonify({"error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


# ─── Scan state (disk-based for gunicorn workers) ──────────────────
def get_scan_state():
    try:
        with open(SCAN_STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"running": False}


def set_scan_state(state):
    tmp = SCAN_STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, SCAN_STATE_FILE)


# ─── Routes ────────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == APP_PASSWORD:
            session["authenticated"] = True
            return redirect("/")
        return '<form method="post"><p style="color:red">Wrong password</p><input name="password" type="password" placeholder="Password"><button>Login</button></form>'
    return '<form method="post"><input name="password" type="password" placeholder="Password" autofocus><button>Login</button></form>'


@app.route("/")
@login_required
def dashboard():
    return DASHBOARD_HTML


@app.route("/api/stats")
@login_required
def api_stats():
    db = BidDatabase(DATABASE_FILE)
    stats = db.get_stats()
    funnel = db.get_conversion_funnel()
    stats["funnel"] = funnel
    return jsonify(stats)


@app.route("/api/bids")
@login_required
def api_bids():
    db = BidDatabase(DATABASE_FILE)

    category = request.args.get("category", "")
    status = request.args.get("status", "")
    pipeline = request.args.get("pipeline", "")
    min_score = int(request.args.get("min_score", 0))
    min_win = int(request.args.get("min_win", 0))
    keyword = request.args.get("q", "")
    source = request.args.get("source", "")
    show_expired = request.args.get("show_expired", "0") == "1"
    limit = min(int(request.args.get("limit", 100)), 500)

    bids = db.search(
        project_type=category or None,
        status=status or None,
        pipeline_stage=pipeline or None,
        min_score=min_score,
        min_win_prob=min_win,
        keyword=keyword or None,
        source=source or None,
        show_expired=show_expired,
        limit=limit,
    )

    return jsonify(bids)


@app.route("/api/run", methods=["POST"])
@api_key_or_session
def api_run():
    state = get_scan_state()
    if state.get("running"):
        return jsonify({"status": "already_running", "progress": state})

    def run_bg():
        set_scan_state({"running": True, "started": datetime.now().isoformat(), "current_source": "starting..."})
        try:
            from main import run_scrapers

            def progress_cb(idx, total, source_name):
                set_scan_state({
                    "running": True,
                    "current_source": source_name,
                    "progress": idx,
                    "total": total,
                    "pct": int(idx / total * 100) if total else 0,
                })

            result = run_scrapers(progress_callback=progress_cb)
            set_scan_state({
                "running": False,
                "completed": datetime.now().isoformat(),
                "result": {
                    "total": result["total"],
                    "new": result["new"],
                    "errors": len(result["errors"]),
                },
            })
        except Exception as e:
            set_scan_state({"running": False, "error": str(e)})

    thread = threading.Thread(target=run_bg, daemon=True)
    thread.start()
    return jsonify({"status": "started"})


@app.route("/api/scan-status")
@login_required
def api_scan_status():
    return jsonify(get_scan_state())


@app.route("/api/status", methods=["POST"])
@login_required
def api_update_status():
    data = request.json
    key = data.get("key")
    new_status = data.get("status")
    new_stage = data.get("pipeline_stage")

    if not key:
        return jsonify({"error": "missing key"}), 400

    db = BidDatabase(DATABASE_FILE)
    import sqlite3
    with sqlite3.connect(DATABASE_FILE) as conn:
        if new_status:
            conn.execute("UPDATE opportunities SET status=?, updated_at=datetime('now') WHERE dedup_key=?", (new_status, key))
        if new_stage:
            db.update_pipeline_stage(key, new_stage, changed_by="dashboard")

    return jsonify({"ok": True})


@app.route("/api/export")
@login_required
def api_export():
    db = BidDatabase(DATABASE_FILE)
    bids = db.search(show_expired=False, limit=1000)

    import csv
    import io
    output = io.StringIO()
    if bids:
        writer = csv.DictWriter(output, fieldnames=bids[0].keys())
        writer.writeheader()
        writer.writerows(bids)

    from flask import Response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=bids_{datetime.now():%Y%m%d}.csv"},
    )


@app.route("/api/email", methods=["POST"])
@api_key_or_session
def api_email():
    try:
        from email_sender import EmailSender
        sender = EmailSender()
        sender.send_digest()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/clear", methods=["POST"])
@login_required
def api_clear():
    db = BidDatabase(DATABASE_FILE)
    import sqlite3
    with sqlite3.connect(DATABASE_FILE) as conn:
        conn.execute("DELETE FROM opportunities")
    return jsonify({"ok": True})


# ─── Dashboard HTML ────────────────────────────────────────────────
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OAK Builders — Bid Finder</title>
<link rel="manifest" href="/manifest.json">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f2f5;color:#1a1a1a}
.top-bar{background:linear-gradient(135deg,#1a472a,#2d6a4f);color:#fff;padding:16px 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100}
.top-bar h1{font-size:20px;font-weight:700}
.top-bar .actions button{background:rgba(255,255,255,.2);color:#fff;border:none;padding:8px 14px;border-radius:6px;cursor:pointer;font-size:13px;margin-left:8px}
.top-bar .actions button:hover{background:rgba(255,255,255,.3)}
.stats-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;padding:16px 24px}
.stat-card{background:#fff;border-radius:10px;padding:16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.stat-card .num{font-size:28px;font-weight:800;color:#1a472a}
.stat-card .label{font-size:12px;color:#666;margin-top:4px}
.filters{padding:8px 24px;display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.filters select,.filters input{padding:7px 12px;border:1px solid #d0d0d0;border-radius:6px;font-size:13px;background:#fff}
.filters input[type=search]{min-width:200px}
.scan-banner{background:#fff3cd;padding:10px 24px;font-size:13px;display:none;align-items:center;gap:10px}
.scan-banner.active{display:flex}
.scan-progress{height:4px;background:#e0e0e0;border-radius:2px;flex:1;overflow:hidden}
.scan-progress-bar{height:100%;background:#2d6a4f;transition:width .3s}
.bids-container{padding:12px 24px}
.bid-card{background:#fff;border-radius:10px;padding:16px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.06);border-left:4px solid #ccc;display:grid;grid-template-columns:1fr auto;gap:12px}
.bid-card.score-high{border-left-color:#28a745}
.bid-card.score-mid{border-left-color:#ffc107}
.bid-card.score-low{border-left-color:#dc3545}
.bid-card.dont-miss{border-left-color:#ff6b35;background:#fffaf7}
.bid-title{font-weight:700;font-size:14px}
.bid-title a{color:#1a472a;text-decoration:none}
.bid-title a:hover{text-decoration:underline}
.bid-meta{font-size:12px;color:#555;line-height:1.8;margin-top:6px}
.bid-actions{display:flex;flex-direction:column;gap:6px;align-items:flex-end}
.badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600}
.badge-green{background:#d4edda;color:#155724}.badge-yellow{background:#fff3cd;color:#856404}
.badge-red{background:#f8d7da;color:#721c24}.badge-fire{background:#ff6b35;color:#fff}
.badge-blue{background:#cce5ff;color:#004085}.badge-purple{background:#e8d5f5;color:#4a148c}
.bid-actions select{font-size:11px;padding:4px 8px;border:1px solid #d0d0d0;border-radius:4px}
.empty-state{text-align:center;padding:60px 24px;color:#888;font-size:15px}
.footer{text-align:center;padding:20px;font-size:11px;color:#aaa}
@media(max-width:600px){.stats-row{grid-template-columns:repeat(2,1fr)}.bid-card{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="top-bar">
  <h1>OAK Builders — Bid Finder</h1>
  <div class="actions">
    <button onclick="startScan()">Scan Now</button>
    <button onclick="exportCSV()">Export CSV</button>
    <button onclick="sendEmail()">Email Digest</button>
  </div>
</div>

<div class="scan-banner" id="scanBanner">
  <span id="scanText">Scanning...</span>
  <div class="scan-progress"><div class="scan-progress-bar" id="scanBar" style="width:0%"></div></div>
</div>

<div class="stats-row" id="statsRow"></div>

<div class="filters">
  <select id="filterCategory" onchange="loadBids()">
    <option value="">All Types</option>
    <option value="waterproofing">Waterproofing</option>
    <option value="tenant_improvements">Tenant Improvements</option>
    <option value="general_contracting">General Contracting</option>
    <option value="commercial_private">Commercial/Private</option>
    <option value="civil_infrastructure">Civil/Infrastructure</option>
  </select>
  <select id="filterPipeline" onchange="loadBids()">
    <option value="">All Stages</option>
    <option value="discovered">Discovered</option>
    <option value="qualified">Qualified</option>
    <option value="estimating">Estimating</option>
    <option value="submitted">Submitted</option>
    <option value="awarded">Awarded</option>
  </select>
  <select id="filterStatus" onchange="loadBids()">
    <option value="">All Status</option>
    <option value="new">New</option>
    <option value="reviewed">Reviewed</option>
    <option value="bid">Bid</option>
    <option value="no_bid">No Bid</option>
  </select>
  <select id="filterScore" onchange="loadBids()">
    <option value="0">Any Score</option>
    <option value="50">50+</option>
    <option value="70" selected>70+</option>
    <option value="80">80+ (Don't Miss)</option>
  </select>
  <input type="search" id="filterKeyword" placeholder="Search keywords..." onkeyup="debounceSearch()">
</div>

<div class="bids-container" id="bidsContainer">
  <div class="empty-state">Loading opportunities...</div>
</div>

<div class="footer">OAK Builders Bid Finder v2</div>

<script>
let searchTimer;
function debounceSearch(){clearTimeout(searchTimer);searchTimer=setTimeout(loadBids,400)}

async function loadStats(){
  try{
    const r=await fetch('/api/stats');const s=await r.json();
    document.getElementById('statsRow').innerHTML=`
      <div class="stat-card"><div class="num">${s.active||0}</div><div class="label">Active</div></div>
      <div class="stat-card"><div class="num">${s.new_today||0}</div><div class="label">New Today</div></div>
      <div class="stat-card"><div class="num">${s.high_relevance||0}</div><div class="label">Score 70+</div></div>
      <div class="stat-card"><div class="num">${s.due_this_week||0}</div><div class="label">Due This Week</div></div>
      <div class="stat-card"><div class="num">${(s.pipeline||{}).qualified||0}</div><div class="label">Qualified</div></div>
      <div class="stat-card"><div class="num">${(s.pipeline||{}).estimating||0}</div><div class="label">Estimating</div></div>
    `;
  }catch(e){console.error(e)}
}

async function loadBids(){
  try{
    const p=new URLSearchParams();
    const cat=document.getElementById('filterCategory').value;
    const pipe=document.getElementById('filterPipeline').value;
    const st=document.getElementById('filterStatus').value;
    const sc=document.getElementById('filterScore').value;
    const q=document.getElementById('filterKeyword').value;
    if(cat)p.set('category',cat);
    if(pipe)p.set('pipeline',pipe);
    if(st)p.set('status',st);
    if(sc)p.set('min_score',sc);
    if(q)p.set('q',q);
    const r=await fetch('/api/bids?'+p.toString());
    const bids=await r.json();
    renderBids(bids);
  }catch(e){console.error(e)}
}

function renderBids(bids){
  const c=document.getElementById('bidsContainer');
  if(!bids.length){c.innerHTML='<div class="empty-state">No opportunities match your filters</div>';return}
  c.innerHTML=bids.map(b=>{
    const score=b.relevance_score||0;
    const win=b.win_probability||0;
    let cls='score-low';
    if(score>=80)cls='dont-miss';
    else if(score>=70)cls='score-high';
    else if(score>=50)cls='score-mid';

    let scoreBadge=`<span class="badge badge-red">${score}</span>`;
    if(score>=80)scoreBadge=`<span class="badge badge-fire">🔥 ${score}</span>`;
    else if(score>=70)scoreBadge=`<span class="badge badge-green">${score}</span>`;
    else if(score>=50)scoreBadge=`<span class="badge badge-yellow">${score}</span>`;

    const winBadge=win?` <span class="badge badge-purple">Win: ${win}%</span>`:'';
    const loc=[b.location_city,b.location_state].filter(Boolean).join(', ')||'TBD';
    const due=b.due_date||'TBD';
    const bond=b.bonding_required?'💰 Bond Required • ':'';
    const prebid=b.pre_bid_date?`<br>📅 Pre-bid: ${b.pre_bid_date}${b.pre_bid_mandatory?' <strong>(MANDATORY)</strong>':''}` :'';
    const source=b.source||'?';
    const agency=b.agency||'Unknown';
    const url=b.source_url||'#';
    const title=b.title||'Untitled';
    const key=b.dedup_key||'';
    const curStatus=b.status||'new';
    const curPipeline=b.pipeline_stage||'discovered';

    return `<div class="bid-card ${cls}">
      <div>
        <div class="bid-title"><a href="${url}" target="_blank">${title}</a></div>
        <div class="bid-meta">
          ${scoreBadge}${winBadge} <span class="badge badge-blue">${source}</span><br>
          📍 ${loc} • 📅 Due: ${due} • 🏢 ${agency}<br>
          ${bond}${b.scope_category?'Scope: '+b.scope_category+' • ':''}${b.budget_display||''}${prebid}
        </div>
      </div>
      <div class="bid-actions">
        <select onchange="updateStatus('${key}','status',this.value)">
          ${['new','reviewed','bid','no_bid','awarded','lost'].map(s=>`<option value="${s}"${s===curStatus?' selected':''}>${s}</option>`).join('')}
        </select>
        <select onchange="updateStatus('${key}','pipeline_stage',this.value)">
          ${['discovered','qualified','estimating','submitted','awarded','lost'].map(s=>`<option value="${s}"${s===curPipeline?' selected':''}>${s}</option>`).join('')}
        </select>
      </div>
    </div>`;
  }).join('');
}

async function updateStatus(key,field,val){
  const body={key};body[field]=val;
  await fetch('/api/status',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  loadStats();
}

async function startScan(){
  const r=await fetch('/api/run',{method:'POST'});
  if(r.ok)pollScan();
}

function pollScan(){
  const banner=document.getElementById('scanBanner');
  banner.classList.add('active');
  const interval=setInterval(async()=>{
    const r=await fetch('/api/scan-status');
    const s=await r.json();
    if(s.running){
      document.getElementById('scanText').textContent=`Scanning: ${s.current_source||'...'}`;
      document.getElementById('scanBar').style.width=(s.pct||0)+'%';
    }else{
      clearInterval(interval);
      banner.classList.remove('active');
      loadStats();loadBids();
    }
  },1500);
}

async function exportCSV(){window.location='/api/export'}
async function sendEmail(){
  const r=await fetch('/api/email',{method:'POST'});
  const d=await r.json();
  alert(d.ok?'Email sent!':'Error: '+(d.error||'unknown'));
}

// Initial load
loadStats();loadBids();
// Check if scan is running
fetch('/api/scan-status').then(r=>r.json()).then(s=>{if(s.running)pollScan()});
</script>
</body>
</html>"""


# ─── PWA manifest ──────────────────────────────────────────────────
@app.route("/manifest.json")
def manifest():
    return jsonify({
        "name": "OAK Bid Finder",
        "short_name": "BidFinder",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#1a472a",
        "theme_color": "#1a472a",
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
