# Contributing

Thanks for your interest in sonar-qc. Contributions that improve measurement
accuracy, reduce false positives/negatives, add honest validation data, or
sharpen the documentation are very welcome.

## Explicit non-goal — read this first

**This project will not accept contributions aimed at evading detection or
removing generative-rendering fingerprints from audio.**

Stripping provenance from generated audio so it can be passed off as
non-generated is the exact harm this tool exists to counter. Pull requests,
issues, or feature requests in that direction will be declined.

## Good contributions

- New or refined **features** with a clear physical rationale (document them in
  `docs/METHODOLOGY.md`).
- **Threshold recalibration** backed by data — the fingerprints drift as models
  change, so weights in `sonar_qc/scoring.py` need periodic review.
- **Validation data**: results tables from real screening runs. Describe the
  sources; **do not commit copyrighted audio** (fixtures are synthetic — see
  `tests/fixtures/README.md`).
- **False-positive / false-negative reports**, especially on lossy or heavily
  reworked material.
- Documentation that keeps the framing honest: this is a disclosure aid, never
  proof, and never an accusation tool.

## Ground rules

- Keep dependencies light (numpy, scipy, soundfile, matplotlib).
- Keep `features.py` free of scoring, and keep every scoring weight in the
  module-level tables in `scoring.py`.
- Every score must carry its evidence (`reasons`). Opaque scores are rejected.
- Add tests for new features and scoring bands. Scoring must be testable without
  audio I/O.
