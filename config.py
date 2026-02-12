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
        # Core waterproofing
        "waterproofing",
        "water intrusion",
        "water infiltration",
        "moisture remediation",
        "below grade waterproofing",
        "foundation waterproofing",
        "envelope repair",
        "building envelope",
        "caulking",
        "sealant replacement",
        "flashing repair",
        "leak repair",
        "moisture barrier",
        "dampproofing",
        "exterior wall coating",
        "plaza deck waterproofing",
        "parking deck coating",
        "joint sealant",
        "elastomeric coating",
        "drainage system",
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
        "roof leak",
        "below-slab drainage",
        "hydrostatic pressure",
        "wet basement",
    ],
    "tenant_improvements": [
        # Core TI
        "tenant improvement",
        "tenant buildout",
        "tenant build-out",
        "TI project",
        "TI buildout",
        "interior renovation",
        "office renovation",
        "office buildout",
        "interior fit-out",
        "commercial renovation",
        "interior construction",
        "space renovation",
        "leasehold improvement",
        "commercial interior",
        "office remodel",
        "suite renovation",
        "commercial upfit",
        # Specific buildout types
        "space buildout",
        "workspace renovation",
        "retail buildout",
        "restaurant buildout",
        "medical office buildout",
        "dental office buildout",
        "law office renovation",
        "fit-up",
        "upfit",
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
        # MEP & specialty
        "commercial plumbing",
        "commercial electrical",
        "data cabling",
        "access flooring",
        "storefront",
        "signage",
    ],
    "general_contracting": [
        # Core GC
        "general contractor",
        "general construction",
        "commercial construction",
        "building renovation",
        "facility renovation",
        "facility improvement",
        "building repair",
        "ADA compliance",
        "restroom renovation",
        "HVAC replacement",
        "roof repair",
        "concrete repair",
        "façade repair",
        "facade repair",
        "door replacement",
        "flooring replacement",
        "painting contractor",
        "demolition",
        "site work",
        # Structural & exterior
        "commercial remodel",
        "building maintenance",
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
    ],
    "government": [
        # Contract vehicles
        "IDIQ",
        "task order",
        "design build",
        "job order contract",
        "JOC",
        "8a set-aside",
        "small business set-aside",
        "SDVOSB",
        "HUBZone",
        "maintenance repair",
        "facility maintenance",
        "government facility",
        "federal building",
        "military construction",
        # Additional contract types
        "BPA",
        "blanket purchase agreement",
        "GSA schedule",
        "indefinite delivery",
        "indefinite quantity",
        "requirements contract",
        # Operations & maintenance
        "base operations",
        "O&M",
        "operations and maintenance",
        "construction services",
        "minor construction",
        "repair and alteration",
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
    ],
}

# ============================================================
# SCRAPER FILTER TERMS (shared across all scrapers)
# ============================================================
# Broad terms used by scrapers to pre-filter listings before
# keyword scoring. Expanding this list widens the net for ALL scrapers.
SCRAPER_FILTER_TERMS = [
    "construction", "building", "renovation", "repair", "maintenance",
    "facility", "contractor", "waterproof", "roofing", "hvac",
    "plumbing", "electrical", "demolition", "painting", "flooring",
    "concrete", "masonry", "carpentry", "drywall", "ceiling",
    "mechanical", "fire protection", "elevator", "sitework",
    "grading", "paving", "landscaping", "fencing", "ADA",
    "abatement", "remediation", "restoration", "remodel",
    "tenant", "buildout", "fit-out", "improvement",
    "general contractor", "subcontractor", "architect",
    "engineering", "structural", "exterior", "interior",
    "commercial", "industrial", "institutional", "municipal",
    "courthouse", "hospital", "school", "university",
    "office", "retail", "warehouse", "parking",
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
    # --- Public Bid Boards (Free) ---
    "sam_gov": {
        "name": "SAM.gov (Federal)",
        "base_url": "https://sam.gov/search/?index=opp",
        "api_url": "https://api.sam.gov/prod/opportunities/v2/search",
        "api_key_env": "SAM_GOV_API_KEY",  # Set as env variable
        "enabled": True,
        "type": "government",
        "cost": "free",
    },
    "eva": {
        "name": "eVA (Virginia)",
        "base_url": "https://mvendor.cgieva.com/Vendor/public/AllOpportunities.jsp",
        "api_url": None,
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
    "fairfax_county": {
        "name": "Fairfax County Procurement",
        "base_url": "https://fairfaxcounty.bonfirehub.com/portal/?tab=openOpportunities",
        "enabled": False,  # Bonfire SPA - requires JavaScript rendering (Selenium)
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

    # --- Additional Free Government Sources ---
    "dc_ocp": {
        "name": "DC Office of Contracting and Procurement",
        "base_url": "https://contracts.ocp.dc.gov/solicitations/search",
        "api_url": "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Government_Operations/MapServer/19/query",
        "enabled": True,
        "type": "government",
        "cost": "free",
    },
    "emma_maryland": {
        "name": "eMarylandMarketplace (eMMA)",
        "base_url": "https://emma.maryland.gov/page.aspx/en/rfp/request_browse_public",
        "enabled": False,  # Ivalua SPA - requires JavaScript rendering (Selenium)
        "type": "government",
        "cost": "free",
    },
    "bidnet_direct": {
        "name": "BidNet Direct (Free Tier)",
        "base_url": "https://www.bidnetdirect.com/virginia",
        "enabled": False,  # SOVRA SPA - requires JavaScript rendering (Selenium)
        "type": "commercial",
        "cost": "free",
    },

    # --- Commercial / Private Sector (Paid) ---
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
        "enabled": False,  # Requires JS rendering
        "type": "commercial",
        "cost": "free",
    },

    # --- Permit Data (Free) ---
    "arlington_permits": {
        "name": "Arlington County Building Permits",
        "base_url": "https://permits.arlingtonva.us/",
        "enabled": False,  # Permit portal requires JavaScript rendering
        "type": "permits",
        "cost": "free",
    },
    "fairfax_permits": {
        "name": "Fairfax County Building Permits",
        "base_url": "https://www.fairfaxcounty.gov/landdevelopment/building-permits",
        "enabled": False,  # Info page, not live permit data
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
