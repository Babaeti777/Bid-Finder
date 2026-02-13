"""
OAK BUILDERS LLC - Bid Finder
Web Dashboard & Desktop App (PWA)

Local:  python app.py           -> http://localhost:8080
Cloud:  Deployed via Render.com -> accessible from any device
Install: Click "Install App" in the browser to add to your home screen
"""

import json
import os
import threading
import time
import functools
from datetime import datetime
from pathlib import Path

from flask import (
    Flask, render_template_string, request, redirect,
    url_for, flash, jsonify, Response, session,
)

from config import SOURCES, OUTPUT
from models import BidDatabase

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))

DB_PATH = OUTPUT["database"]
SETTINGS_FILE = Path(__file__).parent / "settings.json"

# ============================================================
# AUTHENTICATION (password-protect when hosted publicly)
# ============================================================
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
API_TRIGGER_KEY = os.environ.get("API_TRIGGER_KEY", "")


def login_required(f):
    """Decorator: redirect to login page if not authenticated."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if APP_PASSWORD and not session.get("authenticated"):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


@app.route("/login", methods=["GET", "POST"])
def login():
    if not APP_PASSWORD:
        return redirect("/")
    error = ""
    if request.method == "POST":
        if request.form.get("password") == APP_PASSWORD:
            session["authenticated"] = True
            session.permanent = True
            next_url = request.args.get("next", "/")
            return redirect(next_url)
        error = "Wrong password"
    return render_template_string(LOGIN_HTML, error=error)


@app.route("/logout")
def logout():
    session.pop("authenticated", None)
    return redirect("/login")

# Global state for background scraper
_scraper_state = {
    "running": False,
    "progress": [],
    "summary": None,
    "error": None,
}

DEFAULT_SETTINGS = {
    "gmail_address": "",
    "gmail_app_password": "",
    "email_recipients": [],
    "google_sheets_enabled": False,
    "google_sheet_name": "OAK Builders - Bid Tracker",
    "sam_gov_api_key": "",
    "paid_sources": {
        "dodge_construction": {"enabled": False, "username": "", "password": ""},
        "building_connected": {"enabled": False, "username": "", "password": ""},
        "construct_connect": {"enabled": False, "username": "", "password": ""},
        "isqft": {"enabled": False, "username": "", "password": ""},
        "planhub": {"enabled": False, "username": "", "password": ""},
        "bidclerk": {"enabled": False, "username": "", "password": ""},
    },
}


def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE) as f:
            saved = json.load(f)
        merged = {**DEFAULT_SETTINGS, **saved}
        for key, default in DEFAULT_SETTINGS["paid_sources"].items():
            if key not in merged.get("paid_sources", {}):
                merged.setdefault("paid_sources", {})[key] = default
        return merged
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


def _get_db():
    return BidDatabase(DB_PATH)


def _run_scraper_background():
    """Run scrapers in a background thread."""
    global _scraper_state
    _scraper_state["running"] = True
    _scraper_state["progress"] = []
    _scraper_state["summary"] = None
    _scraper_state["error"] = None

    try:
        from main import run_scrapers
        db = _get_db()
        try:
            _scraper_state["progress"].append("Starting bid scan...")
            summary = run_scrapers(db=db)
            _scraper_state["summary"] = summary
            _scraper_state["progress"].append(
                f"Complete! Found {summary['total_found']} bids "
                f"({summary['new_opportunities']} new)"
            )
        finally:
            db.close()
    except Exception as e:
        _scraper_state["error"] = str(e)
        _scraper_state["progress"].append(f"Error: {e}")
    finally:
        _scraper_state["running"] = False


# ============================================================
# PAGE ROUTES
# ============================================================

@app.route("/")
@login_required
def dashboard():
    return render_template_string(DASHBOARD_HTML)


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        s = load_settings()
        s["gmail_address"] = request.form.get("gmail_address", "").strip()
        s["gmail_app_password"] = request.form.get("gmail_app_password", "").strip()
        s["email_recipients"] = [
            e.strip() for e in request.form.get("email_recipients", "").split(",")
            if e.strip()
        ]
        s["google_sheets_enabled"] = "google_sheets_enabled" in request.form
        s["google_sheet_name"] = request.form.get("google_sheet_name", "").strip()
        s["sam_gov_api_key"] = request.form.get("sam_gov_api_key", "").strip()
        for key in s["paid_sources"]:
            s["paid_sources"][key] = {
                "enabled": f"paid_{key}_enabled" in request.form,
                "username": request.form.get(f"paid_{key}_username", "").strip(),
                "password": request.form.get(f"paid_{key}_password", "").strip(),
            }
        save_settings(s)
        flash("Settings saved successfully!")
        return redirect(url_for("settings"))

    s = load_settings()
    return render_template_string(SETTINGS_HTML, s=s, sources=SOURCES)


# ============================================================
# API ROUTES
# ============================================================

@app.route("/api/stats")
@login_required
def api_stats():
    db = _get_db()
    try:
        stats = db.get_stats()
        last_run = db.conn.execute(
            "SELECT run_date, duration_seconds FROM search_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        stats["last_run"] = dict(last_run) if last_run else None
        return jsonify(stats)
    finally:
        db.close()


@app.route("/api/bids")
@login_required
def api_bids():
    db = _get_db()
    try:
        bids = db.search(
            project_type=request.args.get("type") or None,
            source=request.args.get("source") or None,
            status=request.args.get("status") or None,
            min_score=int(request.args.get("min_score", 0)),
            keyword=request.args.get("q") or None,
            limit=int(request.args.get("limit", 100)),
            offset=int(request.args.get("offset", 0)),
        )
        results = []
        for b in bids:
            location = ", ".join(filter(None, [b.location_city, b.location_county, b.location_state]))
            if b.budget_display:
                value = b.budget_display
            elif b.estimated_value_min:
                value = f"${b.estimated_value_min:,.0f} - ${b.estimated_value_max:,.0f}"
            else:
                value = ""
            results.append({
                "id": getattr(b, "id", 0),
                "title": b.title,
                "source": b.source,
                "source_url": b.source_url,
                "project_type": b.project_type or "other",
                "location": location,
                "value": value,
                "due_date": b.due_date or "",
                "score": b.relevance_score,
                "status": b.status,
                "agency": b.agency_name,
                "set_aside": b.set_aside or "",
                "contact_name": b.contact_name,
                "contact_email": b.contact_email,
                "description": (b.description or "")[:200],
            })
        return jsonify(results)
    finally:
        db.close()


@app.route("/api/run", methods=["POST"])
def api_run():
    # Allow access via API trigger key (for GitHub Actions) or login session
    trigger_key = request.args.get("key") or request.headers.get("X-API-Key")
    is_api_auth = API_TRIGGER_KEY and trigger_key == API_TRIGGER_KEY
    is_session_auth = not APP_PASSWORD or session.get("authenticated")

    if not is_api_auth and not is_session_auth:
        return jsonify({"error": "unauthorized"}), 401

    if _scraper_state["running"]:
        return jsonify({"status": "already_running"}), 409
    t = threading.Thread(target=_run_scraper_background, daemon=True)
    t.start()
    return jsonify({"status": "started"})


@app.route("/api/run/status")
@login_required
def api_run_status():
    return jsonify({
        "running": _scraper_state["running"],
        "progress": _scraper_state["progress"],
        "summary": _scraper_state["summary"],
        "error": _scraper_state["error"],
    })


@app.route("/api/status", methods=["POST"])
@login_required
def api_update_status():
    data = request.get_json()
    opp_id = data.get("id")
    new_status = data.get("status")
    if not opp_id or not new_status:
        return jsonify({"error": "Missing id or status"}), 400
    db = _get_db()
    try:
        db.update_status(int(opp_id), new_status)
        return jsonify({"ok": True})
    finally:
        db.close()


# ============================================================
# PWA ROUTES
# ============================================================

@app.route("/manifest.json")
def manifest():
    m = {
        "name": "OAK Builders Bid Finder",
        "short_name": "Bid Finder",
        "description": "Find and track commercial construction bid opportunities",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#f5f5f5",
        "theme_color": "#1a472a",
        "icons": [
            {"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml"},
        ],
    }
    return Response(json.dumps(m), mimetype="application/manifest+json")


@app.route("/sw.js")
def service_worker():
    sw = """
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', e => e.respondWith(fetch(e.request).catch(() => caches.match(e.request))));
"""
    return Response(sw.strip(), mimetype="application/javascript")


@app.route("/icon.svg")
def icon():
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
<rect width="100" height="100" rx="18" fill="#1a472a"/>
<text x="50" y="38" text-anchor="middle" font-family="Arial" font-weight="bold" font-size="20" fill="white">OAK</text>
<text x="50" y="56" text-anchor="middle" font-family="Arial" font-size="12" fill="#8fbc8f">BUILDERS</text>
<text x="50" y="78" text-anchor="middle" font-family="Arial" font-weight="bold" font-size="14" fill="#ffc107">BID FINDER</text>
</svg>"""
    return Response(svg.strip(), mimetype="image/svg+xml")


# ============================================================
# LOGIN HTML
# ============================================================

LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#1a472a">
<title>Login - OAK Builders Bid Finder</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,sans-serif;background:#f0f2f5;display:flex;align-items:center;justify-content:center;min-height:100vh}
.login-box{background:#fff;border-radius:12px;padding:40px;box-shadow:0 4px 24px rgba(0,0,0,.1);width:100%;max-width:380px;text-align:center}
.login-box img{width:64px;height:64px;border-radius:12px;margin-bottom:16px}
.login-box h1{color:#1a472a;font-size:22px;margin-bottom:4px}
.login-box p{color:#888;font-size:14px;margin-bottom:24px}
.login-box input[type=password]{width:100%;padding:12px;border:2px solid #ddd;border-radius:8px;font-size:16px;margin-bottom:16px;text-align:center;transition:.2s}
.login-box input[type=password]:focus{border-color:#1a472a;outline:none}
.login-box button{width:100%;padding:12px;background:#1a472a;color:#fff;border:none;border-radius:8px;font-size:16px;font-weight:600;cursor:pointer;transition:.15s}
.login-box button:hover{background:#245a36}
.error{color:#dc3545;font-size:14px;margin-bottom:12px}
</style>
</head>
<body>
<div class="login-box">
  <img src="/icon.svg" alt="">
  <h1>OAK Builders</h1>
  <p>Bid Finder Dashboard</p>
  {% if error %}<div class="error">{{ error }}</div>{% endif %}
  <form method="POST">
    <input type="password" name="password" placeholder="Enter password" autofocus>
    <button type="submit">Sign In</button>
  </form>
</div>
</body>
</html>"""


# ============================================================
# DASHBOARD HTML
# ============================================================

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#1a472a">
<link rel="manifest" href="/manifest.json">
<title>OAK Builders - Bid Finder</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,sans-serif;background:#f0f2f5;color:#333;min-height:100vh}

/* NAV */
.navbar{background:#1a472a;color:#fff;padding:0 24px;display:flex;align-items:center;height:56px;position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(0,0,0,.15)}
.navbar .logo{font-weight:700;font-size:18px;margin-right:auto;display:flex;align-items:center;gap:10px}
.navbar .logo img{width:28px;height:28px;border-radius:4px}
.navbar a{color:rgba(255,255,255,.85);text-decoration:none;padding:8px 16px;border-radius:6px;font-size:14px;font-weight:500;transition:.15s}
.navbar a:hover,.navbar a.active{background:rgba(255,255,255,.15);color:#fff}

/* MAIN */
.main{max-width:1200px;margin:0 auto;padding:20px}

/* STAT CARDS */
.stats-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:24px}
.stat-card{background:#fff;border-radius:10px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.06);text-align:center;border-top:3px solid #1a472a}
.stat-card.warn{border-top-color:#ffc107}
.stat-card.hot{border-top-color:#dc3545}
.stat-card .num{font-size:32px;font-weight:700;color:#1a472a}
.stat-card .label{font-size:13px;color:#888;margin-top:4px}

/* RUN BUTTON */
.run-section{display:flex;align-items:center;gap:16px;margin-bottom:24px;flex-wrap:wrap}
.btn-run{background:linear-gradient(135deg,#1a472a,#245a36);color:#fff;border:none;padding:14px 32px;border-radius:10px;font-size:16px;font-weight:600;cursor:pointer;display:flex;align-items:center;gap:10px;box-shadow:0 3px 12px rgba(26,71,42,.3);transition:.2s}
.btn-run:hover{transform:translateY(-1px);box-shadow:0 5px 16px rgba(26,71,42,.4)}
.btn-run:disabled{opacity:.6;cursor:not-allowed;transform:none}
.btn-run .spinner{display:none;width:18px;height:18px;border:3px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .7s linear infinite}
.btn-run.running .spinner{display:inline-block}
.btn-run.running .icon{display:none}
@keyframes spin{to{transform:rotate(360deg)}}
.run-status{font-size:14px;color:#666;max-width:500px}
.run-status.error{color:#dc3545}

/* TOOLBAR */
.toolbar{background:#fff;border-radius:10px;padding:16px;margin-bottom:20px;box-shadow:0 1px 4px rgba(0,0,0,.06);display:flex;gap:12px;flex-wrap:wrap;align-items:center}
.toolbar select,.toolbar input{padding:8px 12px;border:1px solid #ddd;border-radius:6px;font-size:14px;background:#fff}
.toolbar input[type=text]{min-width:200px;flex:1}
.toolbar .filter-label{font-size:12px;color:#888;font-weight:600;text-transform:uppercase}

/* CATEGORY SECTIONS */
.cat-section{margin-bottom:28px}
.cat-header{display:flex;align-items:center;gap:10px;margin-bottom:12px;padding-bottom:8px;border-bottom:2px solid #e0e0e0}
.cat-header h2{font-size:18px;color:#1a472a}
.cat-header .count{background:#1a472a;color:#fff;padding:2px 10px;border-radius:12px;font-size:13px;font-weight:600}

/* BID CARDS */
.bid-card{background:#fff;border-radius:8px;padding:16px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.05);border-left:4px solid #ccc;display:grid;grid-template-columns:1fr auto;gap:12px;transition:.15s}
.bid-card:hover{box-shadow:0 3px 12px rgba(0,0,0,.1);transform:translateY(-1px)}
.bid-card.score-high{border-left-color:#28a745}
.bid-card.score-mid{border-left-color:#ffc107}
.bid-card.score-low{border-left-color:#dc3545}
.bid-title{font-weight:600;font-size:15px;margin-bottom:6px}
.bid-title a{color:#1a472a;text-decoration:none}
.bid-title a:hover{text-decoration:underline}
.bid-meta{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:#666}
.bid-meta span{display:flex;align-items:center;gap:4px}
.bid-right{display:flex;flex-direction:column;align-items:flex-end;gap:8px;min-width:100px}
.score-badge{padding:4px 14px;border-radius:14px;font-weight:700;font-size:15px;color:#fff}
.score-badge.high{background:#28a745}
.score-badge.mid{background:#ffc107;color:#333}
.score-badge.low{background:#dc3545}
.status-select{padding:4px 8px;border:1px solid #ddd;border-radius:4px;font-size:12px;background:#f8f9fa;cursor:pointer}

/* EMPTY STATE */
.empty{text-align:center;padding:60px 20px;color:#999}
.empty .big{font-size:48px;margin-bottom:12px}
.empty p{font-size:16px}

/* INSTALL BANNER */
.install-banner{background:linear-gradient(135deg,#245a36,#1a472a);color:#fff;padding:12px 24px;border-radius:10px;display:none;align-items:center;gap:16px;margin-bottom:20px;cursor:pointer}
.install-banner:hover{opacity:.95}
.install-banner .install-text{flex:1;font-size:14px}
.install-banner .install-btn{background:#fff;color:#1a472a;border:none;padding:8px 20px;border-radius:6px;font-weight:600;cursor:pointer;font-size:13px}
.install-banner .dismiss{background:none;border:none;color:rgba(255,255,255,.7);cursor:pointer;font-size:18px;padding:4px 8px}

/* RESPONSIVE */
@media(max-width:768px){
  .navbar{padding:0 12px}
  .main{padding:12px}
  .stats-row{grid-template-columns:repeat(2,1fr)}
  .bid-card{grid-template-columns:1fr;gap:8px}
  .bid-right{flex-direction:row;align-items:center}
  .toolbar input[type=text]{min-width:120px}
}
@media(max-width:480px){
  .stats-row{grid-template-columns:1fr 1fr}
  .bid-meta{flex-direction:column;gap:4px}
}
</style>
</head>
<body>

<nav class="navbar">
  <div class="logo">
    <img src="/icon.svg" alt=""> OAK Builders Bid Finder
  </div>
  <a href="/" class="active">Dashboard</a>
  <a href="/settings">Settings</a>
</nav>

<!-- Install Banner -->
<div class="main">
<div class="install-banner" id="installBanner">
  <div class="install-text">Install Bid Finder on your desktop for quick access</div>
  <button class="install-btn" id="installBtn">Install App</button>
  <button class="dismiss" id="dismissInstall">&times;</button>
</div>

<!-- Stats -->
<div class="stats-row" id="statsRow">
  <div class="stat-card"><div class="num" id="statTotal">-</div><div class="label">Total Bids</div></div>
  <div class="stat-card"><div class="num" id="statNew">-</div><div class="label">New / Unreviewed</div></div>
  <div class="stat-card warn"><div class="num" id="statHigh">-</div><div class="label">High Relevance (70+)</div></div>
  <div class="stat-card hot"><div class="num" id="statDue">-</div><div class="label">Due This Week</div></div>
</div>

<!-- Run Button -->
<div class="run-section">
  <button class="btn-run" id="runBtn" onclick="startScan()">
    <span class="icon">&#9654;</span>
    <span class="spinner"></span>
    Run Scan Now
  </button>
  <div class="run-status" id="runStatus"></div>
</div>

<!-- Filters -->
<div class="toolbar">
  <div>
    <div class="filter-label">Category</div>
    <select id="filterType" onchange="loadBids()">
      <option value="">All Types</option>
      <option value="waterproofing">Waterproofing</option>
      <option value="tenant_improvements">Tenant Improvements</option>
      <option value="general_contracting">General Contracting</option>
      <option value="government">Government</option>
      <option value="general">General</option>
    </select>
  </div>
  <div>
    <div class="filter-label">Status</div>
    <select id="filterStatus" onchange="loadBids()">
      <option value="">All Statuses</option>
      <option value="new">New</option>
      <option value="reviewed">Reviewed</option>
      <option value="bid">Bid</option>
      <option value="no_bid">No Bid</option>
      <option value="awarded">Awarded</option>
    </select>
  </div>
  <div>
    <div class="filter-label">Min Score</div>
    <select id="filterScore" onchange="loadBids()">
      <option value="0">Any Score</option>
      <option value="50">50+</option>
      <option value="60" selected>60+</option>
      <option value="70">70+</option>
      <option value="80">80+</option>
    </select>
  </div>
  <div style="flex:1">
    <div class="filter-label">Search</div>
    <input type="text" id="filterQ" placeholder="Search bids..." onkeyup="debounceSearch()">
  </div>
</div>

<!-- Bid Results -->
<div id="bidResults">
  <div class="empty"><div class="big">&#128269;</div><p>Click "Run Scan Now" to find bid opportunities</p></div>
</div>

</div><!-- .main -->

<script>
// ---- PWA Install ----
let deferredPrompt;
window.addEventListener('beforeinstallprompt', e => {
  e.preventDefault();
  deferredPrompt = e;
  document.getElementById('installBanner').style.display = 'flex';
});
document.getElementById('installBtn').onclick = async () => {
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  await deferredPrompt.userChoice;
  deferredPrompt = null;
  document.getElementById('installBanner').style.display = 'none';
};
document.getElementById('dismissInstall').onclick = e => {
  e.stopPropagation();
  document.getElementById('installBanner').style.display = 'none';
};
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js');

// ---- Stats ----
async function loadStats() {
  try {
    const r = await fetch('/api/stats');
    const s = await r.json();
    document.getElementById('statTotal').textContent = s.total || 0;
    document.getElementById('statNew').textContent = s.new || 0;
    document.getElementById('statHigh').textContent = s.high_relevance || 0;
    document.getElementById('statDue').textContent = s.due_this_week || 0;
  } catch(e) {}
}

// ---- Run Scan ----
let pollTimer = null;
async function startScan() {
  const btn = document.getElementById('runBtn');
  const status = document.getElementById('runStatus');
  btn.classList.add('running');
  btn.disabled = true;
  status.textContent = 'Starting scan...';
  status.className = 'run-status';

  try {
    const r = await fetch('/api/run', {method:'POST'});
    if (r.status === 409) {
      status.textContent = 'A scan is already running...';
      pollProgress();
      return;
    }
    pollProgress();
  } catch(e) {
    status.textContent = 'Failed to start scan: ' + e.message;
    status.className = 'run-status error';
    btn.classList.remove('running');
    btn.disabled = false;
  }
}

function pollProgress() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const r = await fetch('/api/run/status');
      const s = await r.json();
      const status = document.getElementById('runStatus');
      const btn = document.getElementById('runBtn');

      if (s.progress.length) status.textContent = s.progress[s.progress.length - 1];

      if (!s.running) {
        clearInterval(pollTimer);
        pollTimer = null;
        btn.classList.remove('running');
        btn.disabled = false;
        if (s.error) {
          status.textContent = 'Error: ' + s.error;
          status.className = 'run-status error';
        } else if (s.summary) {
          const sm = s.summary;
          status.textContent = `Done! ${sm.total_found} bids found (${sm.new_opportunities} new) from ${sm.sources_searched.length} sources in ${(sm.run_date || '').split('T')[0] || 'today'}`;
          if (sm.errors && sm.errors.length) status.textContent += ` | ${sm.errors.length} source errors`;
        }
        loadStats();
        loadBids();
      }
    } catch(e) {}
  }, 1500);
}

// ---- Load Bids ----
const CAT_NAMES = {
  waterproofing: 'Waterproofing & Envelope',
  tenant_improvements: 'Tenant Improvements',
  general_contracting: 'General Contracting',
  government: 'Government / Federal',
  general: 'General',
  other: 'Other'
};
const CAT_ORDER = ['waterproofing','tenant_improvements','general_contracting','government','general','other'];

let searchTimeout;
function debounceSearch() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(loadBids, 300);
}

async function loadBids() {
  const params = new URLSearchParams();
  const type = document.getElementById('filterType').value;
  const status = document.getElementById('filterStatus').value;
  const score = document.getElementById('filterScore').value;
  const q = document.getElementById('filterQ').value;
  if (type) params.set('type', type);
  if (status) params.set('status', status);
  if (score) params.set('min_score', score);
  if (q) params.set('q', q);
  params.set('limit', '200');

  try {
    const r = await fetch('/api/bids?' + params);
    const bids = await r.json();
    renderBids(bids);
  } catch(e) {
    document.getElementById('bidResults').innerHTML = '<div class="empty"><p>Error loading bids</p></div>';
  }
}

function renderBids(bids) {
  const container = document.getElementById('bidResults');
  if (!bids.length) {
    container.innerHTML = '<div class="empty"><div class="big">&#128269;</div><p>No bids found. Try adjusting filters or run a scan.</p></div>';
    return;
  }

  // Group by category
  const grouped = {};
  bids.forEach(b => {
    const cat = b.project_type || 'other';
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(b);
  });

  let html = '';
  CAT_ORDER.forEach(cat => {
    const list = grouped[cat];
    if (!list || !list.length) return;
    const name = CAT_NAMES[cat] || cat.replace(/_/g, ' ');
    html += `<div class="cat-section">
      <div class="cat-header"><h2>${name}</h2><span class="count">${list.length}</span></div>`;
    list.forEach(b => { html += renderCard(b); });
    html += '</div>';
  });

  // Any categories not in CAT_ORDER
  Object.keys(grouped).forEach(cat => {
    if (CAT_ORDER.includes(cat)) return;
    const list = grouped[cat];
    html += `<div class="cat-section">
      <div class="cat-header"><h2>${cat}</h2><span class="count">${list.length}</span></div>`;
    list.forEach(b => { html += renderCard(b); });
    html += '</div>';
  });

  container.innerHTML = html;
}

function renderCard(b) {
  const scoreClass = b.score >= 70 ? 'high' : b.score >= 50 ? 'mid' : 'low';
  const cardClass = b.score >= 70 ? 'score-high' : b.score >= 50 ? 'score-mid' : 'score-low';
  const statusOpts = ['new','reviewed','bid','no_bid','awarded'].map(s =>
    `<option value="${s}" ${s===b.status?'selected':''}>${s.replace('_',' ')}</option>`
  ).join('');

  return `<div class="bid-card ${cardClass}">
    <div>
      <div class="bid-title"><a href="${b.source_url}" target="_blank">${escHtml(b.title)}</a></div>
      <div class="bid-meta">
        <span><strong>Source:</strong> ${escHtml(b.source)}</span>
        <span><strong>Location:</strong> ${escHtml(b.location || 'N/A')}</span>
        <span><strong>Value:</strong> ${escHtml(b.value || 'N/A')}</span>
        <span><strong>Due:</strong> ${escHtml(b.due_date || 'N/A')}</span>
        ${b.set_aside ? '<span><strong>Set-Aside:</strong> '+escHtml(b.set_aside)+'</span>' : ''}
      </div>
      ${b.description ? '<div style="margin-top:6px;font-size:12px;color:#888">'+escHtml(b.description)+'</div>' : ''}
    </div>
    <div class="bid-right">
      <span class="score-badge ${scoreClass}">${b.score}</span>
      <select class="status-select" onchange="updateStatus(${b.id}, this.value)">${statusOpts}</select>
    </div>
  </div>`;
}

function escHtml(s) {
  if (!s) return '';
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

async function updateStatus(id, status) {
  try {
    await fetch('/api/status', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({id, status})
    });
  } catch(e) { alert('Failed to update status'); }
}

// ---- Init ----
loadStats();
loadBids();

// Check if scan is already running (page reload)
fetch('/api/run/status').then(r=>r.json()).then(s => {
  if (s.running) {
    document.getElementById('runBtn').classList.add('running');
    document.getElementById('runBtn').disabled = true;
    document.getElementById('runStatus').textContent = 'Scan in progress...';
    pollProgress();
  }
});
</script>
</body>
</html>"""


# ============================================================
# SETTINGS HTML
# ============================================================

SETTINGS_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#1a472a">
<link rel="manifest" href="/manifest.json">
<title>Settings - OAK Builders Bid Finder</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,sans-serif;background:#f0f2f5;color:#333}
.navbar{background:#1a472a;color:#fff;padding:0 24px;display:flex;align-items:center;height:56px;position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(0,0,0,.15)}
.navbar .logo{font-weight:700;font-size:18px;margin-right:auto;display:flex;align-items:center;gap:10px}
.navbar .logo img{width:28px;height:28px;border-radius:4px}
.navbar a{color:rgba(255,255,255,.85);text-decoration:none;padding:8px 16px;border-radius:6px;font-size:14px;font-weight:500;transition:.15s}
.navbar a:hover,.navbar a.active{background:rgba(255,255,255,.15);color:#fff}
.main{max-width:860px;margin:0 auto;padding:24px 20px}
h1{color:#1a472a;margin-bottom:4px;font-size:24px}
h1 small{font-weight:normal;color:#888;font-size:14px}
.section{background:#fff;border:1px solid #dee2e6;padding:24px;margin:20px 0;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.section h2{margin-top:0;color:#1a472a;font-size:18px;border-bottom:2px solid #e9ecef;padding-bottom:8px}
label{display:block;margin:12px 0 4px;font-weight:bold;font-size:14px}
label.inline{display:inline;font-weight:normal}
input[type=text],input[type=password],input[type=email]{width:100%;padding:10px;border:1px solid #ccc;border-radius:6px;font-size:14px}
input[type=checkbox]{margin-right:6px}
.hint{color:#888;font-size:12px;margin-top:2px}
.hint a{color:#1a472a}
.source-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}
.source-card{padding:12px;border:1px solid #ddd;border-radius:6px}
.source-card.free{border-left:4px solid #28a745}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:bold;color:#fff;vertical-align:middle}
.badge.free{background:#28a745}
.badge.paid{background:#ffc107;color:#333}
.paid-source{background:#fefefe;border:1px solid #e0e0e0;border-left:4px solid #ffc107;padding:16px;margin:12px 0;border-radius:6px}
.paid-source h4{margin:0 0 10px}
.paid-source .fields{display:grid;grid-template-columns:1fr 1fr;gap:10px}
button[type=submit]{background:#1a472a;color:#fff;padding:12px 30px;border:none;border-radius:8px;cursor:pointer;font-size:16px;font-weight:600;margin-top:20px}
button[type=submit]:hover{background:#245a36}
.flash{padding:12px;background:#d4edda;border:1px solid #c3e6cb;border-radius:6px;margin:12px 0;color:#155724}
@media(max-width:600px){.source-grid,.paid-source .fields{grid-template-columns:1fr}}
</style>
</head>
<body>
<nav class="navbar">
  <div class="logo"><img src="/icon.svg" alt=""> OAK Builders Bid Finder</div>
  <a href="/">Dashboard</a>
  <a href="/settings" class="active">Settings</a>
</nav>
<div class="main">
<h1>Settings<br><small>Configure credentials and data sources</small></h1>
{% for msg in get_flashed_messages() %}<div class="flash">{{ msg }}</div>{% endfor %}
<form method="POST">
  <div class="section">
    <h2>Email Configuration (Gmail SMTP)</h2>
    <p class="hint">Use a Gmail App Password. Go to myaccount.google.com &gt; Security &gt; 2-Step Verification &gt; App Passwords.</p>
    <label>Gmail Address</label>
    <input type="email" name="gmail_address" value="{{ s.gmail_address }}" placeholder="yourname@gmail.com">
    <label>Gmail App Password</label>
    <input type="password" name="gmail_app_password" value="{{ s.gmail_app_password }}" placeholder="xxxx xxxx xxxx xxxx">
    <label>Recipients (comma-separated emails)</label>
    <input type="text" name="email_recipients" value="{{ s.email_recipients | join(', ') }}" placeholder="you@email.com, team@email.com">
  </div>
  <div class="section">
    <h2>Google Sheets Integration</h2>
    <p class="hint">Requires a Google Cloud service account JSON key file (service_account.json) in the project folder.</p>
    <label><input type="checkbox" name="google_sheets_enabled" {{ 'checked' if s.google_sheets_enabled }}><span class="inline">Enable Google Sheets sync</span></label>
    <label>Spreadsheet Name</label>
    <input type="text" name="google_sheet_name" value="{{ s.google_sheet_name }}">
  </div>
  <div class="section">
    <h2>API Keys</h2>
    <label>SAM.gov API Key (free)</label>
    <input type="text" name="sam_gov_api_key" value="{{ s.sam_gov_api_key }}" placeholder="Get free key at api.data.gov/signup">
    <p class="hint">Free API key from <a href="https://api.data.gov/signup/" target="_blank">api.data.gov/signup</a></p>
  </div>
  <div class="section">
    <h2>Data Sources</h2>
    <h3>Free Sources (Always Available)</h3>
    <div class="source-grid">
      {% for key, src in sources.items() %}
      {% if src.get('cost', 'free') == 'free' %}
      <div class="source-card free">
        <span class="badge free">FREE</span>
        <strong>{{ src.name }}</strong><br>
        <small style="color:#666">{{ src.type | title }} &bull; {{ 'Enabled' if src.enabled else 'Disabled' }}</small>
      </div>
      {% endif %}
      {% endfor %}
    </div>
    <h3 style="margin-top:24px">Paid Sources (Add Credentials When Ready)</h3>
    <p class="hint">Enable and enter credentials once you have an active subscription.</p>
    {% for key, paid in s.paid_sources.items() %}
    <div class="paid-source">
      <h4><span class="badge paid">PAID</span> {{ key | replace('_', ' ') | title }}</h4>
      <label><input type="checkbox" name="paid_{{ key }}_enabled" {{ 'checked' if paid.enabled }}><span class="inline">Enable this source</span></label>
      <div class="fields">
        <div><label>Username / Email</label><input type="text" name="paid_{{ key }}_username" value="{{ paid.username }}"></div>
        <div><label>Password</label><input type="password" name="paid_{{ key }}_password" value="{{ paid.password }}"></div>
      </div>
    </div>
    {% endfor %}
  </div>
  <button type="submit">Save Settings</button>
</form>
</div>
</body>
</html>"""


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_ENV") != "production"
    print("=" * 50)
    print("  OAK Builders - Bid Finder Dashboard")
    print(f"  Open: http://localhost:{port}")
    if APP_PASSWORD:
        print(f"  Password protection: ON")
    else:
        print(f"  Password protection: OFF (set APP_PASSWORD to enable)")
    print()
    print("  To install on desktop:")
    print("  1. Open in Chrome/Edge")
    print("  2. Click the install icon in the address bar")
    print("     or click 'Install App' banner on the page")
    print("=" * 50)
    app.run(host="0.0.0.0", port=port, debug=debug)
