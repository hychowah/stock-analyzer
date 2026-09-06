"""Browser smoke: Runs Filters disclosure at phone width. Not part of pytest."""

from __future__ import annotations

import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.support.ui import WebDriverWait

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8776"


def style(d, sel: str, prop: str) -> str:
    return d.execute_script(
        "var e=document.querySelector(arguments[0]);"
        "return e ? getComputedStyle(e).getPropertyValue(arguments[1]) : 'MISSING';",
        sel,
        prop,
    )


def expect(fails: list[str], ok: bool, msg: str) -> None:
    print(msg, "OK" if ok else "FAIL")
    if not ok:
        fails.append(msg)


def main() -> int:
    opts = EdgeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1200,900")
    d = webdriver.Edge(options=opts)
    fails: list[str] = []
    try:
        d.set_window_size(1200, 900)
        d.get(BASE.rstrip("/") + "/")
        WebDriverWait(d, 15).until(lambda drv: drv.find_element(By.ID, "filters-open"))
        expect(
            fails,
            d.find_element(By.NAME, "ticker_prefix").is_displayed(),
            "desktop ticker visible",
        )
        expect(
            fails,
            d.find_element(By.NAME, "sector").is_displayed(),
            "desktop extra filters visible",
        )
        expect(
            fails,
            not d.find_element(By.CSS_SELECTOR, "label[for='filters-open']").is_displayed(),
            "desktop Filters label hidden",
        )

        d.set_window_size(390, 844)
        time.sleep(0.3)
        expect(
            fails,
            d.find_element(By.NAME, "ticker_prefix").is_displayed(),
            "phone ticker visible",
        )
        expect(
            fails,
            d.find_element(By.CSS_SELECTOR, "label[for='filters-open']").is_displayed(),
            "phone Filters label shown",
        )
        expect(
            fails,
            style(d, "#filters-extra", "display") == "none",
            f"phone extra filters hidden ({style(d, '#filters-extra', 'display')})",
        )
        d.find_element(By.CSS_SELECTOR, "label[for='filters-open']").click()
        time.sleep(0.2)
        expect(
            fails,
            style(d, "#filters-extra", "display") == "block",
            f"phone Filters open ({style(d, '#filters-extra', 'display')})",
        )
        expect(
            fails,
            d.find_element(By.NAME, "sector").is_displayed(),
            "phone sector visible after Filters",
        )
        sort = d.find_element(By.CSS_SELECTOR, "#runs-filters input[name='sort']")
        expect(fails, sort.get_attribute("type") == "hidden", "sort stays in always-on form")
    finally:
        d.quit()

    if fails:
        print("BROWSER SMOKE FAIL", len(fails))
        return 1
    print("BROWSER SMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
