"""Browser smoke: live % chips on runs list + run detail. Not part of pytest."""

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
HOVER_TD = "rgba(248, 250, 252, 1)"
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


def wait_chips(d, timeout: float = 20.0) -> None:
    WebDriverWait(d, timeout).until(
        lambda drv: drv.find_elements(By.CSS_SELECTOR, ".quote-live .chg-up, .quote-live .chg-down")
        or drv.find_elements(By.CSS_SELECTOR, ".quote-live")
    )
    # Quotes fill after first poll; wait until at least one signed chip or timeout with status.
    end = time.time() + timeout
    while time.time() < end:
        if d.find_elements(By.CSS_SELECTOR, ".quote-live .chg-up, .quote-live .chg-down"):
            return
        time.sleep(0.4)
    raise TimeoutError("no signed live % chips (chg-up/chg-down)")


def report_page(d, label: str) -> dict:
    ups = d.find_elements(By.CSS_SELECTOR, ".quote-live .chg-up")
    downs = d.find_elements(By.CSS_SELECTOR, ".quote-live .chg-down")
    muted = d.find_elements(By.CSS_SELECTOR, ".quote-live .muted")
    cells = d.find_elements(By.CSS_SELECTOR, ".quote-live")
    dashes = [c for c in cells if (c.text or "").strip() in ("—", "-", "")]
    up_bgs = sorted({d_bg(e) for e in ups})
    down_bgs = sorted({d_bg(e) for e in downs})
    return {
        "label": label,
        "ups": len(ups),
        "downs": len(downs),
        "muted": len(muted),
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
        wait_chips(d)
        home = report_page(d, "home desktop")
        print(home)
        if not home["up_ok"]:
            fails.append(f"home up bg {home['up_bgs']} != {UP_BG}")
        if not home["down_ok"]:
            fails.append(f"home down bg {home['down_bgs']} != {DOWN_BG}")
        if home["ups"] + home["downs"] == 0:
            fails.append("home: no signed chips")

        chip = d.find_elements(By.CSS_SELECTOR, ".quote-live .chg-up, .quote-live .chg-down")[0]
        row = chip.find_element(By.XPATH, "./ancestor::tr")
        td = chip.find_element(By.XPATH, "./ancestor::td")
        ActionChains(d).move_to_element(row).perform()
        time.sleep(0.2)
        chip_bg = d_bg(chip)
        td_bg = d_bg(td)
        print({"hover_chip_bg": chip_bg, "hover_td_bg": td_bg})
        if chip_bg not in (UP_BG, DOWN_BG):
            fails.append(f"hover lost chip bg: {chip_bg}")
        if td_bg != HOVER_TD:
            print("note: hover td bg", td_bg, "expected", HOVER_TD)

        flat_bg = d.execute_script(
            """
            var el = document.querySelector('.quote-live');
            var s = document.createElement('span');
            s.className = 'muted';
            s.textContent = '0.0%';
            el.appendChild(s);
            return window.getComputedStyle(s).backgroundColor;
            """
        )
        print({"flat_injected_bg": flat_bg})
        if flat_bg not in (FLAT_BG, "transparent", "rgba(0, 0, 0, 0)"):
            fails.append(f"0% muted should have no chip bg, got {flat_bg}")

        href = d.find_element(By.CSS_SELECTOR, "table.runs-table tbody a.mono").get_attribute("href")
        d.get(href)
        wait_chips(d)
        detail = report_page(d, "detail desktop")
        print(detail)
        if not detail["up_ok"]:
            fails.append(f"detail up bg {detail['up_bgs']}")
        if not detail["down_ok"]:
            fails.append(f"detail down bg {detail['down_bgs']}")
        if detail["ups"] + detail["downs"] == 0 and detail["emptyish"] == 0:
            fails.append("detail: no chip and not empty")
    finally:
        d.quit()

    d = _driver(390, 844)
    try:
        d.get(BASE + "/")
        wait_chips(d)
        mobile = report_page(d, "home mobile")
        print(mobile)
        if not mobile["up_ok"]:
            fails.append(f"mobile up bg {mobile['up_bgs']}")
        if not mobile["down_ok"]:
            fails.append(f"mobile down bg {mobile['down_bgs']}")
        if mobile["ups"] + mobile["downs"] == 0:
            fails.append("mobile: no signed chips")
    finally:
        d.quit()

    if fails:
        print("FAIL", fails)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
