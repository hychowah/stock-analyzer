"""Browser smoke: Runs stack-table cards at phone width. Not part of pytest."""

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
        WebDriverWait(d, 15).until(
            lambda drv: drv.find_element(By.CSS_SELECTOR, "table.stack-table")
        )
        expect(
            fails,
            style(d, ".stack-table thead", "display") != "none",
            f"desktop thead shown ({style(d, '.stack-table thead', 'display')})",
        )
        expect(
            fails,
            d.find_elements(By.CSS_SELECTOR, "input.compare-pick"),
            "desktop compare-pick present",
        )
        expect(
            fails,
            d.find_elements(By.CSS_SELECTOR, "td.quote-live"),
            "desktop live cell present",
        )

        d.set_window_size(390, 844)
        time.sleep(0.3)
        expect(
            fails,
            style(d, ".stack-table thead", "display") == "none",
            "phone thead hidden",
        )
        row_display = style(d, ".stack-table tbody tr", "display")
        expect(fails, row_display == "block", f"phone row is card ({row_display})")
        hide = style(d, "td.desktop-only", "display")
        expect(fails, hide == "none", f"phone desktop-only hidden ({hide})")
        label = d.execute_script(
            "var td=document.querySelector('.stack-table td[data-label=\"Ticker\"]');"
            "if(!td) return 'MISSING';"
            "return getComputedStyle(td, '::before').getPropertyValue('content');"
        )
        print("ticker ::before", label)
        expect(
            fails,
            "Ticker" in (label or ""),
            f"phone Ticker label from data-label ({label})",
        )
        expect(
            fails,
            d.find_element(By.CSS_SELECTOR, "input.compare-pick").is_displayed(),
            "phone compare-pick still in card",
        )
        expect(
            fails,
            d.find_element(By.CSS_SELECTOR, "td.quote-live").is_displayed(),
            "phone live cell still in card",
        )
        health = BASE.rstrip("/") + "/health"
        d.get(health)
        WebDriverWait(d, 15).until(lambda drv: drv.find_element(By.TAG_NAME, "table"))
        expect(
            fails,
            not d.find_elements(By.CSS_SELECTOR, "table.stack-table"),
            "health is not a stack-table",
        )
    finally:
        d.quit()

    if fails:
        print("BROWSER SMOKE FAIL", len(fails))
        return 1
    print("BROWSER SMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
