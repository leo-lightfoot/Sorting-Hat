"""
Phase 3b - Custom Folder Rename

Rename every file directly inside a given folder using a custom pattern,
independent of the Phase 3 date/category naming convention. Useful for a
folder you want to relabel by hand, e.g. a month folder full of trip
photos you'd rather call "Trip_001.jpg", "Trip_002.jpg", ...

Two-step, safe-by-design workflow (same as rename_classify.py):

  1. DRY RUN (default): reads files directly inside FOLDER, computes the
     new name for each under PATTERN, and writes
     reports/rename_folder_preview.csv for you to review. No files are
     touched.

  2. APPLY: reads that (possibly hand-edited) CSV and actually renames
     files on disk. Only rows with apply=YES are executed. inventory.db
     is updated to match, so later phases keep working correctly.

Pattern syntax: a literal prefix/suffix plus {seq} for a zero-padded
sequence number and {ext} for the original extension (with dot), e.g.:
    "Vacation_{seq}{ext}"   ->  Vacation_001.jpg, Vacation_002.jpg, ...
Files are numbered in alphabetical order of their current filename.
{seq} must appear in the pattern - otherwise every file would resolve to
the same name.

Usage:
    python rename_folder.py <folder> "<pattern>"   # dry run -> preview CSV
    python rename_folder.py --apply                # apply the preview CSV
"""
import csv
import shutil
import sqlite3
import sys
from pathlib import Path

import config
from rename_classify import sanitize

PREVIEW_FILE = "rename_folder_preview.csv"


def build_preview(folder: Path, pattern: str):
    if "{seq}" not in pattern:
        print('[ERROR] Pattern must include "{seq}" so each file gets a unique name.')
        sys.exit(1)
    try:
        pattern.format(seq="001", ext=".ext")
    except (KeyError, IndexError) as e:
        print(f"[ERROR] Pattern uses an unsupported placeholder: {e}. "
              f"Only {{seq}} and {{ext}} are supported.")
        sys.exit(1)

    files = sorted((p for p in folder.iterdir() if p.is_file()), key=lambda p: p.name.lower())
    if not files:
        print(f"[ERROR] No files found directly inside {folder}")
        sys.exit(1)

    width = max(3, len(str(len(files))))
    preview = []
    for i, src in enumerate(files, start=1):
        seq = str(i).zfill(width)
        new_name = sanitize(pattern.format(seq=seq, ext=src.suffix.lower()))
        preview.append({
            "old_path": str(src),
            "new_path": str(src.with_name(new_name)),
            "apply": "YES",
        })
    return preview


def dry_run(folder_arg: str, pattern: str):
    folder = Path(folder_arg)
    if not folder.is_dir():
        print(f"[ERROR] Not a folder: {folder}")
        sys.exit(1)

    preview = build_preview(folder, pattern)

    out_dir = Path(config.OUTPUT_DIR)
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / PREVIEW_FILE
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["old_path", "new_path", "apply"])
        writer.writeheader()
        writer.writerows(preview)

    print(f"Files to rename    : {len(preview)}")
    print(f"Preview written to : {out_file}")
    print("\nReview this CSV. Set apply=NO on any row you want to skip, then run:")
    print("    python rename_folder.py --apply")


def apply():
    preview_file = Path(config.OUTPUT_DIR) / PREVIEW_FILE
    if not preview_file.exists():
        print(f"No preview file found at {preview_file}. Run with a folder + pattern first.")
        sys.exit(1)

    with open(preview_file, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    conn = sqlite3.connect(config.DB_PATH)
    cur = conn.cursor()

    applied, skipped, errors, untracked = 0, 0, 0, 0
    for row in rows:
        if row.get("apply", "YES").strip().upper() != "YES":
            skipped += 1
            continue

        old_path = Path(row["old_path"])
        new_path = Path(row["new_path"])

        if not old_path.exists():
            print(f"[SKIP] Source no longer exists: {old_path}")
            errors += 1
            continue
        if new_path.exists() and new_path.resolve() != old_path.resolve():
            print(f"[SKIP] Target already exists: {new_path}")
            errors += 1
            continue

        try:
            shutil.move(str(old_path), str(new_path))
            cur.execute("UPDATE files SET path=?, filename=? WHERE path=?",
                        (str(new_path), new_path.name, str(old_path)))
            if cur.rowcount == 0:
                untracked += 1
            applied += 1
        except OSError as e:
            print(f"[ERROR] {old_path} -> {new_path}: {e}")
            errors += 1

    conn.commit()
    conn.close()

    print(f"\nApplied: {applied}")
    print(f"Skipped (apply=NO): {skipped}")
    print(f"Errors: {errors}")
    if untracked:
        print(f"Note: {untracked} renamed file(s) were not found in inventory.db "
              f"(not previously scanned) - only the file on disk was renamed.")


if __name__ == "__main__":
    if "--apply" in sys.argv:
        apply()
    else:
        args = sys.argv[1:]
        if len(args) != 2:
            print("Usage:")
            print('    python rename_folder.py <folder> "<pattern>"')
            print("    python rename_folder.py --apply")
            sys.exit(1)
        dry_run(args[0], args[1])
