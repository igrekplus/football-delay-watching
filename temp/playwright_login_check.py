import os
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
SITE_URL = "https://football-delay-watching-a8830.web.app/"
OUTPUT_DIR = PROJECT_ROOT / "temp"


def load_env(path: Path) -> dict:
    data = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip("\"")
    return data


def main() -> int:
    env = load_env(ENV_PATH)
    email = env.get("FIREBASE_TEST_EMAIL")
    password = env.get("FIREBASE_TEST_PASSWORD")
    if not email or not password:
        print("Missing FIREBASE_TEST_EMAIL or FIREBASE_TEST_PASSWORD in .env")
        return 2

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    list_shot = OUTPUT_DIR / "site_reports_list.png"
    report_shot = OUTPUT_DIR / "site_report_view.png"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        page.set_default_timeout(20000)

        page.goto(SITE_URL, wait_until="domcontentloaded")
        page.wait_for_selector("#login-section", state="visible")
        page.fill("#email", email)
        page.fill("#password", password)
        page.click("button.login-btn")

        # Wait until login is applied and report list is rendered
        page.wait_for_selector("#user-info", state="visible")
        page.wait_for_selector("#reports-container .report-item", state="visible")

        page.screenshot(path=str(list_shot), full_page=True)

        # Open the latest report link
        first_link = page.query_selector("#reports-container .report-item a")
        if not first_link:
            print("No report link found after login")
            return 3
        href = first_link.get_attribute("href")
        if not href:
            print("Report link missing href")
            return 4

        page.goto(SITE_URL.rstrip("/") + href, wait_until="domcontentloaded")
        page.wait_for_selector("h1", state="visible")
        page.screenshot(path=str(report_shot), full_page=True)

        browser.close()

    print(f"Login OK. Screenshots: {list_shot.name}, {report_shot.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
