"""
OAK BUILDERS LLC - Bid Finder
Database Models & Schema
"""

import re
import sqlite3
import json
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path

# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class BidOpportunity:
    """Represents a single bid/project opportunity."""

    # Core fields
    title: str
    source: str                      # e.g. "sam_gov", "eva", "fairfax_county"
    source_url: str                  # Direct link to the listing
    source_id: str = ""              # ID from the source system

    # Description & Scope
    description: str = ""
    project_type: str = ""           # waterproofing | tenant_improvement | general | government
    naics_code: str = ""
    category_tags: list = field(default_factory=list)

    # Location
    location_city: str = ""
    location_county: str = ""
    location_state: str = "VA"
    location_zip: str = ""
    location_address: str = ""

    # Financial
    estimated_value_min: Optional[float] = None
    estimated_value_max: Optional[float] = None
    budget_display: str = ""         # As shown on the listing

    # Dates
    posted_date: str = ""
    due_date: str = ""               # Bid submission deadline
    pre_bid_date: str = ""           # Pre-bid meeting date
    project_start_date: str = ""
    project_end_date: str = ""

    # Contacts
    contact_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    agency_name: str = ""

    # Classification
    set_aside: str = ""              # e.g. "8(a)", "SDVOSB", "Small Business"
    contract_type: str = ""          # e.g. "Firm Fixed Price", "IDIQ", "T&M"
    solicitation_type: str = ""      # e.g. "RFP", "IFB", "RFQ"

    # Scoring
    relevance_score: int = 0
    keyword_matches: list = field(default_factory=list)

    # Metadata
    scraped_at: str = ""
    status: str = "new"              # new | reviewed | bid | no_bid | awarded
    notes: str = ""
    attachments: list = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        d["category_tags"] = json.dumps(d["category_tags"])
        d["keyword_matches"] = json.dumps(d["keyword_matches"])
        d["attachments"] = json.dumps(d["attachments"])
        return d

    @classmethod
    def from_dict(cls, d: dict):
        for f in ["category_tags", "keyword_matches", "attachments"]:
            if isinstance(d.get(f), str):
                d[f] = json.loads(d[f])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ============================================================
# DATABASE MANAGER
# ============================================================

class BidDatabase:
    """SQLite database for storing and querying bid opportunities."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS opportunities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        source TEXT NOT NULL,
        source_url TEXT NOT NULL,
        source_id TEXT DEFAULT '',
        description TEXT DEFAULT '',
        project_type TEXT DEFAULT '',
        naics_code TEXT DEFAULT '',
        category_tags TEXT DEFAULT '[]',
        location_city TEXT DEFAULT '',
        location_county TEXT DEFAULT '',
        location_state TEXT DEFAULT 'VA',
        location_zip TEXT DEFAULT '',
        location_address TEXT DEFAULT '',
        estimated_value_min REAL,
        estimated_value_max REAL,
        budget_display TEXT DEFAULT '',
        posted_date TEXT DEFAULT '',
        due_date TEXT DEFAULT '',
        pre_bid_date TEXT DEFAULT '',
        project_start_date TEXT DEFAULT '',
        project_end_date TEXT DEFAULT '',
        contact_name TEXT DEFAULT '',
        contact_email TEXT DEFAULT '',
        contact_phone TEXT DEFAULT '',
        agency_name TEXT DEFAULT '',
        set_aside TEXT DEFAULT '',
        contract_type TEXT DEFAULT '',
        solicitation_type TEXT DEFAULT '',
        relevance_score INTEGER DEFAULT 0,
        keyword_matches TEXT DEFAULT '[]',
        scraped_at TEXT DEFAULT '',
        status TEXT DEFAULT 'new',
        notes TEXT DEFAULT '',
        attachments TEXT DEFAULT '[]',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(source, source_id)
    );

    CREATE INDEX IF NOT EXISTS idx_source ON opportunities(source);
    CREATE INDEX IF NOT EXISTS idx_project_type ON opportunities(project_type);
    CREATE INDEX IF NOT EXISTS idx_location ON opportunities(location_county, location_city);
    CREATE INDEX IF NOT EXISTS idx_due_date ON opportunities(due_date);
    CREATE INDEX IF NOT EXISTS idx_relevance ON opportunities(relevance_score DESC);
    CREATE INDEX IF NOT EXISTS idx_status ON opportunities(status);

    CREATE TABLE IF NOT EXISTS search_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        sources_searched TEXT DEFAULT '[]',
        total_found INTEGER DEFAULT 0,
        new_opportunities INTEGER DEFAULT 0,
        errors TEXT DEFAULT '[]',
        duration_seconds REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS saved_searches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        keywords TEXT DEFAULT '[]',
        locations TEXT DEFAULT '[]',
        project_types TEXT DEFAULT '[]',
        min_value REAL,
        max_value REAL,
        sources TEXT DEFAULT '[]',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS email_sends (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        recipient_count INTEGER DEFAULT 0,
        bid_count INTEGER DEFAULT 0,
        bid_ids TEXT DEFAULT '[]',
        errors TEXT DEFAULT '[]',
        status TEXT DEFAULT 'sent'
    );

    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS sheets_exports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        source_id TEXT NOT NULL,
        exported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(source, source_id)
    );
    """

    def __init__(self, db_path: str = "oak_bids.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        self.conn.executescript(self.SCHEMA)
        self.conn.commit()

    def upsert_opportunity(self, bid: BidOpportunity) -> int:
        """Insert or update a bid opportunity. Returns the row ID."""
        data = bid.to_dict()
        data["updated_at"] = datetime.now().isoformat()
        data["scraped_at"] = data.get("scraped_at") or datetime.now().isoformat()

        try:
            cursor = self.conn.execute("""
                INSERT INTO opportunities ({columns})
                VALUES ({placeholders})
                ON CONFLICT(source, source_id) DO UPDATE SET
                    title=excluded.title,
                    description=excluded.description,
                    due_date=excluded.due_date,
                    relevance_score=excluded.relevance_score,
                    updated_at=excluded.updated_at
            """.format(
                columns=", ".join(data.keys()),
                placeholders=", ".join(["?"] * len(data)),
            ), list(data.values()))
            self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"DB Error: {e}")
            return -1

    def search(
        self,
        project_type: str = None,
        county: str = None,
        city: str = None,
        min_score: int = 0,
        status: str = None,
        due_after: str = None,
        keyword: str = None,
        source: str = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list:
        """Flexible search across stored opportunities."""
        conditions = []
        params = []

        if project_type:
            conditions.append("project_type = ?")
            params.append(project_type)
        if county:
            conditions.append("location_county LIKE ?")
            params.append(f"%{county}%")
        if city:
            conditions.append("location_city LIKE ?")
            params.append(f"%{city}%")
        if min_score > 0:
            conditions.append("relevance_score >= ?")
            params.append(min_score)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if due_after:
            conditions.append("due_date >= ?")
            params.append(due_after)
        if keyword:
            conditions.append("(title LIKE ? OR description LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        if source:
            conditions.append("source = ?")
            params.append(source)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        rows = self.conn.execute(f"""
            SELECT * FROM opportunities
            {where}
            ORDER BY relevance_score DESC, due_date ASC
            LIMIT ? OFFSET ?
        """, params + [limit, offset]).fetchall()

        return [BidOpportunity.from_dict(dict(r)) for r in rows]

    def get_stats(self) -> dict:
        """Dashboard stats summary."""
        stats = {}
        stats["total"] = self.conn.execute(
            "SELECT COUNT(*) FROM opportunities"
        ).fetchone()[0]
        stats["new"] = self.conn.execute(
            "SELECT COUNT(*) FROM opportunities WHERE status = 'new'"
        ).fetchone()[0]
        stats["high_relevance"] = self.conn.execute(
            "SELECT COUNT(*) FROM opportunities WHERE relevance_score >= 70"
        ).fetchone()[0]
        stats["due_this_week"] = self.conn.execute(
            "SELECT COUNT(*) FROM opportunities WHERE due_date BETWEEN date('now') AND date('now', '+7 days')"
        ).fetchone()[0]
        stats["by_type"] = dict(self.conn.execute(
            "SELECT project_type, COUNT(*) FROM opportunities GROUP BY project_type"
        ).fetchall())
        stats["by_source"] = dict(self.conn.execute(
            "SELECT source, COUNT(*) FROM opportunities GROUP BY source"
        ).fetchall())
        stats["by_status"] = dict(self.conn.execute(
            "SELECT status, COUNT(*) FROM opportunities GROUP BY status"
        ).fetchall())
        return stats

    def update_status(self, opp_id: int, status: str, notes: str = ""):
        """Update the status of an opportunity (new/reviewed/bid/no_bid/awarded)."""
        self.conn.execute("""
            UPDATE opportunities
            SET status = ?, notes = ?, updated_at = ?
            WHERE id = ?
        """, [status, notes, datetime.now().isoformat(), opp_id])
        self.conn.commit()

    def log_search_run(self, sources, total, new, errors, duration):
        self.conn.execute("""
            INSERT INTO search_runs (sources_searched, total_found, new_opportunities, errors, duration_seconds)
            VALUES (?, ?, ?, ?, ?)
        """, [json.dumps(sources), total, new, json.dumps(errors), duration])
        self.conn.commit()

    def get_new_since_last_email(self, min_score: int = 0) -> list:
        """Get opportunities created/updated since the last email was sent."""
        last_send = self.conn.execute(
            "SELECT MAX(sent_at) FROM email_sends WHERE status = 'sent'"
        ).fetchone()[0]

        conditions = ["relevance_score >= ?"]
        params = [min_score]

        if last_send:
            conditions.append("(created_at > ? OR updated_at > ?)")
            params.extend([last_send, last_send])

        where = f"WHERE {' AND '.join(conditions)}"
        rows = self.conn.execute(f"""
            SELECT * FROM opportunities
            {where}
            ORDER BY relevance_score DESC
        """, params).fetchall()

        return [BidOpportunity.from_dict(dict(r)) for r in rows]

    def log_email_send(self, recipient_count: int, bid_ids: list, errors: list = None):
        """Record that an email digest was sent."""
        self.conn.execute("""
            INSERT INTO email_sends (recipient_count, bid_count, bid_ids, errors, status)
            VALUES (?, ?, ?, ?, ?)
        """, [
            recipient_count,
            len(bid_ids),
            json.dumps(bid_ids),
            json.dumps(errors or []),
            "sent",
        ])
        self.conn.commit()

    def remove_expired(self) -> int:
        """Remove opportunities whose due_date is in the past.

        Only removes bids with status 'new' (user-reviewed bids are kept).
        Returns the number of rows deleted.
        """
        # due_date is stored as text in various formats; the most common is
        # YYYY-MM-DD which sorts lexicographically.  We handle that plus
        # MM/DD/YYYY by using date('now') comparison for ISO dates, and
        # fetching non-ISO rows for Python-side filtering.
        today = datetime.now().strftime("%Y-%m-%d")

        # 1) Delete ISO-formatted dates that are clearly past due
        cursor = self.conn.execute("""
            DELETE FROM opportunities
            WHERE status = 'new'
              AND due_date != ''
              AND due_date LIKE '____-__-__%'
              AND due_date < ?
        """, [today])
        iso_deleted = cursor.rowcount

        # 2) Handle MM/DD/YYYY and other formats via Python
        rows = self.conn.execute("""
            SELECT id, due_date FROM opportunities
            WHERE status = 'new'
              AND due_date != ''
              AND due_date NOT LIKE '____-__-__%'
        """).fetchall()

        non_iso_ids = []
        for row in rows:
            due_str = row["due_date"]
            for fmt in ["%m/%d/%Y", "%m-%d-%Y"]:
                try:
                    due = datetime.strptime(due_str[:10], fmt)
                    if due.date() < datetime.now().date():
                        non_iso_ids.append(row["id"])
                    break
                except ValueError:
                    continue

        if non_iso_ids:
            for i in range(0, len(non_iso_ids), 100):
                batch = non_iso_ids[i:i + 100]
                placeholders = ",".join("?" * len(batch))
                self.conn.execute(
                    f"DELETE FROM opportunities WHERE id IN ({placeholders})", batch
                )

        self.conn.commit()
        return iso_deleted + len(non_iso_ids)

    # --- Cross-source deduplication ---

    @staticmethod
    def _normalize_title(title: str) -> str:
        """Normalize a title for comparison: lowercase, strip punctuation, collapse whitespace."""
        t = title.lower()
        t = re.sub(r'[^a-z0-9\s]', ' ', t)
        t = re.sub(r'\s+', ' ', t).strip()
        return t

    def deduplicate(self) -> int:
        """Remove cross-source duplicates, keeping the entry with the highest score.
        Returns the number of duplicates removed."""
        rows = self.conn.execute(
            "SELECT id, title, source, relevance_score FROM opportunities ORDER BY relevance_score DESC"
        ).fetchall()

        seen = {}  # normalized_title -> (id, score, source)
        to_delete = []

        for row in rows:
            norm = self._normalize_title(row["title"])
            # Skip very short titles (too generic to dedup)
            if len(norm) < 20:
                continue

            if norm in seen:
                # Keep the one with the higher score (already processed since sorted DESC)
                to_delete.append(row["id"])
            else:
                seen[norm] = (row["id"], row["relevance_score"], row["source"])

        if to_delete:
            # Delete in batches
            for i in range(0, len(to_delete), 100):
                batch = to_delete[i:i+100]
                placeholders = ",".join("?" * len(batch))
                self.conn.execute(
                    f"DELETE FROM opportunities WHERE id IN ({placeholders})", batch
                )
            self.conn.commit()

        return len(to_delete)

    # --- App Settings (persisted in DB, survives container restarts) ---

    def get_setting(self, key: str, default: str = "") -> str:
        row = self.conn.execute(
            "SELECT value FROM app_settings WHERE key = ?", [key]
        ).fetchone()
        return row[0] if row else default

    def set_setting(self, key: str, value: str):
        self.conn.execute(
            "INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            [key, value, datetime.now().isoformat()],
        )
        self.conn.commit()

    def get_all_settings(self) -> dict:
        rows = self.conn.execute("SELECT key, value FROM app_settings").fetchall()
        return {r[0]: r[1] for r in rows}

    def set_all_settings(self, settings: dict):
        now = datetime.now().isoformat()
        for key, value in settings.items():
            self.conn.execute(
                "INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?)"
                " ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                [key, str(value), now],
            )
        self.conn.commit()

    # --- Sheets export tracking (dedup) ---

    def get_exported_keys(self) -> set:
        """Get set of (source, source_id) tuples already exported to Sheets."""
        rows = self.conn.execute("SELECT source, source_id FROM sheets_exports").fetchall()
        return {(r[0], r[1]) for r in rows}

    def mark_exported(self, keys: list):
        """Mark (source, source_id) pairs as exported to Sheets."""
        now = datetime.now().isoformat()
        for source, source_id in keys:
            self.conn.execute(
                "INSERT OR IGNORE INTO sheets_exports (source, source_id, exported_at) VALUES (?, ?, ?)",
                [source, source_id, now],
            )
        self.conn.commit()

    def close(self):
        self.conn.close()


if __name__ == "__main__":
    db = BidDatabase("oak_bids.db")
    print("Database initialized successfully.")
    print(f"Stats: {db.get_stats()}")
    db.close()
