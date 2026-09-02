"""Click range buttons on run detail. Best-effort browser smoke."""

from __future__ import annotations

import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8768"
URL = BASE.rstrip("/") + "/runs/research:META:2026-08-03"


def main() -> int:
    opts = EdgeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1200,900")
    driver = webdriver.Edge(options=opts)
    try:
        driver.get(URL)
        wait = WebDriverWait(driver, 30)
        wait.until(EC.presence_of_element_located((By.ID, "price-chart")))
        svg = driver.find_element(By.ID, "price-chart-svg")
        wait.until(lambda d: svg.find_elements(By.CSS_SELECTOR, "path.chart-price"))
        path1 = svg.find_element(By.CSS_SELECTOR, "path.chart-price").get_attribute("d") or ""
        bear = svg.find_elements(By.CSS_SELECTOR, "line.chart-bear")
        base = svg.find_elements(By.CSS_SELECTOR, "line.chart-base")
        bull = svg.find_elements(By.CSS_SELECTOR, "line.chart-bull")
        print("initial path_len", len(path1), "bear", len(bear), "base", len(base), "bull", len(bull))
        if not (path1 and bear and base and bull):
            print("missing series")
            return 1
        btn = driver.find_element(By.CSS_SELECTOR, '[data-range="3m"]')
        btn.click()
        time.sleep(0.3)
        wait.until(
            lambda d: (d.find_element(By.CSS_SELECTOR, "path.chart-price").get_attribute("d") or "")
            != path1
        )
        path3 = driver.find_element(By.CSS_SELECTOR, "path.chart-price").get_attribute("d") or ""
        pressed = driver.find_element(By.CSS_SELECTOR, '[data-range="3m"]').get_attribute("aria-pressed")
        print("3m path_len", len(path3), "pressed", pressed, "changed", path3 != path1)
        if path3 == path1 or pressed != "true":
            return 1
        readout = driver.find_element(By.ID, "price-chart-readout").text
        print("readout", readout[:160])
        if "Bear" not in readout or "Base" not in readout or "Bull" not in readout:
            return 1
        if "vs base" in readout.lower() or "price vs" in readout.lower():
            return 1
        driver.set_window_size(390, 844)
        time.sleep(0.4)
        path_m = driver.find_element(By.CSS_SELECTOR, "path.chart-price").get_attribute("d") or ""
        stage_h = driver.execute_script(
            "return document.querySelector('.chart-stage').getBoundingClientRect().height"
        )
        print("mobile path_len", len(path_m), "stage_h", stage_h)
        if not path_m or stage_h < 180:
            return 1
        print("BROWSER SMOKE OK")
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
