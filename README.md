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

## Phase 3: Rename & classify

Two-step process — nothing is renamed until you explicitly apply it.

**Step 1 — dry run:**
```
python rename_classify.py
```
Writes `reports/rename_preview.csv` showing every `old_path -> new_path`
change under the current naming convention. **No files are touched.**

**Step 2 — review the CSV.** Open it in Excel. Check the new names look
right. If you want to skip a specific file, change its `apply` column from
`YES` to `NO`.

**Step 3 — apply:**
```
python rename_classify.py --apply
```
Only rows still marked `YES` are renamed/moved. The database is updated to
match the new paths automatically, so later phases (duplicate finder, face
search) keep working correctly.

**Folder organization: ON by default now.** `ORGANIZE_INTO_FOLDERS = True` in
`config.py`, so applying the rename also sorts files by category into:
```
<source>/_Organized/Photo/<year>/<month>/2024-03-14_Photo_IMG_0234.jpg
<source>/_Organized/Video/<year>/<month>/...
<source>/_Organized/Document/<year>/<month>/...
<source>/_Organized/Audio/<year>/<month>/...
```
Category is the top-level folder, year and then month are sub-folders
underneath it. Month folder name format is set by `MONTH_FOLDER_FORMAT` in
`config.py` (default `"%B"`, e.g. `March`).

**Safe to re-run:** if you run the dry run again on already-renamed files,
it correctly reports "already correctly named" instead of stacking a second
prefix onto the filename — this was tested specifically before shipping.

**Collision handling:** if two files would end up with the same new name in
the same folder, the second one gets `_1`, `_2`, etc. appended automatically
— tested, no file is ever silently overwritten.

**Leftover empty folders:** after applying, the original folders your files
used to live in (e.g. `Camera`, `Screenshots`) will still exist but be empty,
since files are moved out of them into `_Organized/`. These aren't cleaned
up automatically — delete them manually once you've confirmed everything
moved correctly.

## Phase 3b: Custom folder rename (`rename_folder.py`)

For relabeling the contents of one specific folder (e.g. a month folder full
of trip photos) with your own naming pattern instead of the Phase 3
date/category convention. Same dry-run → review → apply workflow.

**Step 1 — dry run:**
```
python rename_folder.py "C:\path\to\folder" "Trip_{seq}{ext}"
```
Writes `reports/rename_folder_preview.csv`. **No files are touched.**
`{seq}` is a sequence number (zero-padded, e.g. `001`, `002`, ...), assigned
in alphabetical order of the current filenames — it's required in the
pattern so every file gets a unique name. `{ext}` is the original file
extension (with dot, lowercased). No other placeholders are supported.

**Step 2 — review the CSV**, same as Phase 3: open it, check the names,
flip `apply` to `NO` on any row you want to skip.

**Step 3 — apply:**
```
python rename_folder.py --apply
```
Only files directly inside the given folder are touched (not subfolders).
`inventory.db` is updated for any renamed file that was already tracked
there; files not previously scanned are still renamed on disk, with a note
printed at the end.

## Phase 4: Face recognition ("find me in these photos")

**Important:** this phase depends on `insightface`, which downloads a
~300MB model from the internet the first time it runs. Unlike Phases 1-3,
this code could not be fully tested end-to-end before being handed to you
(no internet access in the environment that built it) — the surrounding
logic (database, incremental scanning, threshold tuning) was verified with
a stand-in for the face model, but the actual face detection/matching
accuracy has not been. **Run the verification step below first.**

### Setup
```
pip install -r requirements.txt
```
(This now includes `insightface`, `onnxruntime`, `opencv-python`, `numpy`.)
No GPU needed — runs on CPU, but expect roughly 1-3 seconds per photo, so a
large library will take minutes to hours, not seconds. Safe to stop and
resume; already-processed photos are skipped on the next run.

### Step 1 — verify it actually works, on one image
```
python test_face_setup.py
```
This checks the packages installed correctly, downloads the model if needed,
and runs real face detection on a single test image, printing exactly what
it found. **Don't skip this** — it's your chance to catch a broken install
or bad model download before running it against your whole library. If it
fails, the error message will tell you what to fix.

### Step 2 — build your reference
Create a folder called `reference_photos` next to these scripts, and add
5-10 clear photos of yourself in it — different angles/lighting, ideally
one person per photo. Then:
```
python find_faces.py --build-reference
```

### Step 3 — scan your photo library
```
python find_faces.py
```
Scans every photo in `inventory.db` not yet processed, compares detected
faces against your reference, and exports `reports/my_photos.xlsx` — every
photo matching above the similarity threshold, sorted by confidence.

**Note:** this only produces a report (file path + confidence score) — it
does not copy, move, or tag the actual photo files. Use the path column in
the spreadsheet to navigate to a match.

### Step 4 — tune the threshold
`FACE_MATCH_THRESHOLD` in `config.py` (default 0.45) controls how strict a
match needs to be. **This will need adjusting based on your actual results**
— there's no universal correct value. Look at `reports/my_photos.xlsx`:
too many photos that aren't you → raise it; missing obvious photos of
yourself → lower it. Re-check instantly without re-scanning:
```
python find_faces.py --rescan-similarity --threshold 0.5
```

### Notes
- HEIC photos (common from iPhones) aren't currently supported by this
  pipeline — they'll be skipped. Let me know if this matters for your
  library and we can add `pillow-heif` conversion support.
- Extending to recognize other people later just means adding another
  reference folder + running `--build-reference` against it.

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
