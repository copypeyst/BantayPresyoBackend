import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pathlib import Path
from datetime import datetime

from config import PDF_FOLDER, PRICE_MONITORING_URL as PAGE_URL, HEADERS


def download_latest_pdf():
    PDF_FOLDER.mkdir(exist_ok=True)

    print("Opening DA website...")

    response = requests.get(
        PAGE_URL,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    tables = soup.select("table.tablepress")

    downloads = []

    for table in tables:

        heading = None

        node = table

        while node:

            node = node.find_previous()

            if node is None:
                break

            if node.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:

                heading = node.get_text(" ", strip=True)

                break

        if heading is None:
            continue

        heading_lower = heading.lower()

        if "daily price index" not in heading_lower:
            continue

        if "weekly" in heading_lower:
            continue

        if "cigarette" in heading_lower:
            continue

        rows = table.select("tbody tr")

        for row in rows:

            link = row.find("a", href=True)

            if link is None:
                continue

            href = urljoin(PAGE_URL, link["href"])

            date_text = link.get_text(strip=True)

            try:
                parsed_date = datetime.strptime(
                    date_text,
                    "%B %d, %Y"
                )
            except:
                continue

            downloads.append({
                "date": parsed_date,
                "url": href
            })

    if not downloads:
        raise Exception("No Daily Price Index PDFs found.")

    downloads.sort(
        key=lambda x: x["date"],
        reverse=True
    )

    latest = downloads[0]

    print()
    print("Latest Daily Price Index")
    print("------------------------")
    print("Date :", latest["date"].strftime("%Y-%m-%d"))
    print("URL  :", latest["url"])

    filename = Path(latest["url"]).name

    output_file = PDF_FOLDER / filename

    print()
    print("Downloading PDF...")

    pdf = requests.get(
        latest["url"],
        headers=HEADERS,
        timeout=60
    )

    pdf.raise_for_status()

    with open(output_file, "wb") as f:
        f.write(pdf.content)

    print()
    print("Download complete.")
    print(output_file.resolve())


if __name__ == "__main__":
    download_latest_pdf()