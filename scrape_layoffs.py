"""
Scraper for layoffs.fyi
Extracts layoff records from the embedded Airtable table and saves to CSV.

Usage:
    python3 scrape_layoffs.py
    python3 scrape_layoffs.py --output my_data.csv
    python3 scrape_layoffs.py --headless false   # show browser window
"""

import argparse
import json
import pandas as pd
from playwright.sync_api import sync_playwright, Route, Request


# ── Airtable response bodies captured via route interception ─────────────────
_captured_bodies: list[bytes] = []


def scrape_layoffs(headless: bool = True, output: str = "layoffs_scraped.csv") -> pd.DataFrame:
    _captured_bodies.clear()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        )

        # Intercept Airtable API calls via route (gives access to response body safely)
        def intercept(route: Route, request: Request):
            response = route.fetch()
            try:
                body = response.body()
                if body:
                    _captured_bodies.append(body)
            except Exception:
                pass
            route.fulfill(response=response)

        context.route("**airtable.com/**", intercept)

        page = context.new_page()

        print("Loading layoffs.fyi ...")
        try:
            page.goto("https://layoffs.fyi/", wait_until="load", timeout=60_000)
        except Exception as e:
            print(f"Page load warning: {e}")

        print("Waiting for Airtable data to load ...")
        page.wait_for_timeout(8_000)

        # Scroll through Airtable iframe to trigger pagination
        for frame in page.frames:
            if "airtable.com" in frame.url:
                print(f"Scrolling Airtable frame: {frame.url[:80]}")
                for _ in range(30):
                    try:
                        frame.evaluate("window.scrollBy(0, 600)")
                    except Exception:
                        break
                    page.wait_for_timeout(400)
                break

        page.wait_for_timeout(3_000)
        browser.close()

    # ── Parse intercepted Airtable payloads ──────────────────────────────────
    records = []
    print(f"Intercepted {len(_captured_bodies)} Airtable response(s).")

    for body in _captured_bodies:
        try:
            data = json.loads(body)
            records.extend(_parse_airtable_payload(data))
        except Exception:
            pass

    if not records:
        print("No structured data from API interception. Falling back to DOM scrape ...")
        records = _dom_scrape(headless)

    if not records:
        print("Could not extract data. The site structure may have changed.")
        return pd.DataFrame()

    df = pd.DataFrame(records)
    # Flatten any list/dict cell values to strings so deduplication works
    for col in df.columns:
        df[col] = df[col].apply(lambda v: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v)
    df = df.drop_duplicates()
    df = _normalise(df)
    df.to_csv(output, index=False)
    print(f"\nSaved {len(df)} records to '{output}'")
    return df


def _parse_airtable_payload(data) -> list[dict]:
    """Recursively extract row dicts from an Airtable JSON payload."""
    rows = []

    def walk(obj):
        if isinstance(obj, dict):
            if "cellValuesByColumnId" in obj:
                rows.append(obj["cellValuesByColumnId"])
            elif "fields" in obj and isinstance(obj["fields"], dict):
                rows.append(obj["fields"])
            else:
                for v in obj.values():
                    walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    return rows


def _dom_scrape(headless: bool) -> list[dict]:
    """Fallback: parse visible <table> elements across all frames."""
    records = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        try:
            page.goto("https://layoffs.fyi/", wait_until="load", timeout=60_000)
        except Exception:
            pass
        page.wait_for_timeout(8_000)

        for frame in [page.main_frame] + list(page.frames):
            try:
                tables = frame.query_selector_all("table")
                for table in tables:
                    headers = [
                        th.inner_text().strip()
                        for th in table.query_selector_all("thead th, thead td")
                    ]
                    body_rows = table.query_selector_all("tbody tr")
                    for row in body_rows:
                        cells = [td.inner_text().strip() for td in row.query_selector_all("td")]
                        if cells:
                            rec = dict(zip(headers, cells)) if len(headers) == len(cells) else {"values": cells}
                            records.append(rec)
                if records:
                    print(f"DOM scrape: extracted {len(records)} rows from frame {frame.url[:60]}")
                    break
            except Exception:
                continue

        browser.close()

    return records


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only the 4 relevant columns and rename them."""
    # Airtable field IDs for layoffs.fyi (base app1PaujS9zxVGUZ4)
    keep = {
        "fld9AHA9YDoNhrVFQ": "Company",
        "fldH1FcSF7DAaS1EB": "Laid_Off",
        "fldZRD6CwpFopYqqv": "Percentage",
        "fldaRiRVH3vaD9DRC": "Date",
    }
    present = {fid: name for fid, name in keep.items() if fid in df.columns}
    df = df[list(present.keys())].rename(columns=present)

    # Clean ISO date strings → date only
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date

    return df


def main():
    parser = argparse.ArgumentParser(description="Scrape layoff data from layoffs.fyi")
    parser.add_argument("--output", default="layoffs_scraped.csv", help="Output CSV filename")
    parser.add_argument(
        "--headless",
        default="true",
        choices=["true", "false"],
        help="Run browser headlessly (default: true)",
    )
    args = parser.parse_args()

    headless = args.headless.lower() == "true"
    df = scrape_layoffs(headless=headless, output=args.output)

    if not df.empty:
        print("\nFirst 5 rows:")
        print(df.head().to_string())
        print(f"\nColumns : {list(df.columns)}")
        print(f"Records : {len(df)}")


if __name__ == "__main__":
    main()
