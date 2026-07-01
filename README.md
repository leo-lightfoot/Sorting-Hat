# Archive Tool — Phase 1: Inventory Scan

## Setup (Windows)

1. Install Python 3.10+ from python.org if you don't have it (check "Add to PATH" during install).
2. Open Command Prompt / PowerShell in this folder.
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. (Optional, for video metadata) Install ffmpeg and make sure `ffprobe` is
   on your PATH. If you skip this, video files still get scanned — you'll
   just get blank duration/codec/resolution columns. Download from
   https://ffmpeg.org/download.html.

## Configure

Open `config.py` and check `SOURCE_DIRS` — it's currently set to:
```python
SOURCE_DIRS = [
    r"C:\Users\abdul\Desktop\DCIM",
]
```
Add more paths later as a comma-separated list once this run looks good.

## Run

```
python scan_inventory.py
```

This will:
- Create `inventory.db` (SQLite database — the source of truth)
- Create `reports/inventory.xlsx` (spreadsheet for you to review)

Re-running the script later only processes new/changed files — already-scanned,
unchanged files are skipped automatically, so it's safe (and fast) to re-run
after adding more files to the same folders.

## Phase 2: Find duplicates

Once `inventory.db` exists (i.e. you've run `scan_inventory.py` at least once),
run:
```
python find_duplicates.py
```
This creates `reports/duplicates.xlsx` — every duplicate group is listed with
a suggested KEEP (green) or DELETE (amber) action, plus total reclaimable
space. **Nothing is deleted automatically** — this only flags candidates for
you to review. Deletion will be a separate, explicit step once you're
comfortable with the results.

Keep-suggestion logic: shortest file path, then oldest creation date.
This script only handles **exact** (byte-for-byte identical) duplicates for
now — near-duplicates (resized/re-exported copies) are a possible future
addition.

## What gets recorded per file

- Path, filename, extension, category (Photo/Video/Document/Audio/Other)
- Size, created/modified/accessed timestamps
- Content hash (used later for duplicate detection — only computed for files
  that appear to match another file, to save time)
- Photos: EXIF date taken, camera model, whether GPS data is present
- Videos: duration, codec, resolution (requires ffprobe, see above)

## Notes

- Junk files (Thumbs.db, desktop.ini, .tmp files, etc.) are skipped automatically.
  Edit `IGNORE_NAMES` / `IGNORE_EXTENSIONS` in `config.py` to adjust.
- If a file can't be read (permissions, locked file, etc.), it's logged in the
  `error` column instead of crashing the whole scan.
- This is tested logic (duplicate detection, incremental re-scan, ignore
  rules) — but it hasn't run against your actual DCIM folder yet. Run it and
  let me know what the output looks like, especially row count and whether
  the reported file categories/dates look right, before we move to Phase 2
  (duplicate finder).
