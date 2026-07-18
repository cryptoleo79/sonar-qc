"""Scoring — turn a feature dict into a calibrated suspicion score + evidence.

Every weight and threshold lives in the module-level tables below so they are
visible and tunable, never buried in branches. The score is meaningless without
its ``reasons`` list: the evidence is the product, not the number.

Nothing here proves provenance. A high score means measurable generative-
rendering artifacts are present; it does not identify a person or a workflow.
"""
from __future__ import annotations

import math

CAP = 100

# Tiered features: strictest tier first; the first tier a value falls below
# scores (tiers are alternatives, not cumulative).
#   lossy_sensitive=True  -> zeroed under --assume-lossy (format-confounded).
TIERED = {
    "ceiling_ratio": {
        "tiers": [(0.74, 35), (0.85, 18), (0.93, 6)],
        "lossy_sensitive": True,
        "label": "bandwidth ceiling",
    },
    "rolloff_db_per_khz": {
        "tiers": [(-5.0, 20), (-2.5, 8)],
        "lossy_sensitive": True,
        "label": "HF rolloff slope",
    },
    "hf_music_corr": {
        "tiers": [(0.15, 25), (0.30, 12), (0.45, 4)],
        "lossy_sensitive": False,
        "label": "HF/music envelope correlation",
    },
}

# Boolean / threshold flags.
FLAG_FAKE_24BIT = 8
STEREO_CORR_THRESHOLD = 0.85
STEREO_CORR_POINTS = 7

# (min_score, band, message) — evaluated high to low.
BANDS = [
    (55, "HIGH", "strong generative-rendering fingerprint — disclose if submitting"),
    (25, "MEDIUM", "some artifacts — review / likely needs disclosure"),
    (0, "LOW", "no obvious red flags — NOT a guarantee"),
]


def _is_num(v):
    return v is not None and not (isinstance(v, float) and math.isnan(v))


def band_for(score):
    for threshold, name, message in BANDS:
        if score >= threshold:
            return name, message
    return BANDS[-1][1], BANDS[-1][2]


def score(features, assume_lossy=False):
    """Score a feature dict. Returns {score, band, band_label, reasons, assume_lossy}.

    ``reasons`` is a list of {factor, points, detail} for each contributing
    signal. --assume-lossy drops the format-confounded bandwidth features,
    leaving the score to rest on HF/music correlation and stereo coherence.
    """
    reasons = []
    total = 0

    for key, cfg in TIERED.items():
        if assume_lossy and cfg["lossy_sensitive"]:
            continue
        val = features.get(key)
        if not _is_num(val):
            continue
        for threshold, points in cfg["tiers"]:
            if val < threshold:
                total += points
                reasons.append({
                    "factor": key,
                    "points": points,
                    "detail": f"{cfg['label']}: {key}={val:.3f} < {threshold}",
                })
                break

    if features.get("fake_24bit"):
        total += FLAG_FAKE_24BIT
        reasons.append({
            "factor": "fake_24bit",
            "points": FLAG_FAKE_24BIT,
            "detail": "16-bit content padded into a 24/32-bit container",
        })

    sc = features.get("hf_stereo_corr")
    if _is_num(sc) and sc > STEREO_CORR_THRESHOLD:
        total += STEREO_CORR_POINTS
        reasons.append({
            "factor": "hf_stereo_corr",
            "points": STEREO_CORR_POINTS,
            "detail": f"HF L/R correlation {sc:.3f} > {STEREO_CORR_THRESHOLD} (synthetic tell)",
        })

    total = min(total, CAP)
    name, message = band_for(total)
    return {
        "score": total,
        "band": name,
        "band_label": message,
        "reasons": reasons,
        "assume_lossy": assume_lossy,
    }
