import pdfplumber
import re
from datetime import datetime
from pathlib import Path

from config import PDF_FOLDER, PDF_PATTERN


def get_latest_pdf():

    pdf_files = list(PDF_FOLDER.glob(PDF_PATTERN))

    if not pdf_files:
        raise FileNotFoundError(
            f"No PDF found inside: {PDF_FOLDER}"
        )

    # Sort all matching files by modification time
    pdf_files.sort(
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )

    # Attempt to find the first valid PDF
    for pdf_path in pdf_files:
        try:
            read_official_date(pdf_path)
            return pdf_path
        except ValueError:
            continue

    raise ValueError("No valid Daily Price Index PDF found in: " + str(PDF_FOLDER))


def read_official_date(pdf_path):

    with pdfplumber.open(pdf_path) as pdf:

        # Extract text from ALL pages instead of just the first page
        text = "\n".join([page.extract_text() or "" for page in pdf.pages])

    required = [
        "Department of Agriculture",
        "DAILY PRICE INDEX",
        "National Capital Region"
    ]

    for word in required:

        if word not in text:

            raise ValueError(
                "This is not a valid Daily Price Index PDF."
            )

    # Added Vegetable check (case-insensitive)
    # Check that "VEGETABLES" appears at least once in the entire document
    text_upper = text.upper()
    if "VEGETABLES" not in text_upper:
        raise ValueError(
            "This PDF does not contain the required 'VEGETABLES' section."
        )

    match = re.search(

        r"\([A-Za-z]+,\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})\)",

        text

    )

    if not match:

        raise ValueError(
            "Unable to locate official date inside PDF."
        )

    official_date = datetime.strptime(
        match.group(1),
        "%B %d, %Y"
    )

    return official_date


def parse_row(row):

    row = [(cell or "").replace('\n', ' ').strip() for cell in row]

    if not any(row):
        return None

    if len(row) == 1:
        return None

    if len(row) >= 7:

        commodity = row[0]
        specification = row[3]
        price = row[6]

    else:

        commodity = row[0]
        specification = row[1]
        price = row[2]

    return row, commodity, specification, price


def parse_pdf():

    pdf_path = get_latest_pdf()

    official_date = read_official_date(pdf_path)

    current_date = official_date.strftime("%Y-%m-%d")

    new_filename = (
        "Daily-Price-Index-"
        + official_date.strftime("%B-%d-%Y")
        + ".pdf"
    )

    new_path = PDF_FOLDER / new_filename

    if pdf_path != new_path:

        if new_path.exists():
            new_path.unlink()

        pdf_path.rename(new_path)

        pdf_path = new_path

    items = []

    current_category = None
    pending_category = None

    warnings = 0

    categories = set()

    with pdfplumber.open(pdf_path) as pdf:

        total_pages = len(pdf.pages)

        for page in pdf.pages:

            tables = page.extract_tables()

            for table in tables:

                for raw_row in table:

                    parsed = parse_row(raw_row)

                    if parsed is None:
                        continue

                    row, commodity, specification, price = parsed

                    text = " ".join(
                        c for c in row if c
                    )

                    if "COMMODITY" in text:
                        continue

                    if "PREVAILING RETAIL PRICE" in text:
                        continue

                    non_empty = [
                        c for c in row if c
                    ]

                    if price == "" and len(non_empty) >= 1:

                        category_text = " ".join(non_empty)

                        if category_text.upper() == category_text:

                            if pending_category:

                                current_category = (
                                    pending_category
                                    + " "
                                    + category_text
                                )

                                categories.add(current_category)

                                pending_category = None

                                continue

                            elif category_text.endswith("MEAT"):

                                pending_category = (
                                    category_text
                                )

                                continue

                            else:

                                current_category = (
                                    category_text
                                )

                                categories.add(current_category)

                                continue

                    if commodity == "":
                        warnings += 1
                        continue

                    if specification == "":
                        specification = None

                    if price.lower() == "n/a" or price == "":
                        price = None
                    else:

                        try:
                            price = float(price)
                        except:
                            price = None

                    items.append({

                        "category": current_category,

                        "commodity": commodity,

                        "specification": specification,

                        "price": price

                    })

    if len(items) < 180:

        print()
        print("WARNING")
        print("--------------------------------")
        print("Only", len(items), "products imported.")
        print("Please verify the PDF format.")
        print("--------------------------------")
        print()

    return {

        "pdf_path": pdf_path,

        "date": current_date,

        "pages": total_pages,

        "categories": len(categories),

        "products": len(items),

        "warnings": warnings,

        "items": items

    }