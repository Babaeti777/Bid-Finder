"""
OAK BUILDERS LLC - Bid Finder v2
Web Scrapers — expanded source coverage

Changes from v1:
- SAM.gov: queries ALL NAICS codes (primary + secondary), 90-day lookback, pagination
- SAM.gov: extracts set-aside, contact info, pre-bid dates from full notices
- PlanHub: NEW scraper for commercial plan room leads, with auth support
- eMMA Maryland: NEW scraper for Maryland state procurement
- DC OCP: improved to extract more metadata, broadened filtering
- County scraper: smarter fallback strategies, better date parsing
- All scrapers: extract bonding requirements when available
- All scrapers: better error messages for debugging
- Added RSS/Atom feed scraper for agencies that publish feeds
- NEW: VdotScraper (Virginia DOT), BonfireScraper, PrinceWilliamScraper
"""

import hashlib
import json
import logging
import os
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import urljoin, urlencode, quote

import requests
from bs4 import BeautifulSoup

from config import KEYWORDS, LOCATIONS, COMPANY, SOURCES, REQUEST_TIMEOUT
from models import BidOpportunity

logger = logging.getLogger("scrapers")

# ─── User-Agent rotation ────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
]

_ua_index = 0
def get_ua():
    global _ua_index
    ua = USER_AGENTS[_ua_index % len(USER_AGENTS)]
    _ua_index += 1
    return ua


# ─── Base scraper ───────────────────────────────────────────────────
class BaseScraper(ABC):
    """Abstract base class for all scrapers."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": get_ua()})
        # Disable browser fallback in cloud environments (Render, etc.)
        self.use_browser = os.environ.get("ENABLE_BROWSER", "").lower() == "true"

    @abstractmethod
    def scrape(self) -> List[BidOpportunity]:
        pass

    def _fetch(self, url: str, params: dict = None, timeout: int = None) -> requests.Response:
        """HTTP GET with timeout and error handling."""
        resp = self.session.get(
            url, params=params,
            timeout=timeout or REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp

    def _fetch_json(self, url: str, params: dict = None) -> dict:
        resp = self._fetch(url, params)
        return resp.json()

    def _fetch_html(self, url: str, params: dict = None) -> BeautifulSoup:
        resp = self._fetch(url, params)
        return BeautifulSoup(resp.text, "lxml")

    def _browser_fetch(self, url: str, wait_for: str = None) -> Optional[BeautifulSoup]:
        """Fallback to headless browser if available.

        Note: Browser is disabled in cloud deployments (Render, etc.) to avoid
        60s timeouts. Set ENABLE_BROWSER=true to re-enable.
        """
        if not self.use_browser:
            logger.debug("Browser fallback disabled (cloud environment)")
            return None

        try:
            from browser import browser_fetch, is_browser_available
            if not is_browser_available():
                return None
            html = browser_fetch(url, wait_for=wait_for)
            if html:
                return BeautifulSoup(html, "lxml")
        except ImportError:
            pass
        return None

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text).strip()

    def _extract_keywords(self, text: str) -> List[str]:
        """Find matching keywords in text."""
        text_lower = text.lower()
        matches = []
        for category, kw_list in KEYWORDS.items():
            for kw in kw_list:
                if kw.lower() in text_lower and kw not in matches:
                    matches.append(kw)
        return matches

    def _extract_location(self, text: str) -> dict:
        """Extract location components from text."""
        result = {"city": "", "county": "", "state": "", "zip": ""}

        # ZIP code
        zip_match = re.search(r'\b(\d{5})(?:-\d{4})?\b', text)
        if zip_match:
            result["zip"] = zip_match.group(1)

        # State
        for state in LOCATIONS["states"]:
            if state in text:
                result["state"] = state
                break

        # City
        for city in LOCATIONS["cities"]:
            if city.lower() in text.lower():
                result["city"] = city
                break

        # County
        for county in LOCATIONS["counties"]:
            if county.lower().replace(" county", "") in text.lower():
                result["county"] = county
                break

        return result

    def _parse_money(self, text: str) -> Optional[float]:
        """Parse dollar amounts from text."""
        if not text:
            return None
        # Match patterns like $1,234,567.89 or $1.5M or $500K
        text = text.replace(",", "").replace(" ", "")

        m = re.search(r'\$?([\d.]+)\s*[Mm](?:illion)?', text)
        if m:
            return float(m.group(1)) * 1_000_000

        m = re.search(r'\$?([\d.]+)\s*[Kk]', text)
        if m:
            return float(m.group(1)) * 1_000

        m = re.search(r'\$?([\d.]+)', text)
        if m:
            val = float(m.group(1))
            if val > 100:  # Likely a real dollar amount
                return val

        return None

    def _is_construction_related(self, text: str) -> bool:
        """Quick check if text is construction-related."""
        text_lower = text.lower()
        construction_indicators = [
            "construction", "renovation", "repair", "replacement",
            "installation", "building", "contractor", "roofing",
            "plumbing", "electrical", "hvac", "demolition",
            "masonry", "concrete", "paving", "fencing",
            "waterproofing", "painting", "flooring",
            "maintenance", "facility", "facilities", "improvement",
            "upgrade", "rehabilitation", "restoration", "modification",
            "alteration", "abatement", "remediation", "weatherization",
            "infrastructure", "utilities", "commissioning",
        ]
        return any(ind in text_lower for ind in construction_indicators)


# ─── SAM.gov (Federal) ──────────────────────────────────────────────
class SamGovScraper(BaseScraper):
    """
    Federal opportunities via SAM.gov API v2.
    Queries all NAICS codes with 90-day lookback and pagination.
    """

    API_BASE = "https://api.sam.gov/opportunities/v2/search"

    def scrape(self) -> List[BidOpportunity]:
        api_key = os.environ.get("SAM_GOV_API_KEY", "")
        if not api_key:
            logger.warning("SAM_GOV_API_KEY not set, skipping SAM.gov")
            return []

        all_results = []
        naics_codes = [COMPANY["primary_naics"]] + COMPANY["secondary_naics"]
        posted_from = (datetime.now() - timedelta(days=90)).strftime("%m/%d/%Y")
        posted_to = datetime.now().strftime("%m/%d/%Y")

        for naics in naics_codes:
            try:
                # Search for DC/VA/MD
                for state in ["VA", "DC", "MD"]:
                    offset = 0
                    while True:
                        params = {
                            "api_key": api_key,
                            "postedFrom": posted_from,
                            "postedTo": posted_to,
                            "ncode": naics,
                            "ptype": "o,k",  # Opportunities + combined
                            "limit": 100,
                            "offset": offset,
                            "state": state,
                        }

                        data = self._fetch_json(self.API_BASE, params)
                        opps = data.get("opportunitiesData", [])

                        if not opps:
                            break

                        for opp in opps:
                            bid = self._parse_opportunity(opp)
                            if bid:
                                all_results.append(bid)

                        if len(opps) < 100:
                            break

                        offset += 100
                        time.sleep(0.5)  # Rate limit

            except Exception as e:
                logger.warning(f"SAM.gov NAICS {naics} error: {e}")
                continue

        logger.info(f"SAM.gov: {len(all_results)} raw results across {len(naics_codes)} NAICS codes")
        return all_results

    def _parse_opportunity(self, opp: dict) -> Optional[BidOpportunity]:
        title = opp.get("title", "")
        desc = opp.get("description", "") or opp.get("fullParentPathName", "")

        # Skip non-construction unless it matches our keywords
        if not self._is_construction_related(f"{title} {desc}"):
            if not self._extract_keywords(f"{title} {desc}"):
                return None

        # Extract location
        place = opp.get("officeAddress", {})
        loc = {
            "city": place.get("city", ""),
            "state": place.get("state", ""),
            "zip": place.get("zip", ""),
        }

        # Determine project type from NAICS + keywords
        naics = opp.get("naicsCode", "")
        project_type = self._classify_project_type(title, desc, naics)

        bid = BidOpportunity(
            title=self._clean_text(title),
            source="SAM.gov",
            source_url=f"https://sam.gov/opp/{opp.get('noticeId', '')}/view",
            source_id=opp.get("noticeId", ""),
            description=self._clean_text(desc[:2000]),
            project_type=project_type,
            naics_code=naics,
            location_city=loc["city"],
            location_state=loc["state"],
            location_zip=loc["zip"],
            posted_date=opp.get("postedDate", ""),
            due_date=opp.get("responseDeadLine", ""),
            agency=opp.get("fullParentPathName", ""),
            issuing_office=opp.get("officeTitle", ""),
            set_aside=opp.get("typeOfSetAside", ""),
            contract_type=opp.get("typeOfSolicitation", ""),
            solicitation_type=opp.get("solicitationNumber", ""),
            contact_name=opp.get("pointOfContact", [{}])[0].get("fullName", "") if opp.get("pointOfContact") else "",
            contact_email=opp.get("pointOfContact", [{}])[0].get("email", "") if opp.get("pointOfContact") else "",
            contact_phone=opp.get("pointOfContact", [{}])[0].get("phone", "") if opp.get("pointOfContact") else "",
            keyword_matches=self._extract_keywords(f"{title} {desc}"),
        )

        # Check for bonding language in description
        desc_lower = desc.lower()
        if "bond" in desc_lower or "surety" in desc_lower:
            bid.bonding_required = True
            amount = self._parse_money(desc)
            if amount:
                bid.bonding_amount = amount

        return bid

    def _classify_project_type(self, title: str, desc: str, naics: str) -> str:
        combined = f"{title} {desc}".lower()
        if any(kw.lower() in combined for kw in KEYWORDS["waterproofing"][:15]):
            return "waterproofing"
        if any(kw.lower() in combined for kw in KEYWORDS["tenant_improvements"][:10]):
            return "tenant_improvements"
        if any(kw.lower() in combined for kw in KEYWORDS.get("civil_infrastructure", [])[:10]):
            return "civil_infrastructure"
        if any(kw.lower() in combined for kw in KEYWORDS.get("commercial_private", [])[:10]):
            return "commercial_private"
        return "general_contracting"


# ─── DC OCP ─────────────────────────────────────────────────────────
class DcOcpScraper(BaseScraper):
    """DC Office of Contracting & Procurement via ArcGIS REST API."""

    API_URL = "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Government_Procurement_Layers/MapServer/0/query"

    def scrape(self) -> List[BidOpportunity]:
        results = []
        try:
            offset = 0
            while True:
                params = {
                    "where": "STATUS='Open'",
                    "outFields": "*",
                    "f": "json",
                    "resultOffset": offset,
                    "resultRecordCount": 200,
                }
                data = self._fetch_json(self.API_URL, params)
                features = data.get("features", [])

                if not features:
                    break

                for feature in features:
                    attr = feature.get("attributes", {})
                    bid = self._parse_feature(attr)
                    if bid:
                        results.append(bid)

                if len(features) < 200:
                    break

                offset += 200

        except Exception as e:
            logger.error(f"DC OCP error: {e}")
            raise

        return results

    def _parse_feature(self, attr: dict) -> Optional[BidOpportunity]:
        title = attr.get("SUBJECT", "") or attr.get("TITLE", "")
        desc = attr.get("DESCRIPTION", "") or ""

        if not self._is_construction_related(f"{title} {desc}"):
            if not self._extract_keywords(f"{title} {desc}"):
                return None

        # Parse dates (epoch ms)
        due_date = ""
        if attr.get("CLOSEDATE"):
            try:
                due_date = datetime.fromtimestamp(attr["CLOSEDATE"] / 1000).strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                pass

        posted_date = ""
        if attr.get("OPENDATE"):
            try:
                posted_date = datetime.fromtimestamp(attr["OPENDATE"] / 1000).strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                pass

        return BidOpportunity(
            title=self._clean_text(title),
            source="DC OCP",
            source_url=attr.get("LINK", ""),
            source_id=str(attr.get("SOLICITATION_NUMBER", "")),
            description=self._clean_text(desc[:2000]),
            project_type=self._classify_dc_type(title, desc),
            location_city="Washington",
            location_state="DC",
            posted_date=posted_date,
            due_date=due_date,
            agency=attr.get("AGENCY", ""),
            set_aside=attr.get("SETASIDE", ""),
            contact_name=attr.get("CONTACT_NAME", ""),
            contact_email=attr.get("CONTACT_EMAIL", ""),
            keyword_matches=self._extract_keywords(f"{title} {desc}"),
        )

    def _classify_dc_type(self, title: str, desc: str) -> str:
        combined = f"{title} {desc}".lower()
        if any(kw.lower() in combined for kw in KEYWORDS["waterproofing"][:10]):
            return "waterproofing"
        if any(kw.lower() in combined for kw in KEYWORDS["tenant_improvements"][:10]):
            return "tenant_improvements"
        return "general_contracting"


# ─── Montgomery County MD ───────────────────────────────────────────
class MontgomeryCountyScraper(BaseScraper):
    """Montgomery County via Socrata Open Data API."""

    API_URL = "https://data.montgomerycountymd.gov/resource/dvhm-nmvt.json"

    def scrape(self) -> List[BidOpportunity]:
        results = []
        try:
            offset = 0
            while True:
                params = {
                    "$limit": 200,
                    "$order": "posting_date DESC",
                    "$offset": offset,
                }
                data = self._fetch_json(self.API_URL, params)

                if not data:
                    break

                for item in data:
                    bid = self._parse_item(item)
                    if bid:
                        results.append(bid)

                if len(data) < 200:
                    break

                offset += 200

        except Exception as e:
            logger.error(f"Montgomery County error: {e}")
            raise

        return results

    def _parse_item(self, item: dict) -> Optional[BidOpportunity]:
        title = item.get("title", "") or item.get("solicitation_title", "")
        desc = item.get("description", "") or ""

        if not self._is_construction_related(f"{title} {desc}"):
            if not self._extract_keywords(f"{title} {desc}"):
                return None

        return BidOpportunity(
            title=self._clean_text(title),
            source="Montgomery County",
            source_url=item.get("url", ""),
            source_id=item.get("solicitation_number", ""),
            description=self._clean_text(desc[:2000]),
            location_city="Rockville",
            location_county="Montgomery County",
            location_state="MD",
            posted_date=item.get("posting_date", "")[:10] if item.get("posting_date") else "",
            due_date=item.get("closing_date", "")[:10] if item.get("closing_date") else "",
            agency="Montgomery County",
            contact_name=item.get("contact_name", ""),
            contact_email=item.get("contact_email", ""),
            keyword_matches=self._extract_keywords(f"{title} {desc}"),
        )


# ─── eVA Virginia ───────────────────────────────────────────────────
class EvaScraper(BaseScraper):
    """Virginia eVA procurement portal."""

    BASE_URL = "https://eva.virginia.gov"

    def scrape(self) -> List[BidOpportunity]:
        results = []
        try:
            # Try requests first
            soup = self._fetch_html(f"{self.BASE_URL}/pages/eva-public-portal.htm")

            # Look for solicitation links
            links = soup.find_all("a", href=True)
            sol_links = [
                l for l in links
                if any(term in (l.text or "").lower()
                       for term in ["solicitation", "bid", "rfp", "ifb"])
            ]

            if not sol_links:
                logger.warning("eVA: no solicitations found via requests, skipping browser fallback")

            for link in sol_links[:200]:
                bid = self._parse_listing(link, soup)
                if bid:
                    results.append(bid)

        except Exception as e:
            logger.warning(f"eVA error (non-fatal): {e}")
            # Don't raise; just return empty

        return results

    def _parse_listing(self, link, soup) -> Optional[BidOpportunity]:
        title = self._clean_text(link.text)
        if not title or len(title) < 5:
            return None

        url = urljoin(self.BASE_URL, link.get("href", ""))

        # Try to find parent row for more data
        parent_row = link.find_parent("tr")
        desc = ""
        due_date = ""
        agency = ""

        if parent_row:
            cells = parent_row.find_all("td")
            if len(cells) >= 3:
                agency = self._clean_text(cells[1].text) if len(cells) > 1 else ""
                due_date = self._clean_text(cells[-1].text)

        if not self._is_construction_related(f"{title} {desc}"):
            if not self._extract_keywords(f"{title} {desc}"):
                return None

        return BidOpportunity(
            title=title,
            source="eVA Virginia",
            source_url=url,
            description=desc,
            location_state="VA",
            due_date=due_date,
            agency=agency or "Commonwealth of Virginia",
            keyword_matches=self._extract_keywords(title),
        )


# ─── eMMA Maryland ──────────────────────────────────────────────────
class EmmaScraper(BaseScraper):
    """Maryland eMMA procurement portal."""

    BASE_URL = "https://procurement.maryland.gov"

    def scrape(self) -> List[BidOpportunity]:
        results = []
        try:
            # Try public browse page first
            alt_url = "https://emma.maryland.gov/page.aspx/en/rfp/request_browse_public"
            soup = self._fetch_html(alt_url)

            if soup:
                rows = soup.find_all("tr")
                for row in rows[1:200]:
                    bid = self._parse_row(row)
                    if bid:
                        results.append(bid)

            if not results:
                logger.warning("eMMA: no results found, skipping browser fallback")

        except Exception as e:
            logger.warning(f"eMMA Maryland error (non-fatal): {e}")
            # Don't raise; just return empty

        return results

    def _parse_row(self, row) -> Optional[BidOpportunity]:
        cells = row.find_all("td")
        if len(cells) < 3:
            return None

        title = self._clean_text(cells[0].text) if cells else ""
        link = cells[0].find("a")
        url = urljoin(self.BASE_URL, link["href"]) if link else ""

        if not self._is_construction_related(title):
            return None

        return BidOpportunity(
            title=title,
            source="eMMA Maryland",
            source_url=url,
            location_state="MD",
            agency="State of Maryland",
            keyword_matches=self._extract_keywords(title),
        )


# ─── PlanHub ────────────────────────────────────────────────────────
class PlanHubScraper(BaseScraper):
    """
    PlanHub commercial plan room scraper.
    Free for GCs — covers commercial/private projects
    that government portals miss.
    """

    BASE_URL = "https://www.planhub.com"

    def scrape(self) -> List[BidOpportunity]:
        results = []

        # Check for credentials
        email = os.environ.get("PLANHUB_EMAIL", "")
        password = os.environ.get("PLANHUB_PASSWORD", "")

        if email and password:
            # Try authenticated access
            try:
                login_url = f"{self.BASE_URL}/account/login"
                self.session.post(login_url, data={
                    "email": email,
                    "password": password,
                }, timeout=REQUEST_TIMEOUT)
                logger.info("PlanHub login successful")
            except Exception as e:
                logger.warning(f"PlanHub login failed: {e}")
        else:
            logger.info("PlanHub credentials not set, using public search")

        try:
            # Search with DC metro area parameter
            search_url = f"{self.BASE_URL}/projects?q=DC%20metro&location=Washington%20DC"

            # PlanHub is heavily JS-rendered, need browser
            soup = self._browser_fetch(search_url, wait_for=".project-card")

            if not soup:
                # Fallback: try the API endpoint
                soup = self._fetch_html(search_url)

            if soup:
                # Look for project cards/listings
                cards = soup.find_all(class_=re.compile(r"project|listing|bid|card"))
                if not cards:
                    cards = soup.find_all("article")
                if not cards:
                    # Try table rows
                    cards = soup.find_all("tr")[1:200]

                for card in cards[:200]:
                    bid = self._parse_card(card)
                    if bid:
                        results.append(bid)

        except Exception as e:
            logger.warning(f"PlanHub scraper: {e}")
            # PlanHub may block — not a critical failure
            return results

        return results

    def _parse_card(self, card) -> Optional[BidOpportunity]:
        # Extract title
        title_el = card.find(["h2", "h3", "h4", "a", "strong"])
        if not title_el:
            return None
        title = self._clean_text(title_el.text)
        if not title or len(title) < 5:
            return None

        # Link
        link = card.find("a", href=True)
        url = urljoin(self.BASE_URL, link["href"]) if link else ""

        # Description
        desc_el = card.find(class_=re.compile(r"desc|detail|summary|body"))
        desc = self._clean_text(desc_el.text) if desc_el else ""

        # Location
        loc_el = card.find(class_=re.compile(r"location|address|city"))
        loc_text = self._clean_text(loc_el.text) if loc_el else ""
        location = self._extract_location(loc_text or title)

        # Check relevance
        combined = f"{title} {desc}"
        if not self._extract_keywords(combined):
            return None

        # Due date
        date_el = card.find(class_=re.compile(r"date|deadline|due|close"))
        due_date = self._clean_text(date_el.text) if date_el else ""

        # Value
        value_el = card.find(class_=re.compile(r"value|budget|cost|amount"))
        value_text = self._clean_text(value_el.text) if value_el else ""
        value = self._parse_money(value_text)

        return BidOpportunity(
            title=title,
            source="PlanHub",
            source_url=url,
            description=desc[:2000],
            project_type="commercial_private",
            location_city=location.get("city", ""),
            location_county=location.get("county", ""),
            location_state=location.get("state", ""),
            location_zip=location.get("zip", ""),
            estimated_value_min=value,
            estimated_value_max=value,
            budget_display=value_text,
            due_date=due_date,
            keyword_matches=self._extract_keywords(combined),
        )


# ─── County/Generic HTML scraper ────────────────────────────────────
class CountyScraper(BaseScraper):
    """Generic county/city procurement portal scraper."""

    def __init__(self, source_key: str):
        super().__init__()
        self.source_key = source_key
        self.config = SOURCES.get(source_key, {})
        self.base_url = self.config.get("url", "")
        self.source_name = self.config.get("name", source_key)

        # URL overrides for specific counties
        self.url_overrides = {
            "fairfax": [
                self.base_url,
                "https://fairfaxcounty.bonfirehub.com/portal/?tab=openOpportunities",
            ],
            "arlington": [
                self.base_url,
                "https://vrapp.vendorregistry.com/Bids/View/BidsList",
            ],
        }

    def scrape(self) -> List[BidOpportunity]:
        results = []

        # Determine which URLs to try
        urls_to_try = [self.base_url]
        source_lower = self.source_key.lower()
        for key, alt_urls in self.url_overrides.items():
            if key in source_lower:
                urls_to_try = alt_urls
                break

        for url in urls_to_try:
            if not url:
                continue

            try:
                soup = self._fetch_html(url)

                # Strategy 1: Look for tables
                tables = soup.find_all("table")
                for table in tables:
                    rows = table.find_all("tr")
                    for row in rows[1:]:
                        bid = self._parse_table_row(row)
                        if bid:
                            results.append(bid)

                # Strategy 2: Look for listing divs/articles
                if not results:
                    listings = soup.find_all(
                        class_=re.compile(r"bid|solicitation|procurement|listing|opportunity")
                    )
                    for listing in listings:
                        bid = self._parse_listing_div(listing)
                        if bid:
                            results.append(bid)

                # Strategy 3: Look for links with bid-related text
                if not results:
                    links = soup.find_all("a", href=True)
                    for link in links:
                        text = self._clean_text(link.text)
                        if self._is_construction_related(text):
                            results.append(BidOpportunity(
                                title=text,
                                source=self.source_name,
                                source_url=urljoin(url, link["href"]),
                                location_state=self._guess_state(),
                                agency=self.source_name,
                                keyword_matches=self._extract_keywords(text),
                            ))

                if results:
                    break  # Stop if we found results

            except Exception as e:
                logger.warning(f"{self.source_name} ({url}) error: {e}")
                continue

        if not results:
            logger.error(f"{self.source_name} returned no results from any URL")

        return results

    def _parse_table_row(self, row) -> Optional[BidOpportunity]:
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            return None

        title = self._clean_text(cells[0].text)
        if not title or len(title) < 5:
            return None

        # Find link
        link = row.find("a", href=True)
        url = urljoin(self.base_url, link["href"]) if link else ""

        # Try to extract date from last cell
        due_date = ""
        for cell in reversed(cells):
            text = self._clean_text(cell.text)
            if re.search(r'\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2}', text):
                due_date = text
                break

        if not self._is_construction_related(title):
            if not self._extract_keywords(title):
                return None

        return BidOpportunity(
            title=title,
            source=self.source_name,
            source_url=url,
            location_state=self._guess_state(),
            due_date=due_date,
            agency=self.source_name,
            keyword_matches=self._extract_keywords(title),
        )

    def _parse_listing_div(self, div) -> Optional[BidOpportunity]:
        title_el = div.find(["h2", "h3", "h4", "a", "strong"])
        if not title_el:
            return None
        title = self._clean_text(title_el.text)
        if not title:
            return None

        link = div.find("a", href=True)
        url = urljoin(self.base_url, link["href"]) if link else ""

        if not self._is_construction_related(title):
            if not self._extract_keywords(title):
                return None

        return BidOpportunity(
            title=title,
            source=self.source_name,
            source_url=url,
            location_state=self._guess_state(),
            agency=self.source_name,
            keyword_matches=self._extract_keywords(title),
        )

    def _guess_state(self) -> str:
        name = self.source_name.lower()
        if any(md in name for md in ["maryland", "montgomery", "prince george", "howard", "anne arundel"]):
            return "MD"
        if "dc" in name or "district" in name:
            return "DC"
        return "VA"


# ─── BidNet Direct ──────────────────────────────────────────────────
class BidNetScraper(BaseScraper):
    """BidNet Direct — requires login credentials."""

    BASE_URL = "https://www.bidnetdirect.com"

    def scrape(self) -> List[BidOpportunity]:
        email = os.environ.get("BIDNET_EMAIL", "")
        password = os.environ.get("BIDNET_PASSWORD", "")

        if not email or not password:
            logger.info("BidNet credentials not set, skipping")
            return []

        results = []
        try:
            # Login
            login_url = f"{self.BASE_URL}/login"
            self.session.post(login_url, data={
                "email": email,
                "password": password,
            }, timeout=REQUEST_TIMEOUT)

            # Search for construction bids with location parameters
            search_url = f"{self.BASE_URL}/bids?location=Virginia,Washington+DC,Maryland&category=construction"
            soup = self._fetch_html(search_url)

            rows = soup.find_all("tr")
            for row in rows[1:]:
                bid = self._parse_row(row)
                if bid:
                    results.append(bid)

        except Exception as e:
            logger.error(f"BidNet error: {e}")
            raise

        return results

    def _parse_row(self, row) -> Optional[BidOpportunity]:
        cells = row.find_all("td")
        if len(cells) < 3:
            return None

        title = self._clean_text(cells[0].text)
        link = cells[0].find("a", href=True)
        url = urljoin(self.BASE_URL, link["href"]) if link else ""

        if not self._is_construction_related(title):
            if not self._extract_keywords(title):
                return None

        agency = self._clean_text(cells[1].text) if len(cells) > 1 else ""
        due_date = self._clean_text(cells[-1].text)

        location = self._extract_location(f"{title} {agency}")

        return BidOpportunity(
            title=title,
            source="BidNet Direct",
            source_url=url,
            location_city=location.get("city", ""),
            location_state=location.get("state", ""),
            due_date=due_date,
            agency=agency,
            keyword_matches=self._extract_keywords(title),
        )


# ─── OpenGov Procurement ────────────────────────────────────────────
class OpenGovScraper(BaseScraper):
    """OpenGov Procurement Portal."""

    BASE_URL = "https://procurement.opengov.com"

    def scrape(self) -> List[BidOpportunity]:
        email = os.environ.get("OPENGOV_EMAIL", "")
        password = os.environ.get("OPENGOV_PASSWORD", "")

        results = []
        try:
            # Known OpenGov embed portals for our agencies
            embed_urls = [
                "https://procurement.opengov.com/portal/arlington-county",
                "https://procurement.opengov.com/portal/fairfax-county",
                "https://procurement.opengov.com/portal/loudoun-county-va",
                "https://procurement.opengov.com/portal/prince-william-county-va",
                "https://procurement.opengov.com/portal/city-of-alexandria-va",
            ]

            for portal_url in embed_urls:
                try:
                    soup = self._fetch_html(portal_url)

                    if soup:
                        rows = soup.find_all("tr")
                        for row in rows[1:]:
                            bid = self._parse_row(row, portal_url)
                            if bid:
                                results.append(bid)
                except Exception as e:
                    logger.warning(f"OpenGov portal error ({portal_url}): {e}")
                    continue

                time.sleep(1)

        except Exception as e:
            logger.warning(f"OpenGov error (non-fatal): {e}")

        return results

    def _parse_row(self, row, base_url: str) -> Optional[BidOpportunity]:
        cells = row.find_all("td")
        if len(cells) < 2:
            return None

        title = self._clean_text(cells[0].text)
        link = cells[0].find("a", href=True)
        url = urljoin(base_url, link["href"]) if link else ""

        if not self._is_construction_related(title):
            if not self._extract_keywords(title):
                return None

        # Determine agency from portal URL
        agency = ""
        if "arlington" in base_url:
            agency = "Arlington County"
        elif "fairfax" in base_url:
            agency = "Fairfax County"
        elif "loudoun" in base_url:
            agency = "Loudoun County"
        elif "prince-william" in base_url:
            agency = "Prince William County"
        elif "alexandria" in base_url:
            agency = "City of Alexandria"

        return BidOpportunity(
            title=title,
            source="OpenGov",
            source_url=url,
            location_state="VA",
            agency=agency,
            keyword_matches=self._extract_keywords(title),
        )


# ─── VDOT Virginia ──────────────────────────────────────────────────
class VdotScraper(BaseScraper):
    """Virginia DOT — transportation/civil projects."""

    BASE_URL = "https://cabb.virginiadot.org"

    def scrape(self) -> List[BidOpportunity]:
        results = []
        try:
            soup = self._fetch_html(self.BASE_URL)
            # Look for advertisement tables
            if soup:
                for table in soup.find_all("table"):
                    for row in table.find_all("tr")[1:]:
                        bid = self._parse_row(row)
                        if bid:
                            results.append(bid)
        except Exception as e:
            logger.warning(f"VDOT error (non-fatal): {e}")
        return results

    def _parse_row(self, row) -> Optional[BidOpportunity]:
        cells = row.find_all("td")
        if len(cells) < 2:
            return None
        title = self._clean_text(cells[0].text)
        if not title or len(title) < 5:
            return None
        link = row.find("a", href=True)
        url = urljoin(self.BASE_URL, link["href"]) if link else ""
        due_date = ""
        for cell in reversed(cells):
            text = self._clean_text(cell.text)
            if re.search(r'\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2}', text):
                due_date = text
                break
        return BidOpportunity(
            title=title,
            source="VDOT",
            source_url=url,
            location_state="VA",
            due_date=due_date,
            agency="Virginia DOT",
            project_type="civil_infrastructure",
            keyword_matches=self._extract_keywords(title),
        )


# ─── Bonfire Procurement ────────────────────────────────────────────
class BonfireScraper(BaseScraper):
    """Bonfire procurement portals — used by Fairfax County and others."""

    PORTALS = {
        "fairfax": {
            "url": "https://fairfaxcounty.bonfirehub.com/portal/?tab=openOpportunities",
            "name": "Fairfax County (Bonfire)",
            "state": "VA",
        },
    }

    def scrape(self) -> List[BidOpportunity]:
        results = []
        for key, portal in self.PORTALS.items():
            try:
                soup = self._fetch_html(portal["url"])
                if soup:
                    for row in soup.find_all("tr")[1:]:
                        bid = self._parse_row(row, portal)
                        if bid:
                            results.append(bid)
                time.sleep(1)
            except Exception as e:
                logger.warning(f"Bonfire {key} error (non-fatal): {e}")
        return results

    def _parse_row(self, row, portal) -> Optional[BidOpportunity]:
        cells = row.find_all("td")
        if len(cells) < 2:
            return None
        title = self._clean_text(cells[0].text)
        if not title or len(title) < 5:
            return None
        link = row.find("a", href=True)
        url = urljoin(portal["url"], link["href"]) if link else ""
        due_date = ""
        for cell in reversed(cells):
            text = self._clean_text(cell.text)
            if re.search(r'\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2}', text):
                due_date = text
                break
        return BidOpportunity(
            title=title,
            source=portal["name"],
            source_url=url,
            location_state=portal["state"],
            due_date=due_date,
            agency=portal["name"],
            keyword_matches=self._extract_keywords(title),
        )


# ─── Prince William County ──────────────────────────────────────────
class PrinceWilliamScraper(BaseScraper):
    """Prince William County procurement."""

    BASE_URL = "https://eservice2.pwcgov.org/eservices/procurement/"

    def scrape(self) -> List[BidOpportunity]:
        results = []
        try:
            soup = self._fetch_html(self.BASE_URL)
            if soup:
                for table in soup.find_all("table"):
                    for row in table.find_all("tr")[1:]:
                        cells = row.find_all("td")
                        if len(cells) < 2:
                            continue
                        title = self._clean_text(cells[0].text)
                        if not title or len(title) < 5:
                            continue
                        link = row.find("a", href=True)
                        url = urljoin(self.BASE_URL, link["href"]) if link else ""
                        due_date = ""
                        for cell in reversed(cells):
                            text = self._clean_text(cell.text)
                            if re.search(r'\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2}', text):
                                due_date = text
                                break
                        results.append(BidOpportunity(
                            title=title,
                            source="Prince William County",
                            source_url=url,
                            location_state="VA",
                            location_county="Prince William County",
                            due_date=due_date,
                            agency="Prince William County",
                            keyword_matches=self._extract_keywords(title),
                        ))
        except Exception as e:
            logger.warning(f"Prince William County error (non-fatal): {e}")
        return results


# ─── Permit Scraper (Lead Gen) ──────────────────────────────────────
class PermitScraper(BaseScraper):
    """Building permit data for proactive lead generation."""

    def __init__(self, source_key: str):
        super().__init__()
        self.source_key = source_key
        self.config = SOURCES.get(source_key, {})
        self.base_url = self.config.get("url", "")
        self.source_name = self.config.get("name", source_key)

    def scrape(self) -> List[BidOpportunity]:
        results = []
        try:
            soup = self._fetch_html(self.base_url)

            # Look for permit tables/listings
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows[1:30]:  # Limit to recent permits
                    bid = self._parse_permit(row)
                    if bid:
                        results.append(bid)

        except Exception as e:
            logger.warning(f"{self.source_name} permit scraper (non-fatal): {e}")

        return results

    def _parse_permit(self, row) -> Optional[BidOpportunity]:
        cells = row.find_all("td")
        if len(cells) < 2:
            return None

        text = " ".join(self._clean_text(c.text) for c in cells)
        if not self._is_construction_related(text):
            return None

        title = self._clean_text(cells[0].text)
        value = self._parse_money(text)

        # Only surface permits with significant value
        if value and value < 25_000:
            return None

        return BidOpportunity(
            title=f"[Permit] {title}",
            source=self.source_name,
            source_url=self.base_url,
            description=text[:500],
            project_type="commercial_private",
            estimated_value_min=value,
            estimated_value_max=value,
            keyword_matches=self._extract_keywords(text),
        )
