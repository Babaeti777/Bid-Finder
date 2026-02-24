"""
OAK BUILDERS LLC - Bid Finder
Web Scrapers for Each Data Source

Scraper Status:
  SAMGovScraper     - SAM.gov REST API (requires free API key from api.data.gov)
  DCOCPScraper      - DC Open Data ArcGIS REST API (no key needed)
  EVAScraper        - eVA Virginia Business Opportunities at mvendor.cgieva.com
  CountyScraper     - Generic HTML scraper for county procurement pages
  PermitScraper     - Generic HTML scraper for building permit pages

Sites requiring JavaScript (Bonfire, Ivalua) use CountyScraper as fallback.
  BidNetScraper      - BidNet Direct with authenticated session login
"""

import os
import re
import json
import time
import hashlib
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from typing import List
from urllib.parse import urljoin, urlencode, quote

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Install dependencies: pip install requests beautifulsoup4 lxml")
    raise

from models import BidOpportunity
from config import KEYWORDS, LOCATIONS, COMPANY, SCRAPER_FILTER_TERMS


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
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        self.results: List[BidOpportunity] = []

    @abstractmethod
    def scrape(self) -> List[BidOpportunity]:
        """Scrape and return bid opportunities.

        IMPORTANT: Let HTTP errors (ConnectionError, HTTPError, Timeout)
        propagate so that main.py retry logic can catch and retry them.
        Only catch errors for individual listing parsing.
        """
        pass

    def _fetch(self, url, params=None, timeout=12):
        """Fetch a URL and return the response. Lets errors propagate."""
        resp = self.session.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp

    def _generate_source_id(self, *parts):
        """Generate a unique source_id from parts of the listing."""
        raw = "|".join(str(p) for p in parts)
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text).strip()

    def _parse_value(self, text: str) -> tuple:
        """Extract min/max dollar values from text."""
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

    def _is_construction_related(self, text: str) -> bool:
        """Check if text matches any construction filter terms."""
        text_lower = text.lower()
        return any(term in text_lower for term in SCRAPER_FILTER_TERMS)

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

    def _is_valid_href(self, href):
        """Check if an href is a real page link (not anchor/javascript)."""
        if not href:
            return False
        href = href.strip()
        if href in ("#", "/", ""):
            return False
        if href.startswith(("#", "javascript:", "mailto:", "tel:")):
            return False
        return True

    def _make_detail_url(self, base_url, href):
        """Build a full URL. Returns base_url if href resolves to just the site root."""
        if not href or not self._is_valid_href(href):
            return base_url
        url = urljoin(base_url, href)
        from urllib.parse import urlparse
        parsed = urlparse(url)
        # If the link just goes to the homepage, return the listing page instead
        if parsed.path in ("", "/", "/index.html", "/index.htm"):
            return base_url
        return url

    def _find_links_broad(self, soup):
        """Try multiple strategies to find bid listing links."""
        results = []

        # Strategy 1: Table rows with links
        for table in soup.select("table"):
            for row in table.select("tr"):
                link = row.select_one("a[href]")
                if link and link.get_text(strip=True) and self._is_valid_href(link.get("href", "")):
                    cells = row.select("td")
                    cell_texts = [c.get_text(strip=True) for c in cells]
                    results.append({
                        "title": link.get_text(strip=True),
                        "href": link.get("href", ""),
                        "extra_text": " ".join(cell_texts),
                    })

        # Strategy 2: List items with links
        if not results:
            for li in soup.select("li"):
                link = li.select_one("a[href]")
                if link and link.get_text(strip=True) and self._is_valid_href(link.get("href", "")):
                    results.append({
                        "title": link.get_text(strip=True),
                        "href": link.get("href", ""),
                        "extra_text": li.get_text(strip=True),
                    })

        # Strategy 3: Div-based listings with links
        if not results:
            for div in soup.select("div.row, div.item, div.listing, div.card, article"):
                link = div.select_one("a[href]")
                if link and link.get_text(strip=True) and self._is_valid_href(link.get("href", "")):
                    results.append({
                        "title": link.get_text(strip=True),
                        "href": link.get("href", ""),
                        "extra_text": div.get_text(strip=True),
                    })

        # Strategy 4: All links as last resort (filter later)
        if not results:
            for link in soup.select("a[href]"):
                text = link.get_text(strip=True)
                href = link.get("href", "")
                if text and len(text) > 10 and self._is_valid_href(href):
                    results.append({
                        "title": text,
                        "href": href,
                        "extra_text": text,
                    })

        return results


# ============================================================
# SAM.GOV SCRAPER (Federal Opportunities - JSON API)
# ============================================================

class SAMGovScraper(BaseScraper):
    """
    Scrapes SAM.gov using the official Opportunities API v2.
    Requires a free API key from https://api.data.gov/signup/
    Set environment variable: SAM_GOV_API_KEY=your_key
    """

    def scrape(self) -> List[BidOpportunity]:
        api_key = os.environ.get("SAM_GOV_API_KEY", "")
        if not api_key:
            print("[SAM.gov] WARNING: No API key found.")
            print("[SAM.gov] Get a FREE key at: https://api.data.gov/signup/")
            print("[SAM.gov] Then set it in Settings or: export SAM_GOV_API_KEY=your_key")
            # Don't raise - just return empty with clear message
            return []

        # Use API URL from config (includes /prod/)
        api_url = self.config.get(
            "api_url",
            "https://api.sam.gov/prod/opportunities/v2/search"
        )

        results = []
        states = ["VA", "DC", "MD"]  # Must query one state at a time
        ptypes = ["o", "k", "p"]  # Solicitation, Combined, Presolicitation

        posted_from = (datetime.now() - timedelta(days=30)).strftime("%m/%d/%Y")
        posted_to = datetime.now().strftime("%m/%d/%Y")

        scan_start = time.time()
        MAX_SAM_SECONDS = 90  # Hard cap so SAM.gov doesn't monopolize the scan

        _timed_out = False
        for state in states:
            if _timed_out:
                break
            for naics in COMPANY["naics_codes"]:
                # Abort if we've been running too long
                if time.time() - scan_start > MAX_SAM_SECONDS:
                    print(f"    [SAM.gov] Time limit reached ({MAX_SAM_SECONDS}s) - stopping")
                    _timed_out = True
                    break
                try:
                    params = {
                        "api_key": api_key,
                        "postedFrom": posted_from,
                        "postedTo": posted_to,
                        "ncode": naics,
                        "ptype": ptypes,  # requests sends as ptype=o&ptype=k&ptype=p
                        "state": state,
                        "limit": 25,
                        "offset": 0,
                    }

                    print(f"    [SAM.gov] Querying {state} / NAICS {naics}...")
                    resp = self._fetch(api_url, params=params, timeout=15)
                    data = resp.json()

                    opps = data.get("opportunitiesData", [])
                    print(f"    [SAM.gov] Got {len(opps)} results for {state}/{naics}")

                    for opp in opps:
                        try:
                            title = opp.get("title", "")
                            # The description field is a URL in the API, not inline text
                            desc_url = opp.get("description", "")
                            sol_num = opp.get("solicitationNumber", "")

                            combined = f"{title} {sol_num}"
                            ptype, kw_matches = self._match_keywords(combined)

                            # Extract location from placeOfPerformance
                            pop = opp.get("placeOfPerformance", {}) or {}
                            pop_city = ""
                            pop_state = state
                            if isinstance(pop.get("city"), dict):
                                pop_city = pop["city"].get("name", "")
                            elif isinstance(pop.get("city"), str):
                                pop_city = pop["city"]
                            if isinstance(pop.get("state"), dict):
                                pop_state = pop["state"].get("code", state)

                            notice_id = opp.get("noticeId", "")
                            ui_link = opp.get("uiLink", "")
                            source_url = ui_link if ui_link else f"https://sam.gov/opp/{notice_id}/view"

                            # Extract contact info safely
                            contacts = opp.get("pointOfContact", []) or []
                            contact_name = ""
                            contact_email = ""
                            if contacts and isinstance(contacts, list):
                                contact_name = contacts[0].get("fullName", "")
                                contact_email = contacts[0].get("email", "")

                            bid = BidOpportunity(
                                title=title,
                                source="sam_gov",
                                source_url=source_url,
                                source_id=notice_id or self._generate_source_id("sam", title),
                                description=f"Solicitation: {sol_num}" if sol_num else "",
                                project_type=ptype,
                                naics_code=naics,
                                location_city=pop_city,
                                location_state=pop_state,
                                posted_date=opp.get("postedDate", ""),
                                due_date=opp.get("responseDeadLine", ""),
                                contact_name=contact_name,
                                contact_email=contact_email,
                                agency_name=opp.get("fullParentPathName", ""),
                                set_aside=opp.get("typeOfSetAsideDescription", ""),
                                solicitation_type=opp.get("type", ""),
                                keyword_matches=kw_matches,
                                scraped_at=datetime.now().isoformat(),
                            )
                            results.append(bid)
                        except Exception as e:
                            print(f"    [SAM.gov] Error parsing opportunity: {e}")

                    time.sleep(1)  # Rate limiting

                except requests.exceptions.HTTPError as e:
                    if e.response is not None and e.response.status_code == 404:
                        # 404 = no results for this NAICS/state combo, not an error
                        pass
                    elif e.response is not None and e.response.status_code == 403:
                        print(f"    [SAM.gov] API key may be invalid or expired (403)")
                        raise  # Propagate to trigger retry
                    elif e.response is not None and e.response.status_code == 429:
                        print(f"    [SAM.gov] Rate limited - waiting 10s...")
                        time.sleep(10)
                    else:
                        print(f"    [SAM.gov] HTTP error for {state}/{naics}: {e}")
                        # Continue to next combination
                except requests.exceptions.ConnectionError:
                    print(f"    [SAM.gov] Connection error - will retry")
                    raise  # Propagate for retry
                except requests.exceptions.Timeout:
                    print(f"    [SAM.gov] Timeout for {state}/{naics}")
                    # Continue to next combination

        print(f"    [SAM.gov] Total results: {len(results)}")
        self.results = results
        return results


# ============================================================
# DC OFFICE OF CONTRACTING AND PROCUREMENT (ArcGIS REST API)
# ============================================================

class DCOCPScraper(BaseScraper):
    """
    Uses DC's Open Data ArcGIS REST API to fetch solicitations.
    This is a real JSON API - no HTML scraping needed.
    Data source: https://opendata.dc.gov/datasets/solicitations-from-pass
    """

    API_URL = (
        "https://maps2.dcgis.dc.gov/dcgis/rest/services/"
        "DCGIS_DATA/Government_Operations/MapServer/19/query"
    )

    def scrape(self) -> List[BidOpportunity]:
        results = []

        params = {
            "where": "1=1",
            "outFields": "*",
            "f": "json",
            "resultRecordCount": 200,
            "orderByFields": "OBJECTID DESC",
        }

        print(f"    [DC OCP] Querying ArcGIS API...")
        resp = self._fetch(self.API_URL, params=params)
        data = resp.json()

        features = data.get("features", [])
        print(f"    [DC OCP] Got {len(features)} solicitations from API")

        for feature in features:
            try:
                attrs = feature.get("attributes", {})
                title = attrs.get("SOLICITATIONTITLE", "") or ""
                sol_number = attrs.get("SOLICITATIONNUMBER", "") or ""
                agency = attrs.get("AGENCY_NAME", "") or ""
                agency_acronym = attrs.get("AGENCY_ACRONYM", "") or ""

                combined = f"{title} {agency}"

                # Filter for construction-related
                if not self._is_construction_related(combined):
                    continue

                ptype, kw_matches = self._match_keywords(combined)

                # Build source URL - use search with solicitation number
                if sol_number:
                    source_url = (
                        f"https://contracts.ocp.dc.gov/solicitations/search"
                        f"?keyword={quote(sol_number)}"
                    )
                else:
                    source_url = (
                        f"https://contracts.ocp.dc.gov/solicitations/search"
                        f"?keyword={quote(title[:50])}"
                    )

                bid = BidOpportunity(
                    title=title,
                    source="dc_ocp",
                    source_url=source_url,
                    source_id=sol_number or self._generate_source_id("dc_ocp", title),
                    description=f"Agency: {agency} ({agency_acronym})" if agency else "",
                    project_type=ptype,
                    location_state="DC",
                    agency_name=agency or "DC Office of Contracting and Procurement",
                    keyword_matches=kw_matches,
                    scraped_at=datetime.now().isoformat(),
                )
                results.append(bid)

            except Exception as e:
                print(f"    [DC OCP] Error parsing solicitation: {e}")

        print(f"    [DC OCP] Construction-related: {len(results)}")
        self.results = results
        return results


# ============================================================
# MONTGOMERY COUNTY MD (Socrata Open Data JSON API)
# ============================================================

class MontgomeryCountyScraper(BaseScraper):
    """
    Montgomery County MD publishes solicitations via Socrata Open Data.
    Returns structured JSON — no HTML scraping needed.
    Dataset: https://data.montgomerycountymd.gov/Government/Active-Solicitations
    """

    def scrape(self) -> List[BidOpportunity]:
        results = []

        api_url = self.config.get(
            "api_url",
            "https://data.montgomerycountymd.gov/resource/di6a-s568.json"
        )

        params = {
            "$order": "issuance_date DESC",
            "$limit": 200,
        }

        print(f"    [MoCo MD] Querying Socrata API...")
        resp = self._fetch(api_url, params=params)
        data = resp.json()

        print(f"    [MoCo MD] Got {len(data)} solicitations from API")

        for record in data:
            try:
                title = record.get("description", "") or record.get("solicitation_title", "") or ""
                sol_number = record.get("solicitation_number", "") or record.get("solicitation", "") or ""
                agency = record.get("department", "") or record.get("agency", "") or ""
                status = record.get("status", "")

                combined = f"{title} {agency} {sol_number}"

                if not self._is_construction_related(combined):
                    continue

                ptype, kw_matches = self._match_keywords(combined)

                # Build URL to the county solicitation page
                source_url = self.config.get("base_url", "")

                bid = BidOpportunity(
                    title=title or sol_number,
                    source="montgomery_county",
                    source_url=source_url,
                    source_id=sol_number or self._generate_source_id("moco", title),
                    description=f"Agency: {agency}" if agency else "",
                    project_type=ptype,
                    location_county="Montgomery County",
                    location_state="MD",
                    agency_name=agency or "Montgomery County MD",
                    posted_date=record.get("issuance_date", ""),
                    due_date=record.get("closing_date", "") or record.get("due_date", ""),
                    keyword_matches=kw_matches,
                    scraped_at=datetime.now().isoformat(),
                )
                results.append(bid)

            except Exception as e:
                print(f"    [MoCo MD] Error parsing record: {e}")

        print(f"    [MoCo MD] Construction-related: {len(results)}")
        self.results = results
        return results


# ============================================================
# eVA VIRGINIA SCRAPER
# ============================================================

class EVAScraper(BaseScraper):
    """
    Scrapes eVA Virginia Business Opportunities (VBO) at mvendor.cgieva.com.
    This is the public posting page for Virginia state procurement.
    Note: Page may use AJAX to load data - if no results are parsed,
    the page likely requires JavaScript rendering.
    """

    def scrape(self) -> List[BidOpportunity]:
        results = []
        base_url = self.config.get("base_url")

        # Try with construction category filter
        params = {"status": "Open"}
        print(f"    [eVA] Fetching {base_url}...")
        resp = self._fetch(base_url, params=params)
        print(f"    [eVA] Response: {resp.status_code}, size: {len(resp.text)} bytes")

        soup = BeautifulSoup(resp.text, "lxml")

        # eVA uses JSP pages - try multiple parsing strategies
        listings = self._find_links_broad(soup)
        print(f"    [eVA] Found {len(listings)} links on page")

        for item in listings:
            try:
                title = item["title"]
                href = item["href"]
                extra = item.get("extra_text", "")
                combined = f"{title} {extra}"

                # Filter for construction-related content
                if not self._is_construction_related(combined):
                    continue

                link = self._make_detail_url(base_url, href)
                ptype, kw_matches = self._match_keywords(combined)
                loc = self._match_location(combined)

                bid = BidOpportunity(
                    title=title,
                    source="eva",
                    source_url=link,
                    source_id=self._generate_source_id("eva", title, href),
                    description=self._clean_text(extra)[:2000],
                    project_type=ptype,
                    location_city=loc.get("city", ""),
                    location_county=loc.get("county", ""),
                    location_state="VA",
                    keyword_matches=kw_matches,
                    scraped_at=datetime.now().isoformat(),
                )
                results.append(bid)
            except Exception as e:
                print(f"    [eVA] Error parsing listing: {e}")

        if not results and len(resp.text) < 5000:
            print(f"    [eVA] Page appears to need JavaScript rendering.")
            print(f"    [eVA] Browse manually: {base_url}")

        print(f"    [eVA] Construction-related results: {len(results)}")
        self.results = results
        return results


# ============================================================
# COUNTY PROCUREMENT SCRAPER (Generic HTML)
# ============================================================

class CountyScraper(BaseScraper):
    """
    Generic scraper for county procurement pages.
    Uses broad CSS selectors and multiple parsing strategies
    to handle different page structures.
    """

    # Navigation / informational link patterns to reject
    _SKIP_PATTERNS = [
        "login", "sign in", "sign up", "register", "contact us",
        "home", "about us", "faq", "help", "privacy",
        "terms of", "sitemap", "search", "menu", "navigation",
        "skip to", "accessibility", "translate", "language",
        "facebook", "twitter", "instagram", "youtube", "linkedin",
        "subscribe", "newsletter", "calendar", "events",
        "how to", "learn more", "read more", "click here",
        "departments", "directory", "staff", "employee",
        "pay online", "report a", "request a", "submit a",
        "map", "hours of operation", "location",
        "news", "press release", "meeting",
        "download", "forms", "application form",
        "job", "career", "employment", "human resources",
        "agendas", "minutes", "board meeting",
        "code of ordinances", "zoning",
        "parks", "recreation", "library",
        "utility", "trash", "recycling", "water bill",
        "permits", "licenses", "inspections",
        "budget report", "financial report", "annual report",
        "view all", "see all", "show all", "back to", "return to",
        "vendor registration", "vendor self-service",
        "copyright", "powered by", "all rights reserved",
        "share this", "print this", "email this",
        # Section headers that are NOT actual bids
        "awarded bids", "current bids", "closed bids", "open bids",
        "bid opening", "bid results", "bid tabulation",
        "bid opportunities", "archived bids", "expired bids",
        "past bids", "active bids", "upcoming bids",
        "collaboration portal", "procurement portal",
        "vendor portal", "supplier portal", "bidder portal",
        "formal solicitations", "informal solicitations",
        "results and awards", "award results",
        "how to bid", "bidding process",
        "procurement home", "purchasing home",
    ]

    # Patterns that strongly indicate a real bid/solicitation listing
    _BID_INDICATORS = [
        "solicitation", "rfp", "rfq", "ifb", "itb",
        "invitation for bid", "request for proposal",
        "request for quote", "request for qualification",
    ]

    # Titles that are just section headers, not real listings
    _SECTION_HEADER_PATTERNS = re.compile(
        r'^(?:awarded|current|closed|open|active|past|archived|expired|upcoming)\s+bids?$'
        r'|^bid\s+(?:opening|results?|tabulation|opportunities|list)',
        re.IGNORECASE,
    )

    def _looks_like_bid_listing(self, title, combined):
        """Check if a link looks like an actual bid/solicitation listing."""
        title_lower = title.lower()
        combined_lower = combined.lower()

        # Reject known section header patterns (e.g. "Awarded Bids", "Current Bids")
        if self._SECTION_HEADER_PATTERNS.search(title):
            return False

        # Strong signal: bid indicator in the TITLE itself (not just surrounding page text)
        if any(ind in title_lower for ind in self._BID_INDICATORS):
            return True

        # Strong signal: has a solicitation number pattern in TITLE
        # e.g. "IFB-2024-001", "RFP 24-12", "Bid #2024-0042", "Sol. 25-001"
        if re.search(r'(?:IFB|RFP|RFQ|ITB|SOL|BID)[\s#.-]*\d', title, re.IGNORECASE):
            return True

        # Strong signal: has a reference number like "24-0012" or "#2024-042" or "PC #194-18537"
        if re.search(r'#?\d{2,4}[-]\d{2,}', title):
            return True

        # Medium signal: construction-related AND substantive title (not just a nav link)
        if len(title) >= 25 and self._is_construction_related(combined):
            return True

        # Weak signal: title contains "bid" + is long enough to be a real listing
        if len(title) >= 30 and re.search(r'\bbids?\b', title_lower):
            return True

        return False

    def scrape(self) -> List[BidOpportunity]:
        results = []
        base_url = self.config.get("base_url")
        name = self.config.get("name", self.source_key)

        print(f"    [{name}] Fetching {base_url}...")
        resp = self._fetch(base_url)
        print(f"    [{name}] Response: {resp.status_code}, size: {len(resp.text)} bytes")

        soup = BeautifulSoup(resp.text, "lxml")

        # Remove nav, header, footer, sidebar to reduce noise
        for tag in soup.select(
            "nav, header, footer, .nav, .header, .footer, "
            "#nav, #header, #footer, .menu, .sidebar, "
            ".breadcrumb, .pagination, .social-links, "
            "#breadcrumb, .dropdown-menu, .mega-menu"
        ):
            tag.decompose()

        # Use broad link-finding strategy
        listings = self._find_links_broad(soup)
        print(f"    [{name}] Found {len(listings)} links on page")

        for item in listings:
            try:
                title = item["title"]
                href = item["href"]
                extra = item.get("extra_text", "")
                combined = f"{title} {extra}"

                # --- Reject obvious non-bid links ---
                if len(title) < 10:
                    continue
                if any(p in title.lower() for p in self._SKIP_PATTERNS):
                    continue

                # --- Must look like a real bid listing ---
                if not self._looks_like_bid_listing(title, combined):
                    continue

                link = self._make_detail_url(base_url, href)
                ptype, kw_matches = self._match_keywords(combined)

                county_name = name.replace(" Procurement", "")
                state = self.config.get("state", "VA")

                bid = BidOpportunity(
                    title=title,
                    source=self.source_key,
                    source_url=link,
                    source_id=self._generate_source_id(self.source_key, title),
                    project_type=ptype,
                    location_county=county_name,
                    location_state=state,
                    agency_name=county_name,
                    keyword_matches=kw_matches,
                    scraped_at=datetime.now().isoformat(),
                )
                results.append(bid)
            except Exception as e:
                print(f"    [{name}] Error parsing listing: {e}")

        if not results:
            body_text = soup.get_text(strip=True)
            if len(body_text) < 500:
                print(f"    [{name}] Page has very little content - may need JavaScript.")
            else:
                print(f"    [{name}] Page has content but no bid listings matched filters.")
                sample_links = [item["title"][:60] for item in listings[:5]]
                if sample_links:
                    print(f"    [{name}] Sample links found: {sample_links}")

        print(f"    [{name}] Bid-related results: {len(results)}")
        self.results = results
        return results


# ============================================================
# BUILDING PERMIT SCRAPER
# ============================================================

class PermitScraper(BaseScraper):
    """Scrapes building permit data for upcoming project leads."""

    def scrape(self) -> List[BidOpportunity]:
        results = []
        base_url = self.config.get("base_url")
        name = self.config.get("name", self.source_key)

        print(f"    [{name}] Fetching {base_url}...")
        resp = self._fetch(base_url)
        print(f"    [{name}] Response: {resp.status_code}, size: {len(resp.text)} bytes")

        soup = BeautifulSoup(resp.text, "lxml")

        # Look for tables with permit data
        commercial_terms = [
            "commercial", "office", "retail", "industrial",
            "renovation", "alteration", "addition", "new construction",
            "tenant", "buildout", "remodel", "restaurant",
            "medical", "dental", "mixed use", "multi-family",
            "parking", "warehouse", "institutional", "municipal",
            "church", "school", "hospital", "hotel",
        ]

        for table in soup.select("table"):
            rows = table.select("tr")
            if len(rows) < 2:
                continue
            for row in rows[1:]:  # Skip header
                cells = row.select("td")
                if len(cells) < 2:
                    continue
                try:
                    text = " ".join(c.get_text(strip=True) for c in cells)
                    if not any(term in text.lower() for term in commercial_terms):
                        continue

                    title = self._clean_text(cells[0].get_text()) if cells else ""
                    ptype, kw_matches = self._match_keywords(text)
                    loc = self._match_location(text)

                    bid = BidOpportunity(
                        title=f"[PERMIT] {title}",
                        source=self.source_key,
                        source_url=base_url,
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
                    print(f"    [{name}] Error parsing permit row: {e}")

        if not results:
            print(f"    [{name}] No permit tables found - site may need JavaScript.")

        print(f"    [{name}] Permit results: {len(results)}")
        self.results = results
        return results


# ============================================================
# BIDNET DIRECT SCRAPER (Authenticated Session)
# ============================================================

class BidNetScraper(BaseScraper):
    """
    Scrapes BidNet Direct using authenticated session login.
    Credentials: BIDNET_EMAIL / BIDNET_PASSWORD env vars, or via Settings page.
    Login is required to access full bid listings and documents.
    """

    LOGIN_URL = "https://www.bidnetdirect.com/public/authentication/login"
    BIDS_URL = "https://www.bidnetdirect.com/virginia/solicitations/open-bids"

    def _login(self) -> bool:
        """Authenticate with BidNet Direct. Returns True on success."""
        email = os.environ.get("BIDNET_EMAIL", "")
        password = os.environ.get("BIDNET_PASSWORD", "")

        if not email or not password:
            print("    [BidNet] No credentials found.")
            print("    [BidNet] Set BIDNET_EMAIL and BIDNET_PASSWORD in Settings or env vars.")
            return False

        # Use realistic browser headers to avoid bot detection
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
        })

        # Step 1: GET login page to get session cookies and CSRF token
        print("    [BidNet] Loading login page...")
        try:
            login_page = self.session.get(self.LOGIN_URL, timeout=20)
            login_page.raise_for_status()
        except Exception as e:
            print(f"    [BidNet] Failed to load login page: {e}")
            return False

        # Extract CSRF token from the login form
        soup = BeautifulSoup(login_page.text, "lxml")
        csrf_token = ""
        csrf_input = soup.select_one('input[name="_csrf"]') or soup.select_one('input[name="csrf"]')
        if csrf_input:
            csrf_token = csrf_input.get("value", "")

        # Also check for meta tag CSRF
        if not csrf_token:
            csrf_meta = soup.select_one('meta[name="_csrf"]') or soup.select_one('meta[name="csrf-token"]')
            if csrf_meta:
                csrf_token = csrf_meta.get("content", "")

        # Step 2: POST login credentials
        print("    [BidNet] Submitting login...")
        login_data = {
            "email": email,
            "password": password,
        }
        if csrf_token:
            login_data["_csrf"] = csrf_token

        try:
            resp = self.session.post(
                self.LOGIN_URL,
                data=login_data,
                timeout=20,
                allow_redirects=True,
            )
            # Check if login succeeded (redirected away from login page, or got 200 on dashboard)
            if "login" in resp.url.lower() and resp.status_code == 200:
                # Still on login page — check for error messages
                error_soup = BeautifulSoup(resp.text, "lxml")
                error_msg = error_soup.select_one(".alert-danger, .error-message, .login-error")
                if error_msg:
                    print(f"    [BidNet] Login failed: {error_msg.get_text(strip=True)}")
                else:
                    print("    [BidNet] Login may have failed (still on login page)")
                return False

            print(f"    [BidNet] Login successful (redirected to {resp.url[:60]}...)")
            return True

        except Exception as e:
            print(f"    [BidNet] Login request failed: {e}")
            return False

    def scrape(self) -> List[BidOpportunity]:
        results = []

        # Try authenticated access first
        logged_in = self._login()
        if not logged_in:
            print("    [BidNet] Falling back to public page scraping...")

        # Fetch open bids page (works with or without auth, but auth gives more data)
        print(f"    [BidNet] Fetching open solicitations...")
        try:
            resp = self._fetch(self.BIDS_URL, timeout=20)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 403:
                print("    [BidNet] Access blocked (403). Site may require JavaScript.")
                print("    [BidNet] Browse manually: https://www.bidnetdirect.com/virginia")
                return []
            raise

        print(f"    [BidNet] Response: {resp.status_code}, size: {len(resp.text)} bytes")

        soup = BeautifulSoup(resp.text, "lxml")

        # Remove navigation noise
        for tag in soup.select("nav, header, footer, .nav, .header, .footer, .sidebar"):
            tag.decompose()

        # BidNet lists solicitations in table rows or div cards
        # Strategy 1: Look for solicitation table rows
        bid_rows = soup.select("table tr, .solicitation-row, .bid-item, .sol-item")
        if not bid_rows:
            # Strategy 2: Look for cards/divs with bid data
            bid_rows = soup.select("div.row, div.card, div.item, article, li.list-group-item")

        print(f"    [BidNet] Found {len(bid_rows)} potential listing elements")

        for row in bid_rows:
            try:
                # Find the main link
                link_tag = row.select_one("a[href]")
                if not link_tag:
                    continue

                title = link_tag.get_text(strip=True)
                href = link_tag.get("href", "")

                if not title or len(title) < 10 or not self._is_valid_href(href):
                    continue

                # Get all text from the row for context
                row_text = row.get_text(strip=True)
                combined = f"{title} {row_text}"

                # Skip navigation links
                if any(p in title.lower() for p in CountyScraper._SKIP_PATTERNS):
                    continue

                # Filter: must be construction-related OR have bid indicators
                is_bid = any(ind in combined.lower() for ind in CountyScraper._BID_INDICATORS)
                is_construction = self._is_construction_related(combined)
                if not is_bid and not is_construction:
                    continue

                detail_url = self._make_detail_url("https://www.bidnetdirect.com", href)
                ptype, kw_matches = self._match_keywords(combined)
                loc = self._match_location(combined)

                # Try to extract closing date from the row
                due_date = ""
                date_match = re.search(
                    r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', row_text
                )
                if date_match:
                    due_date = date_match.group(1)

                # Try to extract agency/org name
                agency = ""
                org_el = row.select_one(".org-name, .agency, .buyer-name, td:nth-of-type(2)")
                if org_el and org_el != link_tag:
                    agency = org_el.get_text(strip=True)

                bid = BidOpportunity(
                    title=title,
                    source="bidnet_direct",
                    source_url=detail_url,
                    source_id=self._generate_source_id("bidnet", title, href),
                    project_type=ptype,
                    location_city=loc.get("city", ""),
                    location_county=loc.get("county", ""),
                    location_state=loc.get("state", "VA"),
                    due_date=due_date,
                    agency_name=agency,
                    keyword_matches=kw_matches,
                    scraped_at=datetime.now().isoformat(),
                )
                results.append(bid)

            except Exception as e:
                print(f"    [BidNet] Error parsing row: {e}")

        # If no structured results, try the generic broad strategy
        if not results:
            print("    [BidNet] No structured bids found, trying broad link scan...")
            listings = self._find_links_broad(soup)
            for item in listings:
                try:
                    title = item["title"]
                    href = item["href"]
                    extra = item.get("extra_text", "")
                    combined = f"{title} {extra}"

                    if len(title) < 15:
                        continue
                    if any(p in title.lower() for p in CountyScraper._SKIP_PATTERNS):
                        continue
                    if not self._is_construction_related(combined):
                        continue

                    detail_url = self._make_detail_url("https://www.bidnetdirect.com", href)
                    ptype, kw_matches = self._match_keywords(combined)

                    bid = BidOpportunity(
                        title=title,
                        source="bidnet_direct",
                        source_url=detail_url,
                        source_id=self._generate_source_id("bidnet", title, href),
                        project_type=ptype,
                        location_state="VA",
                        keyword_matches=kw_matches,
                        scraped_at=datetime.now().isoformat(),
                    )
                    results.append(bid)
                except Exception as e:
                    print(f"    [BidNet] Error parsing listing: {e}")

        if not results:
            body = soup.get_text(strip=True)
            if len(body) < 1000:
                print("    [BidNet] Page has minimal content - may need JavaScript rendering.")
            else:
                print("    [BidNet] Page has content but no construction bids matched filters.")

        print(f"    [BidNet] Construction-related results: {len(results)}")
        self.results = results
        return results


# ============================================================
# OPENGOV PROCUREMENT SCRAPER (Authenticated Session)
# ============================================================

class OpenGovScraper(BaseScraper):
    """
    Scrapes OpenGov Procurement vendor portal.
    Platform: procurement.opengov.com (React SPA)

    Strategy:
    1. Login via form POST to get session cookies
    2. Hit internal API endpoints the React frontend uses
    3. Fall back to embed pages for known agencies
    4. Parse whatever HTML/JSON we can get

    Credentials: OPENGOV_EMAIL / OPENGOV_PASSWORD env vars, or Settings page.
    """

    BASE = "https://procurement.opengov.com"
    LOGIN_URL = "https://procurement.opengov.com/login"

    # Vendor-specific open bids page (React SPA route)
    VENDOR_ID = "410233"  # OAK Builders LLC vendor ID

    # Known agencies in NOVA/DC/MD area that use OpenGov
    EMBED_PORTALS = [
        ("dc", "DC", "DC Dept of General Services"),
    ]

    def _get_browser_headers(self):
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                      "image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

    def _login(self) -> bool:
        """Authenticate with OpenGov Procurement. Returns True on success."""
        email = os.environ.get("OPENGOV_EMAIL", "")
        password = os.environ.get("OPENGOV_PASSWORD", "")

        if not email or not password:
            print("    [OpenGov] No credentials found.")
            print("    [OpenGov] Set OPENGOV_EMAIL and OPENGOV_PASSWORD in Settings or env vars.")
            return False

        self.session.headers.update(self._get_browser_headers())

        # Step 1: GET login page for cookies/CSRF
        print("    [OpenGov] Loading login page...")
        try:
            login_page = self.session.get(self.LOGIN_URL, timeout=20)
        except Exception as e:
            print(f"    [OpenGov] Failed to load login page: {e}")
            return False

        if login_page.status_code == 403:
            print("    [OpenGov] Login page blocked (403). Site requires full browser.")
            return False

        # Extract CSRF token
        soup = BeautifulSoup(login_page.text, "lxml")
        csrf_token = ""
        for selector in [
            'input[name="_csrf"]', 'input[name="csrf"]',
            'input[name="authenticity_token"]', 'input[name="_token"]',
        ]:
            el = soup.select_one(selector)
            if el:
                csrf_token = el.get("value", "")
                break
        if not csrf_token:
            meta = soup.select_one('meta[name="csrf-token"]')
            if meta:
                csrf_token = meta.get("content", "")

        # Step 2: POST login
        print("    [OpenGov] Submitting login...")
        login_data = {"email": email, "password": password}
        if csrf_token:
            login_data["_csrf"] = csrf_token
            login_data["authenticity_token"] = csrf_token

        # Try form POST first
        self.session.headers.update({
            "Referer": self.LOGIN_URL,
            "Origin": self.BASE,
        })

        try:
            resp = self.session.post(
                self.LOGIN_URL,
                data=login_data,
                timeout=20,
                allow_redirects=True,
            )

            if resp.status_code == 403:
                print("    [OpenGov] Login POST blocked (403).")
                # Try JSON login as alternative (many React SPAs use JSON auth)
                return self._try_json_login(email, password)

            if "login" in resp.url.lower() and resp.status_code == 200:
                print("    [OpenGov] Login may have failed (still on login page).")
                return self._try_json_login(email, password)

            print(f"    [OpenGov] Login successful (redirected to {resp.url[:60]})")
            return True

        except Exception as e:
            print(f"    [OpenGov] Login failed: {e}")
            return False

    def _try_json_login(self, email, password) -> bool:
        """Try JSON-based login (common for React SPAs)."""
        print("    [OpenGov] Trying JSON-based login...")

        # Common API login endpoints for React apps
        api_login_urls = [
            f"{self.BASE}/api/auth/login",
            f"{self.BASE}/api/v1/auth/login",
            f"{self.BASE}/api/login",
            f"{self.BASE}/auth/login",
        ]

        json_headers = {
            **self._get_browser_headers(),
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }

        for url in api_login_urls:
            try:
                resp = self.session.post(
                    url,
                    json={"email": email, "password": password},
                    headers=json_headers,
                    timeout=15,
                    allow_redirects=False,
                )
                if resp.status_code in (200, 201, 302):
                    print(f"    [OpenGov] JSON login succeeded at {url}")
                    return True
                if resp.status_code == 403:
                    continue  # Try next endpoint
            except Exception:
                continue

        print("    [OpenGov] All login methods blocked. Site likely requires full browser.")
        return False

    def _scrape_embed_portal(self, org_slug, state, agency_name) -> List[BidOpportunity]:
        """Try scraping an agency's embed portal page."""
        results = []
        url = f"{self.BASE}/portal/embed/{org_slug}/project-list?status=all"

        try:
            resp = self.session.get(url, timeout=20)
            if resp.status_code == 403:
                print(f"    [OpenGov] Embed page blocked for {org_slug}")
                return []

            soup = BeautifulSoup(resp.text, "lxml")
            body_text = soup.get_text(strip=True)

            if len(body_text) < 500:
                print(f"    [OpenGov] {org_slug} embed is JS-only (minimal HTML)")
                return []

            # Try to find project/bid listings
            listings = self._find_links_broad(soup)
            print(f"    [OpenGov] {org_slug} embed: {len(listings)} links found")

            for item in listings:
                title = item["title"]
                href = item["href"]
                extra = item.get("extra_text", "")
                combined = f"{title} {extra}"

                if len(title) < 10:
                    continue
                if any(p in title.lower() for p in CountyScraper._SKIP_PATTERNS):
                    continue
                if not self._is_construction_related(combined):
                    continue

                detail_url = self._make_detail_url(self.BASE, href)
                ptype, kw_matches = self._match_keywords(combined)

                bid = BidOpportunity(
                    title=title,
                    source="opengov",
                    source_url=detail_url,
                    source_id=self._generate_source_id("opengov", org_slug, title),
                    project_type=ptype,
                    location_state=state,
                    agency_name=agency_name,
                    keyword_matches=kw_matches,
                    scraped_at=datetime.now().isoformat(),
                )
                results.append(bid)

        except Exception as e:
            print(f"    [OpenGov] Error scraping {org_slug}: {e}")

        return results

    def _scrape_vendor_page(self) -> List[BidOpportunity]:
        """Try scraping the authenticated vendor open-bids page."""
        results = []
        url = (
            f"{self.BASE}/vendors/{self.VENDOR_ID}/open-bids"
            f"?states=VA%2CDC%2CMD"
        )

        print(f"    [OpenGov] Fetching vendor bids page...")
        try:
            resp = self.session.get(url, timeout=20)
        except Exception as e:
            print(f"    [OpenGov] Failed to fetch vendor page: {e}")
            return []

        if resp.status_code == 403:
            print("    [OpenGov] Vendor page blocked (403)")
            return []

        print(f"    [OpenGov] Vendor page: {resp.status_code}, {len(resp.text)} bytes")

        soup = BeautifulSoup(resp.text, "lxml")

        # Remove nav noise
        for tag in soup.select("nav, header, footer, .nav, .sidebar"):
            tag.decompose()

        # Try to find bid/project listings (React may have server-rendered some content)
        listings = self._find_links_broad(soup)
        print(f"    [OpenGov] Found {len(listings)} links on vendor page")

        for item in listings:
            try:
                title = item["title"]
                href = item["href"]
                extra = item.get("extra_text", "")
                combined = f"{title} {extra}"

                if len(title) < 10:
                    continue
                if any(p in title.lower() for p in CountyScraper._SKIP_PATTERNS):
                    continue

                is_bid = any(ind in combined.lower() for ind in CountyScraper._BID_INDICATORS)
                is_construction = self._is_construction_related(combined)
                if not is_bid and not is_construction:
                    continue

                detail_url = self._make_detail_url(self.BASE, href)
                ptype, kw_matches = self._match_keywords(combined)
                loc = self._match_location(combined)

                due_date = ""
                date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', extra)
                if date_match:
                    due_date = date_match.group(1)

                bid = BidOpportunity(
                    title=title,
                    source="opengov",
                    source_url=detail_url,
                    source_id=self._generate_source_id("opengov", title, href),
                    project_type=ptype,
                    location_city=loc.get("city", ""),
                    location_county=loc.get("county", ""),
                    location_state=loc.get("state", "VA"),
                    due_date=due_date,
                    keyword_matches=kw_matches,
                    scraped_at=datetime.now().isoformat(),
                )
                results.append(bid)
            except Exception as e:
                print(f"    [OpenGov] Error parsing listing: {e}")

        return results

    def scrape(self) -> List[BidOpportunity]:
        results = []

        logged_in = self._login()

        # Strategy 1: Authenticated vendor bids page
        if logged_in:
            vendor_results = self._scrape_vendor_page()
            results.extend(vendor_results)
            if vendor_results:
                print(f"    [OpenGov] Got {len(vendor_results)} from vendor page")

        # Strategy 2: Embed portals for known agencies
        for org_slug, state, agency in self.EMBED_PORTALS:
            embed_results = self._scrape_embed_portal(org_slug, state, agency)
            results.extend(embed_results)

        if not results:
            if not logged_in:
                print("    [OpenGov] No results. Login required — enter credentials in Settings.")
            else:
                print("    [OpenGov] No construction bids found. Site is a React SPA;")
                print("    [OpenGov] data may require JavaScript rendering (Selenium).")
            print(f"    [OpenGov] Browse manually: {self.BASE}/vendors/{self.VENDOR_ID}/open-bids?states=VA,DC,MD")

        print(f"    [OpenGov] Total results: {len(results)}")
        self.results = results
        return results


# ============================================================
# SCRAPER FACTORY
# ============================================================

def get_scraper(source_key: str, source_config: dict) -> BaseScraper:
    """Return the appropriate scraper for a given source."""
    scraper_map = {
        # API-based scrapers (JSON, most reliable)
        "sam_gov": SAMGovScraper,
        "dc_ocp": DCOCPScraper,
        "montgomery_county": MontgomeryCountyScraper,
        # State portals
        "eva": EVAScraper,
        # Authenticated scrapers
        "bidnet_direct": BidNetScraper,
        "opengov": OpenGovScraper,
        # Permit scrapers
        "arlington_permits": PermitScraper,
        "fairfax_permits": PermitScraper,
    }

    scraper_class = scraper_map.get(source_key)
    if scraper_class is None:
        # All other sources use the generic HTML scraper
        return CountyScraper(source_key, source_config)

    return scraper_class(source_key, source_config)
