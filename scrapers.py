"""
OAK BUILDERS LLC - Bid Finder
Web Scrapers for Each Data Source
"""

import os
import re
import json
import time
import hashlib
from datetime import datetime
from abc import ABC, abstractmethod
from typing import List
from urllib.parse import urljoin, urlencode

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Install dependencies: pip install requests beautifulsoup4 lxml")
    raise

from models import BidOpportunity
from config import KEYWORDS, LOCATIONS, COMPANY


# ============================================================
# BASE SCRAPER
# ============================================================

class BaseScraper(ABC):
    """Base class for all bid source scrapers."""

    def __init__(self, source_key: str, source_config: dict):
        self.source_key = source_key
        self.config = source_config
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "OAKBuilders-BidFinder/1.0 (Commercial Construction Research)"
        })
        self.results: List[BidOpportunity] = []

    @abstractmethod
    def scrape(self) -> List[BidOpportunity]:
        """Scrape and return bid opportunities."""
        pass

    def _generate_source_id(self, *parts):
        """Generate a unique source_id from parts of the listing."""
        raw = "|".join(str(p) for p in parts)
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text).strip()

    def _parse_value(self, text: str) -> tuple:
        """Extract min/max dollar values from text like '$50,000 - $100,000'."""
        if not text:
            return None, None
        amounts = re.findall(r'\$[\d,]+(?:\.\d{2})?', text)
        amounts = [float(a.replace('$', '').replace(',', '')) for a in amounts]
        if len(amounts) >= 2:
            return min(amounts), max(amounts)
        elif len(amounts) == 1:
            return amounts[0], amounts[0]
        return None, None

    def _match_keywords(self, text: str) -> tuple:
        """Score text against keyword lists. Returns (project_type, matched_keywords)."""
        text_lower = text.lower()
        best_type = "general"
        best_count = 0
        all_matches = []

        for ptype, keywords in KEYWORDS.items():
            matches = [kw for kw in keywords if kw.lower() in text_lower]
            all_matches.extend(matches)
            if len(matches) > best_count:
                best_count = len(matches)
                best_type = ptype

        return best_type, list(set(all_matches))

    def _match_location(self, text: str) -> dict:
        """Try to extract NOVA location info from text."""
        text_lower = text.lower()
        result = {"city": "", "county": "", "state": "VA"}

        for city in LOCATIONS["cities"]:
            if city.lower() in text_lower:
                result["city"] = city
                break

        for county in LOCATIONS["counties"]:
            if county.lower().replace(" county", "") in text_lower:
                result["county"] = county
                break

        zip_match = re.search(r'\b(2[012]\d{3})\b', text)
        if zip_match:
            result["zip"] = zip_match.group(1)

        if "washington" in text_lower or " dc " in text_lower or "d.c." in text_lower:
            result["state"] = "DC"
        elif "maryland" in text_lower or " md " in text_lower:
            result["state"] = "MD"

        return result


# ============================================================
# SAM.GOV SCRAPER (Federal Opportunities)
# ============================================================

class SAMGovScraper(BaseScraper):
    """
    Scrapes SAM.gov for federal contract opportunities.
    Uses the public API (requires free API key from api.data.gov).

    To get an API key: https://api.data.gov/signup/
    Set environment variable: SAM_GOV_API_KEY=your_key
    """

    API_BASE = "https://api.sam.gov/opportunities/v2/search"

    def scrape(self) -> List[BidOpportunity]:
        api_key = os.environ.get("SAM_GOV_API_KEY", "")
        if not api_key:
            print("[SAM.gov] No API key found. Set SAM_GOV_API_KEY env variable.")
            print("[SAM.gov] Get a free key at: https://api.data.gov/signup/")
            return self._scrape_fallback()

        results = []
        for naics in COMPANY["naics_codes"]:
            params = {
                "api_key": api_key,
                "postedFrom": (datetime.now().replace(day=1)).strftime("%m/%d/%Y"),
                "postedTo": datetime.now().strftime("%m/%d/%Y"),
                "ncode": naics,
                "ptype": "o,k",       # Opportunities & Combined Synopsis
                "state": "VA,DC,MD",   # NOVA area states
                "limit": 25,
                "offset": 0,
            }
            try:
                resp = self.session.get(self.API_BASE, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()

                for opp in data.get("opportunitiesData", []):
                    combined = f"{opp.get('title', '')} {opp.get('description', '')}"
                    ptype, kw_matches = self._match_keywords(combined)
                    loc = self._match_location(
                        f"{opp.get('placeOfPerformance', {}).get('city', {}).get('name', '')} "
                        f"{opp.get('placeOfPerformance', {}).get('state', {}).get('name', '')}"
                    )

                    bid = BidOpportunity(
                        title=opp.get("title", ""),
                        source="sam_gov",
                        source_url=f"https://sam.gov/opp/{opp.get('noticeId', '')}",
                        source_id=opp.get("noticeId", ""),
                        description=self._clean_text(opp.get("description", ""))[:2000],
                        project_type=ptype,
                        naics_code=naics,
                        location_city=loc.get("city", ""),
                        location_state=loc.get("state", "VA"),
                        posted_date=opp.get("postedDate", ""),
                        due_date=opp.get("responseDeadLine", ""),
                        contact_name=opp.get("pointOfContact", [{}])[0].get("fullName", "") if opp.get("pointOfContact") else "",
                        contact_email=opp.get("pointOfContact", [{}])[0].get("email", "") if opp.get("pointOfContact") else "",
                        agency_name=opp.get("fullParentPathName", ""),
                        set_aside=opp.get("typeOfSetAside", ""),
                        solicitation_type=opp.get("type", ""),
                        keyword_matches=kw_matches,
                        scraped_at=datetime.now().isoformat(),
                    )
                    results.append(bid)

                time.sleep(1)  # Rate limiting
            except Exception as e:
                print(f"[SAM.gov] Error for NAICS {naics}: {e}")

        self.results = results
        return results

    def _scrape_fallback(self) -> List[BidOpportunity]:
        """Fallback: provide search URLs for manual checking."""
        print("[SAM.gov] Using fallback mode - generating search URLs only.")
        search_urls = []
        for naics in COMPANY["naics_codes"]:
            url = (
                f"https://sam.gov/search/?index=opp&q=&page=1&sort=-modifiedDate"
                f"&sfm%5Bstatus%5D%5Bis_active%5D=true"
                f"&sfm%5BsimpleSearch%5D%5BkeywordRadio%5D=ALL"
                f"&sfm%5BnaicsCode%5D={naics}"
            )
            search_urls.append({"naics": naics, "url": url})
        print(f"[SAM.gov] Manual search URLs generated: {len(search_urls)}")
        return []


# ============================================================
# eVA VIRGINIA SCRAPER
# ============================================================

class EVAScraper(BaseScraper):
    """
    Scrapes eVA (Virginia's procurement system) for state/local bids.
    Note: eVA may require login for full details. This scrapes public listings.
    """

    BASE_URL = "https://eva.virginia.gov"

    def scrape(self) -> List[BidOpportunity]:
        results = []
        search_terms = []

        # Build search terms from our keyword lists
        for category in ["waterproofing", "tenant_improvements", "general_contracting"]:
            search_terms.extend(KEYWORDS[category][:5])  # Top 5 from each

        for term in set(search_terms):
            try:
                # eVA search endpoint
                search_url = f"{self.BASE_URL}/pages/bids/search.asp"
                params = {
                    "keyword": term,
                    "status": "open",
                    "category": "construction",
                }
                resp = self.session.get(search_url, params=params, timeout=30)

                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "lxml")
                    listings = soup.select(".bid-listing, .search-result, tr.dataRow")

                    for listing in listings:
                        title_el = listing.select_one("a, .title, td:first-child a")
                        if not title_el:
                            continue

                        title = self._clean_text(title_el.get_text())
                        link = urljoin(self.BASE_URL, title_el.get("href", ""))

                        desc_el = listing.select_one(".description, td.description")
                        description = self._clean_text(desc_el.get_text()) if desc_el else ""

                        combined = f"{title} {description}"
                        ptype, kw_matches = self._match_keywords(combined)
                        loc = self._match_location(combined)

                        due_el = listing.select_one(".due-date, td.dueDate")
                        due_date = self._clean_text(due_el.get_text()) if due_el else ""

                        bid = BidOpportunity(
                            title=title,
                            source="eva",
                            source_url=link,
                            source_id=self._generate_source_id("eva", title, link),
                            description=description[:2000],
                            project_type=ptype,
                            location_city=loc.get("city", ""),
                            location_county=loc.get("county", ""),
                            location_state="VA",
                            due_date=due_date,
                            keyword_matches=kw_matches,
                            scraped_at=datetime.now().isoformat(),
                        )
                        results.append(bid)

                time.sleep(2)  # Be respectful
            except Exception as e:
                print(f"[eVA] Error searching '{term}': {e}")

        self.results = results
        return results


# ============================================================
# COUNTY PROCUREMENT SCRAPER (Template for NOVA counties)
# ============================================================

class CountyProcurementScraper(BaseScraper):
    """
    Generic scraper for NOVA county procurement pages.
    Each county has a different page structure, so this uses
    adaptive parsing strategies.
    """

    # County-specific CSS selectors and patterns
    COUNTY_PATTERNS = {
        "arlington_county": {
            "listing_selector": ".view-content .views-row, table.views-table tbody tr",
            "title_selector": "a, td:first-child a",
            "date_selector": ".date-display-single, td.views-field-field-close-date",
        },
        "fairfax_county": {
            "listing_selector": ".solicitation-row, table tbody tr",
            "title_selector": "a.solicitation-title, td a",
            "date_selector": ".close-date, td:nth-child(3)",
        },
        "loudoun_county": {
            "listing_selector": ".bid-item, .view-content .views-row",
            "title_selector": "a, h3 a",
            "date_selector": ".field-due-date, .date",
        },
        "prince_william": {
            "listing_selector": "table tbody tr, .bid-listing",
            "title_selector": "a",
            "date_selector": "td:nth-child(4), .deadline",
        },
        "city_of_alexandria": {
            "listing_selector": "table tbody tr, .solicitation",
            "title_selector": "a",
            "date_selector": "td:last-child, .close-date",
        },
        "city_of_fairfax": {
            "listing_selector": "table tbody tr, .bid-item",
            "title_selector": "a",
            "date_selector": "td:nth-child(3)",
        },
    }

    def scrape(self) -> List[BidOpportunity]:
        results = []
        patterns = self.COUNTY_PATTERNS.get(self.source_key, {})

        if not patterns:
            print(f"[{self.source_key}] No patterns defined, skipping.")
            return results

        try:
            resp = self.session.get(self.config["base_url"], timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            listings = soup.select(patterns.get("listing_selector", ""))

            for listing in listings:
                title_el = listing.select_one(patterns.get("title_selector", "a"))
                if not title_el:
                    continue

                title = self._clean_text(title_el.get_text())
                link = urljoin(self.config["base_url"], title_el.get("href", ""))

                # Filter: only construction-related
                combined = title.lower()
                if not any(
                    kw in combined
                    for kwlist in KEYWORDS.values()
                    for kw in kwlist[:3]
                ) and not any(
                    term in combined
                    for term in ["construction", "building", "renovation",
                                 "repair", "maintenance", "facility", "contractor"]
                ):
                    continue

                ptype, kw_matches = self._match_keywords(title)

                date_el = listing.select_one(patterns.get("date_selector", ""))
                due_date = self._clean_text(date_el.get_text()) if date_el else ""

                county_name = self.config["name"].replace(" Procurement", "")

                bid = BidOpportunity(
                    title=title,
                    source=self.source_key,
                    source_url=link,
                    source_id=self._generate_source_id(self.source_key, title),
                    project_type=ptype,
                    location_county=county_name,
                    location_state="VA",
                    due_date=due_date,
                    agency_name=county_name,
                    keyword_matches=kw_matches,
                    scraped_at=datetime.now().isoformat(),
                )
                results.append(bid)

        except Exception as e:
            print(f"[{self.source_key}] Error: {e}")

        self.results = results
        return results


# ============================================================
# BUILDING PERMIT SCRAPER
# ============================================================

class PermitScraper(BaseScraper):
    """
    Scrapes building permit data to identify upcoming projects
    where contractors may be needed.
    """

    def scrape(self) -> List[BidOpportunity]:
        results = []

        try:
            resp = self.session.get(self.config["base_url"], timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            # Look for commercial permit listings
            tables = soup.select("table")
            for table in tables:
                rows = table.select("tr")[1:]  # Skip header
                for row in rows:
                    cells = row.select("td")
                    if len(cells) < 3:
                        continue

                    text = " ".join(c.get_text() for c in cells)
                    # Only interested in commercial permits
                    if not any(term in text.lower() for term in [
                        "commercial", "office", "retail", "industrial",
                        "renovation", "alteration", "addition", "new construction"
                    ]):
                        continue

                    title = self._clean_text(cells[0].get_text() if cells else "")
                    ptype, kw_matches = self._match_keywords(text)
                    loc = self._match_location(text)

                    bid = BidOpportunity(
                        title=f"[PERMIT] {title}",
                        source=self.source_key,
                        source_url=self.config["base_url"],
                        source_id=self._generate_source_id(self.source_key, text[:100]),
                        description=self._clean_text(text)[:2000],
                        project_type=ptype,
                        location_city=loc.get("city", ""),
                        location_county=loc.get("county", ""),
                        location_state="VA",
                        keyword_matches=kw_matches,
                        category_tags=["permit_lead"],
                        scraped_at=datetime.now().isoformat(),
                    )
                    results.append(bid)

        except Exception as e:
            print(f"[{self.source_key}] Error: {e}")

        self.results = results
        return results


# ============================================================
# SCRAPER FACTORY
# ============================================================

def get_scraper(source_key: str, source_config: dict) -> BaseScraper:
    """Return the appropriate scraper for a given source."""
    scraper_map = {
        "sam_gov": SAMGovScraper,
        "eva": EVAScraper,
        "arlington_county": CountyProcurementScraper,
        "fairfax_county": CountyProcurementScraper,
        "loudoun_county": CountyProcurementScraper,
        "prince_william": CountyProcurementScraper,
        "city_of_alexandria": CountyProcurementScraper,
        "city_of_fairfax": CountyProcurementScraper,
        "arlington_permits": PermitScraper,
        "fairfax_permits": PermitScraper,
    }

    scraper_class = scraper_map.get(source_key, CountyProcurementScraper)
    return scraper_class(source_key, source_config)
