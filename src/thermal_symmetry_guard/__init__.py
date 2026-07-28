"""Thermal Symmetry Guard — differential thermography without calibration.

Absolute IR thermometry on real equipment is a losing game: emissivity is
unknown, drifts with oxidation and dust, and nobody sets it correctly. This
package sidesteps the problem entirely by never trusting an absolute reading.
It watches whether nominally identical points stay *in step with each other*,
which is both the thing that actually predicts failure and the thing that is
invariant to emissivity.
"""

from .robust import Cusum, RobustBaseline, TrendFilter, mad, median
from .symmetry import MIN_RISE_K, Channel, SymmetryGroup, TauEstimator
from .types import (
    ChannelReport,
    GroupMode,
    GroupReport,
    Reading,
    Verdict,
)

__version__ = "1.0.0"

__all__ = [
    "MIN_RISE_K",
    "Channel",
    "ChannelReport",
    "Cusum",
    "GroupMode",
    "GroupReport",
    "Reading",
    "RobustBaseline",
    "SymmetryGroup",
    "TauEstimator",
    "TrendFilter",
    "Verdict",
    "__version__",
    "mad",
    "median",
]
