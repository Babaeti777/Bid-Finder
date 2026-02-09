"""
OAK BUILDERS LLC - Bid Finder
Main Runner / Orchestrator

Usage:
    python main.py                  # Run all scrapers
    python main.py --source sam_gov # Run specific source
    python main.py --export csv     # Export results
    python main.py --stats          # Show dashboard stats
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


def run_scrapers(sources: list = None, db: BidDatabase = None) -> dict:
    """
    Run all enabled scrapers (or specified ones) and store results.
    Returns a summary dict.
    """
    if db is None:
        db = BidDatabase(OUTPUT["database"])

    if sources is None:
        sources = [k for k, v in SOURCES.items() if v.get("enabled", False)]

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

    for source_key in sources:
        if source_key not in SOURCES:
            print(f"\n[!] Unknown source: {source_key}")
            continue

        source_config = SOURCES[source_key]
        if not source_config.get("enabled", False):
            print(f"\n[~] {source_config['name']}: DISABLED (skipping)")
            continue

        print(f"\n[>] Scraping: {source_config['name']}...")

        try:
            scraper = get_scraper(source_key, source_config)
            results = scraper.scrape()
            print(f"    Found: {len(results)} opportunities")

            all_results.extend(results)
            summary["sources_searched"].append(source_key)
            summary["by_source"][source_key] = len(results)

        except Exception as e:
            error_msg = f"{source_config['name']}: {str(e)}"
            errors.append(error_msg)
            summary["errors"].append(error_msg)
            print(f"    ERROR: {e}")

    # Score all results
    print(f"\n[*] Scoring {len(all_results)} opportunities...")
    scored = score_opportunities(all_results)

    # Store in database
    new_count = 0
    for opp in scored:
        row_id = db.upsert_opportunity(opp)
        if row_id > 0:
            new_count += 1

    # Count by type
    for opp in scored:
        ptype = opp.project_type or "unknown"
        summary["by_type"][ptype] = summary["by_type"].get(ptype, 0) + 1

    duration = time.time() - start_time
    summary["total_found"] = len(scored)
    summary["new_opportunities"] = new_count

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

    args = parser.parse_args()
    db = BidDatabase(args.db)

    try:
        if args.stats:
            show_stats(db)
        elif args.export:
            export_results(db, fmt=args.export, min_score=args.min_score)
        else:
            sources = [args.source] if args.source else None
            run_scrapers(sources=sources, db=db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
