"""Scoring tests — pure, no audio I/O. Feed a feature dict, inspect the score."""

from sonar_qc import scoring as S


def feats(**kw):
    """A neutral feature dict (nothing triggers) overridden by kwargs."""
    base = {
        "ceiling_ratio": 1.0,
        "rolloff_db_per_khz": 0.0,
        "hf_music_corr": 0.9,
        "fake_24bit": False,
        "hf_stereo_corr": 0.0,
    }
    base.update(kw)
    return base


def test_clean_signal_scores_zero_low():
    r = S.score(feats())
    assert r["score"] == 0
    assert r["band"] == "LOW"
    assert r["reasons"] == []


def test_ceiling_tiers_are_alternatives_not_cumulative():
    # 0.60 is below all three thresholds but must only score the strictest (+35)
    r = S.score(feats(ceiling_ratio=0.60))
    assert r["score"] == 35
    assert [x["factor"] for x in r["reasons"]] == ["ceiling_ratio"]


def test_ceiling_middle_and_loose_tiers():
    assert S.score(feats(ceiling_ratio=0.80))["score"] == 18
    assert S.score(feats(ceiling_ratio=0.90))["score"] == 6


def test_rolloff_tiers():
    assert S.score(feats(rolloff_db_per_khz=-6.0))["score"] == 20
    assert S.score(feats(rolloff_db_per_khz=-3.0))["score"] == 8
    assert S.score(feats(rolloff_db_per_khz=-1.0))["score"] == 0


def test_hf_music_corr_tiers():
    assert S.score(feats(hf_music_corr=0.10))["score"] == 25
    assert S.score(feats(hf_music_corr=0.20))["score"] == 12
    assert S.score(feats(hf_music_corr=0.40))["score"] == 4
    assert S.score(feats(hf_music_corr=0.90))["score"] == 0


def test_flags():
    assert S.score(feats(fake_24bit=True))["score"] == 8
    assert S.score(feats(hf_stereo_corr=0.90))["score"] == 7
    assert S.score(feats(hf_stereo_corr=0.80))["score"] == 0


def test_bands():
    assert S.score(feats(ceiling_ratio=0.60, rolloff_db_per_khz=-6.0))["band"] == "HIGH"  # 55
    assert S.score(feats(ceiling_ratio=0.80, hf_music_corr=0.20))["band"] == "MEDIUM"     # 30
    assert S.score(feats(ceiling_ratio=0.90))["band"] == "LOW"                            # 6


def test_band_boundaries():
    assert S.band_for(55)[0] == "HIGH"
    assert S.band_for(54)[0] == "MEDIUM"
    assert S.band_for(25)[0] == "MEDIUM"
    assert S.band_for(24)[0] == "LOW"


def test_max_score_and_cap():
    # every signal firing: 35+20+25+8+7 = 95 (the realistic maximum)
    r = S.score(feats(ceiling_ratio=0.60, rolloff_db_per_khz=-9.0,
                      hf_music_corr=0.05, fake_24bit=True, hf_stereo_corr=0.99))
    assert r["score"] == 95
    assert r["score"] <= S.CAP
    assert r["band"] == "HIGH"


def test_assume_lossy_zeros_bandwidth_features():
    f = feats(ceiling_ratio=0.60, rolloff_db_per_khz=-9.0, hf_music_corr=0.10)
    full = S.score(f, assume_lossy=False)
    lossy = S.score(f, assume_lossy=True)
    assert full["score"] == 35 + 20 + 25
    assert lossy["score"] == 25            # only hf_music_corr survives
    assert lossy["assume_lossy"] is True


def test_nan_features_contribute_nothing():
    r = S.score(feats(ceiling_ratio=float("nan"), rolloff_db_per_khz=float("nan"),
                      hf_music_corr=float("nan"), hf_stereo_corr=float("nan")))
    assert r["score"] == 0
    assert r["reasons"] == []


def test_every_reason_names_factor_and_points():
    r = S.score(feats(ceiling_ratio=0.60, hf_music_corr=0.10))
    assert r["reasons"], "evidence must be present"
    for reason in r["reasons"]:
        assert reason["factor"]
        assert isinstance(reason["points"], int) and reason["points"] > 0
        assert reason["detail"]
