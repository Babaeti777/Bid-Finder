"""
OAK BUILDERS LLC - Bid Finder v2
Configuration — expanded for commercial + government coverage

Changes from v1:
- Bonding limits corrected to $1M single / $2M aggregate
- Project range widened to $25K-$1.5M (realistic for bonding)
- Added 30+ commercial/private keywords
- Added secondary NAICS codes for broader matching
- Added PlanHub, ConstructConnect, BidClerk sources
- Added commercial plan room sources (DC Metro, Dodge, iSqFt)
- Source tiers reorganised: free APIs first, then open portals, then paid
- Added "negative keywords" to filter out irrelevant hits
- Added pre-qualification and relationship tracking config
"""

import os
import json

# ─── Credential Keys Metadata ────────────────────────────────────────────
CREDENTIAL_KEYS = {
    "SAM_GOV_API_KEY": {"label": "SAM.gov API Key", "type": "api_key", "required_for": ["sam_gov"]},
    "PLANHUB_EMAIL": {"label": "PlanHub Email", "type": "email", "required_for": ["planhub"]},
    "PLANHUB_PASSWORD": {"label": "PlanHub Password", "type": "password", "required_for": ["planhub"]},
    "BIDNET_EMAIL": {"label": "BidNet Email", "type": "email", "required_for": ["bidnet"]},
    "BIDNET_PASSWORD": {"label": "BidNet Password", "type": "password", "required_for": ["bidnet"]},
    "OPENGOV_EMAIL": {"label": "OpenGov Email", "type": "email", "required_for": ["opengov"]},
    "OPENGOV_PASSWORD": {"label": "OpenGov Password", "type": "password", "required_for": ["opengov"]},
    "EVA_EMAIL": {"label": "eVA Email", "type": "email", "required_for": ["eva_virginia"]},
    "EVA_PASSWORD": {"label": "eVA Password", "type": "password", "required_for": ["eva_virginia"]},
    "EMMA_EMAIL": {"label": "eMMA Email", "type": "email", "required_for": ["emma_maryland"]},
    "EMMA_PASSWORD": {"label": "eMMA Password", "type": "password", "required_for": ["emma_maryland"]},
    "GMAIL_ADDRESS": {"label": "Gmail Address", "type": "email", "required_for": []},
    "GMAIL_APP_PASSWORD": {"label": "Gmail App Password", "type": "password", "required_for": []},
    "EMAIL_RECIPIENTS": {"label": "Email Recipients (comma-separated)", "type": "text", "required_for": []},
    "APP_PASSWORD": {"label": "Dashboard Password", "type": "password", "required_for": []},
    "API_TRIGGER_KEY": {"label": "API Trigger Key", "type": "api_key", "required_for": []},
}

# ─── Company Profile ────────────────────────────────────────────────
COMPANY = {
    "name": "OAK Builders LLC",
    "location": "Falls Church, VA 22044",
    "uei": "YM3RMQHPMTF8",
    "cage": "125C2",
    "primary_naics": "236220",
    "secondary_naics": [
        "236210",   # Industrial building construction
        "238190",   # Other foundation/structure/building exterior
        "238310",   # Drywall and insulation
        "238320",   # Painting and wall covering
        "238990",   # All other specialty trade
        "237310",   # Highway, street, and bridge construction
        "561210",   # Facilities support services
    ],
    "certifications": ["Small Business", "SWaM"],
    "bonding": {
        "single_project": 1_000_000,
        "aggregate": 2_000_000,
    },
    "project_range": {
        "min": 25_000,      # Will look at small jobs
        "max": 1_500_000,   # Hard cap = single bond limit + margin
        "sweet_spot_min": 100_000,
        "sweet_spot_max": 800_000,
    },
    "service_area_miles": 60,  # radius from Falls Church
}

# ─── Keywords ────────────────────────────────────────────────────────
# Organised by Oak Builders' actual competencies + commercial expansion
KEYWORDS = {
    "waterproofing": [
        "waterproofing", "building envelope", "moisture barrier",
        "sealant replacement", "caulking", "joint sealant",
        "below grade waterproofing", "above grade waterproofing",
        "exterior restoration", "facade repair", "facade restoration",
        "masonry restoration", "masonry repair", "repointing",
        "tuckpointing", "stone repair", "stone restoration",
        "concrete restoration", "concrete repair", "spall repair",
        "expansion joint", "control joint", "flashing",
        "membrane", "elastomeric coating", "dampproofing",
        "moisture remediation", "leak repair", "water intrusion",
        "curtain wall", "window replacement", "window installation",
        "storefront", "glazing", "weather barrier",
        "air barrier", "vapor barrier", "thermal envelope",
        "building wrap", "exterior insulation", "EIFS",
        "stucco repair", "stucco replacement",
        "parking deck coating", "traffic coating",
        "plaza waterproofing", "green roof", "roof coating",
        "foundation waterproofing", "foundation repair",
        "structural sealant", "structural adhesive",
        "historic preservation", "historic restoration",
    ],
    "tenant_improvements": [
        "tenant improvement", "tenant buildout", "TI project",
        "interior renovation", "interior remodel", "office renovation",
        "office buildout", "commercial interior", "fit-out", "fitout",
        "space renovation", "space buildout", "leasehold improvement",
        "demising wall", "partition wall", "ceiling grid",
        "suspended ceiling", "drop ceiling", "ACT ceiling",
        "flooring replacement", "carpet tile", "LVT", "VCT",
        "millwork", "casework", "cabinetry",
        "ADA renovation", "ADA compliance", "accessibility upgrade",
        "restroom renovation", "bathroom renovation",
        "break room", "kitchenette", "conference room",
        "reception area", "lobby renovation",
        "data center buildout", "server room",
        "interior painting", "wall covering",
        "door replacement", "hardware replacement",
    ],
    "general_contracting": [
        "general contractor", "general construction",
        "renovation", "remodel", "remodeling",
        "building renovation", "facility renovation",
        "roof replacement", "roofing", "roof repair",
        "HVAC replacement", "HVAC upgrade", "mechanical upgrade",
        "plumbing renovation", "electrical upgrade",
        "fire alarm", "fire suppression", "fire protection",
        "fire sprinkler", "life safety",
        "demolition", "selective demolition", "interior demolition",
        "site work", "earthwork", "grading",
        "concrete work", "flatwork", "sidewalk",
        "parking lot", "asphalt", "paving",
        "fencing", "security fencing", "gate installation",
        "loading dock", "overhead door", "roll-up door",
        "elevator modernization", "escalator",
        "generator installation", "emergency power",
        "stormwater management", "drainage",
        "retaining wall", "site wall",
        "canopy", "awning", "shade structure",
        "signage", "wayfinding",
    ],
    # NEW: Commercial-specific terms the email tool would catch
    "commercial_private": [
        "commercial construction", "private development",
        "retail buildout", "retail renovation",
        "restaurant buildout", "restaurant renovation",
        "medical office", "dental office", "clinic buildout",
        "church renovation", "house of worship",
        "school renovation", "educational facility",
        "warehouse buildout", "warehouse renovation",
        "self-storage", "mini storage",
        "mixed-use", "multifamily", "apartment renovation",
        "HOA", "condominium", "condo renovation",
        "hotel renovation", "hospitality",
        "bank branch", "financial institution",
        "gym buildout", "fitness center",
        "daycare", "childcare center",
        "assisted living", "senior living",
        "property management", "building maintenance",
        "capital improvement", "deferred maintenance",
    ],
    # NEW: Civil/infrastructure (Oak has strong civil background)
    "civil_infrastructure": [
        "sidewalk replacement", "trail construction",
        "ADA ramp", "curb and gutter",
        "stormwater pond", "BMP", "SWM facility",
        "water main", "sewer main", "utility replacement",
        "bridge repair", "culvert", "headwall",
        "street repair", "road repair", "mill and overlay",
        "traffic signal", "streetlight",
        "park improvement", "playground",
        "athletic field", "synthetic turf",
    ],
}

# Keywords that indicate a project is NOT a good fit
NEGATIVE_KEYWORDS = [
    "janitorial", "custodial", "cleaning service",
    "lawn care", "mowing", "landscaping maintenance",
    "snow removal", "snow plowing",
    "pest control", "extermination",
    "security guard", "guard services",
    "IT services", "software development",
    "consulting services", "professional services",
    "medical supplies", "office supplies",
    "catering", "food service",
    "vehicle maintenance", "fleet",
    "inspection services only",  # Not construction
    "testing services only",
]

# ─── Locations ───────────────────────────────────────────────────────
LOCATIONS = {
    "cities": [
        # Virginia - NOVA
        "Falls Church", "Arlington", "Alexandria", "Fairfax",
        "Vienna", "McLean", "Tysons", "Reston", "Herndon",
        "Sterling", "Ashburn", "Leesburg", "Centreville",
        "Chantilly", "Manassas", "Woodbridge", "Springfield",
        "Annandale", "Burke", "Lorton", "Fort Belvoir",
        "Quantico", "Dumfries", "Occoquan",
        # DC
        "Washington", "Washington DC", "District of Columbia",
        # Maryland - close-in
        "Bethesda", "Silver Spring", "Rockville", "College Park",
        "Bowie", "Laurel", "Greenbelt", "Hyattsville",
        "Gaithersburg", "Germantown", "Largo", "Fort Meade",
        "Suitland", "Oxon Hill", "National Harbor",
        "Columbia", "Annapolis",
    ],
    "counties": [
        "Arlington County", "Fairfax County", "Loudoun County",
        "Prince William County", "Stafford County",
        "Fauquier County", "City of Alexandria",
        "City of Fairfax", "City of Falls Church",
        "City of Manassas", "City of Manassas Park",
        # Maryland
        "Montgomery County", "Prince George's County",
        "Howard County", "Anne Arundel County",
        "Charles County", "Frederick County",
    ],
    "zip_prefixes": [
        "220", "221", "222", "223",   # Northern Virginia
        "200", "201", "202", "203",   # DC
        "206", "207", "208", "209",   # Maryland close-in
        "210", "211", "212",          # Baltimore corridor
        "201",                         # MD suburbs
    ],
    "states": ["VA", "DC", "MD", "Virginia", "Maryland",
               "District of Columbia"],
}

# ─── Scoring Weights (total = 100) ──────────────────────────────────
# v2: rebalanced to value scope fit + bonding match more
SCORING = {
    "keyword_match":    25,   # Was 30 — still important but not dominant
    "location_match":   20,   # Was 25 — tightened, most sources are local anyway
    "budget_in_range":  20,   # Same — critical for bonding
    "deadline_buffer":  10,   # Was 15 — less weight, we're fast
    "set_aside_match":  10,   # Same
    # NEW factors
    "scope_fit":        10,   # Core competency match (waterproofing/envelope)
    "bonding_fit":       5,   # Within bonding capacity
}

# ─── Data Sources ────────────────────────────────────────────────────
# Reorganised with status flags and scraper class mapping
SOURCES = {
    # === TIER 1: Free APIs (most reliable) ===
    "sam_gov": {
        "enabled": True,
        "name": "SAM.gov",
        "url": "https://api.sam.gov/opportunities/v2/search",
        "type": "api",
        "auth": "api_key",
        "tier": 1,
        "notes": "Federal opportunities. Free API key from api.data.gov",
    },
    "dc_ocp": {
        "enabled": True,
        "name": "DC Office of Contracting & Procurement",
        "url": "https://opendata.dc.gov",
        "type": "api",
        "auth": None,
        "tier": 1,
        "notes": "ArcGIS REST API, no auth needed",
    },
    "montgomery_county": {
        "enabled": True,
        "name": "Montgomery County MD",
        "url": "https://data.montgomerycountymd.gov",
        "type": "api",
        "auth": None,
        "tier": 1,
        "notes": "Socrata Open Data API",
    },

    # === TIER 2: State portals ===
    "eva_virginia": {
        "enabled": True,
        "name": "eVA Virginia",
        "url": "https://eva.virginia.gov",
        "type": "html",
        "auth": None,
        "tier": 2,
        "notes": "Virginia state procurement. May need browser fallback.",
    },
    "emma_maryland": {
        "enabled": True,
        "name": "eMMA Maryland",
        "url": "https://emma.maryland.gov",
        "type": "html",
        "auth": None,
        "tier": 2,
        "notes": "Maryland state procurement",
    },
    "vdot": {
        "enabled": True,
        "name": "Virginia DOT",
        "url": "https://cabb.virginiadot.org",
        "type": "html",
        "auth": None,
        "tier": 2,
        "notes": "Transportation/civil projects",
    },

    # === TIER 3: County/City portals (NOVA) ===
    "arlington_county": {
        "enabled": True,
        "name": "Arlington County",
        "url": "https://www.arlingtonva.us/Government/Programs/Budget-Finance/Purchasing",
        "type": "html",
        "auth": None,
        "tier": 3,
    },
    "fairfax_county": {
        "enabled": True,
        "name": "Fairfax County",
        "url": "https://fairfaxcounty.bonfirehub.com/portal/?tab=openOpportunities",
        "type": "html",
        "auth": None,
        "tier": 3,
    },
    "loudoun_county": {
        "enabled": True,
        "name": "Loudoun County",
        "url": "https://www.loudoun.gov/bids",
        "type": "html",
        "auth": None,
        "tier": 3,
    },
    "prince_william_county": {
        "enabled": True,
        "name": "Prince William County",
        "url": "https://eservice2.pwcgov.org/eservices/procurement/",
        "type": "html",
        "auth": None,
        "tier": 3,
    },
    "alexandria_city": {
        "enabled": True,
        "name": "City of Alexandria",
        "url": "https://www.alexandriava.gov/Purchasing",
        "type": "html",
        "auth": None,
        "tier": 3,
    },
    "fairfax_city": {
        "enabled": True,
        "name": "City of Fairfax",
        "url": "https://www.fairfaxva.gov/government/finance/purchasing",
        "type": "html",
        "auth": None,
        "tier": 3,
    },

    # === TIER 4: Maryland counties ===
    "prince_georges_county": {
        "enabled": True,
        "name": "Prince George's County",
        "url": "https://www.princegeorgescountymd.gov",
        "type": "html",
        "auth": None,
        "tier": 4,
    },
    "howard_county": {
        "enabled": True,
        "name": "Howard County",
        "url": "https://www.howardcountymd.gov",
        "type": "html",
        "auth": None,
        "tier": 4,
    },
    "anne_arundel_county": {
        "enabled": True,
        "name": "Anne Arundel County",
        "url": "https://www.aacounty.org",
        "type": "html",
        "auth": None,
        "tier": 4,
    },

    # === TIER 5: Aggregators (free tier) ===
    "planhub": {
        "enabled": True,
        "name": "PlanHub",
        "url": "https://www.planhub.com",
        "type": "html",
        "auth": "session",
        "tier": 5,
        "notes": "Free for GCs. Covers commercial plan rooms.",
    },
    "bidnet": {
        "enabled": True,
        "name": "BidNet Direct",
        "url": "https://www.bidnetdirect.com",
        "type": "html",
        "auth": "login",
        "tier": 5,
    },
    "opengov": {
        "enabled": True,
        "name": "OpenGov Procurement",
        "url": "https://procurement.opengov.com",
        "type": "html",
        "auth": "login",
        "tier": 5,
    },

    # === TIER 6: University systems ===
    "gmu": {
        "enabled": True,
        "name": "George Mason University",
        "url": "https://fiscal.gmu.edu/purchasing/",
        "type": "html",
        "auth": None,
        "tier": 6,
    },
    "umd": {
        "enabled": True,
        "name": "University of Maryland",
        "url": "https://procurement.umd.edu",
        "type": "html",
        "auth": None,
        "tier": 6,
    },

    # === TIER 7: Permit databases (lead gen) ===
    "arlington_permits": {
        "enabled": True,
        "name": "Arlington Permits",
        "url": "https://building.arlingtonva.us",
        "type": "html",
        "auth": None,
        "tier": 7,
        "notes": "Building permit data for lead generation",
    },
    "fairfax_permits": {
        "enabled": True,
        "name": "Fairfax Permits",
        "url": "https://www.fairfaxcounty.gov/landdevelopment/",
        "type": "html",
        "auth": None,
        "tier": 7,
    },

    # === TIER 8: Paid/subscription (disabled by default) ===
    "dodge": {
        "enabled": False,
        "name": "Dodge Construction Network",
        "url": "https://www.construction.com",
        "type": "api",
        "auth": "subscription",
        "tier": 8,
        "notes": "Enable if subscribed. Best for commercial/private.",
    },
    "isqft": {
        "enabled": False,
        "name": "iSqFt / ConstructConnect",
        "url": "https://www.constructconnect.com",
        "type": "api",
        "auth": "subscription",
        "tier": 8,
        "notes": "Enable if subscribed.",
    },
    "building_connected": {
        "enabled": False,
        "name": "BuildingConnected",
        "url": "https://www.buildingconnected.com",
        "type": "api",
        "auth": "subscription",
        "tier": 8,
    },
    "dc_metro_plan_room": {
        "enabled": False,
        "name": "DC Metro Plan Room",
        "url": "https://dcmetroplanroom.com",
        "type": "html",
        "auth": "subscription",
        "tier": 8,
        "notes": "Regional commercial plan room. Enable if subscribed.",
    },
    "the_blue_book": {
        "enabled": False,
        "name": "The Blue Book",
        "url": "https://www.thebluebook.com",
        "type": "html",
        "auth": "subscription",
        "tier": 8,
    },
}

# ─── Email Configuration ─────────────────────────────────────────────
EMAIL = {
    "enabled": os.environ.get("GMAIL_ADDRESS", "") != "",
    "from_address": os.environ.get("GMAIL_ADDRESS", ""),
    "app_password": os.environ.get("GMAIL_APP_PASSWORD", ""),
    "recipients": [
        r.strip()
        for r in os.environ.get("EMAIL_RECIPIENTS", "").split(",")
        if r.strip()
    ],
    "min_score_to_include": 25,   # Don't email low-relevance junk
    "highlight_threshold": 70,    # Green highlight above this
    "dont_miss_threshold": 80,    # "Don't miss!" flag
}

# ─── Google Sheets ────────────────────────────────────────────────────
SHEETS = {
    "enabled": os.environ.get("GOOGLE_SHEETS_CREDS", "") != "",
    "spreadsheet_name": os.environ.get(
        "SHEETS_SPREADSHEET_NAME", "OAK Bid Pipeline"
    ),
    "credentials_json": os.environ.get("GOOGLE_SHEETS_CREDS", ""),
    "credentials_file": "credentials.json",
    "min_score": 20,
}

# ─── Runtime settings ────────────────────────────────────────────────
SCRAPER_TIMEOUT = 900   # 15 min total per source
REQUEST_TIMEOUT = 30    # Individual HTTP request
RETRY_ATTEMPTS = 2
RETRY_BACKOFF = 5       # seconds between retries
MIN_RELEVANCE_SCORE = 15
DATABASE_FILE = "bids.db"

# ─── Settings override from file ─────────────────────────────────────
def load_settings_override():
    """Load settings.json if it exists to override env vars.

    Settings are stored as flat keys by the dashboard settings page:
      {"sam_gov_api_key": "xxx", "planhub_email": "xxx", ...}
    We map them to the environment variable names the scrapers expect.
    """
    try:
        with open("settings.json") as f:
            settings = json.load(f)

        # Map flat setting keys -> environment variable names
        KEY_TO_ENV = {
            "sam_gov_api_key": "SAM_GOV_API_KEY",
            "planhub_email": "PLANHUB_EMAIL",
            "planhub_password": "PLANHUB_PASSWORD",
            "bidnet_email": "BIDNET_EMAIL",
            "bidnet_password": "BIDNET_PASSWORD",
            "opengov_email": "OPENGOV_EMAIL",
            "opengov_password": "OPENGOV_PASSWORD",
            "eva_email": "EVA_EMAIL",
            "eva_password": "EVA_PASSWORD",
            "emma_email": "EMMA_EMAIL",
            "emma_password": "EMMA_PASSWORD",
            "gmail_address": "GMAIL_ADDRESS",
            "gmail_app_password": "GMAIL_APP_PASSWORD",
            "email_recipients": "EMAIL_RECIPIENTS",
            "app_password": "APP_PASSWORD",
            "api_trigger_key": "API_TRIGGER_KEY",
        }

        for setting_key, env_var in KEY_TO_ENV.items():
            value = settings.get(setting_key, "")
            if value:
                os.environ[env_var] = value

        # Also support legacy nested "credentials" dict (backward compat)
        creds = settings.get("credentials", {})
        for key, value in creds.items():
            if value:
                os.environ[key] = value

        # Override source enabled/disabled
        source_overrides = settings.get("sources", {})
        for source_key, source_settings in source_overrides.items():
            # source_overrides can be {"source_name": {"enabled": True/False}}
            # or {"source_key": True/False}
            if isinstance(source_settings, dict):
                enabled = source_settings.get("enabled", True)
            else:
                enabled = bool(source_settings)
            # Match by source key or by source name
            if source_key in SOURCES:
                SOURCES[source_key]["enabled"] = enabled
            else:
                # Try matching by name
                for sk, cfg in SOURCES.items():
                    if cfg.get("name") == source_key:
                        cfg["enabled"] = enabled
                        break

        return settings
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
