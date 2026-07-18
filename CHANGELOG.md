# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — 2026-07-18

Localization and signature hints: WHERE the fingerprint lives and WHAT KIND of
pipeline the evidence is consistent with. The honesty contract is unchanged and
now enforced by tests: hints are "consistent with," never identification.

### Added
- **Artifact localization** (`sonar_qc.localize`, CLI `--segments`): sliding
  5 s windows scored with the same weights as the whole file; summary names the
  worst segment and the fraction of windows ≥ MEDIUM. Each scoring factor is
  also mapped to the frequency region its evidence lives in.
- **Segment escalation**: flags the splice case where a partly-generative track
  scores LOW overall but individual windows score HIGH (file-wide averaging
  masks the walled segment). Informational — exit codes stay whole-file.
- **Signature hints** (`sonar_qc.signatures`): visible profile table matching
  features to known families — generative-render patterns, ~128 kbps and
  high-bitrate codec ceilings, padded-24-bit export tell, native full-bandwidth
  PCM. Confidence capped at "indicative"; every hint carries its evidence; the
  no-identification framing is tested.
- **Report**: suspicion-over-time strip (4th panel) aligned with the
  spectrogram when `--segments` is used.
- **CSV**: `signature_hints` and `worst_window` columns.
- `features.extract_from_array()` for in-memory analysis (windowing reuses it).

## [0.1.0] — 2026-07-18

Initial release — a spectral provenance & quality screener for music
submissions. It reports a calibrated suspicion score with the evidence behind
it; it does not (and cannot) prove a track is or is not generatively produced.

### Added
- **Feature extraction** (`sonar_qc.features`): bandwidth ceiling
  (`ceiling_hz` / `ceiling_ratio`), HF rolloff slope, HF↔music envelope
  correlation (the key discriminator), 24/32-bit padding detection, HF stereo
  coherence, and above-ceiling energy.
- **Scoring** (`sonar_qc.scoring`): weighted additive score → LOW / MEDIUM /
  HIGH bands, with every weight in visible module tables and an evidence
  (`reasons`) list for every score. `--assume-lossy` drops the
  format-confounded bandwidth features.
- **Quality control** (`sonar_qc.quality`): clipping, DC offset, dead channel,
  silence, and duration checks with hard-reject semantics.
- **CLI** (`sonar-qc` / `python -m sonar_qc`): single file, `--batch`,
  `--json`, `--csv`, `--report` (PNG spectrogram + LTAS + HF zoom), and
  `--assume-lossy`. Exit codes `0/1/2/3/4` for pipeline gating.
- **Docs**: methodology, limitations (the lossy-codec confound as the primary
  false-positive path), and an explicit anti-evasion non-goal.
- **Tests**: feature/quality behavior on synthetic fixtures and full scoring
  coverage with no audio I/O.
- **CI**: GitHub Actions matrix on Python 3.10 / 3.11 / 3.12.

[0.2.0]: https://github.com/cryptoleo79/sonar-qc/releases/tag/v0.2.0
[0.1.0]: https://github.com/cryptoleo79/sonar-qc/releases/tag/v0.1.0
