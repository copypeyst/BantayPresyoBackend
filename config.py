from pathlib import Path

# --------------------------------------------------
# Project folders
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

PDF_FOLDER = BASE_DIR / "pdf"
LOG_FOLDER = BASE_DIR / "logs"

PDF_FOLDER.mkdir(exist_ok=True)
LOG_FOLDER.mkdir(exist_ok=True)

# --------------------------------------------------
# Database
# --------------------------------------------------

DATABASE_NAME = BASE_DIR / "prices.db"

# --------------------------------------------------
# Options
# --------------------------------------------------

DELETE_IMPORTED_PDF = True
HISTORY_DAYS = 365

# --------------------------------------------------
# PDF Search Pattern
# --------------------------------------------------

PDF_PATTERN = "*.pdf"

# --------------------------------------------------
# DA Website
# --------------------------------------------------

PRICE_MONITORING_URL = "https://www.da.gov.ph/price-monitoring/"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}
