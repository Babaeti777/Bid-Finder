"""
OAK BUILDERS LLC - Bid Finder
Settings Web UI (Local Only)

Run:  python settings_app.py
Open: http://localhost:5000
"""

import json
import os
from pathlib import Path

from flask import Flask, render_template_string, request, redirect, url_for, flash

from config import SOURCES

app = Flask(__name__)
app.secret_key = os.urandom(24)

SETTINGS_FILE = Path(__file__).parent / "settings.json"

DEFAULT_SETTINGS = {
    "gmail_address": "1oakbuilders@gmail.com",
    "gmail_app_password": "Nikian$3879200",
    "email_recipients": ["1oakbuilders@gmail.com],
    "google_sheets_enabled": True,
    "google_sheet_name": "OAK Builders - Bid Tracker",
    "sam_gov_api_key": "Z7kypWqNfdKCFFiltenbzqsZp0n1wNaJE7PGI2pv
",
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
        # Ensure all paid sources exist
        for key, default in DEFAULT_SETTINGS["paid_sources"].items():
            if key not in merged.get("paid_sources", {}):
                merged.setdefault("paid_sources", {})[key] = default
        return merged
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>OAK Builders - Bid Finder Settings</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; }
        body { font-family: Arial, sans-serif; max-width: 860px; margin: 40px auto; padding: 0 20px; background: #f5f5f5; color: #333; }
        h1 { color: #1a472a; margin-bottom: 6px; }
        h1 small { font-weight: normal; color: #888; font-size: 14px; }
        .section { background: white; border: 1px solid #dee2e6; padding: 24px; margin: 20px 0; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
        .section h2 { margin-top: 0; color: #1a472a; font-size: 18px; border-bottom: 2px solid #e9ecef; padding-bottom: 8px; }
        label { display: block; margin: 12px 0 4px; font-weight: bold; font-size: 14px; }
        label.inline { display: inline; font-weight: normal; }
        input[type=text], input[type=password], input[type=email] {
            width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px;
        }
        input[type=checkbox] { margin-right: 6px; }
        .hint { color: #888; font-size: 12px; margin-top: 2px; }
        .source-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px; }
        .source-card { padding: 12px; border: 1px solid #ddd; border-radius: 6px; }
        .source-card.free { border-left: 4px solid #28a745; }
        .source-card.paid { border-left: 4px solid #ffc107; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: bold; color: white; vertical-align: middle; }
        .badge.free { background: #28a745; }
        .badge.paid { background: #ffc107; color: #333; }
        .paid-source { background: #fefefe; border: 1px solid #e0e0e0; border-left: 4px solid #ffc107; padding: 16px; margin: 12px 0; border-radius: 6px; }
        .paid-source h4 { margin: 0 0 10px; }
        .paid-source .fields { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        button { background: #1a472a; color: white; padding: 12px 30px; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; margin-top: 20px; }
        button:hover { background: #245a36; }
        .flash { padding: 12px; background: #d4edda; border: 1px solid #c3e6cb; border-radius: 6px; margin: 12px 0; color: #155724; }
        @media (max-width: 600px) { .source-grid, .paid-source .fields { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <h1>OAK Builders - Bid Finder Settings <br><small>Configure credentials and data sources</small></h1>

    {% for msg in get_flashed_messages() %}<div class="flash">{{ msg }}</div>{% endfor %}

    <form method="POST">
        <!-- EMAIL -->
        <div class="section">
            <h2>Email Configuration (Gmail SMTP)</h2>
            <p class="hint">Use a Gmail App Password. Go to myaccount.google.com > Security > 2-Step Verification > App Passwords.</p>
            <label>Gmail Address</label>
            <input type="email" name="gmail_address" value="{{ s.gmail_address }}" placeholder="yourname@gmail.com">
            <label>Gmail App Password</label>
            <input type="password" name="gmail_app_password" value="{{ s.gmail_app_password }}" placeholder="xxxx xxxx xxxx xxxx">
            <label>Recipients (comma-separated emails)</label>
            <input type="text" name="email_recipients" value="{{ s.email_recipients | join(', ') }}" placeholder="you@email.com, team@email.com">
        </div>

        <!-- GOOGLE SHEETS -->
        <div class="section">
            <h2>Google Sheets Integration</h2>
            <p class="hint">Requires a Google Cloud service account JSON key file (service_account.json) in the project folder.</p>
            <label>
                <input type="checkbox" name="google_sheets_enabled" {{ 'checked' if s.google_sheets_enabled }}>
                <span class="inline">Enable Google Sheets sync</span>
            </label>
            <label>Spreadsheet Name</label>
            <input type="text" name="google_sheet_name" value="{{ s.google_sheet_name }}">
        </div>

        <!-- API KEYS -->
        <div class="section">
            <h2>API Keys</h2>
            <label>SAM.gov API Key (free)</label>
            <input type="text" name="sam_gov_api_key" value="{{ s.sam_gov_api_key }}" placeholder="Get free key at api.data.gov/signup">
            <p class="hint">Free API key from <a href="https://api.data.gov/signup/" target="_blank">api.data.gov/signup</a></p>
        </div>

        <!-- FREE SOURCES -->
        <div class="section">
            <h2>Data Sources</h2>
            <h3>Free Sources (Always Available)</h3>
            <div class="source-grid">
                {% for key, src in sources.items() %}
                {% if src.get('cost', 'free') == 'free' %}
                <div class="source-card free">
                    <span class="badge free">FREE</span>
                    <strong>{{ src.name }}</strong><br>
                    <small style="color:#666;">{{ src.type | title }} &bull; {{ 'Enabled' if src.enabled else 'Disabled' }}</small>
                </div>
                {% endif %}
                {% endfor %}
            </div>

            <!-- PAID SOURCES -->
            <h3 style="margin-top:24px;">Paid Sources (Add Credentials When Ready)</h3>
            <p class="hint">Enable and enter credentials once you have an active subscription.</p>
            {% for key, paid in s.paid_sources.items() %}
            <div class="paid-source">
                <h4>
                    <span class="badge paid">PAID</span>
                    {{ key | replace('_', ' ') | title }}
                </h4>
                <label>
                    <input type="checkbox" name="paid_{{ key }}_enabled" {{ 'checked' if paid.enabled }}>
                    <span class="inline">Enable this source</span>
                </label>
                <div class="fields">
                    <div>
                        <label>Username / Email</label>
                        <input type="text" name="paid_{{ key }}_username" value="{{ paid.username }}">
                    </div>
                    <div>
                        <label>Password</label>
                        <input type="password" name="paid_{{ key }}_password" value="{{ paid.password }}">
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>

        <button type="submit">Save Settings</button>
    </form>
</body>
</html>"""


@app.route("/", methods=["GET", "POST"])
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
    return render_template_string(TEMPLATE, s=s, sources=SOURCES)


if __name__ == "__main__":
    print("=" * 50)
    print("  OAK Builders - Bid Finder Settings")
    print("  Open: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)
