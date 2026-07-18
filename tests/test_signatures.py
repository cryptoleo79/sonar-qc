"""Signature-hint tests — pure dicts, no audio I/O.

The framing contract is tested alongside the matching logic: hints must carry
evidence, and confidence must never exceed 'indicative'.
"""
from sonar_qc import signatures as SIG


def feats(**kw):
    base = {
        "ceiling_hz": 22050.0, "ceiling_ratio": 1.0,
        "rolloff_db_per_khz": 0.0, "hf_music_corr": 0.9,
        "hf_stereo_corr": 0.1, "fake_24bit": False, "sr": 44100,
    }
    base.update(kw)
    return base


def ids(hits):
    return [h["id"] for h in hits]


def test_generative_render_pattern_matches():
    hits = SIG.match(feats(ceiling_ratio=0.71, ceiling_hz=15660, hf_stereo_corr=0.98))
    assert "generative-render" in ids(hits)
    assert "suno-like-render" in ids(hits)


def test_decorrelated_haze_matches():
    hits = SIG.match(feats(ceiling_ratio=0.80, hf_music_corr=0.10))
    assert "generative-render-decorrelated-haze" in ids(hits)


def test_mp3_class_ceiling_matches():
    hits = SIG.match(feats(ceiling_hz=16000, ceiling_ratio=0.73, rolloff_db_per_khz=-10.8))
    assert "mp3-low-bitrate" in ids(hits)


def test_padded_24bit_requires_flag():
    assert "padded-24bit-export" in ids(SIG.match(feats(fake_24bit=True)))
    assert "padded-24bit-export" not in ids(SIG.match(feats(fake_24bit=False)))


def test_full_bandwidth_native():
    hits = SIG.match(feats(ceiling_ratio=0.99))
    assert "native-full-bandwidth" in ids(hits)


def test_clean_mid_ceiling_matches_nothing_spurious():
    # ceiling at 0.90 with healthy HF corr: none of the render/codec families
    hits = SIG.match(feats(ceiling_ratio=0.90, ceiling_hz=19845, rolloff_db_per_khz=-1.0))
    assert ids(hits) == []


def test_suno_like_requires_sr():
    f = feats(ceiling_hz=16000, hf_stereo_corr=0.95, sr=32000)
    assert "suno-like-render" not in ids(SIG.match(f))


def test_nan_features_never_match():
    hits = SIG.match(feats(ceiling_ratio=float("nan"), ceiling_hz=float("nan"),
                           rolloff_db_per_khz=float("nan"), hf_music_corr=float("nan"),
                           hf_stereo_corr=float("nan")))
    assert hits == []


def test_every_hit_carries_evidence_and_capped_confidence():
    hits = SIG.match(feats(ceiling_ratio=0.71, ceiling_hz=15660,
                           hf_stereo_corr=0.98, fake_24bit=True))
    assert hits
    for h in hits:
        assert h["evidence"], f"{h['id']} emitted without evidence"
        assert h["confidence"] in ("indicative", "weak"), \
            f"{h['id']} claims too much: {h['confidence']}"
        assert h["note"]


def test_profile_table_never_claims_identification():
    # the words that would turn a hint into an accusation must not appear
    for p in SIG.PROFILES:
        text = (p["label"] + " " + p["note"]).lower()
        assert "proof" not in text.replace("not proof", "").replace("no proof", "")
        assert "definitely" not in text
        assert "guarantee" not in text
