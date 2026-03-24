"""
OAK BUILDERS LLC - Bid Finder v2
Data Models & Database

Changes from v1:
- Added bonding_required, pre_bid_date, pre_bid_mandatory fields
- Added addendum_count, last_addendum_date for tracking changes
- Added win_probability (7-factor model from tracker)
- Added scope_category for core competency matching
- Added competitor_count, is_set_aside_match
- Added source_quality tier tracking
- Added "pipeline_stage" (discovered -> reviewed -> estimating -> bid -> awarded/lost)
- Added first_seen_date for time-to-bid analytics
- Added project_duration_days, square_footage for better scoping
- Improved search with full-text and date-range filters
- Added analytics: conversion funnel, source ROI, response time stats
"""

import sqlite3
import hashlib
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Optional, List


@dataclass
class BidOpportunity:
    """A single bid/project opportunity."""

    # ── Core identification ──
    title: str = ""
    source: str = ""
    source_url: str = ""
    source_id: str = ""

    # ── Description & scope ──
    description: str = ""
    project_type: str = ""       # waterproofing, tenant_improvement, general, civil
    naics_code: str = ""
    category_tags: List[str] = field(default_factory=list)
    scope_category: str = ""     # NEW: core_competency, adjacent, stretch, poor_fit
    square_footage: Optional[int] = None   # NEW
    project_duration_days: Optional[int] = None  # NEW

    # ── Location ──
    location_city: str = ""
    location_county: str = ""
    location_state: str = ""
    location_zip: str = ""
    location_address: str = ""
    distance_miles: Optional[float] = None  # NEW: calculated from Falls Church

    # ── Financial ──
    estimated_value_min: Optional[float] = None
    estimated_value_max: Optional[float] = None
    budget_display: str = ""
    bonding_required: Optional[bool] = None      # NEW
    bonding_amount: Optional[float] = None        # NEW

    # ── Timeline ──
    posted_date: str = ""
    due_date: str = ""
    pre_bid_date: str = ""          # NEW
    pre_bid_mandatory: bool = False  # NEW
    project_start_date: str = ""
    project_end_date: str = ""
    first_seen_date: str = ""       # NEW: when we first discovered it

    # ── Addendums ──
    addendum_count: int = 0          # NEW
    last_addendum_date: str = ""     # NEW

    # ── Contact ──
    contact_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    agency: str = ""
    issuing_office: str = ""         # NEW

    # ── Classification ──
    set_aside: str = ""
    contract_type: str = ""
    solicitation_type: str = ""
    is_set_aside_match: bool = False  # NEW: matches our certs
    competitor_count: Optional[int] = None  # NEW: estimated bidders

    # ── Scoring ──
    relevance_score: int = 0
    win_probability: int = 0         # NEW: 7-factor model
    keyword_matches: List[str] = field(default_factory=list)
    source_quality_tier: int = 0     # NEW: 1=API, 2=portal, 3=aggregator

    # ── Pipeline tracking ──
    status: str = "new"              # new, reviewed, estimating, bid, no_bid, awarded, lost
    pipeline_stage: str = "discovered"  # NEW: discovered -> qualified -> estimating -> submitted -> outcome
    notes: str = ""
    attachments: List[str] = field(default_factory=list)

    @property
    def dedup_key(self) -> str:
        """Generate deduplication key."""
        raw = f"{self.source}:{self.source_id or self.title}".lower().strip()
        return hashlib.md5(raw.encode()).hexdigest()

    @property
    def days_until_due(self) -> Optional[int]:
        """Days remaining until bid is due."""
        if not self.due_date:
            return None
        for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"]:
            try:
                due = datetime.strptime(self.due_date[:10], fmt)
                return (due - datetime.now()).days
            except ValueError:
                continue
        return None

    @property
    def is_expired(self) -> bool:
        """Check if bid deadline has passed."""
        days = self.days_until_due
        return days is not None and days < 0

    @property
    def urgency_level(self) -> str:
        """Urgency classification."""
        days = self.days_until_due
        if days is None:
            return "unknown"
        if days < 0:
            return "expired"
        if days <= 3:
            return "critical"
        if days <= 7:
            return "urgent"
        if days <= 14:
            return "normal"
        return "comfortable"


class BidDatabase:
    """SQLite database for bid opportunities with analytics."""

    def __init__(self, db_path: str = "bids.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS opportunities (
                    dedup_key TEXT PRIMARY KEY,
                    title TEXT,
                    source TEXT,
                    source_url TEXT,
                    source_id TEXT,
                    description TEXT,
                    project_type TEXT,
                    naics_code TEXT,
                    category_tags TEXT,
                    scope_category TEXT,
                    square_footage INTEGER,
                    project_duration_days INTEGER,
                    location_city TEXT,
                    location_county TEXT,
                    location_state TEXT,
                    location_zip TEXT,
                    location_address TEXT,
                    distance_miles REAL,
                    estimated_value_min REAL,
                    estimated_value_max REAL,
                    budget_display TEXT,
                    bonding_required INTEGER,
                    bonding_amount REAL,
                    posted_date TEXT,
                    due_date TEXT,
                    pre_bid_date TEXT,
                    pre_bid_mandatory INTEGER DEFAULT 0,
                    project_start_date TEXT,
                    project_end_date TEXT,
                    first_seen_date TEXT,
                    addendum_count INTEGER DEFAULT 0,
                    last_addendum_date TEXT,
                    contact_name TEXT,
                    contact_email TEXT,
                    contact_phone TEXT,
                    agency TEXT,
                    issuing_office TEXT,
                    set_aside TEXT,
                    contract_type TEXT,
                    solicitation_type TEXT,
                    is_set_aside_match INTEGER DEFAULT 0,
                    competitor_count INTEGER,
                    relevance_score INTEGER DEFAULT 0,
                    win_probability INTEGER DEFAULT 0,
                    keyword_matches TEXT,
                    source_quality_tier INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'new',
                    pipeline_stage TEXT DEFAULT 'discovered',
                    notes TEXT,
                    attachments TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS search_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_date TEXT DEFAULT (datetime('now')),
                    sources_attempted INTEGER DEFAULT 0,
                    sources_succeeded INTEGER DEFAULT 0,
                    opportunities_found INTEGER DEFAULT 0,
                    opportunities_new INTEGER DEFAULT 0,
                    opportunities_updated INTEGER DEFAULT 0,
                    errors TEXT,
                    duration_seconds REAL
                );

                CREATE TABLE IF NOT EXISTS pipeline_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dedup_key TEXT,
                    old_stage TEXT,
                    new_stage TEXT,
                    changed_at TEXT DEFAULT (datetime('now')),
                    changed_by TEXT DEFAULT 'system',
                    notes TEXT,
                    FOREIGN KEY (dedup_key) REFERENCES opportunities(dedup_key)
                );

                CREATE TABLE IF NOT EXISTS source_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT,
                    run_date TEXT DEFAULT (date('now')),
                    opportunities_found INTEGER DEFAULT 0,
                    high_relevance_count INTEGER DEFAULT 0,
                    errors INTEGER DEFAULT 0,
                    duration_seconds REAL,
                    http_status INTEGER
                );

                CREATE TABLE IF NOT EXISTS email_sends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sent_at TEXT DEFAULT (datetime('now')),
                    recipient_count INTEGER,
                    opportunity_count INTEGER,
                    opportunity_keys TEXT
                );

                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS sheets_exports (
                    source_and_id TEXT PRIMARY KEY,
                    exported_at TEXT DEFAULT (datetime('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_opp_status ON opportunities(status);
                CREATE INDEX IF NOT EXISTS idx_opp_score ON opportunities(relevance_score);
                CREATE INDEX IF NOT EXISTS idx_opp_due ON opportunities(due_date);
                CREATE INDEX IF NOT EXISTS idx_opp_source ON opportunities(source);
                CREATE INDEX IF NOT EXISTS idx_opp_pipeline ON opportunities(pipeline_stage);
                CREATE INDEX IF NOT EXISTS idx_opp_first_seen ON opportunities(first_seen_date);
            """)

    def upsert_opportunity(self, bid: BidOpportunity) -> str:
        """Insert or update an opportunity. Returns 'new' or 'updated'."""
        key = bid.dedup_key
        if not bid.first_seen_date:
            bid.first_seen_date = datetime.now().strftime("%Y-%m-%d")

        with sqlite3.connect(self.db_path) as conn:
            existing = conn.execute(
                "SELECT dedup_key, status, pipeline_stage, notes, first_seen_date "
                "FROM opportunities WHERE dedup_key = ?",
                (key,)
            ).fetchone()

            if existing:
                # Preserve user-set fields
                old_status = existing[1]
                old_stage = existing[2]
                old_notes = existing[3]
                old_first_seen = existing[4]

                # Don't overwrite user decisions
                if old_status not in ("new",):
                    bid.status = old_status
                if old_stage not in ("discovered",):
                    bid.pipeline_stage = old_stage
                if old_notes:
                    bid.notes = old_notes
                if old_first_seen:
                    bid.first_seen_date = old_first_seen

                conn.execute("""
                    UPDATE opportunities SET
                        title=?, description=?, project_type=?, naics_code=?,
                        category_tags=?, scope_category=?, square_footage=?,
                        project_duration_days=?,
                        location_city=?, location_county=?, location_state=?,
                        location_zip=?, location_address=?, distance_miles=?,
                        estimated_value_min=?, estimated_value_max=?, budget_display=?,
                        bonding_required=?, bonding_amount=?,
                        posted_date=?, due_date=?, pre_bid_date=?,
                        pre_bid_mandatory=?, project_start_date=?, project_end_date=?,
                        first_seen_date=?,
                        addendum_count=?, last_addendum_date=?,
                        contact_name=?, contact_email=?, contact_phone=?,
                        agency=?, issuing_office=?,
                        set_aside=?, contract_type=?, solicitation_type=?,
                        is_set_aside_match=?, competitor_count=?,
                        relevance_score=?, win_probability=?,
                        keyword_matches=?, source_quality_tier=?,
                        status=?, pipeline_stage=?, notes=?,
                        attachments=?,
                        updated_at=datetime('now')
                    WHERE dedup_key=?
                """, (
                    bid.title, bid.description, bid.project_type, bid.naics_code,
                    json.dumps(bid.category_tags), bid.scope_category,
                    bid.square_footage, bid.project_duration_days,
                    bid.location_city, bid.location_county, bid.location_state,
                    bid.location_zip, bid.location_address, bid.distance_miles,
                    bid.estimated_value_min, bid.estimated_value_max,
                    bid.budget_display,
                    1 if bid.bonding_required else 0, bid.bonding_amount,
                    bid.posted_date, bid.due_date, bid.pre_bid_date,
                    1 if bid.pre_bid_mandatory else 0,
                    bid.project_start_date, bid.project_end_date,
                    bid.first_seen_date,
                    bid.addendum_count, bid.last_addendum_date,
                    bid.contact_name, bid.contact_email, bid.contact_phone,
                    bid.agency, bid.issuing_office,
                    bid.set_aside, bid.contract_type, bid.solicitation_type,
                    1 if bid.is_set_aside_match else 0, bid.competitor_count,
                    bid.relevance_score, bid.win_probability,
                    json.dumps(bid.keyword_matches), bid.source_quality_tier,
                    bid.status, bid.pipeline_stage, bid.notes,
                    json.dumps(bid.attachments),
                    key,
                ))
                return "updated"
            else:
                conn.execute("""
                    INSERT INTO opportunities (
                        dedup_key, title, source, source_url, source_id,
                        description, project_type, naics_code,
                        category_tags, scope_category, square_footage,
                        project_duration_days,
                        location_city, location_county, location_state,
                        location_zip, location_address, distance_miles,
                        estimated_value_min, estimated_value_max, budget_display,
                        bonding_required, bonding_amount,
                        posted_date, due_date, pre_bid_date,
                        pre_bid_mandatory, project_start_date, project_end_date,
                        first_seen_date,
                        addendum_count, last_addendum_date,
                        contact_name, contact_email, contact_phone,
                        agency, issuing_office,
                        set_aside, contract_type, solicitation_type,
                        is_set_aside_match, competitor_count,
                        relevance_score, win_probability,
                        keyword_matches, source_quality_tier,
                        status, pipeline_stage, notes, attachments
                    ) VALUES (
                        ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
                    )
                """, (
                    key, bid.title, bid.source, bid.source_url, bid.source_id,
                    bid.description, bid.project_type, bid.naics_code,
                    json.dumps(bid.category_tags), bid.scope_category,
                    bid.square_footage, bid.project_duration_days,
                    bid.location_city, bid.location_county, bid.location_state,
                    bid.location_zip, bid.location_address, bid.distance_miles,
                    bid.estimated_value_min, bid.estimated_value_max,
                    bid.budget_display,
                    1 if bid.bonding_required else 0, bid.bonding_amount,
                    bid.posted_date, bid.due_date, bid.pre_bid_date,
                    1 if bid.pre_bid_mandatory else 0,
                    bid.project_start_date, bid.project_end_date,
                    bid.first_seen_date,
                    bid.addendum_count, bid.last_addendum_date,
                    bid.contact_name, bid.contact_email, bid.contact_phone,
                    bid.agency, bid.issuing_office,
                    bid.set_aside, bid.contract_type, bid.solicitation_type,
                    1 if bid.is_set_aside_match else 0, bid.competitor_count,
                    bid.relevance_score, bid.win_probability,
                    json.dumps(bid.keyword_matches), bid.source_quality_tier,
                    bid.status, bid.pipeline_stage, bid.notes,
                    json.dumps(bid.attachments),
                ))

                # Log pipeline history
                conn.execute(
                    "INSERT INTO pipeline_history (dedup_key, old_stage, new_stage, notes) "
                    "VALUES (?, '', 'discovered', 'First seen')",
                    (key,)
                )
                return "new"

    def update_pipeline_stage(self, dedup_key: str, new_stage: str,
                              notes: str = "", changed_by: str = "user"):
        """Move an opportunity through the pipeline with history tracking."""
        with sqlite3.connect(self.db_path) as conn:
            old = conn.execute(
                "SELECT pipeline_stage FROM opportunities WHERE dedup_key = ?",
                (dedup_key,)
            ).fetchone()
            if old:
                conn.execute(
                    "UPDATE opportunities SET pipeline_stage=?, updated_at=datetime('now') "
                    "WHERE dedup_key=?",
                    (new_stage, dedup_key)
                )
                conn.execute(
                    "INSERT INTO pipeline_history (dedup_key, old_stage, new_stage, changed_by, notes) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (dedup_key, old[0], new_stage, changed_by, notes)
                )

    def log_source_performance(self, source: str, found: int,
                                high_rel: int, errors: int,
                                duration: float, http_status: int = 200):
        """Track per-source performance over time."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO source_performance "
                "(source, opportunities_found, high_relevance_count, errors, duration_seconds, http_status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (source, found, high_rel, errors, duration, http_status)
            )

    def search(self, project_type: str = None, location: str = None,
               min_score: int = 0, status: str = None,
               pipeline_stage: str = None,
               due_before: str = None, due_after: str = None,
               keyword: str = None, source: str = None,
               min_win_prob: int = 0,
               show_expired: bool = False,
               limit: int = 200, offset: int = 0) -> List[dict]:
        """Flexible search with all the new fields."""
        conditions = []
        params = []

        if project_type:
            conditions.append("project_type = ?")
            params.append(project_type)
        if location:
            conditions.append(
                "(location_city LIKE ? OR location_county LIKE ? "
                "OR location_state LIKE ? OR location_zip LIKE ?)"
            )
            params.extend([f"%{location}%"] * 4)
        if min_score > 0:
            conditions.append("relevance_score >= ?")
            params.append(min_score)
        if min_win_prob > 0:
            conditions.append("win_probability >= ?")
            params.append(min_win_prob)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if pipeline_stage:
            conditions.append("pipeline_stage = ?")
            params.append(pipeline_stage)
        if due_before:
            conditions.append("due_date <= ?")
            params.append(due_before)
        if due_after:
            conditions.append("due_date >= ?")
            params.append(due_after)
        if keyword:
            conditions.append(
                "(title LIKE ? OR description LIKE ? OR keyword_matches LIKE ?)"
            )
            params.extend([f"%{keyword}%"] * 3)
        if source:
            conditions.append("source = ?")
            params.append(source)
        if not show_expired:
            conditions.append(
                "(due_date IS NULL OR due_date = '' OR due_date >= date('now'))"
            )

        where = " AND ".join(conditions) if conditions else "1=1"
        query = f"""
            SELECT * FROM opportunities
            WHERE {where}
            ORDER BY relevance_score DESC, due_date ASC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        """Comprehensive analytics dashboard data."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
            active = conn.execute(
                "SELECT COUNT(*) FROM opportunities "
                "WHERE (due_date IS NULL OR due_date >= date('now')) "
                "AND status NOT IN ('no_bid', 'lost')"
            ).fetchone()[0]
            new_today = conn.execute(
                "SELECT COUNT(*) FROM opportunities "
                "WHERE first_seen_date = date('now')"
            ).fetchone()[0]
            high_score = conn.execute(
                "SELECT COUNT(*) FROM opportunities "
                "WHERE relevance_score >= 70 AND "
                "(due_date IS NULL OR due_date >= date('now'))"
            ).fetchone()[0]
            due_this_week = conn.execute(
                "SELECT COUNT(*) FROM opportunities "
                "WHERE due_date BETWEEN date('now') AND date('now', '+7 days') "
                "AND status NOT IN ('no_bid', 'lost', 'awarded')"
            ).fetchone()[0]

            # Pipeline funnel
            pipeline = {}
            for row in conn.execute(
                "SELECT pipeline_stage, COUNT(*) FROM opportunities "
                "WHERE (due_date IS NULL OR due_date >= date('now')) "
                "GROUP BY pipeline_stage"
            ).fetchall():
                pipeline[row[0]] = row[1]

            # By source
            by_source = {}
            for row in conn.execute(
                "SELECT source, COUNT(*), AVG(relevance_score) "
                "FROM opportunities GROUP BY source"
            ).fetchall():
                by_source[row[0]] = {"count": row[1], "avg_score": round(row[2] or 0, 1)}

            # By project type
            by_type = {}
            for row in conn.execute(
                "SELECT project_type, COUNT(*) FROM opportunities "
                "WHERE project_type != '' GROUP BY project_type"
            ).fetchall():
                by_type[row[0]] = row[1]

            # Source performance (last 7 days)
            source_perf = {}
            for row in conn.execute(
                "SELECT source, SUM(opportunities_found), SUM(high_relevance_count), "
                "SUM(errors), AVG(duration_seconds) "
                "FROM source_performance "
                "WHERE run_date >= date('now', '-7 days') "
                "GROUP BY source"
            ).fetchall():
                source_perf[row[0]] = {
                    "total_found": row[1],
                    "high_relevance": row[2],
                    "errors": row[3],
                    "avg_duration": round(row[4] or 0, 1),
                }

            return {
                "total": total,
                "active": active,
                "new_today": new_today,
                "high_relevance": high_score,
                "due_this_week": due_this_week,
                "pipeline": pipeline,
                "by_source": by_source,
                "by_type": by_type,
                "source_performance": source_perf,
            }

    def get_conversion_funnel(self) -> dict:
        """Track discovered -> qualified -> bid -> won conversion rates."""
        with sqlite3.connect(self.db_path) as conn:
            stages = ["discovered", "qualified", "estimating", "submitted", "awarded", "lost"]
            funnel = {}
            for stage in stages:
                count = conn.execute(
                    "SELECT COUNT(*) FROM pipeline_history WHERE new_stage = ?",
                    (stage,)
                ).fetchone()[0]
                funnel[stage] = count
            return funnel

    def get_new_since_last_email(self) -> List[dict]:
        """Get opportunities added since last email send."""
        with sqlite3.connect(self.db_path) as conn:
            last_send = conn.execute(
                "SELECT sent_at FROM email_sends ORDER BY sent_at DESC LIMIT 1"
            ).fetchone()
            cutoff = last_send[0] if last_send else "2000-01-01"
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM opportunities "
                "WHERE created_at > ? AND (due_date IS NULL OR due_date >= date('now')) "
                "ORDER BY relevance_score DESC",
                (cutoff,)
            ).fetchall()
            return [dict(r) for r in rows]

    def log_email_send(self, recipients: int, opp_keys: List[str]):
        """Record an email send event."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO email_sends (recipient_count, opportunity_count, opportunity_keys) "
                "VALUES (?, ?, ?)",
                (recipients, len(opp_keys), json.dumps(opp_keys))
            )

    def remove_expired(self, days_past: int = 30):
        """Archive opportunities expired more than N days ago."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM opportunities "
                "WHERE due_date < date('now', ? || ' days') "
                "AND status IN ('new', 'reviewed')",
                (f"-{days_past}",)
            )

    def get_setting(self, key: str, default: str = "") -> str:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT value FROM app_settings WHERE key = ?", (key,)
            ).fetchone()
            return row[0] if row else default

    def set_setting(self, key: str, value: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO app_settings (key, value, updated_at) "
                "VALUES (?, ?, datetime('now'))",
                (key, value)
            )

    def get_exported_keys(self) -> set:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT source_and_id FROM sheets_exports").fetchall()
            return {r[0] for r in rows}

    def mark_exported(self, keys: List[str]):
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO sheets_exports (source_and_id) VALUES (?)",
                [(k,) for k in keys]
            )
