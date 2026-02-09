"""
OAK BUILDERS LLC - Bid Finder
Relevance Scoring Engine
"""

from datetime import datetime, timedelta
from models import BidOpportunity
from config import KEYWORDS, LOCATIONS, COMPANY, SCORING


class RelevanceScorer:
    """
    Scores bid opportunities based on relevance to OAK Builders.
    Higher score = better fit. Max score = 100.
    """

    def score(self, bid: BidOpportunity) -> int:
        """Calculate total relevance score for a bid opportunity."""
        total = 0
        total += self._score_keywords(bid)
        total += self._score_location(bid)
        total += self._score_budget(bid)
        total += self._score_deadline(bid)
        total += self._score_set_aside(bid)
        return min(total, 100)

    def _score_keywords(self, bid: BidOpportunity) -> int:
        """Score based on keyword matches (max 30 pts)."""
        max_pts = SCORING["keyword_match"]
        combined = f"{bid.title} {bid.description}".lower()

        # Direct keyword matches
        match_count = len(bid.keyword_matches)
        if match_count == 0:
            # Rescan if no matches stored yet
            for kw_list in KEYWORDS.values():
                for kw in kw_list:
                    if kw.lower() in combined:
                        match_count += 1

        if match_count == 0:
            return 0

        # Waterproofing projects get a boost (core specialty)
        waterproofing_boost = 0
        for kw in KEYWORDS["waterproofing"]:
            if kw.lower() in combined:
                waterproofing_boost = 5
                break

        base = min(match_count * 5, max_pts - 5)
        return min(base + waterproofing_boost, max_pts)

    def _score_location(self, bid: BidOpportunity) -> int:
        """Score based on proximity to NOVA (max 25 pts)."""
        max_pts = SCORING["location_match"]

        # Check city match
        if bid.location_city:
            for city in LOCATIONS["cities"]:
                if city.lower() in bid.location_city.lower():
                    return max_pts  # Perfect NOVA match

        # Check county match
        if bid.location_county:
            for county in LOCATIONS["counties"]:
                if county.lower().replace(" county", "") in bid.location_county.lower():
                    return max_pts

        # Check zip code
        if bid.location_zip:
            for prefix in LOCATIONS["zip_prefixes"]:
                if bid.location_zip.startswith(prefix):
                    return max_pts - 3

        # Check state-level
        if bid.location_state in ("VA", "Virginia"):
            return max_pts // 2  # In-state but not confirmed NOVA
        if bid.location_state in ("DC", "MD", "Maryland"):
            return max_pts // 2  # Extended service area

        # If location unknown, give partial credit
        if not bid.location_city and not bid.location_county and not bid.location_state:
            return 5

        return 0

    def _score_budget(self, bid: BidOpportunity) -> int:
        """Score based on project value range (max 20 pts)."""
        max_pts = SCORING["budget_in_range"]
        our_min = COMPANY["project_range"]["min"]
        our_max = COMPANY["project_range"]["max"]

        # If no budget info, give partial credit
        if bid.estimated_value_min is None and bid.estimated_value_max is None:
            return max_pts // 3

        val_min = bid.estimated_value_min or 0
        val_max = bid.estimated_value_max or val_min

        # Perfect fit: project range overlaps with our range
        if val_min >= our_min and val_max <= our_max:
            return max_pts
        # Partially overlaps
        if val_min <= our_max and val_max >= our_min:
            return int(max_pts * 0.7)
        # Too small (under $50K) - might still be worth it
        if val_max < our_min and val_max > 20_000:
            return int(max_pts * 0.3)
        # Too large (over $2.5M) - could be a subcontracting opportunity
        if val_min > our_max and val_min < 5_000_000:
            return int(max_pts * 0.4)

        return 0

    def _score_deadline(self, bid: BidOpportunity) -> int:
        """Score based on response time available (max 15 pts)."""
        max_pts = SCORING["deadline_buffer"]

        if not bid.due_date:
            return max_pts // 2  # Unknown deadline

        try:
            # Try multiple date formats
            due = None
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%dT%H:%M:%S"]:
                try:
                    due = datetime.strptime(bid.due_date[:10], fmt[:min(len(fmt), len(bid.due_date))])
                    break
                except ValueError:
                    continue

            if not due:
                return max_pts // 3

            days_left = (due - datetime.now()).days

            if days_left < 0:
                return 0  # Already past due
            elif days_left < 3:
                return 3  # Very tight
            elif days_left < 7:
                return int(max_pts * 0.5)
            elif days_left < 14:
                return int(max_pts * 0.75)
            elif days_left < 30:
                return max_pts
            else:
                return int(max_pts * 0.9)  # Plenty of time

        except Exception:
            return max_pts // 3

    def _score_set_aside(self, bid: BidOpportunity) -> int:
        """Score based on set-aside match (max 10 pts)."""
        max_pts = SCORING["set_aside_match"]

        if not bid.set_aside:
            return max_pts // 2  # Open competition is fine

        sa = bid.set_aside.lower()

        # Favorable set-asides for small business
        favorable = ["small business", "8(a)", "hubzone", "sdvosb", "wosb", "total small"]
        if any(f in sa for f in favorable):
            return max_pts

        # Full and open
        if "full and open" in sa or "unrestricted" in sa:
            return max_pts // 2

        return 2  # Other set-asides (might not qualify)


def score_opportunities(opportunities: list) -> list:
    """Score a list of opportunities and sort by relevance."""
    scorer = RelevanceScorer()
    for opp in opportunities:
        opp.relevance_score = scorer.score(opp)
    return sorted(opportunities, key=lambda o: o.relevance_score, reverse=True)
