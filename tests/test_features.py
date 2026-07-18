"""Feature + quality tests.

All fixtures are synthesized here at run time (into pytest's tmp_path) and never
committed — real music is copyrighted and heavy. Because the fixtures are
synthetic, we assert behavioral bands/flags, not exact scores.
"""
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt

from sonar_qc import features as F
from sonar_qc import scoring as S
from sonar_qc import quality as Q

SR = 44100


def _t(dur=4.0):
    return np.arange(int(SR * dur)) / SR


def _env(t):
    # slowly varying shared amplitude envelope in ~[0.2, 1.0]
    return np.clip(0.6 + 0.4 * np.sin(2 * np.pi * 0.5 * t), 0.2, 1.0)


def _norm(x, peak=0.3):
    return peak * x / (np.max(np.abs(x)) + 1e-12)


def make_low(path):
    """Full-bandwidth, HF envelope tracks the music -> expect LOW."""
    t = _t()
    env = _env(t)
    rng = np.random.default_rng(0)
    chans = []
    for k in range(2):
        noise = rng.standard_normal(len(t))                 # flat to Nyquist
        tones = 0.3 * np.sin(2 * np.pi * 440 * t) + 0.2 * np.sin(2 * np.pi * 1200 * t)
        chans.append((0.5 * noise + tones) * env)           # everything shares env
    sf.write(path, _norm(np.stack(chans, axis=1)), SR, subtype="PCM_16")


def make_high(path):
    """Hard bandwidth wall at 15 kHz + decorrelated HF bed -> expect HIGH."""
    t = _t()
    env = _env(t)
    nyq = SR / 2.0
    rng = np.random.default_rng(1)
    music = (0.5 * rng.standard_normal(len(t))
             + 0.4 * np.sin(2 * np.pi * 300 * t)
             + 0.3 * np.sin(2 * np.pi * 2000 * t)) * env    # broadband, env-modulated
    # decorrelated HF bed (constant amplitude, own noise) dominating 14-14.9 kHz
    bed = sosfiltfilt(butter(6, [14000 / nyq, 14900 / nyq], btype="band", output="sos"),
                      rng.standard_normal(len(t)))
    sig = music + 0.5 * bed / (np.max(np.abs(bed)) + 1e-12)
    # steep wall at 15 kHz
    sig = sosfiltfilt(butter(10, 15000 / nyq, btype="low", output="sos"), sig)
    sf.write(path, _norm(np.stack([sig, sig], axis=1)), SR, subtype="PCM_16")


def make_padded_24(path):
    """16-bit content padded into a 24-bit container -> fake_24bit True."""
    t = _t(2.0)
    x = _norm(np.random.default_rng(2).standard_normal(len(t)), peak=0.5)
    q = np.round(x * 32768) / 32768                         # exact 16-bit grid (2^15)
    sf.write(path, q, SR, subtype="PCM_24")


def make_real_24(path):
    """Genuine full-resolution 24-bit -> fake_24bit False."""
    t = _t(2.0)
    x = _norm(np.random.default_rng(3).standard_normal(len(t)), peak=0.5)
    sf.write(path, x, SR, subtype="PCM_24")


def make_silence(path):
    sf.write(path, np.zeros((int(SR * 2), 2)), SR, subtype="PCM_16")


def make_dead_channel(path):
    t = _t(2.0)
    live = _norm(np.random.default_rng(4).standard_normal(len(t)))
    sf.write(path, np.stack([live, np.zeros(len(t))], axis=1), SR, subtype="PCM_16")


# --- band behavior ----------------------------------------------------------
def test_low_fixture_scores_low(tmp_path):
    p = tmp_path / "low.wav"
    make_low(str(p))
    feats = F.extract(str(p))
    result = S.score(feats)
    assert result["band"] == "LOW", (result, feats)
    assert feats["ceiling_ratio"] > 0.9
    assert feats["hf_music_corr"] > 0.45


def test_high_fixture_scores_high(tmp_path):
    p = tmp_path / "high.wav"
    make_high(str(p))
    feats = F.extract(str(p))
    result = S.score(feats)
    assert result["band"] == "HIGH", (result, feats)
    assert feats["ceiling_ratio"] < 0.74
    assert feats["rolloff_db_per_khz"] < -5.0


def test_hf_music_corr_discriminates(tmp_path):
    lo, hi = tmp_path / "low.wav", tmp_path / "high.wav"
    make_low(str(lo))
    make_high(str(hi))
    corr_lo = F.extract(str(lo))["hf_music_corr"]
    corr_hi = F.extract(str(hi))["hf_music_corr"]
    assert corr_lo > corr_hi, (corr_lo, corr_hi)


# --- individual features ----------------------------------------------------
def test_fake_24bit_detected(tmp_path):
    padded, real = tmp_path / "padded.wav", tmp_path / "real.wav"
    make_padded_24(str(padded))
    make_real_24(str(real))
    assert F.extract(str(padded))["fake_24bit"] is True
    assert F.extract(str(real))["fake_24bit"] is False


def test_assume_lossy_drops_bandwidth(tmp_path):
    p = tmp_path / "high.wav"
    make_high(str(p))
    feats = F.extract(str(p))
    full = S.score(feats, assume_lossy=False)
    lossy = S.score(feats, assume_lossy=True)
    factors = {r["factor"] for r in lossy["reasons"]}
    assert "ceiling_ratio" not in factors
    assert "rolloff_db_per_khz" not in factors
    assert lossy["score"] < full["score"]


# --- quality ----------------------------------------------------------------
def test_silence_rejected(tmp_path):
    p = tmp_path / "silence.wav"
    make_silence(str(p))
    qc = Q.check(str(p))
    assert qc["reject"] is True
    assert any(f["code"] == "silence" for f in qc["flags"])


def test_dead_channel_flagged(tmp_path):
    p = tmp_path / "dead.wav"
    make_dead_channel(str(p))
    qc = Q.check(str(p))
    assert any(f["code"] == "dead_channel" for f in qc["flags"])
    assert qc["reject"] is False  # one live channel remains
