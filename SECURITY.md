# Security Policy

## Scope

sonar-qc parses untrusted audio files (via libsndfile/soundfile, numpy, scipy).
The security surface that matters most:

- crafted audio files causing crashes, hangs, or memory exhaustion during
  analysis (a screener must survive hostile input — it sits on intake paths);
- path handling in batch mode and report generation.

## Reporting a vulnerability

Please report vulnerabilities privately via
[GitHub Security Advisories](https://github.com/cryptoleo79/sonar-qc/security/advisories/new)
rather than a public issue. Include the sonar-qc version, a minimal description
of the malformed input (or a generator script — **do not attach copyrighted
audio**), and the observed behavior.

You can expect an acknowledgement within a week. Fixes are released as patch
versions and noted in the CHANGELOG.

## Not security issues

- False positives/negatives in scoring — that is calibration, not security;
  open a regular issue (there is a template for it).
- The existence of ways to evade detection. Evasion is an acknowledged
  limitation of any screener (see `docs/LIMITATIONS.md`), and this project
  does not accept work that *builds* evasion (see `CONTRIBUTING.md`).
