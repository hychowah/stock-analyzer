"""Desktop + mobile smoke of /portfolio IB performance page."""

from __future__ import annotations

import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8771"
URL = BASE.rstrip("/") + "/portfolio"


def main() -> int:
    opts = EdgeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1200,900")
    driver = webdriver.Edge(options=opts)
    try:
        driver.get(URL)
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        html = driver.page_source
        for s in (
            "Change in NAV",
            "Mark-to-market P/L",
            "IB TWR",
            "Starting Value",
            "Change in Dividend Accruals",
        ):
            if s not in html:
                print("MISSING", s)
                return 1
            print("OK", s)
        if "portfolio_chart.js" in html:
            print("unexpected chart js")
            return 1
        bars = driver.find_elements(By.CSS_SELECTOR, "span.perf-bar")
        print("bars", len(bars))
        if len(bars) < 5:
            print("too few bars")
            return 1
        width = driver.execute_script(
            "return document.querySelector('.perf-bar.pos, .perf-bar.neg')"
            ".getBoundingClientRect().width"
        )
        print("desktop bar width", width)
        if not width or width < 4:
            print("bar not visible")
            return 1
        driver.set_window_size(390, 844)
        time.sleep(0.4)
        grid = driver.execute_script(
            "return getComputedStyle(document.querySelector('.grid2')).gridTemplateColumns"
        )
        print("mobile grid", grid)
        bar_w = driver.execute_script(
            "return [...document.querySelectorAll('.perf-bar')]"
            ".map(e => e.getBoundingClientRect().width)"
            ".filter(w => w > 1)[0] || 0"
        )
        print("mobile bar width", bar_w)
        if bar_w < 4:
            print("mobile bar not visible")
            return 1
        print("BROWSER SMOKE OK")
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
