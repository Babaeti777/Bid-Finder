"""
OAK BUILDERS LLC - Bid Finder
Main Runner / Orchestrator

Usage:
    python main.py                  # Run all scrapers
    python main.py --source sam_gov # Run specific source
    python main.py --export csv     # Export results
    python main.py --stats          # Show dashboard stats
    python main.py --email          # Scrape + send email digest
    python main.py --sheets         # Scrape + update Google Sheet
    python main.py --cloud          # Scrape + email + sheets (for GitHub Actions)
"""

import argparse
import csv
import json
import time
from datetime import datetime
from pathlib import Path

from config import SOURCES, OUTPUT
from models import BidDatabase, BidOpportunity
from scrapers import get_scraper
from scorer import score_opportunities


def _run_scraper_with_retry(source_key, source_config, max_retries=2, backoff=2):
    """Run a single scraper with retry logic. Returns (results, error_msg_or_None)."""
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            scraper = get_scraper(source_key, source_config)
            results = scraper.scrape()
            return results, None
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries:
                wait = backoff * attempt
                print(f"    Retry {attempt}/{max_retries - 1} in {wait}s...")
                time.sleep(wait)

    error_msg = f"{source_config['name']}: {last_error} (failed after {max_retries} attempts)"
    return [], error_msg


def run_scrapers(sources: list = None, db: BidDatabase = None, progress_callback=None) -> dict:
    """
    Run all enabled scrapers (or specified ones) and store results.
    Returns a summary dict.
    progress_callback: optional callable(msg) for live status updates.
    """
    if db is None:
        db = BidDatabase(OUTPUT["database"])

    if sources is None:
        sources = [k for k, v in SOURCES.items() if v.get("enabled", False)]

    def _progress(msg):
        print(msg)
        if progress_callback:
            progress_callback(msg)

    start_time = time.time()
    all_results = []
    errors = []
    summary = {
        "run_date": datetime.now().isoformat(),
        "sources_searched": [],
        "total_found": 0,
        "new_opportunities": 0,
        "by_source": {},
        "by_type": {},
        "errors": [],
    }

    print("=" * 60)
    print(f"  OAK BUILDERS LLC - Bid Finder")
    print(f"  Run Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    enabled_sources = []
    for source_key in sources:
        if source_key not in SOURCES:
            continue
        source_config = SOURCES[source_key]
        if source_config.get("enabled", False):
            enabled_sources.append((source_key, source_config))

    MAX_TOTAL_SECONDS = 420  # Hard cap: entire scan stops after 7 minutes (~60 sources)

    for i, (source_key, source_config) in enumerate(enabled_sources, 1):
        # Abort if total scan time exceeded
        elapsed = time.time() - start_time
        if elapsed > MAX_TOTAL_SECONDS:
            _progress(f"Time limit reached ({MAX_TOTAL_SECONDS}s) - skipping remaining sources")
            remaining = [s[1]["name"] for s in enabled_sources[i-1:]]
            errors.append(f"Skipped due to time limit: {', '.join(remaining)}")
            summary["errors"].append(errors[-1])
            break

        _progress(f"Scanning {source_config['name']} ({i}/{len(enabled_sources)})...")

        results, error_msg = _run_scraper_with_retry(source_key, source_config)
        print(f"    Found: {len(results)} opportunities")
        all_results.extend(results)
        summary["sources_searched"].append(source_key)
        summary["by_source"][source_key] = len(results)

        if error_msg:
            errors.append(error_msg)
            summary["errors"].append(error_msg)
            print(f"    ERROR (after retries): {error_msg}")

    # Score all results
    print(f"\n[*] Scoring {len(all_results)} opportunities...")
    scored = score_opportunities(all_results)

    # Filter out very low-quality results (score < 5 = almost certainly noise)
    MIN_STORE_SCORE = 5
    quality_results = [opp for opp in scored if opp.relevance_score >= MIN_STORE_SCORE]
    discarded = len(scored) - len(quality_results)
    if discarded:
        print(f"    Discarded {discarded} low-quality results (score < {MIN_STORE_SCORE})")

    # Store in database
    new_count = 0
    for opp in quality_results:
        row_id = db.upsert_opportunity(opp)
        if row_id > 0:
            new_count += 1

    # Deduplicate cross-source entries
    dedup_count = db.deduplicate()
    if dedup_count:
        print(f"    Removed {dedup_count} cross-source duplicates")

    # Count by type
    for opp in quality_results:
        ptype = opp.project_type or "unknown"
        summary["by_type"][ptype] = summary["by_type"].get(ptype, 0) + 1

    duration = time.time() - start_time
    summary["total_found"] = len(quality_results) - dedup_count
    summary["new_opportunities"] = max(0, new_count - dedup_count)

    # Log the run
    db.log_search_run(
        sources=summary["sources_searched"],
        total=summary["total_found"],
        new=new_count,
        errors=errors,
        duration=duration,
    )

    # Print summary
    print("\n" + "=" * 60)
    print("  SEARCH COMPLETE")
    print("=" * 60)
    print(f"  Sources searched:    {len(summary['sources_searched'])}")
    print(f"  Total found:         {summary['total_found']}")
    print(f"  New opportunities:   {summary['new_opportunities']}")
    print(f"  Duration:            {duration:.1f}s")

    if summary["by_type"]:
        print(f"\n  By Project Type:")
        for ptype, count in sorted(summary["by_type"].items(), key=lambda x: -x[1]):
            print(f"    {ptype:25s} {count}")

    if errors:
        print(f"\n  Errors ({len(errors)}):")
        for e in errors:
            print(f"    - {e}")

    # Show top opportunities
    top = scored[:10]
    if top:
        print(f"\n  TOP {len(top)} OPPORTUNITIES:")
        print(f"  {'Score':>5}  {'Type':15}  {'Title'}")
        print(f"  {'-'*5}  {'-'*15}  {'-'*40}")
        for opp in top:
            print(f"  {opp.relevance_score:>5}  {opp.project_type:15}  {opp.title[:50]}")

    return summary


def export_results(db: BidDatabase, fmt: str = "csv", min_score: int = 0):
    """Export opportunities to file."""
    results = db.search(min_score=min_score, limit=500)

    if not results:
        print("No results to export.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"oak_bids_{timestamp}.{fmt}"

    if fmt == "csv":
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Score", "Status", "Title", "Source", "Project Type",
                "Location", "Due Date", "Budget", "Agency/Contact",
                "Set-Aside", "URL", "Keywords"
            ])
            for opp in results:
                location = ", ".join(filter(None, [
                    opp.location_city, opp.location_county, opp.location_state
                ]))
                writer.writerow([
                    opp.relevance_score,
                    opp.status,
                    opp.title,
                    opp.source,
                    opp.project_type,
                    location,
                    opp.due_date,
                    opp.budget_display or f"${opp.estimated_value_min:,.0f}-${opp.estimated_value_max:,.0f}" if opp.estimated_value_min else "",
                    f"{opp.agency_name} / {opp.contact_name}".strip(" /"),
                    opp.set_aside,
                    opp.source_url,
                    ", ".join(opp.keyword_matches[:5]),
                ])
        print(f"Exported {len(results)} results to {filename}")

    elif fmt == "json":
        with open(filename, "w", encoding="utf-8") as f:
            json.dump([opp.to_dict() for opp in results], f, indent=2)
        print(f"Exported {len(results)} results to {filename}")


def show_stats(db: BidDatabase):
    """Display database statistics."""
    stats = db.get_stats()
    print("\n" + "=" * 50)
    print("  OAK BUILDERS - Bid Database Stats")
    print("=" * 50)
    print(f"  Total opportunities:  {stats['total']}")
    print(f"  New (unreviewed):     {stats['new']}")
    print(f"  High relevance (70+): {stats['high_relevance']}")
    print(f"  Due this week:        {stats['due_this_week']}")

    if stats["by_type"]:
        print(f"\n  By Type:")
        for t, c in stats["by_type"].items():
            print(f"    {t:25s} {c}")

    if stats["by_source"]:
        print(f"\n  By Source:")
        for s, c in stats["by_source"].items():
            print(f"    {s:25s} {c}")

    if stats["by_status"]:
        print(f"\n  By Status:")
        for s, c in stats["by_status"].items():
            print(f"    {s:25s} {c}")


def main():
    parser = argparse.ArgumentParser(description="OAK Builders Bid Finder")
    parser.add_argument("--source", type=str, help="Run specific source only")
    parser.add_argument("--export", type=str, choices=["csv", "json"], help="Export results")
    parser.add_argument("--stats", action="store_true", help="Show database stats")
    parser.add_argument("--min-score", type=int, default=0, help="Min score filter")
    parser.add_argument("--db", type=str, default=OUTPUT["database"], help="Database path")
    parser.add_argument("--email", action="store_true", help="Send email digest after scraping")
    parser.add_argument("--sheets", action="store_true", help="Update Google Sheet after scraping")
    parser.add_argument("--cloud", action="store_true", help="Cloud mode: scrape + email + sheets")

    args = parser.parse_args()
    db = BidDatabase(args.db)

    try:
        if args.stats:
            show_stats(db)
        elif args.export:
            export_results(db, fmt=args.export, min_score=args.min_score)
        else:
            sources = [args.source] if args.source else None
            summary = run_scrapers(sources=sources, db=db)

            if args.email or args.cloud:
                from email_sender import EmailSender
                print("\n[*] Sending email digest...")
                sender = EmailSender(db)
                sender.send_digest(scraper_errors=summary.get("errors", []))

            if args.sheets or args.cloud:
                from google_sheets import SheetsUpdater
                print("\n[*] Updating Google Sheet...")
                try:
                    updater = SheetsUpdater(db)
                    updater.append_new_bids()
                except ImportError as e:
                    print(f"[Sheets] Skipped: {e}")
                except Exception as e:
                    print(f"[Sheets] Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
