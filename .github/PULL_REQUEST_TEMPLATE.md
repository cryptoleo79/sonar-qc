<!-- Thanks! Quick scope check: contributions aimed at evading detection or
removing fingerprints are out of scope and will be declined (CONTRIBUTING.md). -->

## What this changes

## Checklist

- [ ] `pytest -q` passes and new behavior is covered by tests
- [ ] `ruff check sonar_qc/ tests/` is clean
- [ ] No audio files committed (fixtures are synthesized in code)
- [ ] Scoring weights/thresholds remain in the visible tables in `scoring.py` /
      `signatures.py` (no magic numbers in branches)
- [ ] Every score/hint still carries its evidence (`reasons` / `evidence`)
- [ ] New measurements are documented in `docs/METHODOLOGY.md`; wording keeps
      the disclosure-aid framing (no certainty claims)
