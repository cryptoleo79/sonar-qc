"""Provenance signature hints — WHAT KIND of pipeline the evidence is consistent with.

Each profile below is a named, visible set of feature ranges tied to a known
rendering or encoding family (a generative-render pattern, a codec's
psychoacoustic ceiling, an export-pipeline tell). When a file's features fall
inside a profile's ranges, that profile is reported as a *hint*.

FRAMING IS LOAD-BEARING — read before editing:
  - A match means the measurements are CONSISTENT WITH that family. It is not
    an identification. Different tools share pipelines, and pipelines change.
  - Profiles marked observed_in are calibrated on the project's small informal
    validation set; they are indicative at best.
  - Codec profiles describe the CODEC's fingerprint, which says nothing about
    who or what made the music that was encoded.
Every emitted match carries its evidence and a confidence of at most
"indicative". Nothing in this module may claim a specific product as fact.
"""
from __future__ import annotations

import math

# range spec: feature -> (min, max)  (None = unbounded on that side)
PROFILES = [
    {
        "id": "generative-render",
        "label": "Generative music render (family)",
        "confidence": "indicative",
        "ranges": {"ceiling_ratio": (None, 0.80), "hf_stereo_corr": (0.85, None)},
        "note": "hard synthetic bandwidth wall with mono-coherent HF — the pattern "
                "current generative music pipelines leave. Consistent-with, not proof.",
    },
    {
        "id": "generative-render-decorrelated-haze",
        "label": "Generative render with decorrelated HF haze (family)",
        "confidence": "indicative",
        "ranges": {"ceiling_ratio": (None, 0.85), "hf_music_corr": (None, 0.30)},
        "note": "HF energy present but not tracking the music — vocoder/decoder haze "
                "rather than captured air. Consistent-with, not proof.",
    },
    {
        "id": "suno-like-render",
        "label": "Suno-like render pattern (observed in validation set)",
        "confidence": "indicative",
        "ranges": {"ceiling_hz": (15000, 17000), "hf_stereo_corr": (0.90, None)},
        "requires_sr": (44100, 48000),
        "note": "ceiling/coherence pattern matching Suno renders in this project's "
                "small informal validation set (n<10). Indicative only — other tools "
                "sharing the decoder family produce the same pattern.",
    },
    {
        "id": "mp3-low-bitrate",
        "label": "Low-bitrate MP3-family encode (~128 kbps class)",
        "confidence": "indicative",
        "ranges": {"ceiling_hz": (15000, 16800), "rolloff_db_per_khz": (None, -5.0)},
        "note": "psychoacoustic lowpass typical of ~128 kbps MP3/AAC-class encoding. "
                "Describes the ENCODER, not how the underlying music was made — this "
                "is the primary false-positive path (see LIMITATIONS.md).",
    },
    {
        "id": "lossy-high-bitrate",
        "label": "High-bitrate lossy encode (~256–320 kbps class)",
        "confidence": "weak",
        "ranges": {"ceiling_hz": (18500, 20900), "rolloff_db_per_khz": (None, -2.5)},
        "note": "ceiling just under Nyquist with a steep edge — typical of high-bitrate "
                "lossy encoding. Encoder fingerprint only.",
    },
    {
        "id": "padded-24bit-export",
        "label": "16-bit source padded to 24/32-bit container",
        "confidence": "indicative",
        "ranges": {},
        "requires_flags": ["fake_24bit"],
        "note": "the export pipeline upconverted 16-bit content into a wider container "
                "— common in render-download-reupload chains and some DAW exports.",
    },
    {
        "id": "native-full-bandwidth",
        "label": "Native full-bandwidth PCM (no ceiling fingerprint)",
        "confidence": "weak",
        "ranges": {"ceiling_ratio": (0.97, None)},
        "note": "energy to Nyquist with no synthetic wall — consistent with a native "
                "capture/mix chain. Absence of a fingerprint is NOT proof of human origin.",
    },
]


def _is_num(v):
    return v is not None and not (isinstance(v, float) and math.isnan(v))


def _in_range(val, lo, hi):
    if not _is_num(val):
        return False
    if lo is not None and val < lo:
        return False
    if hi is not None and val > hi:
        return False
    return True


def match(features):
    """Return the profile hints consistent with a feature dict.

    Each hint: {id, label, confidence, note, evidence:[str]}. Order follows the
    PROFILES table. An empty list means no known family matched — which is
    information, not exoneration.
    """
    hits = []
    for p in PROFILES:
        evidence = []
        ok = True
        for feat, (lo, hi) in p.get("ranges", {}).items():
            val = features.get(feat)
            if not _in_range(val, lo, hi):
                ok = False
                break
            bound = []
            if lo is not None:
                bound.append(f">={lo}")
            if hi is not None:
                bound.append(f"<={hi}")
            evidence.append(f"{feat}={val:.3f} ({' and '.join(bound)})")
        if not ok:
            continue
        sr_req = p.get("requires_sr")
        if sr_req and features.get("sr") not in sr_req:
            continue
        flag_missing = [fl for fl in p.get("requires_flags", []) if not features.get(fl)]
        if flag_missing:
            continue
        for fl in p.get("requires_flags", []):
            evidence.append(f"{fl}=True")
        hits.append({
            "id": p["id"],
            "label": p["label"],
            "confidence": p["confidence"],
            "note": p["note"],
            "evidence": evidence,
        })
    return hits
