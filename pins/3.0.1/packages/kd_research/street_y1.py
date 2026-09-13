"""Street Y1 statute table by harness version.

check_street_bind applies StreetY1Policy. This table is the one home for
default Y1 level, |delta| bands, whether independent_y1 needs a named gate,
which named exits are legal, and whether story_fail requires will_own=false.

3.0.1 STREET_REF: Street FY+1 is the default Y1 forecast; independent_y1 needs
a named object-level gate from GATES_300; story_fail is will_own=false.
3.0.0 INDEPENDENT: ungated independent default; same GATES_300; 40-char
story_fail hatch. 2.28 GATED: Street default; GATES_228 only (no ttc_midcycle).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

STREET_SINCE = (2, 7, 0)
STREET_Y1_SINCE = (2, 18, 0)
STREET_GATED_Y1_SINCE = (2, 28, 0)
STREET_INDEPENDENT_SINCE = (3, 0, 0)
STREET_REF_SINCE = (3, 0, 1)

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

GATES_228 = frozenset(
    {
        "destock_this_print",
        "definition_mismatch",
        "native_kpi",
        "street_unusable",
    }
)
GATES_300 = GATES_228 | frozenset({"story_fail", "ttc_midcycle"})


@dataclass(frozen=True)
class StreetY1Policy:
    """Street Y1 statute for one harness floor.

    Default next-year *level*, legal responses, named independence exits,
    and how tight story_fail is. Bind code applies these fields; it does
    not keep a second version table for which gates exist.
    """

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
    path_copy_legal: bool
    gate_optional: bool = False
    legal_gates: frozenset[str] = frozenset()
    story_fail_requires_will_own: bool = False

    @classmethod
    def for_session(cls, session: Path) -> StreetY1Policy:
        from packages.kd_research.check_core import session_since

        if session_since(session, STREET_REF_SINCE):
            return STREET_REF
        if session_since(session, STREET_INDEPENDENT_SINCE):
            return INDEPENDENT
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
    path_copy_legal=False,
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
    path_copy_legal=False,
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
    path_copy_legal=True,
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
    path_copy_legal=True,
    legal_gates=GATES_228,
)
INDEPENDENT = StreetY1Policy(
    y1=True,
    gated=True,
    responses=RESPONSE_ENUM_GATED,
    fail_band=Y1_BAND,
    warn_band=Y1_WARN_BAND,
    calibration_band=CALIBRATION_BAND,
    keep_independent_illegal=True,
    fy1_baseline_required=False,
    independent_y1_ok=True,
    rehydrate=True,
    path_copy_legal=True,
    gate_optional=True,
    legal_gates=GATES_300,
)
STREET_REF = StreetY1Policy(
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
    path_copy_legal=True,
    gate_optional=False,
    legal_gates=GATES_300,
    story_fail_requires_will_own=True,
)
