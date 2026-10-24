#!/usr/bin/env python3
"""
USBSTOR Device History Parser
-----------------------------
Lists USB storage devices that have been connected to a Windows system, using the
SYSTEM hive key  ControlSet00X\\Enum\\USBSTOR.

Two input modes:
  1. A .reg export of the USBSTOR key (regedit → right-click USBSTOR → Export, or
     export from Registry Explorer / FTK Registry Viewer). Works on any OS.
  2. --live  : read the current Windows machine's registry directly (Windows only).

For every device it reports vendor, product, revision, serial number, and friendly name,
and flags serials with '&' in the second character, which Windows generates when the
device has no unique hardware serial (that makes attribution weaker).

Usage:
    python3 usbstor_parser.py ../samples/usbstor_export.reg
    python3 usbstor_parser.py ../samples/usbstor_export.reg --csv usb_devices.csv
    python3 usbstor_parser.py --live          # on Windows, as Administrator
"""

import argparse
import codecs
import csv
import re
import sys

KEY_RE = re.compile(r"^\[.*\\Enum\\USBSTOR\\([^\\\]]+)\\([^\\\]]+)\]$", re.I)
CLASS_RE = re.compile(r"^(?P<type>[^&]+)&Ven_(?P<ven>[^&]*)&Prod_(?P<prod>[^&]*)(?:&Rev_(?P<rev>.*))?$", re.I)
VAL_RE = re.compile(r'^"(?P<name>[^"]+)"="(?P<val>.*)"$')


def split_class(device_class):
    m = CLASS_RE.match(device_class)
    if not m:
        return {"type": "", "vendor": "", "product": device_class, "revision": ""}
    return {"type": m["type"], "vendor": m["ven"].replace("_", " ").strip(),
            "product": m["prod"].replace("_", " ").strip(), "revision": m["rev"] or ""}


def read_reg_text(path):
    raw = open(path, "rb").read()
    if raw.startswith(codecs.BOM_UTF16_LE) or raw[1:2] == b"\x00":
        return raw.decode("utf-16")       # regedit exports are UTF-16 LE
    return raw.decode("utf-8", errors="replace")


def parse_reg(path):
    devices, current = {}, None
    for line in read_reg_text(path).splitlines():
        line = line.strip()
        if line.startswith("["):
            m = KEY_RE.match(line)
            current = None
            if m:
                current = (m[1], m[2])
                devices.setdefault(current, {"class": m[1], "serial": m[2], "friendly_name": ""})
        elif current:
            v = VAL_RE.match(line)
            if v and v["name"].lower() == "friendlyname":
                devices[current]["friendly_name"] = v["val"]
    return list(devices.values())


def parse_live():
    try:
        import winreg
    except ImportError:
        sys.exit("[!] --live only works on Windows. Export the USBSTOR key to a .reg file instead.")
    out = []
    root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Enum\USBSTOR")
    for i in range(winreg.QueryInfoKey(root)[0]):
        cls = winreg.EnumKey(root, i)
        ck = winreg.OpenKey(root, cls)
        for j in range(winreg.QueryInfoKey(ck)[0]):
            serial = winreg.EnumKey(ck, j)
            try:
                name = winreg.QueryValueEx(winreg.OpenKey(ck, serial), "FriendlyName")[0]
            except OSError:
                name = ""
            out.append({"class": cls, "serial": serial, "friendly_name": name})
    return out


def main():
    p = argparse.ArgumentParser(description="Parse USBSTOR device history.")
    p.add_argument("regfile", nargs="?", help=".reg export of the USBSTOR key")
    p.add_argument("--live", action="store_true", help="read this Windows machine's registry")
    p.add_argument("--csv")
    args = p.parse_args()
    if not args.live and not args.regfile:
        p.error("give a .reg file or use --live")

    devices = parse_live() if args.live else parse_reg(args.regfile)
    rows = []
    for d in devices:
        info = split_class(d["class"])
        serial = d["serial"]
        rows.append({**info, "serial": serial,
                     "unique_serial": "no" if len(serial) > 1 and serial[1] == "&" else "yes",
                     "friendly_name": d["friendly_name"]})
    rows.sort(key=lambda r: (r["vendor"].lower(), r["product"].lower(), r["serial"]))

    print(f"[*] {len(rows)} USB storage device(s) found\n")
    print(f"{'Vendor':<10} {'Product':<16} {'Rev':<6} {'Serial':<26} {'Uniq':<5} Friendly name")
    print("-" * 100)
    for r in rows:
        print(f"{r['vendor'][:10]:<10} {r['product'][:16]:<16} {r['revision'][:6]:<6} "
              f"{r['serial'][:26]:<26} {r['unique_serial']:<5} {r['friendly_name']}")
    vendors = sorted({r["vendor"] for r in rows if r["vendor"]})
    print(f"\n[*] Vendors: {', '.join(vendors)}")
    print("[*] Next steps: match serials to MountPoints2 (NTUSER.DAT) for the user, and to")
    print("    SYSTEM\\MountedDevices for drive letters; check setupapi.dev.log for first-connect times.")

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["vendor"])
            w.writeheader()
            w.writerows(rows)
        print(f"[*] CSV written to {args.csv}")


if __name__ == "__main__":
    main()
