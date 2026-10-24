#!/usr/bin/env python3
"""
File Signature Analyzer
-----------------------
Compares each file's extension with its real type, determined from its "magic bytes"
(the first bytes of the file). A mismatch, such as a JPEG renamed to .txt or an EXE
renamed to .pdf, is a classic way to hide data and a standard step in forensic tools
("signature analysis" in Forensic Explorer, EnCase, and Autopsy).

Usage:
    python3 file_signature_check.py ./suspect_folder
    python3 file_signature_check.py ./suspect_folder --mismatches-only --csv sig_report.csv
"""

import argparse
import csv
import os
import sys

# (magic bytes, offset, type label, extensions that are legitimate for it)
SIGNATURES = [
    (b"\xFF\xD8\xFF", 0, "JPEG image", {"jpg", "jpeg", "jfif", "jpe"}),
    (b"\x89PNG\r\n\x1a\n", 0, "PNG image", {"png"}),
    (b"GIF87a", 0, "GIF image", {"gif"}),
    (b"GIF89a", 0, "GIF image", {"gif"}),
    (b"BM", 0, "BMP image", {"bmp", "dib"}),
    (b"%PDF", 0, "PDF document", {"pdf"}),
    (b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1", 0, "MS Office 97-2003 (OLE)", {"doc", "xls", "ppt", "msg", "msi", "vsd"}),
    (b"PK\x03\x04", 0, "ZIP / Office Open XML", {"zip", "docx", "xlsx", "pptx", "jar", "apk", "odt", "epub"}),
    (b"Rar!\x1a\x07", 0, "RAR archive", {"rar"}),
    (b"7z\xBC\xAF\x27\x1C", 0, "7-Zip archive", {"7z"}),
    (b"\x1F\x8B", 0, "GZIP archive", {"gz", "tgz"}),
    (b"MZ", 0, "Windows executable (PE)", {"exe", "dll", "sys", "scr", "cpl", "ocx", "com"}),
    (b"\x7FELF", 0, "Linux executable (ELF)", {"", "so", "elf", "bin", "o"}),
    (b"SQLite format 3\x00", 0, "SQLite database", {"db", "sqlite", "sqlite3", "db3"}),
    (b"regf", 0, "Windows registry hive", {"", "dat", "hve", "log1", "log2"}),
    (b"EVF\x09\x0D\x0A\xFF\x00", 0, "EnCase evidence file (E01)", {"e01", "ex01"}),
    (b"ID3", 0, "MP3 audio", {"mp3"}),
    (b"ftyp", 4, "MP4 / MOV video", {"mp4", "m4v", "mov", "m4a", "3gp"}),
    (b"RIFF", 0, "RIFF (WAV/AVI/WEBP)", {"wav", "avi", "webp"}),
    (b"{\\rtf", 0, "RTF document", {"rtf", "doc"}),
]


def identify(path):
    try:
        with open(path, "rb") as f:
            head = f.read(32)
    except OSError:
        return None, None
    for magic, off, label, exts in SIGNATURES:
        if head[off:off + len(magic)] == magic:
            return label, exts
    return None, None


def main():
    p = argparse.ArgumentParser(description="Detect files whose extension doesn't match their content.")
    p.add_argument("directory")
    p.add_argument("--mismatches-only", action="store_true")
    p.add_argument("--csv")
    args = p.parse_args()
    if not os.path.isdir(args.directory):
        sys.exit(f"[!] {args.directory} is not a directory")

    rows, mismatches = [], 0
    for root, _, files in os.walk(args.directory):
        for name in sorted(files):
            path = os.path.join(root, name)
            ext = os.path.splitext(name)[1].lower().lstrip(".")
            label, valid = identify(path)
            if label is None:
                status = "UNKNOWN"
            elif ext in valid:
                status = "OK"
            else:
                status = "MISMATCH"
                mismatches += 1
            if args.mismatches_only and status != "MISMATCH":
                continue
            rows.append((status, os.path.relpath(path, args.directory), ext or "(none)", label or "unrecognized"))

    for status, rel, ext, label in rows:
        mark = {"MISMATCH": "[!]", "OK": "[ ]", "UNKNOWN": "[?]"}[status]
        print(f"{mark} {status:<9} {rel:<45} ext={ext:<6} actual={label}")
    print(f"\n[*] {mismatches} extension/signature mismatch(es) found")

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["status", "file", "extension", "detected_type"])
            w.writerows(rows)
        print(f"[*] CSV written to {args.csv}")


if __name__ == "__main__":
    main()
