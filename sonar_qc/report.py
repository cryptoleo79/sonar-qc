"""PNG report generation: spectrogram + long-term average spectrum + HF zoom.

The report is a visual companion to the numeric evidence. It renders offline
(matplotlib 'Agg') and never blocks. One PNG per input file.
"""
from __future__ import annotations

import os

import numpy as np
import soundfile as sf
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from . import features as F  # noqa: E402


BAND_COLOR = {"HIGH": "#d62728", "MEDIUM": "#ff7f0e", "LOW": "#2ca02c"}


def generate(path, feats, score_result, out_dir, localization=None):
    """Write ``<stem>_sonar-qc.png`` into ``out_dir``. Returns the PNG path.

    With ``localization`` (from localize.analyze), adds a suspicion-over-time
    strip aligned with the spectrogram so a reviewer can see WHERE the
    artifacts live, not just that they exist.
    """
    os.makedirs(out_dir, exist_ok=True)
    data, sr = sf.read(path, always_2d=True)
    mono = data.astype(np.float64).mean(axis=1)
    nyq = sr / 2.0
    f, db = F.welch_db(mono, sr)
    ceil_hz = feats.get("ceiling_hz", nyq)

    n_panels = 4 if localization else 3
    fig, axes = plt.subplots(n_panels, 1, figsize=(10, 11 if n_panels == 3 else 13.5))
    stem = os.path.splitext(os.path.basename(path))[0]
    fig.suptitle(
        f"sonar-qc  ·  {stem}\n"
        f"score {score_result['score']} [{score_result['band']}]  ·  "
        f"{sr} Hz / {feats.get('subtype', '?')} / {feats.get('channels', '?')}ch",
        fontsize=12,
    )

    # 1) spectrogram
    ax = axes[0]
    nfft = 2048
    ax.specgram(mono, NFFT=nfft, Fs=sr, noverlap=nfft // 2, cmap="magma")
    ax.axhline(ceil_hz, color="cyan", lw=1.0, ls="--", label=f"ceiling {ceil_hz:.0f} Hz")
    ax.set_ylabel("Hz")
    ax.set_title("Spectrogram")
    ax.legend(loc="upper right", fontsize=8)

    # 2) long-term average spectrum (the Welch PSD)
    ax = axes[1]
    ax.plot(f / 1000.0, db, color="#1f77b4", lw=0.8)
    ax.axvline(ceil_hz / 1000.0, color="crimson", ls="--", lw=1.0,
               label=f"ceiling {ceil_hz:.0f} Hz (ratio {feats.get('ceiling_ratio', float('nan')):.2f})")
    ax.set_xlabel("kHz")
    ax.set_ylabel("dB")
    ax.set_title("Long-term average spectrum (LTAS)")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(alpha=0.2)

    # 3) HF zoom (>=10 kHz)
    ax = axes[2]
    m = f >= 10000.0
    if m.any():
        ax.plot(f[m] / 1000.0, db[m], color="#6a3d9a", lw=0.9)
    ax.axvline(ceil_hz / 1000.0, color="crimson", ls="--", lw=1.0)
    ro = feats.get("rolloff_db_per_khz", float("nan"))
    hc = feats.get("hf_music_corr", float("nan"))
    ax.set_title(f"HF zoom  ·  rolloff {ro:.1f} dB/kHz  ·  HF/music corr {hc:.2f}")
    ax.set_xlabel("kHz")
    ax.set_ylabel("dB")
    ax.grid(alpha=0.2)

    # 4) suspicion over time (only when localization was computed)
    if localization:
        ax = axes[3]
        wins = localization.get("windows", [])
        for w in wins:
            ax.bar(x=(w["start_s"] + w["end_s"]) / 2.0,
                   height=w["score"],
                   width=max(0.1, w["end_s"] - w["start_s"]) * 0.95,
                   color=BAND_COLOR.get(w["band"], "#7f7f7f"),
                   alpha=0.75, edgecolor="none")
        ax.axhline(55, color="#d62728", lw=0.8, ls=":", label="HIGH ≥55")
        ax.axhline(25, color="#ff7f0e", lw=0.8, ls=":", label="MEDIUM ≥25")
        ax.set_xlim(0, len(mono) / sr)
        ax.set_ylim(0, 100)
        ax.set_xlabel("s")
        ax.set_ylabel("window score")
        ax.set_title("Suspicion over time (same weights as the file score)")
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(alpha=0.2, axis="y")

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out_path = os.path.join(out_dir, f"{stem}_sonar-qc.png")
    fig.savefig(out_path, dpi=110)
    plt.close(fig)
    return out_path
