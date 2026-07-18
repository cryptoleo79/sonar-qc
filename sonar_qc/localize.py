"""Artifact localization — WHERE in the track the fingerprint lives.

The whole-file score says *that* artifacts are present; this module says *when*
(sliding-window scores over time) and *where in frequency* (which bands the
evidence points at). Windows are scored with the same weights as the whole
file, so a window's number means the same thing as a file's number.

Localization sharpens review — a human can jump straight to the worst segment —
but it inherits every caveat of the score itself: it locates *measured
artifacts*, it does not prove how a segment was made.
"""
from __future__ import annotations

import numpy as np
import soundfile as sf

from . import features as F
from . import scoring as S

WIN_S = 5.0            # analysis window length
HOP_S = 2.5            # hop between window starts (50% overlap)
MIN_WINDOWS = 2        # fewer than this -> whole file is one segment

# Frequency-band attribution: which band each factor's evidence points at.
FACTOR_BAND = {
    "ceiling_ratio": "above the measured ceiling (missing HF band)",
    "rolloff_db_per_khz": "15–18 kHz (rolloff fit band)",
    "hf_music_corr": "≥14 kHz vs 200 Hz–8 kHz (envelope comparison)",
    "hf_stereo_corr": "≥14 kHz stereo field",
    "fake_24bit": "quantization floor (bits 1–8 of 24)",
}


def _score_window(data, sr, assume_lossy):
    feats = F.extract_from_array(data, sr)
    result = S.score(feats, assume_lossy=assume_lossy)
    return feats, result


def analyze(path, assume_lossy=False, win_s=WIN_S, hop_s=HOP_S):
    """Per-window suspicion over time. Returns {windows, summary}.

    Each window: {start_s, end_s, score, band, top_factors}. The summary names
    the worst window and how much of the track scores MEDIUM+.
    """
    data, sr = sf.read(path, always_2d=True)
    data = data.astype(np.float64)
    n = data.shape[0]
    win = int(win_s * sr)
    hop = int(hop_s * sr)

    starts = list(range(0, max(1, n - win + 1), max(1, hop)))
    if len(starts) < MIN_WINDOWS or n < win:
        starts = [0]
        win = n

    windows = []
    for s0 in starts:
        seg = data[s0:s0 + win]
        feats, result = _score_window(seg, sr, assume_lossy)
        windows.append({
            "start_s": round(s0 / sr, 2),
            "end_s": round(min(s0 + win, n) / sr, 2),
            "score": result["score"],
            "band": result["band"],
            "top_factors": [r["factor"] for r in result["reasons"]],
        })

    scores = [w["score"] for w in windows]
    worst = max(windows, key=lambda w: w["score"]) if windows else None
    med_plus = [w for w in windows if w["score"] >= 25]
    summary = {
        "windows": len(windows),
        "win_s": win_s,
        "hop_s": hop_s,
        "worst": worst,
        "medium_plus_fraction": round(len(med_plus) / len(windows), 3) if windows else 0.0,
        "mean_score": round(float(np.mean(scores)), 1) if scores else 0.0,
        "uniform": bool(windows and (max(scores) - min(scores) <= 10)),
    }
    return {"windows": windows, "summary": summary}


def escalation(file_score_result, localization):
    """Detect the splice case: a file whose whole-file band understates a segment.

    Whole-file spectra average clean and walled material together, so a track
    that is only PARTLY generative can score LOW overall while single windows
    score HIGH. Returns {escalated, file_band, worst_window_band, note} — the
    caller decides what to do with it (we flag; we do not change exit codes)."""
    if not localization:
        return None
    worst = localization["summary"].get("worst")
    if not worst:
        return None
    order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
    file_band = file_score_result["band"]
    esc = order.get(worst["band"], 0) > order.get(file_band, 0)
    return {
        "escalated": esc,
        "file_band": file_band,
        "worst_window_band": worst["band"],
        "note": ("segment(s) score above the whole-file band — the file-wide average "
                 "can mask partial/spliced generative content; review the flagged "
                 "windows" if esc else "no window exceeds the whole-file band"),
    }


def frequency_evidence(score_result):
    """Map each contributing factor to the frequency region its evidence lives in."""
    out = []
    for r in score_result.get("reasons", []):
        band = FACTOR_BAND.get(r["factor"])
        if band:
            out.append({"factor": r["factor"], "points": r["points"], "frequency_region": band})
    return out
