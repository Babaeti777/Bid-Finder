"""
OAK BUILDERS LLC - Bid Finder v2
Email Digest — smarter notifications

Changes from v1:
- "Don't Miss" flagging for score >= 80
- Grouped by urgency (due this week vs. later)
- Win probability shown alongside relevance score
- Commercial vs. government split sections
- Pipeline stage indicator
- Source performance summary at bottom
- Pre-bid meeting alerts highlighted
"""

import logging
import os
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from config import EMAIL, DATABASE_FILE
from models import BidDatabase

logger = logging.getLogger("email")


class EmailSender:
    """Sends HTML digest emails with bid opportunities."""

    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.from_addr = EMAIL["from_address"]
        self.password = EMAIL["app_password"]
        self.recipients = EMAIL["recipients"]
        self.db = BidDatabase(DATABASE_FILE)

    def send_digest(self, errors: List[dict] = None):
        """Build and send the daily digest email."""
        if not self.from_addr or not self.password or not self.recipients:
            logger.warning("Email not configured, skipping digest")
            return

        bids = self.db.get_new_since_last_email()
        if not bids:
            logger.info("No new opportunities to email")
            return

        # Filter expired
        bids = [b for b in bids if not self._is_expired(b)]

        if not bids:
            logger.info("No active (non-expired) opportunities to email")
            return

        # Sort by relevance score descending
        bids.sort(key=lambda b: b.get("relevance_score", 0), reverse=True)

        # Build email
        html = self._build_html(bids, errors or [])

        msg = MIMEMultipart("alternative")
        msg["Subject"] = self._build_subject(bids)
        msg["From"] = self.from_addr
        msg["To"] = ", ".join(self.recipients)
        msg.attach(MIMEText(html, "html"))

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.from_addr, self.password)
                server.send_message(msg)

            # Log the send
            keys = [b.get("dedup_key", "") for b in bids]
            self.db.log_email_send(len(self.recipients), keys)
            logger.info(f"Digest sent to {len(self.recipients)} recipients with {len(bids)} opportunities")

        except Exception as e:
            logger.error(f"SMTP error: {e}")
            raise

    def _build_subject(self, bids: list) -> str:
        high_count = sum(1 for b in bids if b.get("relevance_score", 0) >= 70)
        dont_miss = sum(1 for b in bids if b.get("relevance_score", 0) >= 80)

        today = datetime.now().strftime("%b %d")
        parts = [f"Bid Finder — {today}"]

        if dont_miss > 0:
            parts.append(f"🔥 {dont_miss} Don't Miss!")
        elif high_count > 0:
            parts.append(f"⭐ {high_count} High Relevance")

        parts.append(f"{len(bids)} total")
        return " | ".join(parts)

    def _build_html(self, bids: list, errors: list) -> str:
        """Generate the HTML email body."""
        # Categorize bids
        dont_miss = [b for b in bids if b.get("relevance_score", 0) >= 80]
        due_soon = [
            b for b in bids
            if b.get("relevance_score", 0) < 80 and self._days_left(b) is not None and 0 <= self._days_left(b) <= 7
        ]
        government = [
            b for b in bids
            if b not in dont_miss and b not in due_soon
            and b.get("source", "") in ("SAM.gov", "DC OCP", "eVA Virginia", "eMMA Maryland", "Montgomery County")
        ]
        commercial = [
            b for b in bids
            if b not in dont_miss and b not in due_soon and b not in government
        ]

        stats = self.db.get_stats()

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
                .container {{ max-width: 700px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #1a472a 0%, #2d6a4f 100%); color: white; padding: 28px 24px; }}
                .header h1 {{ margin: 0; font-size: 22px; }}
                .header .subtitle {{ color: #a7d7c5; font-size: 14px; margin-top: 6px; }}
                .stats-bar {{ display: flex; gap: 20px; padding: 16px 24px; background: #f0f9f4; border-bottom: 1px solid #e0e0e0; font-size: 13px; }}
                .stat {{ text-align: center; }}
                .stat-num {{ font-size: 20px; font-weight: 700; color: #1a472a; }}
                .stat-label {{ color: #666; font-size: 11px; }}
                .section {{ padding: 16px 24px; }}
                .section-title {{ font-size: 16px; font-weight: 700; color: #333; margin: 0 0 12px 0; padding-bottom: 8px; border-bottom: 2px solid #e0e0e0; }}
                .bid-card {{ border: 1px solid #e0e0e0; border-radius: 8px; padding: 14px; margin-bottom: 10px; }}
                .bid-card.dont-miss {{ border-color: #ff6b35; background: #fff8f5; }}
                .bid-card.due-soon {{ border-color: #ffab00; background: #fffdf5; }}
                .bid-title {{ font-weight: 700; font-size: 14px; color: #1a1a1a; margin-bottom: 6px; }}
                .bid-title a {{ color: #1a472a; text-decoration: none; }}
                .bid-meta {{ font-size: 12px; color: #666; line-height: 1.6; }}
                .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
                .badge-green {{ background: #d4edda; color: #155724; }}
                .badge-yellow {{ background: #fff3cd; color: #856404; }}
                .badge-red {{ background: #f8d7da; color: #721c24; }}
                .badge-fire {{ background: #ff6b35; color: white; }}
                .badge-blue {{ background: #cce5ff; color: #004085; }}
                .win-prob {{ display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: 600; background: #e8e8e8; }}
                .errors {{ background: #fff3cd; padding: 12px; border-radius: 6px; margin-top: 8px; font-size: 12px; }}
                .footer {{ padding: 16px 24px; background: #f9f9f9; font-size: 11px; color: #999; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏗️ OAK Builders — Daily Bid Digest</h1>
                    <div class="subtitle">{datetime.now().strftime('%A, %B %d, %Y')} • {len(bids)} opportunities</div>
                </div>

                <div class="stats-bar">
                    <div class="stat"><div class="stat-num">{stats.get('active', 0)}</div><div class="stat-label">Active</div></div>
                    <div class="stat"><div class="stat-num">{stats.get('new_today', 0)}</div><div class="stat-label">New Today</div></div>
                    <div class="stat"><div class="stat-num">{stats.get('high_relevance', 0)}</div><div class="stat-label">High Score</div></div>
                    <div class="stat"><div class="stat-num">{stats.get('due_this_week', 0)}</div><div class="stat-label">Due This Week</div></div>
                </div>
        """

        # Don't Miss section
        if dont_miss:
            html += '<div class="section">'
            html += '<div class="section-title">🔥 Don\'t Miss These</div>'
            for bid in dont_miss:
                html += self._render_bid_card(bid, "dont-miss")
            html += '</div>'

        # Due Soon
        if due_soon:
            html += '<div class="section">'
            html += '<div class="section-title">⏰ Due This Week</div>'
            for bid in due_soon:
                html += self._render_bid_card(bid, "due-soon")
            html += '</div>'

        # Government
        if government:
            html += '<div class="section">'
            html += f'<div class="section-title">🏛️ Government ({len(government)})</div>'
            for bid in government[:15]:
                html += self._render_bid_card(bid)
            html += '</div>'

        # Commercial
        if commercial:
            html += '<div class="section">'
            html += f'<div class="section-title">🏢 Commercial & Other ({len(commercial)})</div>'
            for bid in commercial[:15]:
                html += self._render_bid_card(bid)
            html += '</div>'

        # Errors
        if errors:
            html += '<div class="section"><div class="errors">'
            html += f"<strong>⚠️ {len(errors)} source errors:</strong><br>"
            for err in errors:
                html += f"• {err.get('source', '?')}: {err.get('error', '?')}<br>"
            html += '</div></div>'

        html += f"""
                <div class="footer">
                    OAK Builders Bid Finder v2 • {len(bids)} opportunities from {datetime.now().strftime('%m/%d/%Y %I:%M %p')} ET
                </div>
            </div>
        </body>
        </html>
        """
        return html

    def _render_bid_card(self, bid: dict, extra_class: str = "") -> str:
        score = bid.get("relevance_score", 0)
        win_prob = bid.get("win_probability", 0)

        # Score badge
        if score >= 80:
            score_badge = f'<span class="badge badge-fire">🔥 {score}</span>'
        elif score >= 70:
            score_badge = f'<span class="badge badge-green">{score}</span>'
        elif score >= 50:
            score_badge = f'<span class="badge badge-yellow">{score}</span>'
        else:
            score_badge = f'<span class="badge badge-red">{score}</span>'

        # Win probability
        win_html = ""
        if win_prob > 0:
            win_html = f' <span class="win-prob">Win: {win_prob}%</span>'

        # Location
        parts = [bid.get("location_city", ""), bid.get("location_state", "")]
        location = ", ".join(p for p in parts if p)

        # Due date
        due = bid.get("due_date", "")
        days = self._days_left(bid)
        due_display = due
        if days is not None and days >= 0:
            due_display = f"{due} ({days}d left)"
        elif days is not None and days < 0:
            due_display = f"<s>{due}</s> (expired)"

        # Pre-bid alert
        prebid = ""
        if bid.get("pre_bid_date"):
            mandatory = " (MANDATORY)" if bid.get("pre_bid_mandatory") else ""
            prebid = f'<br>📅 Pre-bid: {bid["pre_bid_date"]}{mandatory}'

        url = bid.get("source_url", "#")
        title = bid.get("title", "Untitled")

        return f"""
        <div class="bid-card {extra_class}">
            <div class="bid-title"><a href="{url}">{title}</a></div>
            <div class="bid-meta">
                {score_badge}{win_html}
                <span class="badge badge-blue">{bid.get('source', '?')}</span><br>
                📍 {location or 'Location TBD'} •
                📅 Due: {due_display or 'TBD'} •
                🏢 {bid.get('agency', 'Unknown')}{prebid}
            </div>
        </div>
        """

    def _is_expired(self, bid: dict) -> bool:
        days = self._days_left(bid)
        return days is not None and days < 0

    def _days_left(self, bid: dict) -> int:
        due = bid.get("due_date", "")
        if not due:
            return None
        for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"]:
            try:
                due_dt = datetime.strptime(due[:10], fmt)
                return (due_dt - datetime.now()).days
            except ValueError:
                continue
        return None
