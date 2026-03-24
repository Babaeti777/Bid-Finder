"""
OAK BUILDERS LLC - Bid Finder v2
Google Sheets Integration

Changes from v1:
- Added win_probability column
- Added pipeline_stage column
- Added bonding_required indicator
- Added scope_category for quick filtering
- Better date formatting
- Sheet auto-sorts by relevance score
"""

import json
import logging
import os
from datetime import datetime
from typing import List

from config import SHEETS, DATABASE_FILE
from models import BidDatabase

logger = logging.getLogger("sheets")

# Headers for the sheet
HEADERS = [
    "Date Found", "Score", "Win %", "Pipeline",
    "Project Type", "Scope Fit", "Title",
    "Location", "Value Range", "Bonding?",
    "Due Date", "Days Left", "Agency",
    "Set-Aside", "Source", "Contact", "URL",
]


class SheetsUpdater:
    """Export bid opportunities to Google Sheets."""

    def __init__(self):
        self.db = BidDatabase(DATABASE_FILE)
        self.sheet = None
        self._connect()

    def _connect(self):
        """Authenticate and open spreadsheet."""
        try:
            import gspread
            from google.oauth2.service_account import Credentials

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]

            # Try env var first (GitHub Actions), then file
            creds_json = SHEETS.get("credentials_json", "")
            if creds_json:
                info = json.loads(creds_json)
                creds = Credentials.from_service_account_info(info, scopes=scopes)
            else:
                creds_file = SHEETS.get("credentials_file", "credentials.json")
                creds = Credentials.from_service_account_file(creds_file, scopes=scopes)

            client = gspread.authorize(creds)

            # Open or create spreadsheet
            sheet_name = SHEETS["spreadsheet_name"]
            try:
                self.sheet = client.open(sheet_name)
            except gspread.SpreadsheetNotFound:
                self.sheet = client.create(sheet_name)
                logger.info(f"Created new spreadsheet: {sheet_name}")

        except Exception as e:
            logger.error(f"Google Sheets connection failed: {e}")
            raise

    def update(self):
        """Append new opportunities to the sheet."""
        if not self.sheet:
            return

        min_score = SHEETS.get("min_score", 20)
        bids = self.db.search(min_score=min_score, show_expired=False, limit=500)

        if not bids:
            logger.info("No opportunities to export to Sheets")
            return

        # Filter already-exported
        exported = self.db.get_exported_keys()
        new_bids = [
            b for b in bids
            if f"{b.get('source', '')}:{b.get('source_id', '')}" not in exported
        ]

        if not new_bids:
            logger.info("All opportunities already exported to Sheets")
            return

        # Sort by project type then score
        new_bids.sort(
            key=lambda b: (b.get("project_type", ""), -b.get("relevance_score", 0))
        )

        # Ensure worksheet exists with headers
        today = datetime.now().strftime("%b %Y")
        try:
            ws = self.sheet.worksheet(today)
        except Exception:
            ws = self.sheet.add_worksheet(title=today, rows=500, cols=len(HEADERS))
            ws.append_row(HEADERS)
            # Bold the header row
            ws.format("1:1", {"textFormat": {"bold": True}})

        # Build rows
        rows = []
        export_keys = []
        for bid in new_bids:
            # Calculate days left
            days_left = ""
            due = bid.get("due_date", "")
            if due:
                for fmt in ["%Y-%m-%d", "%m/%d/%Y"]:
                    try:
                        dt = datetime.strptime(due[:10], fmt)
                        days_left = str((dt - datetime.now()).days)
                        break
                    except ValueError:
                        continue

            # Value range display
            val_min = bid.get("estimated_value_min")
            val_max = bid.get("estimated_value_max")
            if val_min and val_max and val_min != val_max:
                value_display = f"${val_min:,.0f} - ${val_max:,.0f}"
            elif val_min:
                value_display = f"${val_min:,.0f}"
            elif val_max:
                value_display = f"${val_max:,.0f}"
            else:
                value_display = ""

            # Location
            loc_parts = [bid.get("location_city", ""), bid.get("location_state", "")]
            location = ", ".join(p for p in loc_parts if p)

            row = [
                bid.get("first_seen_date", datetime.now().strftime("%Y-%m-%d")),
                bid.get("relevance_score", 0),
                bid.get("win_probability", 0),
                bid.get("pipeline_stage", "discovered"),
                bid.get("project_type", ""),
                bid.get("scope_category", ""),
                bid.get("title", ""),
                location,
                value_display,
                "Yes" if bid.get("bonding_required") else "",
                bid.get("due_date", ""),
                days_left,
                bid.get("agency", ""),
                bid.get("set_aside", ""),
                bid.get("source", ""),
                bid.get("contact_email", "") or bid.get("contact_name", ""),
                bid.get("source_url", ""),
            ]
            rows.append(row)
            export_keys.append(f"{bid.get('source', '')}:{bid.get('source_id', '')}")

        # Batch append
        if rows:
            ws.append_rows(rows, value_input_option="USER_ENTERED")
            self.db.mark_exported(export_keys)
            logger.info(f"Exported {len(rows)} opportunities to Google Sheets '{today}' tab")
