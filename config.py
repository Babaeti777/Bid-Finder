"""
OAK BUILDERS LLC - Commercial Project Bid Finder
Configuration & Settings
"""

# ============================================================
# COMPANY PROFILE
# ============================================================
COMPANY = {
    "name": "OAK Builders LLC",
    "location": "Falls Church, VA",
    "service_area": "Northern Virginia (NOVA) / DC / MD / VA",
    "naics_codes": [
        "238390",  # Other Building Finishing Contractors (Waterproofing)
        "236220",  # Commercial and Institutional Building Construction
        "238190",  # Other Foundation, Structure, and Building Exterior Contractors
        "238990",  # All Other Specialty Trade Contractors
        "238160",  # Roofing Contractors (roofing/waterproofing overlap)
        "238140",  # Masonry Contractors (facade/exterior repair)
        "238310",  # Drywall and Insulation Contractors (TI work)
        "238320",  # Painting and Wall Covering Contractors (coatings)
        "561210",  # Facilities Support Services (government O&M)
    ],
    "cage_code": "",       # Fill in if registered
    "uei_number": "",      # Fill in your SAM.gov UEI
    "sam_registered": True,
    "eva_registered": True,
    "project_range": {
        "min": 50_000,
        "max": 2_500_000,
    },
}

# ============================================================
# SEARCH KEYWORDS BY PROJECT TYPE
# ============================================================
KEYWORDS = {
    "waterproofing": [
        # Top 15: most common procurement terms first (used by county pre-filter)
        "waterproofing",
        "building envelope",
        "caulking",
        "leak repair",
        "sealant replacement",
        "moisture remediation",
        "envelope repair",
        "foundation waterproofing",
        "roof leak",
        "moisture barrier",
        "dampproofing",
        "flashing repair",
        "drainage system",
        "weatherproofing",
        "foundation repair",
        # Core waterproofing
        "water intrusion",
        "water infiltration",
        "below grade waterproofing",
        "exterior wall coating",
        "plaza deck waterproofing",
        "parking deck coating",
        "joint sealant",
        "elastomeric coating",
        # Membrane & coatings
        "membrane",
        "cementitious coating",
        "crystalline waterproofing",
        "traffic coating",
        "polyurethane coating",
        "sheet membrane",
        "liquid membrane",
        "hot rubberized asphalt",
        "bentonite",
        "protective coating",
        "deck coating",
        # Injection & structural sealing
        "epoxy injection",
        "crack injection",
        "expansion joint",
        "control joint",
        "vapor barrier",
        "water management",
        # Leak-related
        "negative-side waterproofing",
        "positive-side waterproofing",
        "curtain wall repair",
        "window leak",
        "below-slab drainage",
        "hydrostatic pressure",
        "wet basement",
        # New: procurement-language variants
        "moisture control",
        "moisture mitigation",
        "water seepage",
        "waterstop",
        "water stop",
        "basement waterproofing",
        "foundation sealing",
        "building envelope restoration",
        "envelope restoration",
        "exterior caulking",
        "re-caulking",
        "recaulking",
        "joint seal",
        "joint repair",
        "garage deck repair",
        "tunnel waterproofing",
        "tank lining",
        "water remediation",
    ],
    "tenant_improvements": [
        # Top 15: most common procurement terms first (used by county pre-filter)
        "tenant improvement",
        "interior renovation",
        "interior alterations",
        "office renovation",
        "leasehold improvement",
        "commercial renovation",
        "interior construction",
        "restroom renovation",
        "tenant buildout",
        "interior fit-out",
        "interior alteration",
        "interior modifications",
        "office remodel",
        "suite renovation",
        "commercial interior",
        # Core TI
        "tenant build-out",
        "TI project",
        "TI buildout",
        "office buildout",
        "space renovation",
        "commercial upfit",
        # Specific buildout types
        "space buildout",
        "workspace renovation",
        "workspace buildout",
        "retail buildout",
        "restaurant buildout",
        "medical office buildout",
        "dental office buildout",
        "law office renovation",
        "fit-up",
        "upfit",
        "build out",
        "office alterations",
        # Interior systems
        "demising wall",
        "drop ceiling",
        "suspended ceiling",
        "partition wall",
        "commercial flooring",
        "commercial painting",
        "millwork",
        "cabinetry",
        "reception area",
        "conference room renovation",
        "break room",
        "ADA restroom",
        "interior finish",
        "finish work",
        # Room-specific renovations
        "laboratory renovation",
        "laboratory buildout",
        "clinic renovation",
        "clinic buildout",
        "classroom renovation",
        "locker room renovation",
        "kitchen renovation",
        "cafeteria renovation",
        # MEP & specialty
        "commercial plumbing",
        "commercial electrical",
        "data cabling",
        "access flooring",
        "storefront",
        "signage",
    ],
    "general_contracting": [
        # Top 15: most common procurement terms first (used by county pre-filter)
        "building renovation",
        "facility renovation",
        "construction services",
        "building repair",
        "concrete repair",
        "roof repair",
        "general construction",
        "building maintenance",
        "facility improvement",
        "commercial construction",
        "facility repair",
        "building services",
        "repair services",
        "general contractor",
        "building alteration",
        # Core GC
        "ADA compliance",
        "HVAC replacement",
        "façade repair",
        "facade repair",
        "door replacement",
        "flooring replacement",
        "painting contractor",
        "demolition",
        "site work",
        # Structural & exterior
        "commercial remodel",
        "structural repair",
        "masonry repair",
        "brick repair",
        "stucco repair",
        "exterior renovation",
        "window replacement",
        "curtain wall",
        "storefront replacement",
        "canopy",
        "awning",
        "loading dock",
        "parking garage repair",
        "elevator modernization",
        # Demolition & abatement
        "interior demolition",
        "selective demolition",
        "abatement",
        "hazmat",
        "asbestos",
        "lead paint",
        # Damage & emergency
        "fire damage",
        "water damage",
        "storm damage",
        "emergency repair",
        # Maintenance & capital
        "preventive maintenance",
        "capital improvement",
        "deferred maintenance",
        # Roofing
        "commercial roofing",
        "TPO",
        "EPDM",
        "standing seam",
        "roof replacement",
        # Delivery methods
        "turnkey",
        "design-build",
        "CM at risk",
        "construction management",
        # Specialty
        "metal building",
        "pre-engineered building",
        "sitework",
        "grading",
        "paving",
        # New: procurement-language variants
        "general construction services",
        "facility upgrade",
        "facility modification",
        "building modification",
        "repair and renovation",
        "miscellaneous construction",
        "minor repair",
        "major repair",
        "life safety",
        "fire alarm",
        "fire suppression",
        "sprinkler",
        "accessibility",
        "ADA upgrade",
        "ADA modification",
        "concrete restoration",
        "spall repair",
        "expansion joint repair",
        "caulk",
        "sealant",
        "power washing",
        "pressure washing",
        "exterior cleaning",
        "framing",
        "insulation",
        "metal stud",
    ],
    "government": [
        # Top 15: most common procurement terms first (used by county pre-filter)
        "IDIQ",
        "task order",
        "construction services",
        "facility maintenance",
        "job order contract",
        "design build",
        "operations and maintenance",
        "repair and alteration",
        "solicitation",
        "RFP",
        "IFB",
        "federal building",
        "government facility",
        "military construction",
        "small business set-aside",
        # Contract vehicles & set-asides
        "JOC",
        "8a set-aside",
        "SDVOSB",
        "HUBZone",
        "maintenance repair",
        "BPA",
        "blanket purchase agreement",
        "GSA schedule",
        "indefinite delivery",
        "indefinite quantity",
        "requirements contract",
        "WOSB",
        "EDWOSB",
        "service-disabled veteran",
        # Solicitation types
        "RFQ",
        "invitation for bid",
        "request for proposal",
        "request for quotation",
        "sources sought",
        "presolicitation",
        "pre-solicitation",
        # Operations & maintenance
        "base operations",
        "O&M",
        "minor construction",
        # Military & federal
        "sustainment restoration modernization",
        "SRM",
        "MILCON",
        "MATOC",
        "SATOC",
        "MACC",
        "military base",
        "VA hospital",
        "federal courthouse",
        "post office",
        "government housing",
        "GSA building",
        "guard station",
        "barracks",
        # Federal agencies
        "NAVFAC",
        "USACE",
        "Army Corps",
        "GSA",
    ],
}

# ============================================================
# SCRAPER FILTER TERMS (shared across all scrapers)
# ============================================================
# Broad terms used by scrapers to pre-filter listings before
# keyword scoring. Expanding this list widens the net for ALL scrapers.
SCRAPER_FILTER_TERMS = [
    # Generic procurement words (appear in almost every solicitation)
    "construction", "building", "renovation", "repair", "maintenance",
    "facility", "contractor", "services", "project", "work",
    "contract", "bid", "alterations", "modifications", "improvements",
    "refurbishment", "rehabilitation",
    # Trades & scopes
    "waterproof", "roofing", "hvac", "plumbing", "electrical",
    "demolition", "painting", "flooring", "concrete", "masonry",
    "carpentry", "drywall", "ceiling", "mechanical", "fire protection",
    "elevator", "sitework", "grading", "paving", "landscaping",
    "fencing", "ADA", "abatement", "remediation", "restoration",
    "remodel", "tenant", "buildout", "fit-out", "improvement",
    "general contractor", "subcontractor", "architect",
    "engineering", "structural", "exterior", "interior",
    "sprinkler", "fire alarm", "life safety", "caulk", "sealant",
    "coating", "pressure washing", "insulation", "framing",
    # Building & facility types
    "commercial", "industrial", "institutional", "municipal",
    "courthouse", "hospital", "school", "university",
    "office", "retail", "warehouse", "parking",
    "library", "fire station", "recreation center", "community center",
    "gymnasium", "garage", "bridge", "tunnel",
    "church", "museum", "theater", "arena", "transit",
    # Infrastructure & systems
    "stormwater", "utilities", "sewer", "water main",
    "door", "window", "roof", "facade", "envelope",
    "modernization", "upgrade", "replacement", "installation",
]

# ============================================================
# GEOGRAPHIC FILTERS (NOVA Focus)
# ============================================================
LOCATIONS = {
    "counties": [
        "Arlington County",
        "Fairfax County",
        "Loudoun County",
        "Prince William County",
        "Fauquier County",
        "Stafford County",
    ],
    "cities": [
        "Falls Church",
        "Alexandria",
        "Fairfax",
        "Manassas",
        "Manassas Park",
        "Herndon",
        "Reston",
        "Vienna",
        "McLean",
        "Tysons",
        "Ashburn",
        "Leesburg",
        "Sterling",
        "Centreville",
        "Chantilly",
        "Springfield",
        "Woodbridge",
        "Annandale",
        "Burke",
    ],
    "zip_prefixes": ["201", "220", "221", "222"],
    "extended_area": {
        "dc": True,
        "maryland": [
            "Montgomery County",
            "Prince George's County",
            "Bethesda",
            "Rockville",
            "Silver Spring",
            "College Park",
        ],
    },
}

# ============================================================
# DATA SOURCES
# ============================================================
SOURCES = {
    # ==========================================================
    # FREE GOVERNMENT — API-based (most reliable)
    # ==========================================================
    "sam_gov": {
        "name": "SAM.gov (Federal)",
        "base_url": "https://sam.gov/search/?index=opp",
        "api_url": "https://api.sam.gov/prod/opportunities/v2/search",
        "api_key_env": "SAM_GOV_API_KEY",
        "enabled": True,
        "type": "government",
        "cost": "free",
    },
    "dc_ocp": {
        "name": "DC Office of Contracting & Procurement",
        "base_url": "https://contracts.ocp.dc.gov/solicitations/search",
        "api_url": "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Government_Operations/MapServer/19/query",
        "enabled": True,
        "type": "government",
        "cost": "free",
    },
    "montgomery_county": {
        "name": "Montgomery County MD (Open Data)",
        "base_url": "https://www.montgomerycountymd.gov/PRO/solicitations/formal-solicitations.html",
        "api_url": "https://data.montgomerycountymd.gov/resource/di6a-s568.json",
        "enabled": True,
        "type": "government",
        "cost": "free",
    },

    # ==========================================================
    # FREE GOVERNMENT — HTML scraping (server-rendered)
    # ==========================================================
    "eva": {
        "name": "eVA (Virginia)",
        "base_url": "https://mvendor.cgieva.com/Vendor/public/AllOpportunities.jsp",
        "enabled": True,
        "type": "government",
        "cost": "free",
    },
    "arlington_county": {
        "name": "Arlington County Procurement",
        "base_url": "https://vrapp.vendorregistry.com/Bids/View/BidsList?BuyerId=a596c7c4-0123-4202-bf15-3583300ee088",
        "enabled": True,
        "type": "government",
        "cost": "free",
    },
    "loudoun_county": {
        "name": "Loudoun County Procurement",
        "base_url": "https://www.loudoun.gov/Bids.aspx",
        "enabled": True,
        "type": "government",
        "cost": "free",
    },
    "prince_william": {
        "name": "Prince William County Procurement",
        "base_url": "https://eservice2.pwcgov.org/eservices/procurement/",
        "enabled": True,
        "type": "government",
        "cost": "free",
    },
    "city_of_alexandria": {
        "name": "City of Alexandria Procurement",
        "base_url": "https://www.alexandriava.gov/purchasing/current-solicitations",
        "enabled": True,
        "type": "government",
        "cost": "free",
    },
    "city_of_fairfax": {
        "name": "City of Fairfax Procurement",
        "base_url": "https://www.fairfaxva.gov/government/finance/procurement/current-solicitations",
        "enabled": True,
        "type": "government",
        "cost": "free",
    },
    "prince_georges_county": {
        "name": "Prince George's County MD Procurement",
        "base_url": "https://www.princegeorgescountymd.gov/Bids.aspx",
        "enabled": True,
        "type": "government",
        "cost": "free",
    },
    "city_of_manassas": {
        "name": "City of Manassas Procurement",
        "base_url": "https://www.manassasva.gov/purchasing/bid_postings.php",
        "enabled": True,
        "type": "government",
        "cost": "free",
    },
    "stafford_county": {
        "name": "Stafford County Procurement",
        "base_url": "https://staffordcountyva.gov/government/finance/central_procurement_division/bid_opportunities.php",
        "enabled": True,
        "type": "government",
        "cost": "free",
    },

    # ==========================================================
    # FREE GOVERNMENT — JavaScript SPAs (may return limited results)
    # ==========================================================
    "fairfax_county": {
        "name": "Fairfax County Procurement",
        "base_url": "https://fairfaxcounty.bonfirehub.com/portal/?tab=openOpportunities",
        "enabled": True,  # Bonfire SPA - may need JS, will try anyway
        "type": "government",
        "cost": "free",
    },
    "emma_maryland": {
        "name": "eMarylandMarketplace (eMMA)",
        "base_url": "https://emma.maryland.gov/page.aspx/en/rfp/request_browse_public",
        "enabled": True,  # Ivalua SPA - may need JS, will try anyway
        "type": "government",
        "cost": "free",
    },
    "bidnet_direct": {
        "name": "BidNet Direct (Free Tier)",
        "base_url": "https://www.bidnetdirect.com/virginia",
        "enabled": True,  # SOVRA SPA - may need JS, will try anyway
        "type": "commercial",
        "cost": "free",
    },

    # ==========================================================
    # COMMERCIAL / PAID (enabled when credentials are configured)
    # ==========================================================
    "dodge_construction": {
        "name": "Dodge Construction Network",
        "base_url": "https://www.construction.com",
        "enabled": False,  # Requires paid subscription ~$400/mo
        "type": "commercial",
        "cost": "paid",
    },
    "building_connected": {
        "name": "BuildingConnected",
        "base_url": "https://www.buildingconnected.com",
        "enabled": False,  # Free basic, ~$150/mo pro
        "type": "commercial",
        "cost": "paid",
    },
    "the_blue_book": {
        "name": "The Blue Book",
        "base_url": "https://www.thebluebook.com",
        "enabled": True,  # Free, may need JS
        "type": "commercial",
        "cost": "free",
    },

    # ==========================================================
    # PERMIT DATA
    # ==========================================================
    "arlington_permits": {
        "name": "Arlington County Building Permits",
        "base_url": "https://permits.arlingtonva.us/",
        "enabled": True,  # May need JS, will try
        "type": "permits",
        "cost": "free",
    },
    "fairfax_permits": {
        "name": "Fairfax County Building Permits",
        "base_url": "https://www.fairfaxcounty.gov/landdevelopment/building-permits",
        "enabled": True,  # Info page - will try to find links
        "type": "permits",
        "cost": "free",
    },
}

# Paid sources not yet integrated - configure via Settings in dashboard (http://localhost:8080):
# - ConstructConnect (constructconnect.com) ~$300/mo
# - iSqFt (isqft.com) ~$200/mo
# - PlanHub (planhub.com) - free basic tier
# - BidClerk (bidclerk.com) ~$250/mo

# ============================================================
# SCORING / RELEVANCE WEIGHTS
# ============================================================
SCORING = {
    "keyword_match": 30,        # Max points for keyword relevance
    "location_match": 25,       # Max points for NOVA location
    "budget_in_range": 20,      # Points if budget fits $50K-$2.5M
    "deadline_buffer": 15,      # Points for adequate response time
    "set_aside_match": 10,      # Points for matching set-asides
}

# ============================================================
# NOTIFICATION SETTINGS
# ============================================================
NOTIFICATIONS = {
    "email": {
        "enabled": False,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "sender_email": "",       # Gmail address
        "sender_password": "",    # Gmail App Password (not regular password)
        "recipients": [],         # List of email addresses
    },
    "min_score_to_notify": 60,  # Only notify for high-relevance bids
    "digest_frequency": "daily",
}

# ============================================================
# GOOGLE SHEETS SETTINGS
# ============================================================
GOOGLE_SHEETS = {
    "enabled": False,
    "spreadsheet_name": "OAK Builders - Bid Tracker",
    "service_account_file": "service_account.json",
    "worksheet_name": "Bids",
}

# ============================================================
# OUTPUT SETTINGS
# ============================================================
OUTPUT = {
    "database": "oak_bids.db",
    "export_formats": ["csv", "xlsx", "json"],
    "dashboard_port": 8050,
    "max_results_per_source": 50,
    "dedup_threshold": 0.85,  # Similarity threshold for dedup
}


# ============================================================
# SETTINGS OVERRIDE (loads from settings.json if present)
# ============================================================
def load_settings_override():
    """Load settings.json overrides if the file exists."""
    import json as _json
    from pathlib import Path as _Path

    settings_file = _Path(__file__).parent / "settings.json"
    if not settings_file.exists():
        return

    with open(settings_file) as f:
        s = _json.load(f)

    if s.get("gmail_address"):
        NOTIFICATIONS["email"]["sender_email"] = s["gmail_address"]
        NOTIFICATIONS["email"]["sender_password"] = s.get("gmail_app_password", "")
        NOTIFICATIONS["email"]["recipients"] = s.get("email_recipients", [])
        NOTIFICATIONS["email"]["enabled"] = True

    if s.get("google_sheets_enabled"):
        GOOGLE_SHEETS["enabled"] = True
        GOOGLE_SHEETS["spreadsheet_name"] = s.get(
            "google_sheet_name", GOOGLE_SHEETS["spreadsheet_name"]
        )

    if s.get("sam_gov_api_key"):
        import os
        os.environ.setdefault("SAM_GOV_API_KEY", s["sam_gov_api_key"])

    for key, creds in s.get("paid_sources", {}).items():
        if key in SOURCES and creds.get("enabled"):
            SOURCES[key]["enabled"] = True


# Auto-load on import
load_settings_override()
