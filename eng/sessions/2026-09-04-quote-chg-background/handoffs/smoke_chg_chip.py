"""Browser smoke: signed Live cell fill on runs list + run detail. Not part of pytest."""

from __future__ import annotations

import sys
import time

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait

BASE = "http://127.0.0.1:8765"
UP_BG = "rgba(187, 247, 208, 1)"
DOWN_BG = "rgba(254, 202, 202, 1)"
FLAT_BG = "rgba(0, 0, 0, 0)"


def _driver(width: int, height: int) -> webdriver.Edge:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument(f"--window-size={width},{height}")
    d = webdriver.Edge(options=opts)
    d.set_window_size(width, height)
    return d


def d_bg(el) -> str:
    return el.value_of_css_property("background-color")


def wait_signed(d, timeout: float = 20.0) -> None:
    WebDriverWait(d, timeout).until(
        lambda drv: drv.find_elements(By.CSS_SELECTOR, ".quote-live")
    )
    end = time.time() + timeout
    while time.time() < end:
        if d.find_elements(By.CSS_SELECTOR, ".quote-live.chg-up, .quote-live.chg-down"):
            return
        time.sleep(0.4)
    raise TimeoutError("no signed live cells (.quote-live.chg-up/.chg-down)")


def report_page(d, label: str) -> dict:
    ups = d.find_elements(By.CSS_SELECTOR, ".quote-live.chg-up")
    downs = d.find_elements(By.CSS_SELECTOR, ".quote-live.chg-down")
    cells = d.find_elements(By.CSS_SELECTOR, ".quote-live")
    dashes = [c for c in cells if (c.text or "").strip() in ("—", "-", "")]
    up_bgs = sorted({d_bg(e) for e in ups})
    down_bgs = sorted({d_bg(e) for e in downs})
    return {
        "label": label,
        "ups": len(ups),
        "downs": len(downs),
        "cells": len(cells),
        "emptyish": len(dashes),
        "up_bgs": up_bgs,
        "down_bgs": down_bgs,
        "up_ok": (not ups) or up_bgs == [UP_BG],
        "down_ok": (not downs) or down_bgs == [DOWN_BG],
    }


def main() -> int:
    fails: list[str] = []
    d = _driver(1280, 800)
    try:
        d.get(BASE + "/")
        wait_signed(d)
        home = report_page(d, "home desktop")
        print(home)
        if not home["up_ok"]:
            fails.append(f"home up bg {home['up_bgs']} != {UP_BG}")
        if not home["down_ok"]:
            fails.append(f"home down bg {home['down_bgs']} != {DOWN_BG}")
        if home["ups"] + home["downs"] == 0:
            fails.append("home: no signed live cells")

        cell = d.find_elements(By.CSS_SELECTOR, ".quote-live.chg-up, .quote-live.chg-down")[0]
        row = cell.find_element(By.XPATH, "./ancestor::tr")
        ActionChains(d).move_to_element(row).perform()
        time.sleep(0.2)
        cell_bg = d_bg(cell)
        print({"hover_live_bg": cell_bg})
        if cell_bg not in (UP_BG, DOWN_BG):
            fails.append(f"hover lost live cell bg: {cell_bg}")

        unsigned = d.execute_script(
            """
            var el = document.querySelector('.quote-live:not(.chg-up):not(.chg-down)');
            if (!el) return null;
            return window.getComputedStyle(el).backgroundColor;
            """
        )
        print({"unsigned_cell_bg": unsigned})
        if unsigned not in (None, FLAT_BG, "transparent", "rgba(0, 0, 0, 0)"):
            fails.append(f"unsigned live cell should have no fill, got {unsigned}")

        href = d.find_element(By.CSS_SELECTOR, "table.runs-table tbody a.mono").get_attribute("href")
        d.get(href)
        wait_signed(d)
        detail = report_page(d, "detail desktop")
        print(detail)
        if not detail["up_ok"]:
            fails.append(f"detail up bg {detail['up_bgs']}")
        if not detail["down_ok"]:
            fails.append(f"detail down bg {detail['down_bgs']}")
        if detail["ups"] + detail["downs"] == 0 and detail["emptyish"] == 0:
            fails.append("detail: no signed live cell and not empty")
    finally:
        d.quit()

    d = _driver(390, 844)
    try:
        d.get(BASE + "/")
        wait_signed(d)
        mobile = report_page(d, "home mobile")
        print(mobile)
        if not mobile["up_ok"]:
            fails.append(f"mobile up bg {mobile['up_bgs']}")
        if not mobile["down_ok"]:
            fails.append(f"mobile down bg {mobile['down_bgs']}")
        if mobile["ups"] + mobile["downs"] == 0:
            fails.append("mobile: no signed live cells")
    finally:
        d.quit()

    if fails:
        print("FAIL", fails)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
