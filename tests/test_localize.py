"""Localization tests — a track that is clean in its first half and walled in
its second half must light up the second half's windows, not the first's."""
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt

from sonar_qc import localize as L
from sonar_qc import scoring as S

SR = 44100


def _half_and_half(path, dur=20.0):
    """First half full-bandwidth/envelope-correlated; second half hard-walled
    with a decorrelated HF bed (same construction as the HIGH fixture)."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    env = np.clip(0.6 + 0.4 * np.sin(2 * np.pi * 0.5 * t), 0.2, 1.0)
    rng = np.random.default_rng(7)
    nyq = SR / 2.0

    clean = (0.5 * rng.standard_normal(n) + 0.3 * np.sin(2 * np.pi * 440 * t)) * env

    music = (0.5 * rng.standard_normal(n) + 0.4 * np.sin(2 * np.pi * 300 * t)) * env
    bed = sosfiltfilt(butter(6, [14000 / nyq, 14900 / nyq], btype="band", output="sos"),
                      rng.standard_normal(n))
    walled = sosfiltfilt(butter(10, 15000 / nyq, btype="low", output="sos"),
                         music + 0.5 * bed / (np.abs(bed).max() + 1e-12))

    half = n // 2
    sig = np.concatenate([clean[:half], walled[half:]])
    sig = 0.3 * sig / (np.abs(sig).max() + 1e-12)
    sf.write(path, np.stack([sig, sig], axis=1), SR, subtype="PCM_16")
    return dur


def test_windows_localize_the_walled_half(tmp_path):
    p = tmp_path / "half.wav"
    dur = _half_and_half(str(p))
    loc = L.analyze(str(p))
    wins = loc["windows"]
    assert len(wins) >= 4

    mid = dur / 2.0
    first = [w["score"] for w in wins if w["end_s"] <= mid]
    second = [w["score"] for w in wins if w["start_s"] >= mid]
    assert first and second
    assert max(second) > max(first), (first, second)
    assert loc["summary"]["worst"]["start_s"] >= mid - 2.5  # worst window in walled half
    assert loc["summary"]["uniform"] is False


def test_short_file_falls_back_to_single_window(tmp_path):
    p = tmp_path / "short.wav"
    t = np.arange(int(SR * 2)) / SR
    x = 0.3 * np.sin(2 * np.pi * 440 * t)
    sf.write(str(p), np.stack([x, x], axis=1), SR, subtype="PCM_16")
    loc = L.analyze(str(p))
    assert loc["summary"]["windows"] == 1
    assert loc["windows"][0]["start_s"] == 0.0


def test_escalation_flags_partial_content(tmp_path):
    """The splice case: whole-file LOW but a walled segment scores HIGH."""
    p = tmp_path / "half.wav"
    _half_and_half(str(p))
    from sonar_qc import features as F
    file_result = S.score(F.extract(str(p)))
    loc = L.analyze(str(p))
    esc = L.escalation(file_result, loc)
    assert esc is not None
    assert esc["worst_window_band"] == "HIGH"
    if file_result["band"] != "HIGH":       # whole-file average masks the wall
        assert esc["escalated"] is True


def test_frequency_evidence_maps_factors():
    result = S.score({"ceiling_ratio": 0.6, "rolloff_db_per_khz": -6.0,
                      "hf_music_corr": 0.9, "fake_24bit": False, "hf_stereo_corr": 0.0})
    ev = L.frequency_evidence(result)
    factors = {e["factor"] for e in ev}
    assert factors == {"ceiling_ratio", "rolloff_db_per_khz"}
    for e in ev:
        assert e["frequency_region"]
