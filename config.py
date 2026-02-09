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
    ],
    "tenant_improvements": [
        "tenant improvement",
        "tenant buildout",
        "tenant build-out",
        "TI project",
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
    ],
    "general_contracting": [
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
        "door replacement",
        "flooring replacement",
        "painting contractor",
        "demolition",
        "site work",
    ],
    "government": [
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
    ],
}

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
    # --- Public Bid Boards ---
    "sam_gov": {
        "name": "SAM.gov (Federal)",
        "base_url": "https://sam.gov/search/?index=opp",
        "api_url": "https://api.sam.gov/opportunities/v2/search",
        "api_key_env": "SAM_GOV_API_KEY",  # Set as env variable
        "enabled": True,
        "type": "government",
    },
    "eva": {
        "name": "eVA (Virginia)",
        "base_url": "https://eva.virginia.gov",
        "api_url": None,  # Web scraping required
        "enabled": True,
        "type": "government",
    },
    "arlington_county": {
        "name": "Arlington County Procurement",
        "base_url": "https://www.arlingtonva.us/Government/Programs/Purchasing",
        "enabled": True,
        "type": "government",
    },
    "fairfax_county": {
        "name": "Fairfax County Procurement",
        "base_url": "https://www.fairfaxcounty.gov/cregister/",
        "enabled": True,
        "type": "government",
    },
    "loudoun_county": {
        "name": "Loudoun County Procurement",
        "base_url": "https://www.loudoun.gov/bids",
        "enabled": True,
        "type": "government",
    },
    "prince_william": {
        "name": "Prince William County Procurement",
        "base_url": "https://www.pwcva.gov/department/finance/procurement-bids-and-proposals",
        "enabled": True,
        "type": "government",
    },
    "city_of_alexandria": {
        "name": "City of Alexandria Procurement",
        "base_url": "https://www.alexandriava.gov/Purchasing",
        "enabled": True,
        "type": "government",
    },
    "city_of_fairfax": {
        "name": "City of Fairfax Procurement",
        "base_url": "https://www.fairfaxva.gov/government/finance/procurement",
        "enabled": True,
        "type": "government",
    },

    # --- Commercial / Private Sector ---
    "dodge_construction": {
        "name": "Dodge Construction Network",
        "base_url": "https://www.construction.com",
        "enabled": False,  # Requires paid subscription
        "type": "commercial",
    },
    "building_connected": {
        "name": "BuildingConnected",
        "base_url": "https://www.buildingconnected.com",
        "enabled": False,  # Requires account
        "type": "commercial",
    },
    "the_blue_book": {
        "name": "The Blue Book",
        "base_url": "https://www.thebluebook.com",
        "enabled": True,
        "type": "commercial",
    },

    # --- Permit Data ---
    "arlington_permits": {
        "name": "Arlington County Building Permits",
        "base_url": "https://building.arlingtonva.us/permits/",
        "enabled": True,
        "type": "permits",
    },
    "fairfax_permits": {
        "name": "Fairfax County Building Permits",
        "base_url": "https://www.fairfaxcounty.gov/landdevelopment/",
        "enabled": True,
        "type": "permits",
    },
}

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
        "recipients": [],     # Add email addresses
        "smtp_server": "",
        "smtp_port": 587,
    },
    "min_score_to_notify": 60,  # Only notify for high-relevance bids
    "digest_frequency": "daily",
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
