# Methodology

What each feature measures, how it is computed, and why it carries signal.
All features are computed from a **mono mixdown at the file's native sample
rate** unless noted. Nothing here interprets — interpretation is in
[`sonar_qc/scoring.py`](../sonar_qc/scoring.py).

The spectral features use a **Welch PSD** (`scipy.signal.welch`,
`nperseg = min(32768, len)`), converted to dB as `10·log10(PSD + 1e-20)`.

## ceiling_hz / ceiling_ratio — bandwidth ceiling

The reference level is the mean PSD (dB) over **8–12 kHz**. Stepping up from
12 kHz in **250 Hz** steps, the ceiling is the first `lo` where the mean over
`[lo, lo+500)` falls **more than 25 dB** below the reference. If that never
happens, the ceiling defaults to Nyquist. `ceiling_ratio = ceiling_hz / Nyquist`.

*Why:* many generative renders and low-bitrate encodes stop hard at a fixed
frequency; a natural recording usually tapers to Nyquist.

## rolloff_db_per_khz — HF rolloff slope

Linear fit (dB vs kHz) of the PSD over **15–18 kHz**. A steep negative slope is a
hard synthetic wall.

*Confound:* **lossy codecs produce the same steep rolloff.** This feature is
format-confounded and is dropped under `--assume-lossy`. See
[LIMITATIONS.md](LIMITATIONS.md).

## hf_music_corr — HF vs music envelope correlation (the key discriminator)

1. **HF signal:** 6th-order Butterworth highpass at `min(14000, 0.9·Nyquist)`.
2. **Music signal:** 4th-order bandpass **200–8000 Hz**.
3. Frame both at **50 ms**, take the RMS envelope of each.
4. Return the **Pearson correlation** of the two envelopes.

*Why:* real cymbals, air, and transients rise and fall *with* the music, so their
HF envelope tracks the music-band envelope. A generative/vocoder HF haze is
comparatively independent of the musical content, so the correlation is low.
Because it does not depend on absolute bandwidth, this feature survives lossy
transcoding and carries the score under `--assume-lossy`.

## fake_24bit — bit-depth padding

For 24/32-bit PCM containers only: read as `int32` and inspect
`(raw >> 8) & 0xFF` (the low byte of the 24-bit sample). If it takes **≤2 distinct
values**, the low bits are unused — i.e. 16-bit content padded into a wider
wrapper. Not applicable to ≤16-bit or float containers.

## hf_stereo_corr — stereo HF coherence

L/R sample correlation of the highpassed signal (same highpass as above).
Near **1.0** is a synthetic tell — genuinely captured HF decorrelates across the
stereo field. NaN for mono input.

## above_ceiling_level_db — energy above the ceiling

Mean PSD level over `(ceiling+500 Hz, 0.98·Nyquist)`. Distinguishes a real
dither/noise floor (some energy) from digital silence (none) above the ceiling.

## Carried context

`sr`, `duration_s`, `subtype`, `channels` are attached for reporting and CSV.

## Robustness

Filters are skipped (feature → NaN) when the signal is shorter than the filter's
padding requirement or when a band edge is invalid for a low sample rate.
Envelope correlations return NaN on silent/constant input. NaN features simply
contribute no points — they never raise and never inflate a score.
