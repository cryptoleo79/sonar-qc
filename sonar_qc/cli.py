"""Command-line interface.

    sonar-qc track.wav                     human-readable, evidence listed
    sonar-qc track.wav --json              machine-readable
    sonar-qc ./folder --batch --csv out.csv
    sonar-qc track.wav --report ./reports  PNG: spectrogram + LTAS + HF zoom
    sonar-qc track.mp3 --assume-lossy      score without format-confounded bands

Exit codes (usable as a submission gate):
    0 LOW · 1 MEDIUM · 2 HIGH · 3 quality REJECT · 4 usage/error
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from . import features as F
from . import scoring as S
from . import quality as Q

AUDIO_EXTS = {".wav", ".flac", ".aiff", ".aif", ".ogg", ".oga", ".opus",
              ".mp3", ".aac", ".m4a", ".wma"}

EXIT_LOW, EXIT_MEDIUM, EXIT_HIGH, EXIT_REJECT, EXIT_ERROR = 0, 1, 2, 3, 4
_BAND_EXIT = {"LOW": EXIT_LOW, "MEDIUM": EXIT_MEDIUM, "HIGH": EXIT_HIGH}


def _analyze_one(path, assume_lossy=False):
    """Return a result dict for one file. ``kind`` is 'reject', 'ok', or 'error'."""
    try:
        qc = Q.check(path)
    except Exception as exc:  # unreadable / unsupported container
        return {"file": path, "kind": "error", "error": f"{type(exc).__name__}: {exc}"}

    if qc["reject"]:
        return {"file": path, "kind": "reject", "quality": qc}

    feats = F.extract(path)
    lossy = F.is_lossy(path, F_info(path))
    result = S.score(feats, assume_lossy=assume_lossy)
    return {
        "file": path,
        "kind": "ok",
        "quality": qc,
        "features": feats,
        "score": result,
        "lossy_source": lossy,
        "assume_lossy": assume_lossy,
    }


def F_info(path):
    import soundfile as sf
    try:
        return sf.info(path)
    except Exception:
        return None


# --- rendering --------------------------------------------------------------
def _fmt_human(res):
    lines = []
    name = os.path.basename(res["file"])
    if res["kind"] == "error":
        return f"ERROR  {name}\n  {res['error']}"
    if res["kind"] == "reject":
        lines.append(f"REJECT {name}  (quality)")
        for fl in res["quality"]["flags"]:
            mark = "✗" if fl["severity"] == "reject" else "!"
            lines.append(f"  {mark} {fl['code']}: {fl['detail']}")
        return "\n".join(lines)

    sc = res["score"]
    feats = res["features"]
    lines.append(f"{sc['band']:<6} {name}   score {sc['score']}")
    lines.append(f"  {sc['band_label']}")
    if res.get("assume_lossy"):
        lines.append("  [--assume-lossy] bandwidth features excluded from score")
    elif res.get("lossy_source"):
        lines.append("  [caveat] lossy source: bandwidth-derived points (ceiling, rolloff) "
                     "may be unreliable — consider --assume-lossy")
    if sc["reasons"]:
        lines.append("  evidence:")
        for r in sc["reasons"]:
            lines.append(f"    +{r['points']:<3} {r['detail']}")
    else:
        lines.append("  evidence: none — no measured red flags")
    warns = [fl for fl in res["quality"]["flags"] if fl["severity"] == "warn"]
    if warns:
        lines.append("  quality notes:")
        for fl in warns:
            lines.append(f"    ! {fl['code']}: {fl['detail']}")
    lines.append("  features: "
                 f"ceiling {feats['ceiling_hz']:.0f} Hz (ratio {feats['ceiling_ratio']:.2f}), "
                 f"rolloff {feats['rolloff_db_per_khz']:.1f} dB/kHz, "
                 f"hf_music_corr {feats['hf_music_corr']:.2f}, "
                 f"hf_stereo_corr {feats['hf_stereo_corr']:.2f}, "
                 f"fake_24bit {feats['fake_24bit']}")
    return "\n".join(lines)


def _csv_rows(results):
    header = ["file", "kind", "band", "score", "assume_lossy", "lossy_source",
              "ceiling_hz", "ceiling_ratio", "rolloff_db_per_khz", "hf_music_corr",
              "hf_stereo_corr", "above_ceiling_level_db", "fake_24bit",
              "sr", "duration_s", "subtype", "channels", "quality_reject", "note"]
    rows = [header]
    for res in results:
        if res["kind"] == "ok":
            f, sc = res["features"], res["score"]
            rows.append([res["file"], "ok", sc["band"], sc["score"], res.get("assume_lossy"),
                         res.get("lossy_source"), f["ceiling_hz"], round(f["ceiling_ratio"], 4),
                         round(f["rolloff_db_per_khz"], 3) if f["rolloff_db_per_khz"] == f["rolloff_db_per_khz"] else "",
                         round(f["hf_music_corr"], 4) if f["hf_music_corr"] == f["hf_music_corr"] else "",
                         round(f["hf_stereo_corr"], 4) if f["hf_stereo_corr"] == f["hf_stereo_corr"] else "",
                         round(f["above_ceiling_level_db"], 2) if f["above_ceiling_level_db"] == f["above_ceiling_level_db"] else "",
                         f["fake_24bit"], f["sr"], round(f["duration_s"], 3), f["subtype"],
                         f["channels"], res["quality"]["reject"], ""])
        elif res["kind"] == "reject":
            note = ";".join(fl["code"] for fl in res["quality"]["flags"] if fl["severity"] == "reject")
            rows.append([res["file"], "reject", "", "", "", "", "", "", "", "", "", "", "",
                         "", "", "", "", True, note])
        else:
            rows.append([res["file"], "error", "", "", "", "", "", "", "", "", "", "", "",
                         "", "", "", "", "", res.get("error", "")])
    return rows


def _write_csv(path, results):
    import csv
    with open(path, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(_csv_rows(results))


def _iter_audio(folder):
    for root, _dirs, files in os.walk(folder):
        for name in sorted(files):
            if os.path.splitext(name)[1].lower() in AUDIO_EXTS:
                yield os.path.join(root, name)


def _exit_code_for(res):
    if res["kind"] == "error":
        return EXIT_ERROR
    if res["kind"] == "reject":
        return EXIT_REJECT
    return _BAND_EXIT.get(res["score"]["band"], EXIT_ERROR)


def build_parser():
    p = argparse.ArgumentParser(
        prog="sonar-qc",
        description="Audio provenance & quality screening. Reports a calibrated "
                    "suspicion score with evidence — it does NOT prove a track is or "
                    "is not generatively produced.",
    )
    p.add_argument("path", help="audio file, or a directory with --batch")
    p.add_argument("--batch", action="store_true", help="treat PATH as a directory of audio")
    p.add_argument("--json", action="store_true", help="emit JSON")
    p.add_argument("--csv", metavar="OUT", help="write results as CSV to OUT")
    p.add_argument("--report", metavar="DIR", help="write a PNG report per file into DIR")
    p.add_argument("--assume-lossy", action="store_true",
                   help="score without the format-confounded bandwidth features")
    p.add_argument("--version", action="version", version=f"sonar-qc {__version__}")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.batch:
        if not os.path.isdir(args.path):
            print(f"error: --batch requires a directory, got {args.path}", file=sys.stderr)
            return EXIT_ERROR
        targets = list(_iter_audio(args.path))
        if not targets:
            print(f"error: no audio files under {args.path}", file=sys.stderr)
            return EXIT_ERROR
    else:
        if not os.path.isfile(args.path):
            print(f"error: file not found: {args.path}", file=sys.stderr)
            return EXIT_ERROR
        targets = [args.path]

    results = [_analyze_one(t, assume_lossy=args.assume_lossy) for t in targets]

    if args.report:
        from . import report as R
        for res in results:
            if res["kind"] == "ok":
                try:
                    png = R.generate(res["file"], res["features"], res["score"], args.report)
                    res["report_png"] = png
                except Exception as exc:  # reporting must never break analysis
                    res["report_error"] = f"{type(exc).__name__}: {exc}"

    if args.csv:
        _write_csv(args.csv, results)

    if args.json:
        payload = results[0] if (len(results) == 1 and not args.batch) else results
        print(json.dumps(payload, indent=2, default=str))
    else:
        print("\n\n".join(_fmt_human(r) for r in results))
        if args.csv:
            print(f"\n[csv] wrote {args.csv}", file=sys.stderr)
        for res in results:
            if res.get("report_png"):
                print(f"[report] {res['report_png']}", file=sys.stderr)

    # exit code = worst severity across all analyzed files
    codes = [_exit_code_for(r) for r in results]
    return max(codes) if codes else EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
