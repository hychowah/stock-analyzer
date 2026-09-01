"""Mode B API for harness versions (live working tree or in-repo pins/<semver>/).

Callers pass a version string and a live ARCHIVE_ROOT. They do not know
about copy, PYTHONPATH, or live-vs-published internals.
"""

from packages.harness_pin.pin import (
    LIVE,
    Pin,
    PinError,
    UnknownVersion,
    list_versions,
    publish,
    resolve,
)

__all__ = [
    "LIVE",
    "Pin",
    "PinError",
    "UnknownVersion",
    "list_versions",
    "publish",
    "resolve",
]
