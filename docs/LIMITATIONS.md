# Limitations

sonar-qc is a **screening aid, not proof.** Read this before trusting a score.

## The primary false-positive path: lossy / lo-fi sources

Lossy codecs (MP3, AAC, Opus, Vorbis) impose their **own** bandwidth ceiling and
steep HF rolloff as part of psychoacoustic compression. So the two bandwidth
features — `ceiling_hz`/`ceiling_ratio` and `rolloff_db_per_khz` — are
**format-confounded**: a genuine human recording that only ever existed as a low
bitrate MP3 can trip both and score MEDIUM or higher on bandwidth alone.

Measured example: the *same* human track read
**−6.6 dB/kHz** rolloff as WAV and **−10.8 dB/kHz** as a 128 kbps MP3.

**Mitigations built in:**
- The CLI detects a lossy container (by extension or libsndfile format) and
  prints a caveat that bandwidth-derived points are unreliable.
- `--assume-lossy` **zeros the ceiling and rolloff contributions**, scoring on
  `hf_music_corr` and `hf_stereo_corr` only — the two features that survive
  transcoding.

When in doubt about a lossy or lo-fi source, trust `hf_music_corr` over the
bandwidth features.

## False negatives

- **High-quality or heavily reworked generative audio.** Resampling, re-recording
  through analog gear, heavy editing, or layering real instruments over a render
  can weaken or erase the fingerprints.
- **Short clips.** Envelope correlation needs enough frames to be meaningful.

## The arms race

These fingerprints are properties of *today's* rendering pipelines. As models
improve, the tells shrink. **Thresholds in `scoring.py` will need recalibration
over time.** A LOW score from a future model is not a clean bill of health — it
may just mean the model no longer leaves the artifacts this version looks for.

## What a score is not

- A HIGH score is **not** proof of AI generation, and **not** evidence that a
  creator did no work (a real human vocal routed through a generative decoder
  inherits the fingerprint — the tool measures the *pipeline*, not the person).
- A LOW score is **not** a guarantee of human origin.
- No score should be the **sole** basis for an accusation, a rejection, or a
  takedown. Use it to prompt disclosure or human review.
