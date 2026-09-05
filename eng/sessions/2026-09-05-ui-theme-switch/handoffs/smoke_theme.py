"""Browser smoke: Light/Night toggle persist across pages. Not part of pytest."""

from __future__ import annotations

import os
import sys

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait

BASE = os.environ.get("THEME_SMOKE_BASE", "http://127.0.0.1:8765")
LIGHT_BG = "rgba(246, 247, 249, 1)"
NIGHT_BG = "rgba(11, 18, 32, 1)"
PAPER_BG = "rgba(255, 255, 255, 1)"
UP_BG = "rgba(187, 247, 208, 1)"
DOWN_BG = "rgba(254, 202, 202, 1)"
PAGES = ("/", "/harness", "/architecture", "/analyze", "/portfolio", "/health")


def _driver(width: int, height: int) -> webdriver.Edge:
    opts = Options()
    opts.page_load_strategy = "eager"
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument(f"--window-size={width},{height}")
    d = webdriver.Edge(options=opts)
    d.set_window_size(width, height)
    return d


def theme(d) -> str:
    return d.execute_script(
        "return document.documentElement.getAttribute('data-theme')"
    )


def body_bg(d) -> str:
    return d.find_element(By.TAG_NAME, "body").value_of_css_property(
        "background-color"
    )


def stored(d) -> str | None:
    return d.execute_script("return localStorage.getItem('analysis_web.theme')")


def wait_toggle(d) -> None:
    WebDriverWait(d, 10).until(lambda drv: drv.find_element(By.ID, "theme-toggle"))


def click_toggle(d) -> None:
    d.find_element(By.ID, "theme-toggle").click()


def expect(fails: list[str], ok: bool, msg: str) -> None:
    print(msg, "OK" if ok else "FAIL")
    if not ok:
        fails.append(msg)


def run_at(d, width: int, height: int, label: str, fails: list[str]) -> None:
    d.set_window_size(width, height)
    d.get(BASE + "/")
    wait_toggle(d)
    d.execute_script("localStorage.removeItem('analysis_web.theme')")
    d.get(BASE + "/")
    wait_toggle(d)

    first = theme(d)
    expect(fails, first in ("light", "dark"), f"{label} first data-theme={first}")
    expect(fails, stored(d) is None, f"{label} first visit does not write storage ({stored(d)!r})")
    expect(
        fails,
        body_bg(d) == (NIGHT_BG if first == "dark" else LIGHT_BG),
        f"{label} first body bg {body_bg(d)} theme={first}",
    )

    click_toggle(d)
    after = theme(d)
    want = "dark" if first == "light" else "light"
    expect(fails, after == want, f"{label} click -> {after} want {want}")
    expect(fails, stored(d) == want, f"{label} stored {stored(d)!r} want {want}")
    expect(
        fails,
        body_bg(d) == (NIGHT_BG if want == "dark" else LIGHT_BG),
        f"{label} after click body {body_bg(d)}",
    )

    for path in PAGES:
        d.get(BASE + path)
        try:
            wait_toggle(d)
        except Exception as err:
            expect(fails, False, f"{label} {path} no toggle ({err.__class__.__name__})")
            continue
        expect(
            fails,
            theme(d) == want,
            f"{label} {path} theme={theme(d)} want {want}",
        )
        expect(
            fails,
            body_bg(d) == (NIGHT_BG if want == "dark" else LIGHT_BG),
            f"{label} {path} body {body_bg(d)}",
        )

    d.get(BASE + "/architecture")
    wait_toggle(d)
    figs = d.find_elements(By.CSS_SELECTOR, ".architecture-figure")
    if figs:
        fig_bg = figs[0].value_of_css_property("background-color")
        expect(fails, fig_bg == PAPER_BG, f"{label} architecture figure paper {fig_bg}")
    else:
        print(f"{label} architecture: no figure (skip paper check)")

    d.get(BASE + "/")
    wait_toggle(d)
    ups = d.find_elements(By.CSS_SELECTOR, ".quote-live.chg-up")
    downs = d.find_elements(By.CSS_SELECTOR, ".quote-live.chg-down")
    if ups:
        ub = ups[0].value_of_css_property("background-color")
        expect(fails, ub == UP_BG, f"{label} chg-up {ub}")
    if downs:
        db = downs[0].value_of_css_property("background-color")
        expect(fails, db == DOWN_BG, f"{label} chg-down {db}")

    d.get(BASE + "/")
    wait_toggle(d)
    d.refresh()
    wait_toggle(d)
    expect(fails, theme(d) == want, f"{label} reload theme={theme(d)} want {want}")

    click_toggle(d)
    back = theme(d)
    expect(fails, back == first, f"{label} toggle back {back} want {first}")
    expect(fails, stored(d) == first, f"{label} stored back {stored(d)!r}")
    expect(
        fails,
        body_bg(d) == (NIGHT_BG if first == "dark" else LIGHT_BG),
        f"{label} back body {body_bg(d)}",
    )


def main() -> int:
    fails: list[str] = []
    d = _driver(1280, 800)
    try:
        run_at(d, 1280, 800, "desktop", fails)
        run_at(d, 375, 812, "mobile", fails)
        d.set_window_size(1280, 800)
        d.get(BASE + "/")
        wait_toggle(d)
        run = d.find_elements(By.CSS_SELECTOR, "a[href^='/runs/']")
        if run:
            href = run[0].get_attribute("href")
            click_toggle(d)
            nightish = theme(d)
            d.get(href)
            wait_toggle(d)
            expect(
                fails,
                theme(d) == nightish,
                f"run detail theme={theme(d)} want {nightish}",
            )
            chart = d.find_elements(By.CSS_SELECTOR, ".chart-stage, #price-chart-svg")
            print("run detail chart", bool(chart), "theme", theme(d), "body", body_bg(d))
    finally:
        d.quit()
    if fails:
        print("FAIL", len(fails))
        for f in fails:
            print(" -", f)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
