"""
OAK BUILDERS LLC - Bid Finder v2
Relevance Scoring Engine — 7-Factor Model

Changes from v1:
- Adopted the 7-factor win probability model from the Excel tracker
- Added scope_fit scoring (core competency matching)
- Added bonding_fit scoring (within $1M single / $2M aggregate)
- Added competition/set-aside analysis
- Added negative keyword filtering (returns 0 for poor fits)
- Added commercial project boost (private sector gets extra weight)
- Added "don't miss" flagging for high-probability opportunities
- Budget scoring now uses sweet spot range, not just min/max
- Location scoring differentiates NOVA core vs. extended service area
"""

from datetime import datetime, timedelta
from models import BidOpportunity
from config import KEYWORDS, NEGATIVE_KEYWORDS, LOCATIONS, COMPANY, SCORING


class RelevanceScorer:
    """
    Scores bid opportunities on 0-100 scale.
    Uses weighted factors aligned with Oak Builders' actual win patterns.
    """

    def score(self, bid: BidOpportunity) -> int:
        """Calculate total relevance score."""
        # First check for negative keywords — instant disqualification
        if self._has_negative_keywords(bid):
            bid.scope_category = "poor_fit"
            return 0

        total = 0
        total += self._score_keywords(bid)
        total += self._score_location(bid)
        total += self._score_budget(bid)
        total += self._score_deadline(bid)
        total += self._score_set_aside(bid)
        total += self._score_scope_fit(bid)
        total += self._score_bonding_fit(bid)

        return min(total, 100)

    def calculate_win_probability(self, bid: BidOpportunity) -> int:
        """
        7-factor win probability model (matches Excel tracker).
        Returns 0-100 probability score.
        """
        factors = {
            "scope_fit": self._wp_scope_fit(bid) * 0.25,
            "past_performance": self._wp_past_performance(bid) * 0.20,
            "bonding_fit": self._wp_bonding_fit(bid) * 0.15,
            "competition": self._wp_competition(bid) * 0.15,
            "relationship": self._wp_relationship(bid) * 0.10,
            "pricing_confidence": self._wp_pricing_confidence(bid) * 0.10,
            "timeline_fit": self._wp_timeline_fit(bid) * 0.05,
        }
        return min(int(sum(factors.values())), 100)

    # ── Negative keyword check ──────────────────────────────────────
    def _has_negative_keywords(self, bid: BidOpportunity) -> bool:
        combined = f"{bid.title} {bid.description}".lower()
        for neg in NEGATIVE_KEYWORDS:
            if neg.lower() in combined:
                return True
        return False

    # ── Relevance scoring factors ───────────────────────────────────

    def _score_keywords(self, bid: BidOpportunity) -> int:
        """Keyword relevance (max 25 pts)."""
        max_pts = SCORING["keyword_match"]
        combined = f"{bid.title} {bid.description}".lower()

        matches = []
        for category, kw_list in KEYWORDS.items():
            for kw in kw_list:
                if kw.lower() in combined and kw not in matches:
                    matches.append(kw)

        bid.keyword_matches = matches
        match_count = len(matches)

        if match_count == 0:
            return 0

        # Core competency boost
        core_boost = 0
        core_categories = ["waterproofing", "civil_infrastructure"]
        for cat in core_categories:
            for kw in KEYWORDS.get(cat, []):
                if kw.lower() in combined:
                    core_boost = 6
                    break
            if core_boost:
                break

        # Commercial project boost (these are harder to find)
        commercial_boost = 0
        for kw in KEYWORDS.get("commercial_private", []):
            if kw.lower() in combined:
                commercial_boost = 4
                break

        # Scale based on match density
        if match_count == 1:
            base = 3
        elif match_count == 2:
            base = 7
        elif match_count <= 4:
            base = min(match_count * 3, max_pts - 8)
        else:
            base = min(match_count * 2.5, max_pts - 5)

        return min(int(base + core_boost + commercial_boost), max_pts)

    def _score_location(self, bid: BidOpportunity) -> int:
        """Location proximity (max 20 pts)."""
        max_pts = SCORING["location_match"]

        # Tier 1: NOVA core cities (Falls Church, Arlington, Alexandria, Fairfax)
        nova_core = [
            "falls church", "arlington", "alexandria", "fairfax",
            "vienna", "mclean", "tysons",
        ]
        if bid.location_city:
            city_lower = bid.location_city.lower()
            for city in nova_core:
                if city in city_lower:
                    return max_pts  # Perfect match

        # Tier 2: NOVA extended + DC
        nova_extended = [
            "reston", "herndon", "sterling", "ashburn",
            "springfield", "annandale", "burke", "centreville",
            "chantilly", "manassas", "woodbridge", "lorton",
            "washington", "district of columbia",
        ]
        if bid.location_city:
            city_lower = bid.location_city.lower()
            for city in nova_extended:
                if city in city_lower:
                    return max_pts - 2

        # Tier 3: Close-in Maryland
        md_close = [
            "bethesda", "silver spring", "rockville",
            "college park", "greenbelt", "hyattsville",
        ]
        if bid.location_city:
            city_lower = bid.location_city.lower()
            for city in md_close:
                if city in city_lower:
                    return max_pts - 4

        # County check
        if bid.location_county:
            county_lower = bid.location_county.lower()
            nova_counties = ["arlington", "fairfax", "loudoun", "prince william"]
            for county in nova_counties:
                if county in county_lower:
                    return max_pts - 2

            md_counties = ["montgomery", "prince george"]
            for county in md_counties:
                if county in county_lower:
                    return max_pts - 5

        # ZIP prefix
        if bid.location_zip:
            nova_zips = ["220", "221", "222"]
            dc_zips = ["200", "201", "202", "203"]
            md_zips = ["206", "207", "208", "209", "210"]

            for prefix in nova_zips:
                if bid.location_zip.startswith(prefix):
                    return max_pts - 2
            for prefix in dc_zips:
                if bid.location_zip.startswith(prefix):
                    return max_pts - 3
            for prefix in md_zips:
                if bid.location_zip.startswith(prefix):
                    return max_pts - 5

        # State-level only
        if bid.location_state in ("VA", "Virginia"):
            return 6
        if bid.location_state in ("DC", "MD", "Maryland"):
            return 5

        return 0

    def _score_budget(self, bid: BidOpportunity) -> int:
        """Budget alignment (max 20 pts)."""
        max_pts = SCORING["budget_in_range"]
        sweet_min = COMPANY["project_range"]["sweet_spot_min"]
        sweet_max = COMPANY["project_range"]["sweet_spot_max"]
        hard_min = COMPANY["project_range"]["min"]
        hard_max = COMPANY["project_range"]["max"]

        if bid.estimated_value_min is None and bid.estimated_value_max is None:
            return 0

        val_min = bid.estimated_value_min or 0
        val_max = bid.estimated_value_max or val_min

        # Sweet spot: $100K-$800K
        if val_min >= sweet_min and val_max <= sweet_max:
            return max_pts

        # Within hard range: $25K-$1.5M
        if val_min >= hard_min and val_max <= hard_max:
            return int(max_pts * 0.8)

        # Partially overlaps our range
        if val_min <= hard_max and val_max >= hard_min:
            return int(max_pts * 0.6)

        # Small but doable (under $25K but over $10K)
        if val_max < hard_min and val_max > 10_000:
            return int(max_pts * 0.2)

        # Too large but possible as sub ($1.5M-$3M)
        if val_min > hard_max and val_min <= 3_000_000:
            return int(max_pts * 0.3)

        return 0

    def _score_deadline(self, bid: BidOpportunity) -> int:
        """Deadline feasibility (max 10 pts)."""
        max_pts = SCORING["deadline_buffer"]

        if not bid.due_date:
            return 0

        days = bid.days_until_due
        if days is None:
            return 0

        if days < 0:
            return 0
        elif days < 3:
            return 2  # Very tight
        elif days < 7:
            return int(max_pts * 0.5)
        elif days < 14:
            return int(max_pts * 0.75)
        elif days < 30:
            return max_pts
        else:
            return int(max_pts * 0.9)

    def _score_set_aside(self, bid: BidOpportunity) -> int:
        """Set-aside match (max 10 pts)."""
        max_pts = SCORING["set_aside_match"]

        if not bid.set_aside:
            return 0

        sa = bid.set_aside.lower()

        # We qualify for these
        favorable = [
            "small business", "total small business",
            "sbr", "swam", "micro-purchase",
        ]
        if any(f in sa for f in favorable):
            bid.is_set_aside_match = True
            return max_pts

        # Full and open — we can compete
        if "full and open" in sa or "unrestricted" in sa:
            return int(max_pts * 0.6)

        # Don't qualify (8(a), SDVOSB, HUBZone, WOSB)
        no_qualify = ["8(a)", "sdvosb", "hubzone", "wosb", "edwosb"]
        if any(n in sa for n in no_qualify):
            bid.is_set_aside_match = False
            return 0

        return 2

    def _score_scope_fit(self, bid: BidOpportunity) -> int:
        """Core competency match (max 10 pts). NEW in v2."""
        max_pts = SCORING["scope_fit"]
        combined = f"{bid.title} {bid.description}".lower()

        # Tier 1: Core competencies (waterproofing, envelope, restoration)
        core_terms = KEYWORDS["waterproofing"][:20]  # Top waterproofing terms
        core_hits = sum(1 for t in core_terms if t.lower() in combined)
        if core_hits >= 2:
            bid.scope_category = "core_competency"
            return max_pts

        # Tier 2: Strong adjacency (TI, general reno, civil)
        adjacent_cats = ["tenant_improvements", "civil_infrastructure"]
        adj_hits = 0
        for cat in adjacent_cats:
            for kw in KEYWORDS.get(cat, []):
                if kw.lower() in combined:
                    adj_hits += 1
        if adj_hits >= 2:
            bid.scope_category = "adjacent"
            return int(max_pts * 0.7)

        # Tier 3: General contracting
        gc_hits = sum(1 for kw in KEYWORDS["general_contracting"]
                      if kw.lower() in combined)
        if gc_hits >= 1:
            bid.scope_category = "adjacent"
            return int(max_pts * 0.5)

        # Tier 4: Commercial/private (new territory)
        comm_hits = sum(1 for kw in KEYWORDS.get("commercial_private", [])
                        if kw.lower() in combined)
        if comm_hits >= 1:
            bid.scope_category = "stretch"
            return int(max_pts * 0.4)

        bid.scope_category = "poor_fit"
        return 0

    def _score_bonding_fit(self, bid: BidOpportunity) -> int:
        """Bonding capacity check (max 5 pts). NEW in v2."""
        max_pts = SCORING["bonding_fit"]
        bond_limit = COMPANY["bonding"]["single_project"]

        # No budget info — assume it's within range
        if bid.estimated_value_min is None and bid.estimated_value_max is None:
            return int(max_pts * 0.5)

        val_max = bid.estimated_value_max or bid.estimated_value_min or 0

        # Comfortably within bonding ($0-$800K)
        if val_max <= bond_limit * 0.8:
            return max_pts

        # Within bonding limit ($800K-$1M)
        if val_max <= bond_limit:
            return int(max_pts * 0.8)

        # Over single limit but under aggregate ($1M-$2M)
        if val_max <= COMPANY["bonding"]["aggregate"]:
            return int(max_pts * 0.4)

        # Over aggregate — risky
        return 0

    # ── Win Probability factors ─────────────────────────────────────
    # These mirror the 7-factor model from the Excel bid tracker

    def _wp_scope_fit(self, bid: BidOpportunity) -> int:
        """0-100: Does this match our core work?"""
        cat = bid.scope_category
        if cat == "core_competency":
            return 90
        elif cat == "adjacent":
            return 70
        elif cat == "stretch":
            return 45
        else:
            return 20

    def _wp_past_performance(self, bid: BidOpportunity) -> int:
        """0-100: Have we done similar work / worked with this agency?"""
        score = 30  # Base — we have general construction experience

        # Agency familiarity boost
        known_agencies = {
            "arlington county": 40,
            "gsa": 35,
            "fairfax county": 25,
            "dod": 30,
            "pentagon": 30,
            "library of congress": 20,
            "dc": 15,
            "montgomery county": 10,
        }
        agency_lower = (bid.agency or "").lower()
        for agency, boost in known_agencies.items():
            if agency in agency_lower:
                score += boost
                break

        # Scope familiarity
        if bid.scope_category == "core_competency":
            score += 20
        elif bid.scope_category == "adjacent":
            score += 10

        return min(score, 100)

    def _wp_bonding_fit(self, bid: BidOpportunity) -> int:
        """0-100: Within our bonding capacity?"""
        bond_limit = COMPANY["bonding"]["single_project"]
        val_max = bid.estimated_value_max or bid.estimated_value_min or 0

        if val_max == 0:
            return 60  # Unknown — assume medium fit
        if val_max <= bond_limit * 0.5:
            return 95
        if val_max <= bond_limit * 0.8:
            return 85
        if val_max <= bond_limit:
            return 70
        if val_max <= COMPANY["bonding"]["aggregate"]:
            return 40
        return 15

    def _wp_competition(self, bid: BidOpportunity) -> int:
        """0-100: How competitive is this? Set-asides help."""
        score = 50  # Base assumption

        # Set-aside advantage
        if bid.is_set_aside_match:
            score += 25  # Smaller pool

        # Small project = fewer competitors
        val = bid.estimated_value_max or bid.estimated_value_min or 0
        if 0 < val < 150_000:
            score += 15  # Micro-purchase / simplified
        elif val < 500_000:
            score += 5

        # Known competitor count
        if bid.competitor_count is not None:
            if bid.competitor_count <= 3:
                score += 20
            elif bid.competitor_count <= 6:
                score += 10
            elif bid.competitor_count > 10:
                score -= 15

        return min(max(score, 0), 100)

    def _wp_relationship(self, bid: BidOpportunity) -> int:
        """0-100: Do we know this agency?"""
        known = {
            "arlington county": 80,
            "gsa": 70,
            "fairfax county": 50,
            "city of fairfax": 45,
            "loudoun county": 35,
            "alexandria": 40,
            "pentagon": 65,
            "dod": 60,
        }
        agency_lower = (bid.agency or "").lower()
        for agency, val in known.items():
            if agency in agency_lower:
                return val
        return 20  # No relationship

    def _wp_pricing_confidence(self, bid: BidOpportunity) -> int:
        """0-100: Can we price this accurately?"""
        score = 40  # Base

        if bid.scope_category == "core_competency":
            score += 35  # We know these costs well
        elif bid.scope_category == "adjacent":
            score += 20

        # Detailed description helps pricing
        if bid.description and len(bid.description) > 200:
            score += 10

        # Budget range given = better pricing intel
        if bid.estimated_value_min or bid.estimated_value_max:
            score += 10

        return min(score, 100)

    def _wp_timeline_fit(self, bid: BidOpportunity) -> int:
        """0-100: Can we meet the timeline?"""
        days = bid.days_until_due
        if days is None:
            return 50

        if days < 3:
            return 15  # Very tight
        if days < 7:
            return 40
        if days < 14:
            return 65
        if days < 30:
            return 85
        return 90


def score_opportunities(opportunities: list) -> list:
    """Score and rank a list of opportunities."""
    scorer = RelevanceScorer()
    for opp in opportunities:
        opp.relevance_score = scorer.score(opp)
        opp.win_probability = scorer.calculate_win_probability(opp)
    return sorted(opportunities, key=lambda o: o.relevance_score, reverse=True)
