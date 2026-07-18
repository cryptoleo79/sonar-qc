# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.1.0]: https://github.com/cryptoleo79/sonar-qc/releases/tag/v0.1.0
