"""Feature extraction — pure measurement, no scoring.

Each function measures one physical property of the signal and returns numbers.
Interpretation lives in scoring.py. The separation is deliberate: measurements
are objective and testable; the suspicion score built from them is tunable and
fallible. Constants that shape a measurement are named module-level values and
documented in docs/METHODOLOGY.md.
"""
from __future__ import annotations

import os
import math

import numpy as np
import soundfile as sf
from scipy.signal import welch, butter, sosfiltfilt
from scipy.stats import pearsonr

# --- analysis constants (see docs/METHODOLOGY.md) ---------------------------
HP_HF_HZ = 14000.0          # highpass corner defining the "HF" band
BP_MUSIC_LO = 200.0         # bandpass defining the "music" band
BP_MUSIC_HI = 8000.0
FRAME_S = 0.050             # RMS envelope frame length (50 ms)

CEILING_REF_LO = 8000.0     # reference band whose level the ceiling is judged against
CEILING_REF_HI = 12000.0
CEILING_START_HZ = 12000.0
CEILING_STEP_HZ = 250.0
CEILING_WIN_HZ = 500.0
CEILING_DROP_DB = 25.0      # a window this far below the reference marks the ceiling

ROLLOFF_LO = 15000.0        # PSD slope is fit over this band
ROLLOFF_HI = 18000.0

LOSSY_EXTS = {".mp3", ".aac", ".m4a", ".ogg", ".oga", ".opus", ".wma"}
LOSSY_FORMATS = {"MP3", "OGG", "VORBIS", "OPUS", "AAC", "WMA"}


# --- io ---------------------------------------------------------------------
def _load(path):
    data, sr = sf.read(path, always_2d=True)
    data = data.astype(np.float64)
    mono = data.mean(axis=1)
    info = sf.info(path)
    return data, mono, sr, info


def is_lossy(path, info=None):
    """True if the source is a lossy container (extension or libsndfile format)."""
    if os.path.splitext(str(path))[1].lower() in LOSSY_EXTS:
        return True
    fmt = (getattr(info, "format", "") or "").upper()
    return fmt in LOSSY_FORMATS


# --- spectra ----------------------------------------------------------------
def welch_db(mono, sr):
    """Welch PSD in dB. Returns (freqs, psd_db)."""
    n = len(mono)
    nperseg = int(min(32768, n)) if n >= 16 else n
    if nperseg < 2:
        return np.array([0.0]), np.array([-200.0])
    f, pxx = welch(mono, fs=sr, nperseg=nperseg)
    return f, 10.0 * np.log10(pxx + 1e-20)


def _band_mean(f, db, lo, hi):
    m = (f >= lo) & (f < hi)
    return float(db[m].mean()) if m.any() else float("nan")


# --- individual features ----------------------------------------------------
def ceiling(f, db, sr):
    """Bandwidth ceiling. Returns (ceiling_hz, ceiling_ratio).

    Reference = mean level over 8-12 kHz. Stepping up from 12 kHz in 250 Hz
    steps, the ceiling is the first window [lo, lo+500) more than 25 dB below
    the reference. Defaults to Nyquist if that never happens.
    """
    nyq = sr / 2.0
    ref = _band_mean(f, db, CEILING_REF_LO, CEILING_REF_HI)
    ceil_hz = nyq
    if not math.isnan(ref):
        lo = CEILING_START_HZ
        while lo < nyq:
            if _band_mean(f, db, lo, lo + CEILING_WIN_HZ) < ref - CEILING_DROP_DB:
                ceil_hz = lo
                break
            lo += CEILING_STEP_HZ
    return float(ceil_hz), float(ceil_hz / nyq)


def rolloff_db_per_khz(f, db):
    """Linear slope of the PSD (dB vs kHz) fit over 15-18 kHz. NaN if unavailable."""
    m = (f >= ROLLOFF_LO) & (f <= ROLLOFF_HI)
    if int(m.sum()) < 2:
        return float("nan")
    khz = f[m] / 1000.0
    return float(np.polyfit(khz, db[m], 1)[0])


def _sos(order, cutoffs, btype, nyq):
    wn = np.atleast_1d(np.asarray(cutoffs, dtype=float) / nyq)
    if np.any(wn <= 0) or np.any(wn >= 1):
        wn = np.clip(wn, 1e-4, 0.999)
    if wn.size == 2 and wn[0] >= wn[1]:
        return None
    try:
        return butter(order, wn if wn.size > 1 else float(wn[0]), btype=btype, output="sos")
    except ValueError:
        return None


def _filtfilt(sos, x):
    if sos is None:
        return None
    try:
        return sosfiltfilt(sos, x)
    except ValueError:
        # signal shorter than the filter's padding requirement
        return None


def _rms_env(x, sr):
    frame = max(1, int(FRAME_S * sr))
    n = len(x) // frame
    if n < 2:
        return np.array([])
    return np.sqrt(np.mean(x[: n * frame].reshape(n, frame) ** 2, axis=1))


def hf_music_corr(mono, sr):
    """Correlation between the HF envelope and the music-band envelope.

    THE key discriminator. Real air/cymbals/transients track the music; a
    generative HF haze does not. Returns Pearson r, or NaN if uncomputable
    (e.g. silence or too-short signal).
    """
    nyq = sr / 2.0
    hf = _filtfilt(_sos(6, min(HP_HF_HZ, 0.9 * nyq), "high", nyq), mono)
    music = _filtfilt(_sos(4, [BP_MUSIC_LO, min(BP_MUSIC_HI, 0.99 * nyq)], "band", nyq), mono)
    if hf is None or music is None:
        return float("nan")
    e_hf, e_mu = _rms_env(hf, sr), _rms_env(music, sr)
    n = min(len(e_hf), len(e_mu))
    if n < 3 or np.std(e_hf[:n]) < 1e-12 or np.std(e_mu[:n]) < 1e-12:
        return float("nan")
    return float(pearsonr(e_hf[:n], e_mu[:n])[0])


def hf_stereo_corr(data, sr):
    """L/R sample correlation of the highpassed signal. Near 1.0 is a synthetic
    tell (real HF decorrelates across the stereo field). NaN if not stereo."""
    if data.shape[1] < 2:
        return float("nan")
    nyq = sr / 2.0
    sos = _sos(6, min(HP_HF_HZ, 0.9 * nyq), "high", nyq)
    left, right = _filtfilt(sos, data[:, 0]), _filtfilt(sos, data[:, 1])
    if left is None or right is None or np.std(left) < 1e-12 or np.std(right) < 1e-12:
        return float("nan")
    return float(np.corrcoef(left, right)[0, 1])


def fake_24bit(path, info):
    """True if a 24/32-bit container holds only 16-bit content (padded).

    Reads as int32 and inspects (raw >> 8) & 0xFF — the low byte of the 24-bit
    sample. If it takes <=2 distinct values, the low bits are unused, i.e. the
    real resolution is 16-bit dressed up as 24-bit. Not applicable to <=16-bit
    or float containers -> False.
    """
    if info.subtype not in ("PCM_24", "PCM_32"):
        return False
    raw, _ = sf.read(path, dtype="int32", always_2d=True)
    low = (raw.astype(np.int64) >> 8) & 0xFF
    return bool(np.unique(low).size <= 2)


def above_ceiling_level_db(f, db, ceil_hz, sr):
    """Mean PSD level above ceiling+500 Hz and below 0.98*Nyquist. Distinguishes
    a real dither/noise floor from digital silence above the ceiling."""
    nyq = sr / 2.0
    m = (f > ceil_hz + 500.0) & (f < 0.98 * nyq)
    return float(db[m].mean()) if m.any() else float("nan")


# --- top level --------------------------------------------------------------
def extract_from_array(data, sr):
    """Extract the signal-derived features from an in-memory (n, ch) array.

    Everything except fake_24bit (which needs the container) — this is what
    windowed localization reuses on slices of the file.
    """
    data = np.atleast_2d(np.asarray(data, dtype=np.float64))
    if data.shape[0] < data.shape[1]:
        data = data.T
    mono = data.mean(axis=1)
    f, db = welch_db(mono, sr)
    ceil_hz, ceil_ratio = ceiling(f, db, sr)
    return {
        "ceiling_hz": ceil_hz,
        "ceiling_ratio": ceil_ratio,
        "rolloff_db_per_khz": rolloff_db_per_khz(f, db),
        "hf_music_corr": hf_music_corr(mono, sr),
        "hf_stereo_corr": hf_stereo_corr(data, sr),
        "above_ceiling_level_db": above_ceiling_level_db(f, db, ceil_hz, sr),
        "sr": int(sr),
        "duration_s": float(len(mono) / sr) if sr else 0.0,
        "channels": int(data.shape[1]),
    }


def extract(path):
    """Extract every provenance feature. Returns a plain dict (JSON-friendly)."""
    data, mono, sr, info = _load(path)
    feats = extract_from_array(data, sr)
    feats["fake_24bit"] = fake_24bit(path, info)
    feats["subtype"] = info.subtype
    return feats
