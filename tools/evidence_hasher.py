#!/usr/bin/env python3
"""
Evidence Hasher & Chain-of-Custody Logger
-----------------------------------------
Computes MD5, SHA-1, and SHA-256 for evidence files (disk images, exports, single files),
optionally verifies against a known acquisition hash, and appends every action to a
chain-of-custody log (CSV) with examiner, case number, and UTC timestamp.

Why: if an evidence file changes in any way its hash changes, so matching hashes are how
you show the evidence you analyzed is the evidence that was acquired.

Usage:
    python3 evidence_hasher.py evidence.E01 --case 2026-014 --examiner "K. Washington"
    python3 evidence_hasher.py evidence.E01 --verify-md5 31217210a1a69f272079a3bde3d9d8fc
    python3 evidence_hasher.py ./exports/ --case 2026-014 --examiner kw     # every file in a folder
"""

import argparse
import csv
import hashlib
import os
import sys
from datetime import datetime, timezone

LOG_FIELDS = ["timestamp_utc", "case", "examiner", "action", "file", "size_bytes",
              "md5", "sha1", "sha256", "verified_against", "result"]


def hash_file(path, chunk=1024 * 1024):
    md5, sha1, sha256 = hashlib.md5(), hashlib.sha1(), hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            md5.update(block)
            sha1.update(block)
            sha256.update(block)
    return md5.hexdigest(), sha1.hexdigest(), sha256.hexdigest()


def iter_files(target):
    if os.path.isfile(target):
        yield target
    else:
        for root, _, files in os.walk(target):
            for name in sorted(files):
                yield os.path.join(root, name)


def main():
    p = argparse.ArgumentParser(description="Hash evidence and log chain of custody.")
    p.add_argument("target", help="file or directory")
    p.add_argument("--case", default="UNSPECIFIED")
    p.add_argument("--examiner", default=os.environ.get("USER", "unknown"))
    p.add_argument("--log", default="chain_of_custody.csv")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--verify-md5")
    g.add_argument("--verify-sha1")
    g.add_argument("--verify-sha256")
    args = p.parse_args()

    if not os.path.exists(args.target):
        sys.exit(f"[!] Not found: {args.target}")
    expected = next(((alg, v.lower()) for alg, v in (("md5", args.verify_md5), ("sha1", args.verify_sha1),
                                                      ("sha256", args.verify_sha256)) if v), None)

    new_log = not os.path.exists(args.log)
    failures = 0
    with open(args.log, "a", newline="") as logf:
        w = csv.DictWriter(logf, fieldnames=LOG_FIELDS)
        if new_log:
            w.writeheader()
        for path in iter_files(args.target):
            if os.path.abspath(path) == os.path.abspath(args.log):
                continue
            md5, sha1, sha256 = hash_file(path)
            row = {"timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                   "case": args.case, "examiner": args.examiner, "action": "hash",
                   "file": os.path.abspath(path), "size_bytes": os.path.getsize(path),
                   "md5": md5, "sha1": sha1, "sha256": sha256, "verified_against": "", "result": ""}
            print(f"\n{path}  ({row['size_bytes']:,} bytes)")
            print(f"  MD5    {md5}\n  SHA1   {sha1}\n  SHA256 {sha256}")
            if expected:
                alg, value = expected
                ok = {"md5": md5, "sha1": sha1, "sha256": sha256}[alg] == value
                row.update(action="verify", verified_against=f"{alg}:{value}", result="MATCH" if ok else "MISMATCH")
                print(f"  {'[MATCH]   ' if ok else '[MISMATCH]'} expected {alg.upper()} {value}")
                failures += not ok
            w.writerow(row)
    print(f"\n[*] Logged to {args.log}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
