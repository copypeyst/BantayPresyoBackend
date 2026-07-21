import sqlite3
import json
from pathlib import Path

from config import DATABASE_NAME


def initialize_database():

    # Check for migration first
    check_and_migrate()

    conn = sqlite3.connect(DATABASE_NAME)

    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON;")

    # Create products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            category TEXT,

            commodity TEXT NOT NULL,

            specification TEXT,

            UNIQUE (
                category,
                commodity,
                specification
            )

        )
    """)

    # Create daily_prices table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_prices (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            product_id INTEGER NOT NULL,

            date TEXT NOT NULL,

            price REAL,

            FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,

            UNIQUE (
                product_id,
                date
            )

        )
    """)

    # Create indexes for performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_prices_product_date 
        ON daily_prices (product_id, date)
    """)

    # Create aliases table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            name TEXT NOT NULL COLLATE NOCASE,
            FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
            UNIQUE (product_id, name)
        )
    """)

    conn.commit()

    conn.close()


def check_and_migrate():

    conn = sqlite3.connect(DATABASE_NAME)

    cursor = conn.cursor()

    # Check if old table 'prices' exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='prices'")

    if not cursor.fetchone():

        conn.close()

        return

    print("Migrating existing data from flat 'prices' table to normalized schema...")

    cursor.execute("PRAGMA foreign_keys = ON;")

    # Ensure tables are created
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            category TEXT,

            commodity TEXT NOT NULL,

            specification TEXT,

            UNIQUE (
                category,
                commodity,
                specification
            )

        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_prices (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            product_id INTEGER NOT NULL,

            date TEXT NOT NULL,

            price REAL,

            FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,

            UNIQUE (
                product_id,
                date
            )

        )
    """)

    # Migrate products
    cursor.execute("""
        INSERT OR IGNORE INTO products (category, commodity, specification)
        SELECT DISTINCT category, commodity, specification FROM prices
    """)

    # Migrate daily prices
    cursor.execute("""
        INSERT OR IGNORE INTO daily_prices (product_id, date, price)
        SELECT p.id, old.date, old.price
        FROM prices old
        JOIN products p ON 
            (old.category = p.category OR (old.category IS NULL AND p.category IS NULL)) AND
            old.commodity = p.commodity AND
            (old.specification = p.specification OR (old.specification IS NULL AND p.specification IS NULL))
    """)

    # Drop old table
    cursor.execute("DROP TABLE prices")

    conn.commit()

    conn.close()

    print("Migration completed successfully!")


def sync_translations():
    translations_file = Path(__file__).resolve().parent / "data" / "translations.json"
    if not translations_file.exists():
        print(f"Warning: {translations_file} not found. Skipping alias synchronization.")
        return

    print("Synchronizing product aliases...")

    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    with open(translations_file, 'r', encoding='utf-8') as f:
        translations = json.load(f)

    for entry in translations:
        commodity = entry.get("commodity")
        aliases = entry.get("aliases", [])

        if not commodity:
            continue

        # Find all product IDs matching this commodity
        cursor.execute("""
            SELECT id FROM products 
            WHERE commodity = ?
        """, (commodity,))
        product_rows = cursor.fetchall()

        if not product_rows:
            continue

        for product_row in product_rows:
            product_id = product_row[0]

            for alias_name in aliases:
                if alias_name and alias_name.strip():
                    cursor.execute("""
                        INSERT OR IGNORE INTO aliases (product_id, name)
                        VALUES (?, ?)
                    """, (product_id, alias_name.strip()))
    
    conn.commit()
    conn.close()
    print("Alias synchronization completed.")


def save_to_database(data):

    conn = sqlite3.connect(DATABASE_NAME)

    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON;")

    inserted = 0
    duplicates = 0

    for item in data["items"]:

        # 1. Insert or ignore the product to ensure it exists
        cursor.execute("""
            INSERT OR IGNORE INTO products (
                category,
                commodity,
                specification
            )
            VALUES (?, ?, ?)
        """, (
            item["category"],
            item["commodity"],
            item["specification"]
        ))

        # 2. Retrieve the product ID
        cursor.execute("""
            SELECT id FROM products 
            WHERE (category = ? OR (category IS NULL AND ? IS NULL))
              AND commodity = ? 
              AND (specification = ? OR (specification IS NULL AND ? IS NULL))
        """, (
            item["category"], item["category"],
            item["commodity"],
            item["specification"], item["specification"]
        ))

        row = cursor.fetchone()

        if row is None:
            continue

        product_id = row[0]

        # 3. Insert price info into daily_prices
        cursor.execute("""
            INSERT OR IGNORE INTO daily_prices (
                product_id,
                date,
                price
            )
            VALUES (?, ?, ?)
        """, (
            product_id,
            data["date"],
            item["price"]
        ))

        if cursor.rowcount == 1:
            inserted += 1
        else:
            duplicates += 1

    conn.commit()
    conn.close()

    return {

        "inserted": inserted,

        "duplicates": duplicates

    }


def perform_maintenance(latest_date_str, history_days):
    from datetime import datetime, timedelta
    
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Calculate cutoff date
    latest_date = datetime.strptime(latest_date_str, "%Y-%m-%d")
    cutoff_date = (latest_date - timedelta(days=history_days)).strftime("%Y-%m-%d")

    # 1. Delete old prices
    cursor.execute("DELETE FROM daily_prices WHERE date < ?", (cutoff_date,))

    # 2. Delete orphaned products (no prices)
    cursor.execute("""
        DELETE FROM products 
        WHERE id NOT IN (SELECT DISTINCT product_id FROM daily_prices)
    """)

    # 3. Delete orphaned aliases (no product)
    cursor.execute("""
        DELETE FROM aliases 
        WHERE product_id NOT IN (SELECT id FROM products)
    """)

    conn.commit()
    conn.close()
    print(f"Maintenance completed: Removed data older than {cutoff_date}")
