"""Browser smoke: desktop Tab is not a mystery checkbox; 844px stacked cards.

Not part of pytest. Usage:
    python eng/sessions/2026-09-06-ui-a11y-phone/handoffs/smoke_a11y.py http://127.0.0.1:8776
"""

from __future__ import annotations

import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
        expect(fails, style(d, "#nav-open", "display") == "none", "desktop #nav-open display none")
        expect(fails, style(d, ".disclose-btn", "display") == "none", "desktop Menu hidden")
        expect(
            fails,
            style(d, "#filters-open", "display") == "none",
            "desktop Filters checkbox hidden",
        )
        d.find_element(By.TAG_NAME, "body").send_keys(Keys.TAB)
        time.sleep(0.15)
        active = d.execute_script(
            "var e=document.activeElement; return {id:e && e.id, tag:e && e.tagName,"
            " cls:e && e.className, type:e && e.type};"
        )
        print("first Tab", active)
        expect(
            fails,
            active.get("id") != "nav-open" and active.get("type") != "checkbox",
            "first Tab is not a mystery checkbox",
        )
        expect(
            fails,
            "skip-link" in (active.get("cls") or ""),
            "first Tab is skip-link",
        )

        d.set_window_size(844, 390)
        time.sleep(0.4)
        inner = d.execute_script("return window.innerWidth")
        print("844 innerWidth", inner)
        expect(fails, inner <= 1100, f"844 innerWidth {inner} <= 1100")
        expect(
            fails,
            style(d, ".stack-table thead", "display") == "none",
            f"844 thead display ({style(d, '.stack-table thead', 'display')})",
        )
        expect(
            fails,
            style(d, ".stack-table tr", "display") == "block",
            f"844 tr display ({style(d, '.stack-table tr', 'display')})",
        )
        expect(
            fails,
            style(d, ".disclose-btn", "display") != "none",
            f"844 Menu shown ({style(d, '.disclose-btn', 'display')})",
        )
        sort_tabbable = d.execute_script(
            "var as=document.querySelectorAll('a.sort'); var n=0;"
            "as.forEach(function(a){ var r=a.getBoundingClientRect();"
            " var cs=getComputedStyle(a);"
            " if(r.width>0 && r.height>0 && cs.display!=='none' && cs.visibility!=='hidden') n++; });"
            "return {count: as.length, visible: n};"
        )
        print("sort links", sort_tabbable)
        expect(fails, sort_tabbable["visible"] == 0, "844 sort links not visible tab stops")
    finally:
        d.quit()

    if fails:
        print("BROWSER SMOKE FAIL", len(fails))
        return 1
    print("BROWSER SMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
