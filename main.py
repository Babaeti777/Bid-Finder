#!/usr/bin/env python3
"""
OAK BUILDERS LLC - Bid Finder v2
Main orchestrator — scrape, score, store, notify

Changes from v1:
- Tracks source performance per-run for ROI analysis
- Better dedup across sources (title similarity + location match)
- Trend reporting: new opportunities per day/week
- Win probability calculated alongside relevance score
- Pipeline stage auto-assignment based on score thresholds
- Summary includes commercial vs. government breakdown
- JSON export with full metadata
- Retry logic distinguishes transient vs. permanent failures
"""

import argparse
import csv
import json
import logging
import sys
import time
from datetime import datetime, timedelta
from difflib import SequenceMatcher

from config import (
    SOURCES, MIN_RELEVANCE_SCORE, DATABASE_FILE,
    SCRAPER_TIMEOUT, RETRY_ATTEMPTS, RETRY_BACKOFF,
    EMAIL, SHEETS,
)
from models import BidOpportunity, BidDatabase
from scorer import score_opportunities, RelevanceScorer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("bid-finder")


# ─── Scraper registry ──────────────────────────────────────────────
def get_scraper(source_key: str):
    """Import and return the scraper class for a source."""
    from scrapers import (
        SamGovScraper, DcOcpScraper, MontgomeryCountyScraper,
        EvaScraper, CountyScraper, BidNetScraper,
        OpenGovScraper, PermitScraper, PlanHubScraper,
        EmmaScraper,
    )

    SCRAPER_MAP = {
        "sam_gov": SamGovScraper,
        "dc_ocp": DcOcpScraper,
        "montgomery_county": MontgomeryCountyScraper,
        "eva_virginia": EvaScraper,
        "emma_maryland": EmmaScraper,
        "arlington_county": lambda: CountyScraper("arlington_county"),
        "fairfax_county": lambda: CountyScraper("fairfax_county"),
        "loudoun_county": lambda: CountyScraper("loudoun_county"),
        "prince_william_county": lambda: CountyScraper("prince_william_county"),
        "alexandria_city": lambda: CountyScraper("alexandria_city"),
        "fairfax_city": lambda: CountyScraper("fairfax_city"),
        "prince_georges_county": lambda: CountyScraper("prince_georges_county"),
        "howard_county": lambda: CountyScraper("howard_county"),
        "anne_arundel_county": lambda: CountyScraper("anne_arundel_county"),
        "planhub": PlanHubScraper,
        "bidnet": BidNetScraper,
        "opengov": OpenGovScraper,
        "gmu": lambda: CountyScraper("gmu"),
        "umd": lambda: CountyScraper("umd"),
        "arlington_permits": lambda: PermitScraper("arlington_permits"),
        "fairfax_permits": lambda: PermitScraper("fairfax_permits"),
    }

    factory = SCRAPER_MAP.get(source_key)
    if factory is None:
        return None
    return factory() if callable(factory) else factory


def is_permanent_failure(error: Exception) -> bool:
    """Check if an error is permanent (don't retry)."""
    err_str = str(error).lower()
    permanent_indicators = ["403", "404", "401", "not found", "forbidden", "unauthorized"]
    return any(ind in err_str for ind in permanent_indicators)


# ─── Cross-source deduplication ─────────────────────────────────────
def fuzzy_dedup(opportunities: list, threshold: float = 0.85) -> list:
    """Remove near-duplicate listings across different sources."""
    seen = []
    unique = []

    for opp in opportunities:
        title_lower = opp.title.lower().strip()
        is_dup = False

        for seen_title, seen_loc in seen:
            # Title similarity
            similarity = SequenceMatcher(None, title_lower, seen_title).ratio()
            if similarity >= threshold:
                # Same location too? Definitely a dup.
                loc = (opp.location_city or "").lower()
                if loc == seen_loc or not loc or not seen_loc:
                    is_dup = True
                    break

        if not is_dup:
            unique.append(opp)
            seen.append((title_lower, (opp.location_city or "").lower()))

    dedup_count = len(opportunities) - len(unique)
    if dedup_count > 0:
        logger.info(f"Fuzzy dedup removed {dedup_count} near-duplicates")

    return unique


# ─── Pipeline auto-classification ───────────────────────────────────
def auto_classify_pipeline(opp: BidOpportunity):
    """Set initial pipeline stage based on score + urgency."""
    if opp.relevance_score >= 70 and opp.win_probability >= 50:
        opp.pipeline_stage = "qualified"
    elif opp.relevance_score >= 50:
        opp.pipeline_stage = "discovered"
    else:
        opp.pipeline_stage = "discovered"


# ─── Main scraping run ──────────────────────────────────────────────
def run_scrapers(source_filter: str = None, progress_callback=None):
    """Execute all enabled scrapers and return results."""
    db = BidDatabase(DATABASE_FILE)
    all_opportunities = []
    errors = []
    run_start = time.time()

    sources_to_run = {}
    for key, cfg in SOURCES.items():
        if not cfg.get("enabled", False):
            continue
        if source_filter and key != source_filter:
            continue
        sources_to_run[key] = cfg

    total_sources = len(sources_to_run)
    logger.info(f"Running {total_sources} scrapers...")

    for idx, (source_key, source_cfg) in enumerate(sources_to_run.items()):
        source_name = source_cfg.get("name", source_key)
        source_start = time.time()
        source_errors = 0
        found_count = 0
        high_rel_count = 0

        if progress_callback:
            progress_callback(idx, total_sources, source_name)

        logger.info(f"[{idx+1}/{total_sources}] Scraping {source_name}...")

        scraper = get_scraper(source_key)
        if scraper is None:
            logger.warning(f"No scraper implemented for {source_key}, skipping")
            continue

        # Retry loop
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                results = scraper.scrape()
                found_count = len(results)

                # Tag source quality tier
                tier = source_cfg.get("tier", 9)
                for r in results:
                    r.source_quality_tier = tier

                all_opportunities.extend(results)
                logger.info(f"  -> {source_name}: {found_count} opportunities")
                break

            except Exception as e:
                source_errors += 1
                if is_permanent_failure(e):
                    logger.error(f"  -> {source_name}: permanent failure: {e}")
                    errors.append({"source": source_name, "error": str(e), "type": "permanent"})
                    break
                elif attempt < RETRY_ATTEMPTS:
                    logger.warning(f"  -> {source_name}: attempt {attempt} failed: {e}, retrying...")
                    time.sleep(RETRY_BACKOFF * attempt)
                else:
                    logger.error(f"  -> {source_name}: failed after {RETRY_ATTEMPTS} attempts: {e}")
                    errors.append({"source": source_name, "error": str(e), "type": "transient"})

        source_duration = time.time() - source_start

        # Score what we found so far to count high-relevance
        if found_count > 0:
            scorer = RelevanceScorer()
            for opp in results:
                if opp.relevance_score == 0:
                    opp.relevance_score = scorer.score(opp)
                if opp.relevance_score >= 70:
                    high_rel_count += 1

        # Log source performance
        db.log_source_performance(
            source=source_key,
            found=found_count,
            high_rel=high_rel_count,
            errors=source_errors,
            duration=source_duration,
        )

    # ── Post-processing pipeline ────────────────────────────────────
    logger.info(f"Total raw results: {len(all_opportunities)}")

    # 1. Score all opportunities
    all_opportunities = score_opportunities(all_opportunities)

    # 2. Filter by minimum relevance
    qualified = [o for o in all_opportunities if o.relevance_score >= MIN_RELEVANCE_SCORE]
    logger.info(f"After relevance filter (>={MIN_RELEVANCE_SCORE}): {qualified}")

    # 3. Remove expired
    active = [o for o in qualified if not o.is_expired]
    logger.info(f"After expiration filter: {len(active)}")

    # 4. Fuzzy dedup across sources
    deduped = fuzzy_dedup(active)
    logger.info(f"After deduplication: {len(deduped)}")

    # 5. Auto-classify pipeline stage
    for opp in deduped:
        auto_classify_pipeline(opp)

    # 6. Persist to database
    new_count = 0
    updated_count = 0
    for opp in deduped:
        result = db.upsert_opportunity(opp)
        if result == "new":
            new_count += 1
        else:
            updated_count += 1

    # 7. Log the run
    run_duration = time.time() - run_start
    with db._init_db.__func__(db) if False else open(os.devnull, 'w'):
        pass  # Just need the db connection
    import sqlite3
    with sqlite3.connect(DATABASE_FILE) as conn:
        conn.execute(
            "INSERT INTO search_runs "
            "(sources_attempted, sources_succeeded, opportunities_found, "
            "opportunities_new, opportunities_updated, errors, duration_seconds) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                total_sources,
                total_sources - len(errors),
                len(deduped),
                new_count,
                updated_count,
                json.dumps(errors),
                run_duration,
            )
        )

    logger.info(
        f"Run complete in {run_duration:.1f}s: "
        f"{len(deduped)} opportunities ({new_count} new, {updated_count} updated), "
        f"{len(errors)} source errors"
    )

    return {
        "total": len(deduped),
        "new": new_count,
        "updated": updated_count,
        "errors": errors,
        "duration": run_duration,
        "opportunities": deduped,
    }


# ─── Export functions ───────────────────────────────────────────────
def export_csv(output_file: str = "bids_export.csv", min_score: int = 0):
    """Export opportunities to CSV."""
    db = BidDatabase(DATABASE_FILE)
    bids = db.search(min_score=min_score, show_expired=False, limit=1000)

    if not bids:
        logger.info("No opportunities to export.")
        return

    fieldnames = [
        "title", "source", "source_url", "project_type", "scope_category",
        "relevance_score", "win_probability", "pipeline_stage",
        "location_city", "location_county", "location_state", "location_zip",
        "estimated_value_min", "estimated_value_max", "budget_display",
        "bonding_required",
        "posted_date", "due_date", "pre_bid_date", "pre_bid_mandatory",
        "agency", "contact_name", "contact_email", "contact_phone",
        "set_aside", "is_set_aside_match",
        "status", "notes", "description",
    ]

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(bids)

    logger.info(f"Exported {len(bids)} opportunities to {output_file}")


def export_json(output_file: str = "bids_export.json", min_score: int = 0):
    """Export to JSON with full metadata."""
    db = BidDatabase(DATABASE_FILE)
    bids = db.search(min_score=min_score, show_expired=False, limit=1000)
    stats = db.get_stats()

    output = {
        "exported_at": datetime.now().isoformat(),
        "stats": stats,
        "opportunities": bids,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    logger.info(f"Exported {len(bids)} opportunities to {output_file}")


def print_stats():
    """Print database statistics."""
    db = BidDatabase(DATABASE_FILE)
    stats = db.get_stats()
    funnel = db.get_conversion_funnel()

    print("\n" + "=" * 60)
    print("  OAK BUILDERS - BID FINDER STATISTICS")
    print("=" * 60)
    print(f"\n  Total opportunities:    {stats['total']}")
    print(f"  Active (not expired):   {stats['active']}")
    print(f"  New today:              {stats['new_today']}")
    print(f"  High relevance (70+):   {stats['high_relevance']}")
    print(f"  Due this week:          {stats['due_this_week']}")

    if stats.get("pipeline"):
        print(f"\n  Pipeline:")
        for stage, count in stats["pipeline"].items():
            print(f"    {stage:20s}  {count}")

    if stats.get("by_type"):
        print(f"\n  By project type:")
        for ptype, count in stats["by_type"].items():
            print(f"    {ptype:25s}  {count}")

    if stats.get("by_source"):
        print(f"\n  By source:")
        for source, data in stats["by_source"].items():
            print(f"    {source:25s}  {data['count']:3d}  (avg score: {data['avg_score']})")

    if stats.get("source_performance"):
        print(f"\n  Source performance (7 days):")
        for source, perf in stats["source_performance"].items():
            print(
                f"    {source:25s}  found: {perf['total_found']:3d}  "
                f"high: {perf['high_relevance']:2d}  "
                f"errors: {perf['errors']:2d}  "
                f"avg: {perf['avg_duration']:.1f}s"
            )

    if any(funnel.values()):
        print(f"\n  Conversion funnel:")
        for stage, count in funnel.items():
            bar = "█" * min(count, 40)
            print(f"    {stage:15s}  {count:4d}  {bar}")

    print()


# ─── CLI ────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="OAK Builders Bid Finder v2")
    parser.add_argument("--source", help="Run only one source")
    parser.add_argument("--export-csv", nargs="?", const="bids_export.csv",
                        help="Export to CSV")
    parser.add_argument("--export-json", nargs="?", const="bids_export.json",
                        help="Export to JSON")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--email", action="store_true", help="Send email digest")
    parser.add_argument("--sheets", action="store_true", help="Update Google Sheets")
    parser.add_argument("--min-score", type=int, default=0,
                        help="Minimum relevance score for exports")

    args = parser.parse_args()

    if args.stats:
        print_stats()
        return

    if args.export_csv:
        export_csv(args.export_csv, args.min_score)
        return

    if args.export_json:
        export_json(args.export_json, args.min_score)
        return

    # Run scrapers
    result = run_scrapers(source_filter=args.source)

    # Send email if requested
    if args.email and EMAIL.get("enabled"):
        try:
            from email_sender import EmailSender
            sender = EmailSender()
            sender.send_digest(result.get("errors", []))
            logger.info("Email digest sent.")
        except Exception as e:
            logger.error(f"Email failed: {e}")

    # Update Google Sheets if requested
    if args.sheets and SHEETS.get("enabled"):
        try:
            from google_sheets import SheetsUpdater
            updater = SheetsUpdater()
            updater.update()
            logger.info("Google Sheets updated.")
        except Exception as e:
            logger.error(f"Sheets update failed: {e}")

    # Always print stats at the end
    print_stats()


if __name__ == "__main__":
    import os
    main()
