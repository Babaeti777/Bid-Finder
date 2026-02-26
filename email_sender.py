"""
OAK BUILDERS LLC - Bid Finder
Email Notification Module

Sends HTML email digests of new bid opportunities via Gmail SMTP.
Supports environment variable overrides for cloud deployment (GitHub Actions).
"""

import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from collections import defaultdict

from config import NOTIFICATIONS, SOURCES
from models import BidDatabase


def _is_expired(bid) -> bool:
    """Return True if the bid's due_date is in the past."""
    if not bid.due_date:
        return False
    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%dT%H:%M:%S"]:
        try:
            due = datetime.strptime(bid.due_date[:10], fmt[:min(len(fmt), len(bid.due_date))])
            return due.date() < datetime.now().date()
        except ValueError:
            continue
    return False


class EmailSender:
    """Sends HTML email digests of new bid opportunities."""

    def __init__(self, db: BidDatabase):
        self.db = db
        self.config = NOTIFICATIONS["email"]
        # Environment variables override config (for GitHub Actions)
        self.smtp_server = os.environ.get("SMTP_SERVER", self.config["smtp_server"])
        self.smtp_port = int(os.environ.get("SMTP_PORT", str(self.config["smtp_port"])))
        self.sender_email = os.environ.get("GMAIL_ADDRESS", self.config["sender_email"])
        self.sender_password = os.environ.get("GMAIL_APP_PASSWORD", self.config["sender_password"])
        recipients_env = os.environ.get("EMAIL_RECIPIENTS")
        if recipients_env:
            self.recipients = json.loads(recipients_env)
        else:
            self.recipients = self.config["recipients"]

    def send_digest(self, scraper_errors: list = None) -> bool:
        """Send a digest email of new bids since the last email."""
        if not self.sender_email or not self.sender_password or not self.recipients:
            print("[Email] Missing credentials or recipients. Configure via settings page or env vars.")
            return False

        min_score = NOTIFICATIONS.get("min_score_to_notify", 0)
        opportunities = self.db.get_new_since_last_email(min_score=min_score)
        # Exclude expired bids from the email digest
        opportunities = [opp for opp in opportunities if not _is_expired(opp)]

        if not opportunities and not scraper_errors:
            print("[Email] No new opportunities and no errors to report. Skipping email.")
            return False

        html = self._build_html(opportunities, scraper_errors or [])
        count = len(opportunities)
        subject = f"OAK Builders Bid Alert - {count} New Opportunities ({datetime.now().strftime('%m/%d/%Y')})"

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.sender_email
            msg["To"] = ", ".join(self.recipients)
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            bid_ids = [opp.source_id for opp in opportunities]
            self.db.log_email_send(
                recipient_count=len(self.recipients),
                bid_ids=bid_ids,
                errors=scraper_errors,
            )
            print(f"[Email] Sent digest with {count} bids to {len(self.recipients)} recipients.")
            return True

        except Exception as e:
            print(f"[Email] Failed to send: {e}")
            return False

    def _build_html(self, opportunities: list, errors: list) -> str:
        """Build HTML email body grouped by project type."""
        grouped = defaultdict(list)
        for opp in opportunities:
            grouped[opp.project_type or "other"].append(opp)

        category_names = {
            "waterproofing": "Waterproofing & Envelope",
            "tenant_improvements": "Tenant Improvements",
            "general_contracting": "General Contracting",
            "government": "Government / Federal",
            "general": "General",
            "other": "Other",
        }
        category_order = [
            "waterproofing", "tenant_improvements", "general_contracting",
            "government", "general", "other",
        ]

        sections_html = ""
        for cat in category_order:
            bids = grouped.get(cat, [])
            if not bids:
                continue
            cat_name = category_names.get(cat, cat.replace("_", " ").title())
            sections_html += (
                f'<h2 style="color:#1a472a; border-bottom:2px solid #1a472a; '
                f'padding-bottom:6px; margin-top:28px;">'
                f'{cat_name} ({len(bids)})</h2>\n'
            )
            for opp in bids:
                sections_html += self._render_bid_card(opp)

        error_html = ""
        if errors:
            error_html = (
                '<div style="background:#fff3cd; border:1px solid #ffc107; '
                'padding:14px; border-radius:6px; margin:16px 0;">'
                '<h3 style="margin-top:0; color:#856404;">Scraper Notices</h3><ul>'
            )
            for err in errors:
                error_html += f"<li>{err}</li>"
            error_html += "</ul></div>"

        no_bids_html = ""
        if not opportunities:
            no_bids_html = (
                '<div style="text-align:center; padding:30px; color:#666;">'
                '<p style="font-size:16px;">No new opportunities above the score threshold today.</p>'
                '</div>'
            )

        return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width:700px; margin:0 auto; background:#f5f5f5; padding:0;">
    <div style="background:#1a472a; color:white; padding:24px; text-align:center;">
        <h1 style="margin:0; font-size:22px;">OAK Builders - Daily Bid Report</h1>
        <p style="margin:8px 0 0; opacity:0.9;">
            {datetime.now().strftime('%B %d, %Y')} &bull; {len(opportunities)} New Opportunities
        </p>
    </div>
    <div style="background:white; padding:20px;">
        {error_html}
        {no_bids_html}
        {sections_html}
    </div>
    <div style="text-align:center; padding:16px; color:#999; font-size:12px;">
        <p>OAK Builders LLC &mdash; Falls Church, VA | Automated Bid Finder</p>
    </div>
</body>
</html>"""

    def _render_bid_card(self, opp) -> str:
        """Render a single bid as an HTML card."""
        location = ", ".join(filter(None, [
            opp.location_city, opp.location_county, opp.location_state,
        ]))
        if opp.budget_display:
            value = opp.budget_display
        elif opp.estimated_value_min:
            value = f"${opp.estimated_value_min:,.0f} - ${opp.estimated_value_max:,.0f}"
        else:
            value = "Not specified"

        score = opp.relevance_score
        if score >= 70:
            score_color = "#28a745"
        elif score >= 50:
            score_color = "#ffc107"
        else:
            score_color = "#dc3545"

        source_name = SOURCES.get(opp.source, {}).get("name", opp.source.replace("_", " ").title())
        link_html = f'<a href="{opp.source_url}" style="color:#1a472a; text-decoration:none; font-weight:bold;">{opp.title[:80]}</a>'

        return f"""
<div style="border:1px solid #e0e0e0; border-left:4px solid {score_color};
            padding:14px; margin:10px 0; border-radius:4px; background:#fafafa;">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div style="flex:1;">{link_html}</div>
        <span style="background:{score_color}; color:white; padding:3px 12px;
                     border-radius:12px; font-weight:bold; font-size:14px;
                     margin-left:10px; white-space:nowrap;">{score}</span>
    </div>
    <table style="width:100%; margin-top:8px; font-size:13px; color:#555;">
        <tr>
            <td><strong>Source:</strong> {source_name}</td>
            <td><strong>Location:</strong> {location or 'N/A'}</td>
        </tr>
        <tr>
            <td><strong>Est. Value:</strong> {value}</td>
            <td><strong>Due Date:</strong> {opp.due_date or 'N/A'}</td>
        </tr>
    </table>
</div>"""
