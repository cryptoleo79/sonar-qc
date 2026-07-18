"""sonar-qc — audio provenance & quality screening for music submissions.

This package measures acoustic traits of an audio file and reports a calibrated
*suspicion* score with the evidence behind it. It does not — and cannot — prove
that a track is or is not generatively produced. See the README and
docs/LIMITATIONS.md for what that means in practice.
"""

__version__ = "0.1.0"

from . import features, scoring, quality  # noqa: F401

__all__ = ["features", "scoring", "quality", "__version__"]
