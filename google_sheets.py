"""
OAK BUILDERS LLC - Bid Finder
Google Sheets Integration

Appends new bid opportunities to a Google Sheet organized by category.
Uses gspread with a Google Cloud service account for authentication.

Setup:
  1. Create a project at console.cloud.google.com
  2. Enable Google Sheets API and Google Drive API
  3. Create a Service Account and download the JSON key as service_account.json
  4. Share your Google Sheet with the service account email address
"""

import os
import json
from datetime import datetime

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    gspread = None

from config import GOOGLE_SHEETS, NOTIFICATIONS
from models import BidDatabase


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_HEADERS = [
    "Date Added", "Score", "Project Type", "Title", "Source",
    "Location", "Est. Value", "Due Date", "Agency/Contact",
    "Set-Aside", "Status", "URL",
]


class SheetsUpdater:
    """Appends new bid opportunities to a Google Sheet."""

    def __init__(self, db: BidDatabase):
        self.db = db
        self.config = GOOGLE_SHEETS

        if gspread is None:
            raise ImportError("Install Google Sheets deps: pip install gspread google-auth")

        # Support both env-var (GitHub Actions) and file-based (local) credentials
        sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        if sa_json:
            info = json.loads(sa_json)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        else:
            sa_file = self.config.get("service_account_file", "service_account.json")
            creds = Credentials.from_service_account_file(sa_file, scopes=SCOPES)

        self.client = gspread.authorize(creds)

    def append_new_bids(self) -> int:
        """Append new bids since last email to the Google Sheet. Returns count appended."""
        min_score = NOTIFICATIONS.get("min_score_to_notify", 0)
        opportunities = self.db.get_new_since_last_email(min_score=min_score)

        if not opportunities:
            print("[Sheets] No new opportunities to append.")
            return 0

        spreadsheet_name = os.environ.get(
            "GOOGLE_SHEET_NAME",
            self.config.get("spreadsheet_name", "OAK Builders - Bid Tracker"),
        )

        try:
            spreadsheet = self.client.open(spreadsheet_name)
        except gspread.SpreadsheetNotFound:
            print(f"[Sheets] Spreadsheet '{spreadsheet_name}' not found. Creating...")
            spreadsheet = self.client.create(spreadsheet_name)

        worksheet_name = self.config.get("worksheet_name", "Bids")
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=worksheet_name, rows=1000, cols=len(SHEET_HEADERS),
            )
            worksheet.append_row(SHEET_HEADERS)

        # Ensure headers exist
        existing = worksheet.get_all_values()
        if not existing or existing[0] != SHEET_HEADERS:
            worksheet.insert_row(SHEET_HEADERS, index=1)

        # Build rows sorted by project type then score descending
        rows = []
        for opp in sorted(
            opportunities, key=lambda o: (o.project_type or "zzz", -o.relevance_score)
        ):
            location = ", ".join(filter(None, [
                opp.location_city, opp.location_county, opp.location_state,
            ]))
            if opp.budget_display:
                value = opp.budget_display
            elif opp.estimated_value_min:
                value = f"${opp.estimated_value_min:,.0f}-${opp.estimated_value_max:,.0f}"
            else:
                value = ""

            contact = f"{opp.agency_name} / {opp.contact_name}".strip(" /")

            rows.append([
                datetime.now().strftime("%Y-%m-%d"),
                opp.relevance_score,
                opp.project_type or "other",
                opp.title[:100],
                opp.source,
                location,
                value,
                opp.due_date or "",
                contact,
                opp.set_aside or "",
                opp.status or "new",
                opp.source_url or "",
            ])

        worksheet.append_rows(rows, value_input_option="USER_ENTERED")
        print(f"[Sheets] Appended {len(rows)} bids to '{spreadsheet_name}'.")
        return len(rows)
