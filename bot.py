import asyncio
import csv
import os
import subprocess
from playwright.async_api import async_playwright

TARGET_URL = "https://www.nhis.gov.gh/payments"
CSV_FILE = "result.csv"

TABLE_HEADER_SELECTOR = "table#ctl00_ContentPlaceHolder1_RadGrid1_ctl00 thead tr:first-of-type th"
TABLE_ROW_SELECTOR = "table#ctl00_ContentPlaceHolder1_RadGrid1_ctl00 tbody tr"
TABLE_CELL_SELECTOR = "td"
NEXT_PAGE_SELECTOR = "table#ctl00_ContentPlaceHolder1_RadGrid1_ctl00 tfoot tr.rgPager div.rgArrPart2 button.rgPageNext"

def ensure_playwright_browsers():
    try:
        subprocess.run(["playwright", "install", "--with-deps"], check=True, shell=True)
    except Exception as e:
        print(f"Error installing Playwright: {e}")

def clear_csv_file():
    if os.path.isfile(CSV_FILE):
        open(CSV_FILE, 'w').close()

async def get_table_headers(page):
    headers = await page.query_selector_all(TABLE_HEADER_SELECTOR)
    return [await header.text_content() or "N/A" for header in headers]

async def scrape_table(page):
    table_data = []
    rows = await page.query_selector_all(TABLE_ROW_SELECTOR)

    for row in rows:
        cells = await row.query_selector_all(TABLE_CELL_SELECTOR)
        cell_values = [await cell.text_content() or "N/A" for cell in cells]

        if cell_values:
            table_data.append(cell_values)

    return table_data

def save_to_csv(data, headers, append=True):
    file_exists = os.path.isfile(CSV_FILE)

    with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        if not file_exists or not append:
            writer.writerow(headers)

        writer.writerows(data)

async def main():
    clear_csv_file()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(TARGET_URL, timeout=60000)

        await page.click("table tfoot tr.rgPager div.rgAdvPart button.rcbActionButton")
        await page.click("ul.rcbList li:last-of-type")
        await asyncio.sleep(3)

        headers = await get_table_headers(page)

        first_page = True

        while True:
            table_data = await scrape_table(page)

            if first_page:
                save_to_csv(table_data, headers, append=False) 
                first_page = False
            else:
                save_to_csv(table_data, None, append=True) 

            next_button = page.locator(NEXT_PAGE_SELECTOR)            
            if not next_button:
                print("✅ Scraping complete. Data saved to", CSV_FILE)
                break

            await next_button.scroll_into_view_if_needed()
            await asyncio.sleep(1)
            await next_button.click(force=True)
            await asyncio.sleep(2)

        await browser.close()

ensure_playwright_browsers()
asyncio.run(main())
