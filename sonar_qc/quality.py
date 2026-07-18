"""Non-provenance quality control.

These checks are orthogonal to provenance: they catch broken or unusable audio
(clipping, DC offset, dead channels, silence, too-short) regardless of how the
audio was made. A hard failure here (``reject``) means the file cannot be
meaningfully screened and the pipeline should route it out (CLI exit code 3).
Thresholds are named constants so they are easy to audit and tune.
"""
from __future__ import annotations

import numpy as np
import soundfile as sf

# --- thresholds -------------------------------------------------------------
CLIP_LEVEL = 0.999          # |sample| at/above this counts as clipped
CLIP_FRAC_WARN = 0.001      # warn if >0.1% of samples are clipped
DC_WARN = 0.01              # warn if |mean| exceeds this (fraction of full scale)
SILENCE_DBFS = -60.0        # reject if overall RMS is below this
DEAD_CH_PEAK = 1e-4         # a channel whose peak is below this is "dead"
MIN_DURATION_S = 1.0        # reject if shorter than this (too little to analyze)


def _dbfs(x):
    rms = float(np.sqrt(np.mean(x ** 2))) if x.size else 0.0
    return 20.0 * np.log10(rms + 1e-20)


def check(path):
    """Run quality checks. Returns {reject, flags, metrics}.

    ``flags`` is a list of {code, severity, detail}; severity is 'reject' or
    'warn'. ``reject`` is True if any hard failure is present.
    """
    data, sr = sf.read(path, always_2d=True)
    data = data.astype(np.float64)
    n, ch = data.shape
    mono = data.mean(axis=1) if n else np.zeros(0)
    dur = n / sr if sr else 0.0

    peak = float(np.max(np.abs(data))) if n else 0.0
    rms_dbfs = _dbfs(mono)
    clip_frac = float(np.mean(np.abs(data) >= CLIP_LEVEL)) if n else 0.0
    dc = float(np.mean(mono)) if n else 0.0
    dead = [i for i in range(ch) if (np.max(np.abs(data[:, i])) if n else 0.0) < DEAD_CH_PEAK]

    flags = []

    def add(code, severity, detail):
        flags.append({"code": code, "severity": severity, "detail": detail})

    if dur < MIN_DURATION_S:
        add("too_short", "reject", f"duration {dur:.3f}s < {MIN_DURATION_S}s minimum")
    if n == 0 or rms_dbfs < SILENCE_DBFS:
        add("silence", "reject", f"overall level {rms_dbfs:.1f} dBFS < {SILENCE_DBFS} dBFS")
    if ch > 0 and len(dead) == ch:
        add("all_channels_dead", "reject", "every channel is silent")
    elif dead:
        add("dead_channel", "warn", f"channel(s) {dead} effectively silent")
    if clip_frac > CLIP_FRAC_WARN:
        add("clipping", "warn", f"{clip_frac * 100:.2f}% of samples at full scale")
    if abs(dc) > DC_WARN:
        add("dc_offset", "warn", f"DC offset {dc:+.4f}")

    reject = any(f["severity"] == "reject" for f in flags)
    return {
        "reject": reject,
        "flags": flags,
        "metrics": {
            "duration_s": dur,
            "peak": peak,
            "rms_dbfs": rms_dbfs,
            "clip_frac": clip_frac,
            "dc_offset": dc,
            "channels": ch,
            "dead_channels": dead,
        },
    }
