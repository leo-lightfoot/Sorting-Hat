# Personal Data Archive Project — Plan

## Overview
Build a set of Python scripts to inventory, deduplicate, classify/rename, and
face-search a personal archive of photos/documents/videos (~50–500GB) currently
scattered across multiple drives with duplicate copies.

**Environment:** Windows. No NVIDIA GPU (face recognition will run on CPU —
this affects library choice and expected speed, see Phase 4).

**Core design decision:** Use a local **SQLite database** (`inventory.db`) as
the single source of truth. Excel/CSV files are *exports* generated from the
database for manual review — not the primary storage. This makes re-scans
incremental instead of full re-runs every time.

```
inventory.db
  ├── files table   (path, name, size, hash, created, modified, type, exif, ...)
  ├── faces table   (file_id, embedding, matched_person)
  └── exports → inventory.xlsx, duplicates.xlsx, rename_preview.csv
```

All scripts share one config file (target folders, naming convention, DB path)
so they can be run independently and re-run safely.

---

## Phase 1 — Inventory Scan (`scan_inventory.py`)

**Goal:** Walk all target folders/drives and record metadata for every file
into the database, then export a full inventory spreadsheet.

**Actions:**
- [ ] Define list of source folders/drives to scan (config file)
- [ ] Walk directory tree, skip system/junk files (thumbs.db, .tmp, etc. — configurable ignore list)
- [ ] For every file, record:
  - Full path, filename, extension
  - Size (bytes)
  - Created / modified / accessed timestamps
  - File type category (Photo / Video / Document / Audio / Other)
  - Content hash (for dedup — see hashing strategy below)
  - Type-specific metadata:
    - Photos: EXIF date taken, camera model, GPS (via Pillow / exifread)
    - Videos: duration, codec, resolution (via ffprobe)
    - Documents: author, page count where available
- [ ] **Hashing strategy (performance):** compare file size first (free) →
  hash only first ~64KB → full-hash only if still matching. Avoids hashing
  every byte of 500GB unnecessarily.
- [ ] Write results into SQLite `files` table (upsert, so re-running only
  updates new/changed files — track by path + modified time)
- [ ] Export full inventory to `inventory.xlsx`
- [ ] Log summary: total files, total size, breakdown by type, any unreadable/errored files

**Output:** `inventory.db` populated, `inventory.xlsx` for review.

---

## Phase 2 — Duplicate Detection (`find_duplicates.py`)

**Goal:** Identify exact and near-duplicate files, suggest which copy to keep.

**Actions:**
- [ ] Group files in DB by content hash → exact duplicate groups
- [ ] For each duplicate group, apply "keep" suggestion rules (configurable priority order):
  - Shortest/cleanest file path
  - Oldest creation date
  - Highest resolution (photos) or bitrate (videos)
- [ ] **Near-duplicate detection for photos** (optional but recommended): use
  perceptual hashing (`imagehash` library) to catch resized/re-exported/
  screenshotted versions that exact-hash matching misses
- [ ] Calculate total reclaimable space
- [ ] Export `duplicates.xlsx`:
  - Group ID, file paths in group, suggested keep/delete, space savings
- [ ] **No automatic deletion** — this script only flags. Deletion is a manual
  step (or a separate `delete_confirmed.py` that reads a reviewed/edited copy
  of the export and only deletes rows explicitly marked "delete")

**Output:** `duplicates.xlsx` for manual review, reclaimable space report.

---

## Phase 3 — Classification & Renaming (`rename_classify.py`)

**Goal:** Rename and organize files into a consistent naming convention.

**Naming convention (to finalize before running):**
```
YYYY-MM-DD_Category_OriginalName.ext
Example: 2019-03-14_Photo_IMG_0234.jpg
Example: 2021-11-02_Document_TaxReturn.pdf
```
- Photos: prefer EXIF "date taken" over file-modified date (file-modified date
  is often unreliable after copying between drives)
- Documents/videos: fall back to created/modified date if no embedded date

**Actions:**
- [ ] Finalize naming convention format and category labels
- [ ] Generate a **dry-run CSV**: `old_path → new_path` for every file — no
  files are touched at this stage
- [ ] Manually review the dry-run CSV (spot-check especially edge cases:
  missing dates, duplicate resulting names, special characters)
- [ ] Run "apply" step that only executes renames/moves from the reviewed CSV
- [ ] Optional: auto-organize into folder structure post-rename (e.g.
  `Year/Month` or `Year/Category`)
- [ ] Update DB with new paths after applying

**Output:** `rename_preview.csv` (review before applying), then renamed/organized files.

---

## Phase 4 — Face Recognition — "Find me in these photos" (`find_faces.py`)

**Goal:** Given a reference set of my photos, scan the full photo library and
find all photos containing me (extensible to other people later).

**No NVIDIA GPU — library choice matters:**
- Use **`insightface` + `onnxruntime`** (CPU build), not the classic
  `face_recognition`/`dlib` combo — `dlib` is painful to install on Windows
  (needs CMake/Visual Studio build tools) and gives no real benefit without GPU
- Expect CPU inference to be noticeably slower than GPU — plan for batch
  processing over hours for a large library, not minutes. Runs unattended
  once started; incremental re-scans will only process new files
- If speed becomes a real problem later, consider: downscaling images before
  detection, processing in parallel across CPU cores, or renting brief cloud
  GPU time as a one-off (optional, not required)

**Actions:**
- [ ] Collect 5–10 clear, varied reference photos of myself
- [ ] Build reference face embedding(s) from those photos
- [ ] Scan photo library (from inventory DB), detect faces per image, compute embeddings
- [ ] Compare each detected face against reference embedding(s); flag matches
      above a similarity threshold (tune threshold based on false positive/negative rate)
- [ ] Store all embeddings in DB `faces` table — enables incremental scans
      (only new photos need processing next time) and easy extension to
      other people later (just add more reference sets)
- [ ] Export match list: `my_photos.xlsx` or copy matched files into a
      dedicated folder
- [ ] Manually spot-check a sample of matches/near-misses to tune the threshold

**Output:** List/copy of all photos containing me; reusable face DB for future people/scans.

---

## Suggested Build Order
1. Phase 1 — Inventory scan (foundation for everything else)
2. Phase 2 — Duplicate finder
3. Phase 3 — Rename/classify (dry-run → apply)
4. Phase 4 — Face recognition

Each phase is a standalone script sharing the same config file and database,
so they can be run/re-run independently as the archive grows or changes.

---

## Other Features to Consider (not yet scheduled)
- [ ] Storage breakdown report (treemap/chart of space usage by folder and file type)
- [ ] Broken/corrupt file detector (0-byte files, unreadable images, truncated videos)
- [ ] Junk filter (auto-flag thumbs.db, .tmp, cache files, old screenshots)
- [ ] HTML gallery report — browsable thumbnail grid for duplicates or face matches, no need to open each file
- [ ] Incremental re-scan support across all phases (only process new/changed files since last run)
- [ ] Extend face recognition to tag multiple family members, not just me

---

## Open Decisions to Finalize Before Building
- [ ] Exact naming convention format and category labels (Phase 3)
- [ ] List of source folders/drives to scan (Phase 1)
- [ ] Ignore list for junk files/folders (Phase 1)
- [ ] Duplicate "keep" priority rules — confirm order of preference (Phase 2)
- [ ] Face match similarity threshold — will be tuned empirically (Phase 4)
