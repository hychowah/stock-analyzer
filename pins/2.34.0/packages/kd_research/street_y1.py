"""Street Y1 policy table by harness version (2.7 / 2.18 / 2.28).

StreetY1Policy.for_session returns y1/gated plus the legal response set and
|delta| bands. check_street_bind currently reads y1 and gated from this object
and still applies RESPONSE_ENUM / Y1_BAND / Y1_WARN_BAND in the bind body.
The street_bind module docstring describes the three statutes in prose.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

STREET_SINCE = (2, 7, 0)
STREET_Y1_SINCE = (2, 18, 0)
STREET_GATED_Y1_SINCE = (2, 28, 0)

RESPONSE_ENUM = frozenset(
    {
        "reopen_path",
        "keep_independent_vs_street",
        "street_unusable",
        "guide_missing",
        "street_baseline",
    }
)
RESPONSE_ENUM_Y1 = frozenset(
    {
        "reopen_path",
        "street_unusable",
        "guide_missing",
        "street_baseline",
    }
)
RESPONSE_ENUM_GATED = frozenset(
    {
        "reopen_path",
        "street_unusable",
        "guide_missing",
        "street_baseline",
        "independent_y1",
    }
)

Y1_BAND = 0.05
Y1_WARN_BAND = 0.03
CALIBRATION_BAND = 0.20


@dataclass(frozen=True)
class StreetY1Policy:
    """Legal Y1 response set and |delta| bands for one harness floor."""

    y1: bool
    gated: bool
    responses: frozenset[str]
    fail_band: float | None
    warn_band: float | None
    calibration_band: float
    keep_independent_illegal: bool
    fy1_baseline_required: bool
    independent_y1_ok: bool
    rehydrate: bool

    @classmethod
    def for_session(cls, session: Path) -> StreetY1Policy:
        from packages.kd_research.check_core import session_since

        if session_since(session, STREET_GATED_Y1_SINCE):
            return GATED
        if session_since(session, STREET_Y1_SINCE):
            return Y1
        if session_since(session, STREET_SINCE):
            return CALIB
        return LEGACY


LEGACY = StreetY1Policy(
    y1=False,
    gated=False,
    responses=frozenset(),
    fail_band=None,
    warn_band=None,
    calibration_band=CALIBRATION_BAND,
    keep_independent_illegal=False,
    fy1_baseline_required=False,
    independent_y1_ok=False,
    rehydrate=False,
)
CALIB = StreetY1Policy(
    y1=False,
    gated=False,
    responses=RESPONSE_ENUM,
    fail_band=None,
    warn_band=None,
    calibration_band=CALIBRATION_BAND,
    keep_independent_illegal=False,
    fy1_baseline_required=False,
    independent_y1_ok=False,
    rehydrate=False,
)
Y1 = StreetY1Policy(
    y1=True,
    gated=False,
    responses=RESPONSE_ENUM_Y1,
    fail_band=Y1_BAND,
    warn_band=Y1_WARN_BAND,
    calibration_band=CALIBRATION_BAND,
    keep_independent_illegal=True,
    fy1_baseline_required=True,
    independent_y1_ok=False,
    rehydrate=False,
)
GATED = StreetY1Policy(
    y1=True,
    gated=True,
    responses=RESPONSE_ENUM_GATED,
    fail_band=Y1_BAND,
    warn_band=Y1_WARN_BAND,
    calibration_band=CALIBRATION_BAND,
    keep_independent_illegal=True,
    fy1_baseline_required=True,
    independent_y1_ok=True,
    rehydrate=True,
)
