import os
import json
from datetime import datetime

from config import (
    DELETE_IMPORTED_PDF,
    LOG_FOLDER,
    HISTORY_DAYS,
    DATABASE_NAME
)

from pdfparser import parse_pdf
from database import (
    initialize_database,
    save_to_database,
    sync_translations,
    perform_maintenance
)

def write_log(text):
    LOG_FOLDER.mkdir(exist_ok=True)
    with open(LOG_FOLDER / "import.log", "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"\n[{timestamp}]\n")
        f.write(text)
        f.write("\n" + "-"*30 + "\n")

def generate_version_json(latest_date):
    version_info = {
        "latest_date": latest_date,
        "generated_at": datetime.now().isoformat(),
        "database_file": DATABASE_NAME.name
    }
    with open(DATABASE_NAME.parent / "version.json", "w", encoding="utf-8") as f:
        json.dump(version_info, f, indent=4)

def main():
    initialize_database()
    data = parse_pdf()
    db_result = save_to_database(data)
    sync_translations()
    
    # Run maintenance
    perform_maintenance(data["date"], HISTORY_DAYS)
    
    # Generate version info
    generate_version_json(data["date"])

    if DELETE_IMPORTED_PDF:
        try:
            os.remove(data["pdf_path"])
        except:
            pass

    summary = f"File     : {data['pdf_path'].name}\nDate     : {data['date']}\nProducts : {data['products']}\nWarnings : {data['warnings']}"

    print(summary)
    write_log(summary)

if __name__ == "__main__":
    main()

