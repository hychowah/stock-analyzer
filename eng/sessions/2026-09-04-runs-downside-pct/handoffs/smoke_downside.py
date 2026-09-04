"""One-shot smoke: live archive home + one run detail. Not part of CI."""

from __future__ import annotations

import importlib
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
import sys

sys.path.insert(0, str(ROOT))
os.environ["ARCHIVE_ROOT"] = str(ROOT / "archive")

import apps.analysis_web.app as app_mod

importlib.reload(app_mod)
from fastapi.testclient import TestClient

c = TestClient(app_mod.create_app())
r = c.get("/")
print("home", r.status_code)
print("header", "Downside %" in r.text)
print("attr", "data-downside-pct" in r.text)
print("sort_key", 'data-sort="downside_pct"' in r.text)
m = re.search(r"data-downside-pct[\s\S]{0,400}?>([^<]+)", r.text)
print("first_cell", m.group(1).strip() if m else None)
m2 = re.search(r'title="(as-of · [^"]+)"', r.text)
print("first_title", m2.group(1) if m2 else None)

api = c.get("/api/runs", params={"limit": 1}).json()
row = api["runs"][0] if api.get("runs") else {}
print("api_has_field", "downside_pct" in row)
print("api_inputs", {k: row.get(k) for k in ("asof_price", "fv_bear", "run_id")})
rid = row.get("run_id")
if rid:
    d = c.get("/runs/" + str(rid))
    print("detail", d.status_code, "Downside %" in d.text, "data-downside-pct" in d.text)
