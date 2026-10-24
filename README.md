# 🧪 dfir-toolkit

Python tools that automate common **digital forensics and incident response (DFIR)** tasks: evidence integrity, signature analysis, USB device attribution, and timeline building. They're the same steps commercial suites like Magnet AXIOM, Forensic Explorer, and FTK perform, written from scratch so I understand what happens under the hood.

**Python 3.8+ standard library only**, so nothing to install. Every tool ships with sample data.

> I used these concepts in my [Windows disk forensic case study](https://github.com/kamronw23/forensic-case-study-mantooth): hash verification of an E01 image, USBSTOR analysis of 15 devices, and a cross-tool UTC timeline.

---

## 🧰 Tools

| Tool | What it does | Forensic question it answers |
|---|---|---|
| [`evidence_hasher.py`](tools/evidence_hasher.py) | MD5 + SHA-1 + SHA-256 of files or folders, verification against the acquisition hash, and an automatic **chain-of-custody log** (CSV) | *Is this evidence exactly what was acquired? Who handled it, and when?* |
| [`file_signature_check.py`](tools/file_signature_check.py) | Compares each file's **magic bytes** with its extension (20+ signatures: JPEG, PE/EXE, Office, ZIP, SQLite, registry hives, E01…) | *Is someone hiding a file by renaming it?* |
| [`usbstor_parser.py`](tools/usbstor_parser.py) | Parses the `SYSTEM\…\Enum\USBSTOR` key from a `.reg` export (any OS) or the **live registry** (Windows) into vendor, product, revision, and serial, and flags non-unique serials | *What removable storage was connected to this machine?* |
| [`timeline_builder.py`](tools/timeline_builder.py) | Merges CSV exports from different tools into one **UTC super-timeline**, with time-zone correction, date filtering, and gap detection | *What happened, in what order, across every source?* |

---

## 🚀 Quick Start

```bash
git clone https://github.com/kamronw23/dfir-toolkit.git
cd dfir-toolkit/tools
```

### Verify evidence and log chain of custody
```bash
python3 evidence_hasher.py evidence.E01 --case 2026-014 --examiner "K. Washington" \
    --verify-md5 31217210a1a69f272079a3bde3d9d8fc
```
```
evidence.E01  (128,450,048 bytes)
  MD5    31217210a1a69f272079a3bde3d9d8fc
  SHA1   ...
  SHA256 ...
  [MATCH]    expected MD5 31217210a1a69f272079a3bde3d9d8fc
[*] Logged to chain_of_custody.csv
```
Exit code `1` on a mismatch, so it can be scripted.

### Catch disguised files
```bash
python3 file_signature_check.py ../samples/sig_demo
```
```
[ ] OK        budget.xlsx      ext=xlsx   actual=ZIP / Office Open XML
[!] MISMATCH  invoice.pdf      ext=pdf    actual=Windows executable (PE)
[!] MISMATCH  notes.txt        ext=txt    actual=JPEG image
[ ] OK        report.pdf       ext=pdf    actual=PDF document

[*] 2 extension/signature mismatch(es) found
```

### USB device history
```bash
python3 usbstor_parser.py ../samples/usbstor_export.reg --csv usb_devices.csv
python3 usbstor_parser.py --live        # on Windows, as Administrator
```
```
Vendor     Product          Rev    Serial                     Uniq  Friendly name
Apple      iPod             1.62   000A270014B302AB&0         yes   Apple iPod USB Device
SanDisk    Cruzer Mini      0.1    SNDK4DB2A41B47901706&0     yes   SanDisk Cruzer Mini USB Device
Sony       Sony DSC         5.00   6&382957cd&0               no    Sony Sony DSC USB Device
```
`Uniq = no` means Windows generated the serial because the device has none, which makes tying that device to a physical drive harder.

### Build a timeline
```bash
python3 timeline_builder.py ../samples/web_history.csv ../samples/file_activity.csv \
    --start "2007-07-12 23:00" --end "2007-07-13 00:00"
```
```
2007-07-12 23:13:10  web_history      http://www.snopes.com/fraud/atm/atmcamera.asp
2007-07-12 23:14:20  file_activity    E:\Business Ideas\untitled.bmp  [Action=Opened]
2007-07-12 23:15:34  web_history      http://www.google.com/search?q=atm+card+stealing
2007-07-12 23:29:42  file_activity    E:\Business Ideas\ATM_THEFTS1.ppt  [Action=Opened]
```
It accepts most timestamp formats (`2007-07-12 23:15:34`, `07/12/2007 11:15:34 PM`, `12-Feb-2008 19:12:08 [UTC]`, ISO 8601). Use `--tz-offset -5` if a source recorded local time instead of UTC.

---

## 🧠 Forensic Principles Behind These Tools

- **Integrity first.** Hash before and after, and log every touch. Evidence you can't prove is unaltered is evidence that gets thrown out.
- **Never trust the extension.** File type comes from content, not the name.
- **Correlate, don't assume.** A single artifact is a clue; the same event seen in browser history, the file system, and the registry within seconds is a finding.
- **Normalize time.** Mixing local time and UTC is one of the most common timeline mistakes.

## 🗺️ Roadmap
- [ ] Prefetch parser (program execution evidence)
- [ ] `$MFT` timestamp parser with timestomping detection ($SI vs $FN)
- [ ] Browser history extraction from Chrome/Firefox SQLite databases
- [ ] EXIF metadata extractor for photos (camera model, GPS)

---

Part of my [cybersecurity portfolio](https://github.com/kamronw23/Portfolio) · See also: [forensic-case-study-mantooth](https://github.com/kamronw23/forensic-case-study-mantooth) · [dfir-cheatsheets](https://github.com/kamronw23/dfir-cheatsheets)
