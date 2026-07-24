import os
import json
import shutil
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
        f.write("\n" + "-" * 30 + "\n")


def generate_version_json(latest_date):
    version_path = DATABASE_NAME.parent / "version.json"
    version_number = 1

    if version_path.exists():
        try:
            with open(version_path, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                if "version" in old_data:
                    version_number = int(old_data["version"]) + 1
        except:
            pass

    version_info = {
        "version": version_number,
        "latest_date": latest_date,
        "generated_at": datetime.now().isoformat(),
        "database_file": DATABASE_NAME.name
    }

    with open(version_path, "w", encoding="utf-8") as f:
        json.dump(version_info, f, indent=4)


def backup_database(latest_date):
    backup_folder = DATABASE_NAME.parent / "db_backups"
    backup_folder.mkdir(parents=True, exist_ok=True)

    backup_file = backup_folder / f"prices_{latest_date}.db"

    # Copy latest database
    shutil.copy2(DATABASE_NAME, backup_file)

    # Keep only the newest 30 backups
    backups = sorted(backup_folder.glob("prices_*.db"))

    while len(backups) > 30:
        backups[0].unlink()
        backups.pop(0)


def main():
    initialize_database()

    data = parse_pdf()

    db_result = save_to_database(data)

    sync_translations()

    # Run maintenance
    perform_maintenance(data["date"], HISTORY_DAYS)

    # Generate version info
    generate_version_json(data["date"])

    # Backup current database
    backup_database(data["date"])

    if DELETE_IMPORTED_PDF:
        try:
            os.remove(data["pdf_path"])
        except:
            pass

    summary = (
        f"File     : {data['pdf_path'].name}\n"
        f"Date     : {data['date']}\n"
        f"Products : {data['products']}\n"
        f"Warnings : {data['warnings']}"
    )

    print(summary)
    write_log(summary)


if __name__ == "__main__":
    main()