"""Confirm Live chips and pass badges stay hex under night chrome."""

from __future__ import annotations

import os
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait

BASE = os.environ.get("THEME_SMOKE_BASE", "http://127.0.0.1:8765")
UP_BG = "rgba(187, 247, 208, 1)"
DOWN_BG = "rgba(254, 202, 202, 1)"
PASS_BG = "rgba(187, 247, 208, 1)"


def main() -> int:
    opts = Options()
    opts.page_load_strategy = "eager"
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1280,800")
    d = webdriver.Edge(options=opts)
    try:
        d.get(BASE + "/")
        WebDriverWait(d, 10).until(lambda x: x.find_element(By.ID, "theme-toggle"))
        d.execute_script(
            "localStorage.setItem('analysis_web.theme','dark');"
            "document.documentElement.setAttribute('data-theme','dark');"
        )
        d.get(BASE + "/")
        WebDriverWait(d, 10).until(lambda x: x.find_element(By.ID, "theme-toggle"))
        end = time.time() + 20
        while time.time() < end:
            if d.find_elements(
                By.CSS_SELECTOR, ".quote-live.chg-up, .quote-live.chg-down"
            ):
                break
            time.sleep(0.4)
        theme = d.execute_script(
            "return document.documentElement.getAttribute('data-theme')"
        )
        ups = d.find_elements(By.CSS_SELECTOR, ".quote-live.chg-up")
        downs = d.find_elements(By.CSS_SELECTOR, ".quote-live.chg-down")
        badges = d.find_elements(By.CSS_SELECTOR, ".badge.pass")
        print("theme", theme)
        up_bg = ups[0].value_of_css_property("background-color") if ups else None
        down_bg = downs[0].value_of_css_property("background-color") if downs else None
        badge_bg = (
            badges[0].value_of_css_property("background-color") if badges else None
        )
        print("ups", len(ups), up_bg)
        print("downs", len(downs), down_bg)
        print("pass badges", len(badges), badge_bg)
        fails = []
        if theme != "dark":
            fails.append(f"theme {theme}")
        if ups and up_bg != UP_BG:
            fails.append(f"up {up_bg}")
        if downs and down_bg != DOWN_BG:
            fails.append(f"down {down_bg}")
        if badges and badge_bg != PASS_BG:
            fails.append(f"badge {badge_bg}")
        if not badges:
            fails.append("no pass badges")
        if fails:
            print("FAIL", fails)
            return 1
        print("PASS")
        return 0
    finally:
        d.quit()


if __name__ == "__main__":
    raise SystemExit(main())
