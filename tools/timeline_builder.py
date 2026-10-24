#!/usr/bin/env python3
"""
Super-Timeline Builder
----------------------
Merges timestamped CSV exports from different tools (browser history, file system,
registry, event logs, AXIOM/Autopsy/KAPE exports) into ONE chronological timeline,
normalized to UTC, so activity from different sources can be correlated.

Each input CSV only needs a timestamp column and a description column. The script
auto-detects common column names, or you can name them with --time-col / --desc-col.

Usage:
    python3 timeline_builder.py ../samples/web_history.csv ../samples/file_activity.csv
    python3 timeline_builder.py *.csv --start "2007-07-12 23:00" --end "2007-07-13 00:00"
    python3 timeline_builder.py *.csv --tz-offset -5 --out timeline.csv   # inputs recorded in UTC-5
"""

import argparse
import csv
import os
import sys
from datetime import datetime, timedelta

TIME_COLS = ["timestamp", "timestamp_utc", "time", "datetime", "date/time", "date", "visited", "created",
             "modified", "last_visited", "event_time", "time_utc"]
DESC_COLS = ["description", "event", "url", "title", "message", "artifact", "file", "path", "name", "details"]
FORMATS = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%m/%d/%Y %I:%M:%S %p",
           "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%d-%b-%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ",
           "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%fZ"]


def parse_time(value):
    value = value.strip().replace(" UTC", "").replace(" [UTC]", "")
    for fmt in FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def pick(headers, wanted, override):
    if override:
        return override if override in headers else None
    lower = {h.lower().strip(): h for h in headers}
    return next((lower[w] for w in wanted if w in lower), None)


def main():
    p = argparse.ArgumentParser(description="Merge CSV artifacts into a single UTC timeline.")
    p.add_argument("csvs", nargs="+")
    p.add_argument("--time-col")
    p.add_argument("--desc-col")
    p.add_argument("--tz-offset", type=float, default=0, help="hours the INPUT times are offset from UTC (e.g. -5)")
    p.add_argument("--start", help="only events at/after this UTC time")
    p.add_argument("--end", help="only events before this UTC time")
    p.add_argument("--out", help="write merged timeline CSV")
    args = p.parse_args()

    start = parse_time(args.start) if args.start else None
    end = parse_time(args.end) if args.end else None
    events, skipped = [], 0
    for path in args.csvs:
        source = os.path.splitext(os.path.basename(path))[0]
        with open(path, newline="", errors="replace") as f:
            reader = csv.DictReader(f)
            tcol = pick(reader.fieldnames or [], TIME_COLS, args.time_col)
            dcol = pick(reader.fieldnames or [], DESC_COLS, args.desc_col)
            if not tcol:
                print(f"[!] {path}: no timestamp column found (use --time-col). Skipping.", file=sys.stderr)
                continue
            for row in reader:
                ts = parse_time(row.get(tcol, ""))
                if not ts:
                    skipped += 1
                    continue
                ts -= timedelta(hours=args.tz_offset)
                if (start and ts < start) or (end and ts >= end):
                    continue
                desc = row.get(dcol, "") if dcol else ""
                extra = "; ".join(f"{k}={v}" for k, v in row.items() if k not in (tcol, dcol) and v)
                events.append((ts, source, desc, extra))

    events.sort(key=lambda e: e[0])
    print(f"[*] {len(events)} event(s) from {len(args.csvs)} source(s)" + (f", {skipped} unparseable row(s) skipped" if skipped else ""))
    print(f"\n{'Timestamp (UTC)':<20} {'Source':<16} Event")
    print("-" * 100)
    prev = None
    for ts, source, desc, extra in events:
        gap = "" if prev is None or (ts - prev) < timedelta(hours=1) else "\n" + " " * 20 + f"... {ts - prev} gap ...\n"
        print(f"{gap}{ts:%Y-%m-%d %H:%M:%S}  {source[:16]:<16} {desc}" + (f"  [{extra}]" if extra else ""))
        prev = ts

    if args.out:
        with open(args.out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp_utc", "source", "event", "details"])
            for ts, source, desc, extra in events:
                w.writerow([ts.strftime("%Y-%m-%d %H:%M:%S"), source, desc, extra])
        print(f"\n[*] Timeline written to {args.out}")


if __name__ == "__main__":
    main()
