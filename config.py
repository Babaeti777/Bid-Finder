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
    # Construction-specific terms (NOT generic words like "services", "project", "work")
    # These must be specific enough to not match government site navigation
    "construction", "renovation", "repair", "demolition",
    "contractor", "general contractor", "subcontractor",
    "alterations", "modifications", "refurbishment", "rehabilitation",
    "buildout", "build-out", "fit-out", "remodel",
    # Trades & scopes
    "waterproof", "roofing", "hvac", "plumbing", "electrical",
    "painting", "flooring", "concrete", "masonry",
    "carpentry", "drywall", "ceiling", "mechanical", "fire protection",
    "elevator", "sitework", "grading", "paving", "landscaping",
    "fencing", "abatement", "remediation", "restoration",
    "tenant improvement", "architect", "structural",
    "sprinkler", "fire alarm", "life safety", "caulk", "sealant",
    "coating", "pressure washing", "insulation", "framing",
    # Specific building/facility scopes
    "roof replacement", "window replacement", "door replacement",
    "facade repair", "envelope repair", "parking garage",
    "stormwater", "sewer", "water main",
    "modernization", "ADA compliance", "ADA upgrade",
]

# ============================================================
# GEOGRAPHIC FILTERS (NOVA Focus)
# ============================================================
LOCATIONS = {
    "counties": [
        # Core NOVA
        "Arlington County",
        "Fairfax County",
        "Loudoun County",
        "Prince William County",
        # Outer VA
        "Fauquier County",
        "Stafford County",
        "Spotsylvania County",
        "Culpeper County",
        "Clarke County",
        "Warren County",
        "Rappahannock County",
        "King George County",
        # Maryland
        "Montgomery County",
        "Prince George's County",
        "Howard County",
        "Anne Arundel County",
        "Frederick County",
        "Charles County",
        "Calvert County",
    ],
    "cities": [
        # Core NOVA cities & towns
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
        "Dumfries",
        "Warrenton",
        "Purcellville",
        # Outer VA cities
        "Fredericksburg",
        "Winchester",
        "Front Royal",
        "Culpeper",
        # Maryland cities
        "Bethesda",
        "Rockville",
        "Silver Spring",
        "Gaithersburg",
        "Germantown",
        "Bowie",
        "College Park",
        "Laurel",
        "Greenbelt",
        "Takoma Park",
        "Hyattsville",
        "Frederick",
        "Waldorf",
        "La Plata",
        "Columbia",
        "Ellicott City",
        "Annapolis",
        "Glen Burnie",
    ],
    "zip_prefixes": ["200", "201", "207", "208", "209", "220", "221", "222", "223", "226"],
    "extended_area": {
        "dc": True,
        "maryland": [
            "Montgomery County",
            "Prince George's County",
            "Howard County",
            "Anne Arundel County",
            "Frederick County",
            "Charles County",
            "Calvert County",
        ],
    },
}

# ============================================================
# DATA SOURCES
# ============================================================
SOURCES = {
    # ==========================================================
    # TIER 1 — API-based sources (most reliable, scanned first)
    # ==========================================================
    "sam_gov": {
        "name": "SAM.gov (Federal)",
        "base_url": "https://sam.gov/search/?index=opp",
        "api_url": "https://api.sam.gov/prod/opportunities/v2/search",
        "api_key_env": "SAM_GOV_API_KEY",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",  # Multi-state (VA/DC/MD) handled internally
    },
    "dc_ocp": {
        "name": "DC Office of Contracting & Procurement",
        "base_url": "https://contracts.ocp.dc.gov/solicitations/search",
        "api_url": "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Government_Operations/MapServer/19/query",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "DC",
    },
    "montgomery_county": {
        "name": "Montgomery County MD (Open Data)",
        "base_url": "https://www.montgomerycountymd.gov/PRO/solicitations/formal-solicitations.html",
        "api_url": "https://data.montgomerycountymd.gov/resource/m3ju-5p4v.json",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "MD",
    },

    # ==========================================================
    # TIER 2 — Core NOVA counties & cities (primary service area)
    # ==========================================================
    "eva": {
        "name": "eVA (Virginia)",
        "base_url": "https://mvendor.cgieva.com/Vendor/public/AllOpportunities.jsp",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "fairfax_county": {
        "name": "Fairfax County Procurement",
        "base_url": "https://fairfaxcounty.bonfirehub.com/portal/?tab=openOpportunities",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "arlington_county": {
        "name": "Arlington County Procurement",
        "base_url": "https://vrapp.vendorregistry.com/Bids/View/BidsList?BuyerId=a596c7c4-0123-4202-bf15-3583300ee088",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "loudoun_county": {
        "name": "Loudoun County Procurement",
        "base_url": "https://www.loudoun.gov/Bids.aspx",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "prince_william": {
        "name": "Prince William County Procurement",
        "base_url": "https://eservice2.pwcgov.org/eservices/procurement/",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "city_of_alexandria": {
        "name": "City of Alexandria Procurement",
        "base_url": "https://www.alexandriava.gov/purchasing",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "city_of_fairfax": {
        "name": "City of Fairfax Procurement",
        "base_url": "https://www.fairfaxva.gov/government/finance/procurement/current-solicitations",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "city_of_falls_church": {
        "name": "City of Falls Church Procurement",
        "base_url": "https://www.fallschurchva.gov/Bids.aspx",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "city_of_manassas": {
        "name": "City of Manassas Procurement",
        "base_url": "https://www.demandstar.com/app/agencies/virginia/city-of-manassas/procurement-opportunities/19f69d32-2937-4f84-bcf3-aec285941c4c/",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "city_of_manassas_park": {
        "name": "City of Manassas Park Procurement",
        "base_url": "https://www.manassasparkva.gov/government/city_purchasing___procurement.php",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "stafford_county": {
        "name": "Stafford County Procurement",
        "base_url": "https://staffordcountyva.gov/government/finance/central_procurement_division/bid_opportunities.php",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "fauquier_county": {
        "name": "Fauquier County Procurement",
        "base_url": "https://www.fauquiercounty.gov/government/departments-a-g/county-administration/procurement",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "spotsylvania_county": {
        "name": "Spotsylvania County Procurement",
        "base_url": "https://www.spotsylvania.va.us/Bids.aspx",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },

    # ==========================================================
    # TIER 3 — Regional authorities (large construction budgets)
    # ==========================================================
    "wmata": {
        "name": "WMATA (Metro Transit)",
        "base_url": "https://www.wmata.com/business/procurement/solicitations/",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "DC",
    },
    "mwaa": {
        "name": "Metropolitan Washington Airports Authority",
        "base_url": "https://www.mwaa.com/business/current-contracting-opportunities",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "wssc_water": {
        "name": "WSSC Water",
        "base_url": "https://www.wsscwater.com/procurement",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "MD",
    },
    "dc_water": {
        "name": "DC Water",
        "base_url": "https://www.dcwater.com/procurement",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "DC",
    },
    "fairfax_water": {
        "name": "Fairfax Water",
        "base_url": "https://www.fairfaxwater.org/procurement",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "loudoun_water": {
        "name": "Loudoun Water",
        "base_url": "https://www.loudounwater.org/doing-business-loudoun-water",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "vre": {
        "name": "Virginia Railway Express (VRE)",
        "base_url": "https://www.vre.org/about/procurement/",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },

    # ==========================================================
    # TIER 4 — School districts (major construction spenders)
    # ==========================================================
    "fcps": {
        "name": "Fairfax County Public Schools",
        "base_url": "https://www.fcps.edu/get-involved/procurement-services/facilities-management-current-solicitations",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "lcps": {
        "name": "Loudoun County Public Schools",
        "base_url": "https://www.lcps.org/Page/2010",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "pwcs": {
        "name": "Prince William County Schools",
        "base_url": "https://www.pwcs.edu/departments/office_of_financial_services/procurement_services",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "aps": {
        "name": "Arlington Public Schools",
        "base_url": "https://www.apsva.us/procurement-office/solicitations/",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "acps": {
        "name": "Alexandria City Public Schools",
        "base_url": "https://www.acps.k12.va.us/departments/financial-services/procurement-and-general-services",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "mcps": {
        "name": "Montgomery County Public Schools MD",
        "base_url": "https://www.montgomeryschoolsmd.org/departments/procurement/",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "MD",
    },
    "pgcps": {
        "name": "Prince George's County Public Schools",
        "base_url": "https://offices.pgcps.org/procurement/",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "MD",
    },

    # ==========================================================
    # TIER 5 — Maryland counties & cities
    # ==========================================================
    "prince_georges_county": {
        "name": "Prince George's County MD Procurement",
        "base_url": "https://www.princegeorgescountymd.gov/Bids.aspx",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "MD",
    },
    "howard_county": {
        "name": "Howard County MD Procurement",
        "base_url": "https://www.howardcountymd.gov/procurement-contract-administration/current-solicitations",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "MD",
    },
    "anne_arundel_county": {
        "name": "Anne Arundel County MD Procurement",
        "base_url": "https://www.aacounty.org/departments/central-services/purchasing/",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "MD",
    },
    "frederick_county_md": {
        "name": "Frederick County MD Procurement",
        "base_url": "https://frederickcountymd.gov/Bids.aspx",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "MD",
    },
    "charles_county": {
        "name": "Charles County MD Procurement",
        "base_url": "https://www.charlescountymd.gov/services/economic-development-and-tourism/central-services-procurement",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "MD",
    },
    "calvert_county": {
        "name": "Calvert County MD Procurement",
        "base_url": "https://www.calvertcountymd.gov/Bids.aspx",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "MD",
    },
    "city_of_rockville": {
        "name": "City of Rockville MD Procurement",
        "base_url": "https://www.rockvillemd.gov/Bids.aspx",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "MD",
    },
    "city_of_gaithersburg": {
        "name": "City of Gaithersburg MD Procurement",
        "base_url": "https://www.gaithersburgmd.gov/services/bids-and-proposals",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "MD",
    },
    "city_of_bowie": {
        "name": "City of Bowie MD Procurement",
        "base_url": "https://www.cityofbowie.org/Bids.aspx",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "MD",
    },
    "city_of_frederick": {
        "name": "City of Frederick MD Procurement",
        "base_url": "https://www.cityoffrederickmd.gov/Bids.aspx",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "MD",
    },

    # ==========================================================
    # TIER 6 — Outer VA counties, cities & towns
    # ==========================================================
    "culpeper_county": {
        "name": "Culpeper County Procurement",
        "base_url": "https://web.culpepercounty.gov/rfps",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "warren_county": {
        "name": "Warren County VA Procurement",
        "base_url": "https://www.warrencountyva.net/departments/purchasing",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "clarke_county": {
        "name": "Clarke County VA Procurement",
        "base_url": "https://www.clarkecounty.gov/government/bids-rfps",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "king_george_county": {
        "name": "King George County VA Procurement",
        "base_url": "https://www.king-george.va.us/Bids.aspx",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "city_of_fredericksburg": {
        "name": "City of Fredericksburg Procurement",
        "base_url": "https://www.fredericksburgva.gov/Bids.aspx",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "city_of_winchester": {
        "name": "City of Winchester Procurement",
        "base_url": "https://www.winchesterva.gov/finance/purchasing",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "town_of_herndon": {
        "name": "Town of Herndon Procurement",
        "base_url": "https://www.herndon-va.gov/departments/procurement",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "town_of_vienna": {
        "name": "Town of Vienna Procurement",
        "base_url": "https://www.viennava.gov/government/purchasing",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "town_of_leesburg": {
        "name": "Town of Leesburg Procurement",
        "base_url": "https://www.leesburgva.gov/government/departments/finance/purchasing-bids",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "town_of_warrenton": {
        "name": "Town of Warrenton Procurement",
        "base_url": "https://www.warrentonva.gov/488/Bids-Proposals",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "town_of_front_royal": {
        "name": "Town of Front Royal Procurement",
        "base_url": "https://www.frontroyalva.com/367/Purchasing",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "town_of_purcellville": {
        "name": "Town of Purcellville Procurement",
        "base_url": "https://www.purcellvilleva.gov/bids",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "town_of_culpeper": {
        "name": "Town of Culpeper Procurement",
        "base_url": "https://www.culpeperva.gov/government/finance_and_treasurer/procurement/current_solicitations.php",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "town_of_dumfries": {
        "name": "Town of Dumfries Procurement",
        "base_url": "https://www.dumfriesva.gov/departments/finance/procurement.php",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "rappahannock_county": {
        "name": "Rappahannock County VA Procurement",
        "base_url": "https://www.rappahannockcountyva.gov/business/bid_opportunities.php",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },

    # ==========================================================
    # TIER 7 — Universities (construction/renovation projects)
    # ==========================================================
    "gmu": {
        "name": "George Mason University Procurement",
        "base_url": "https://fiscal.gmu.edu/procurement/",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "umd": {
        "name": "University of Maryland Procurement",
        "base_url": "https://procurement.umd.edu/",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "MD",
    },
    "nvcc": {
        "name": "Northern Virginia Community College",
        "base_url": "https://www.ssc.vccs.edu/procurement/solicitations-and-contracts/",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",
    },
    "gw_university": {
        "name": "George Washington University Procurement",
        "base_url": "https://procurement.gwu.edu/",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "DC",
    },

    # ==========================================================
    # TIER 8 — Aggregator / SPA sites (may need JS)
    # ==========================================================
    "opengov": {
        "name": "OpenGov Procurement (VA/DC/MD)",
        "base_url": "https://procurement.opengov.com/vendors/410233/open-bids?states=VA%2CDC%2CMD",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "VA",  # Multi-state (VA/DC/MD) handled internally
    },
    "emma_maryland": {
        "name": "eMarylandMarketplace (eMMA)",
        "base_url": "https://emma.maryland.gov/page.aspx/en/rfp/request_browse_public",
        "enabled": True,
        "type": "government",
        "cost": "free",
        "state": "MD",
    },
    "bidnet_direct": {
        "name": "BidNet Direct (Free Tier)",
        "base_url": "https://www.bidnetdirect.com/virginia",
        "enabled": True,
        "type": "commercial",
        "cost": "free",
        "state": "VA",
    },
    "the_blue_book": {
        "name": "The Blue Book",
        "base_url": "https://www.thebluebook.com",
        "enabled": True,
        "type": "commercial",
        "cost": "free",
        "state": "VA",
    },

    # ==========================================================
    # COMMERCIAL / PAID (enabled when credentials are configured)
    # ==========================================================
    "dodge_construction": {
        "name": "Dodge Construction Network",
        "base_url": "https://www.construction.com",
        "enabled": False,
        "type": "commercial",
        "cost": "paid",
        "state": "VA",
    },
    "building_connected": {
        "name": "BuildingConnected",
        "base_url": "https://www.buildingconnected.com",
        "enabled": False,
        "type": "commercial",
        "cost": "paid",
        "state": "VA",
    },

    # ==========================================================
    # PERMIT DATA
    # ==========================================================
    "arlington_permits": {
        "name": "Arlington County Building Permits",
        "base_url": "https://permits.arlingtonva.us/",
        "enabled": True,
        "type": "permits",
        "cost": "free",
        "state": "VA",
    },
    "fairfax_permits": {
        "name": "Fairfax County Building Permits",
        "base_url": "https://www.fairfaxcounty.gov/landdevelopment/building-permits",
        "enabled": True,
        "type": "permits",
        "cost": "free",
        "state": "VA",
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

    import os

    if s.get("sam_gov_api_key"):
        os.environ.setdefault("SAM_GOV_API_KEY", s["sam_gov_api_key"])

    if s.get("bidnet_email"):
        os.environ.setdefault("BIDNET_EMAIL", s["bidnet_email"])
    if s.get("bidnet_password"):
        os.environ.setdefault("BIDNET_PASSWORD", s["bidnet_password"])

    if s.get("opengov_email"):
        os.environ.setdefault("OPENGOV_EMAIL", s["opengov_email"])
    if s.get("opengov_password"):
        os.environ.setdefault("OPENGOV_PASSWORD", s["opengov_password"])

    for key, creds in s.get("paid_sources", {}).items():
        if key in SOURCES and creds.get("enabled"):
            SOURCES[key]["enabled"] = True


# Auto-load on import
load_settings_override()
