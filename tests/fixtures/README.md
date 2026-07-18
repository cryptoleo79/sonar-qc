# Test fixtures

**There are no audio files committed here, by design.**

Real music is copyrighted and would bloat the repo, so the test suite
**synthesizes every fixture in code** at run time (into a temporary directory)
and deletes it afterward. See the generators in `tests/test_features.py`.

The synthetic fixtures are:

- **full-bandwidth, HF-correlated** signal (broadband noise + tones sharing one
  amplitude envelope) → expected band **LOW**;
- **hard-walled** signal (music lowpassed with a steep wall, plus HF noise that
  is *decorrelated* from the music envelope) → expected band **HIGH**;
- **16-bit content in a 24-bit container** → expected `fake_24bit == True`;
- **near-silent** and **dead-channel** signals → expected quality flags.

Because the fixtures are synthetic, the tests check *behavioral bands and flags*
(LOW/HIGH, True/False), not exact scores calibrated on real renders.
