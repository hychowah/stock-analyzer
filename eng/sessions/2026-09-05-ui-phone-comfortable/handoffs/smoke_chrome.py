"""Browser smoke: header Menu at phone width. Not part of pytest."""

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
        WebDriverWait(d, 15).until(lambda drv: drv.find_element(By.ID, "nav-open"))
        expect(fails, style(d, ".disclose-btn", "display") == "none", "desktop Menu hidden")
        expect(
            fails,
            style(d, ".header-tagline", "display") != "none",
            f"desktop tagline visible ({style(d, '.header-tagline', 'display')})",
        )
        expect(
            fails,
            style(d, ".header-links", "display") != "none",
            f"desktop links visible ({style(d, '.header-links', 'display')})",
        )
        expect(
            fails,
            d.find_element(By.ID, "theme-toggle").is_displayed(),
            "desktop theme toggle visible",
        )

        d.set_window_size(390, 844)
        time.sleep(0.3)
        inner = d.execute_script("return window.innerWidth")
        print("phone innerWidth", inner)
        expect(fails, inner <= 800, f"phone innerWidth {inner} <= 800")
        expect(
            fails,
            style(d, ".disclose-btn", "display") != "none",
            f"phone Menu shown ({style(d, '.disclose-btn', 'display')})",
        )
        expect(
            fails,
            style(d, ".header-tagline", "display") == "none",
            "phone tagline hidden",
        )
        expect(
            fails,
            style(d, ".header-links", "display") == "none",
            f"phone links hidden until Menu ({style(d, '.header-links', 'display')})",
        )
        menu_h = d.execute_script(
            "return document.querySelector('.disclose-btn').getBoundingClientRect().height"
        )
        expect(fails, menu_h >= 44, f"phone Menu height {menu_h} >= 44")
        d.find_element(By.CSS_SELECTOR, "label.disclose-btn").click()
        time.sleep(0.2)
        expect(
            fails,
            style(d, ".header-links", "display") == "flex",
            f"phone Menu open links ({style(d, '.header-links', 'display')})",
        )
        expect(
            fails,
            d.find_element(By.ID, "nav-runs").is_displayed(),
            "phone Runs link visible after Menu",
        )
        expect(
            fails,
            d.find_element(By.ID, "theme-toggle").is_displayed(),
            "phone theme toggle still visible",
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
