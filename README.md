# OAK Builders LLC — Commercial Project Bid Finder

A Python-based tool that automatically searches, scores, and tracks commercial construction bid opportunities across Northern Virginia (NOVA), the DC metro area, and surrounding regions.

---

## What It Does

This system aggregates bid opportunities from multiple sources into a single searchable database, scores each opportunity based on relevance to OAK Builders' services, and exports results for review. It covers:

- **Government bids** from SAM.gov (federal), eVA (Virginia state), and six NOVA county/city procurement offices
- **Building permits** from Arlington and Fairfax counties to identify upcoming private-sector projects
- **Commercial platforms** like Dodge Construction Network and BuildingConnected (subscription-based)

Each opportunity is automatically scored (0–100) based on keyword relevance, geographic fit, budget range, deadline feasibility, and set-aside eligibility.

---

## Project Structure

```
oak_bid_finder/
├── config.py          # Company profile, keywords, locations, source URLs, scoring weights
├── models.py          # Data models + SQLite database manager
├── scrapers.py        # Web scrapers for each data source
├── scorer.py          # Relevance scoring engine
├── main.py            # CLI runner / orchestrator
├── requirements.txt   # Python dependencies
└── README.md          # This file
```

---

## Quick Start

### 1. Install Dependencies

```bash
cd oak_bid_finder
pip install -r requirements.txt
```

### 2. Configure API Keys (Optional but Recommended)

**SAM.gov API Key** (free): Sign up at [api.data.gov/signup](https://api.data.gov/signup/), then set the key:

```bash
export SAM_GOV_API_KEY=your_key_here
```

### 3. Customize `config.py`

Open `config.py` and fill in:
- Your **CAGE code** and **UEI number** (if SAM-registered)
- **Email addresses** for notifications (optional)
- Enable/disable specific sources as needed
- Adjust **scoring weights** to match your priorities

### 4. Run the Finder

```bash
# Run all enabled scrapers
python main.py

# Run a specific source only
python main.py --source sam_gov

# Export results to CSV
python main.py --export csv

# Export high-scoring results only
python main.py --export csv --min-score 60

# View database statistics
python main.py --stats
```

---

## How Scoring Works

Each opportunity receives a score from 0 to 100 based on five weighted factors:

| Factor              | Max Points | What It Measures                                      |
|---------------------|-----------|-------------------------------------------------------|
| Keyword Match       | 30        | How well the listing matches your services (waterproofing gets a bonus) |
| Location Match      | 25        | Proximity to NOVA — exact city/county match scores highest |
| Budget in Range     | 20        | Whether the project value fits $50K–$2.5M             |
| Deadline Buffer     | 15        | Whether there's adequate time to prepare a bid        |
| Set-Aside Match     | 10        | Whether it's a small business or other favorable set-aside |

You can adjust these weights in `config.py` under the `SCORING` section.

---

## Data Sources

### Government (Enabled by Default)
- **SAM.gov** — Federal opportunities (requires free API key)
- **eVA** — Virginia state procurement
- **Arlington County** — County procurement office
- **Fairfax County** — County procurement office
- **Loudoun County** — County procurement office
- **Prince William County** — County procurement office
- **City of Alexandria** — City procurement office
- **City of Fairfax** — City procurement office

### Commercial (Subscription Required)
- **Dodge Construction Network** — Disabled by default; enable after subscribing
- **BuildingConnected** — Disabled by default; enable after creating account
- **The Blue Book** — Enabled for public listings

### Permits (Enabled by Default)
- **Arlington County Building Permits** — Tracks commercial permits for lead generation
- **Fairfax County Building Permits** — Tracks commercial permits for lead generation

---

## Keyword Coverage

The system searches across four project categories, each with 15–20 targeted keywords:

- **Waterproofing & Water Intrusion** — waterproofing, envelope repair, sealant, flashing, elastomeric coating, etc.
- **Tenant Improvements** — tenant buildout, interior renovation, leasehold improvement, office remodel, etc.
- **General Contracting** — building renovation, ADA compliance, concrete repair, façade repair, etc.
- **Government-Specific** — IDIQ, JOC, task order, set-aside, facility maintenance, etc.

Add or modify keywords in `config.py` under the `KEYWORDS` section.

---

## Recommended Workflow

1. **Daily**: Run `python main.py` to pull new opportunities (consider setting up a cron job or Windows Task Scheduler)
2. **Review**: Export with `python main.py --export csv --min-score 50` and review in Excel
3. **Track**: Update status in the database as you review, bid, or pass on opportunities
4. **Tune**: Adjust scoring weights and keywords based on what wins

---

## Next Steps / Enhancements

- **Email digest**: Configure SMTP settings in `config.py` to receive daily bid alerts
- **Power Automate integration**: Trigger the script from a Power Automate flow for automated scheduling
- **Dashboard UI**: Build a web dashboard (Streamlit or similar) for visual bid tracking
- **Subcontractor matching**: Cross-reference permits with GC contact lists for sub opportunities
- **AI-enhanced scoring**: Use Claude API to analyze full bid documents for deeper relevance scoring

---

## Notes

- County procurement page structures change periodically. If a scraper stops returning results, the CSS selectors in `scrapers.py` may need updating.
- Be respectful of rate limits. The scrapers include built-in delays between requests.
- Some sources (eVA, county sites) may require periodic manual verification since they don't have stable APIs.
- The SAM.gov API is the most reliable automated source. Getting a free API key is highly recommended.
