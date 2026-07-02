"""
Phase 3 - Classification & Renaming

Two-step, safe-by-design workflow:

  1. DRY RUN (default): reads inventory.db, computes what every file's new
     name/location WOULD be under the naming convention in config.py, and
     writes reports/rename_preview.csv for you to review. No files are
     touched.

  2. APPLY: reads that same (possibly hand-edited) CSV and actually renames
     / moves files on disk. Only rows with apply=YES are executed.

Usage:
    python rename_classify.py            # dry run -> reports/rename_preview.csv
    python rename_classify.py --apply    # apply reports/rename_preview.csv
"""
import csv
import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import config

INVALID_CHARS = r'<>:"/\|?*'

_ALL_CATEGORIES = list(config.CATEGORY_MAP.keys()) + ["Other"]
_PREFIX_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}_(?:" + "|".join(re.escape(c) for c in _ALL_CATEGORIES) + r")_"
)


def strip_existing_prefix(stem):
    """
    If a file was already renamed by this script in a previous run, its
    basename will start with a date+category prefix. Strip it before
    reapplying the template, so re-running the script is idempotent
    instead of stacking prefixes on top of each other.
    """
    return _PREFIX_PATTERN.sub("", stem, count=1)


def sanitize(name):
    """Strip characters that are invalid in Windows filenames."""
    cleaned = "".join(c for c in name if c not in INVALID_CHARS)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned or "unnamed"


def parse_best_date(exif_date_taken, created_iso, modified_iso):
    """Priority: EXIF date taken > created time > modified time."""
    if exif_date_taken:
        try:
            return datetime.strptime(exif_date_taken, "%Y:%m:%d %H:%M:%S")
        except (ValueError, TypeError):
            pass
    for iso in (created_iso, modified_iso):
        if iso:
            try:
                return datetime.fromisoformat(iso)
            except (ValueError, TypeError):
                pass
    return None


def build_new_name(row, used_names_in_dir):
    """
    row: sqlite3.Row with path, filename, extension, category,
         exif_date_taken, created, modified
    used_names_in_dir: set of filenames already claimed in the target dir,
         mutated in place to avoid collisions within this run.
    """
    src_path = Path(row["path"])
    ext = row["extension"] or src_path.suffix
    basename = sanitize(strip_existing_prefix(src_path.stem))
    category = row["category"] or "Other"

    dt = parse_best_date(row["exif_date_taken"], row["created"], row["modified"])
    date_str = dt.strftime(config.DATE_FORMAT) if dt else "0000-00-00"

    new_name = config.RENAME_TEMPLATE.format(
        date=date_str, category=category, basename=basename, ext=ext
    )
    new_name = sanitize(new_name)

    if config.ORGANIZE_INTO_FOLDERS:
        year = dt.strftime("%Y") if dt else "Unknown"
        month = dt.strftime(config.MONTH_FOLDER_FORMAT) if dt else "Unknown"
        # Organize relative to whichever configured source dir this file is under
        source_root = next(
            (s for s in config.SOURCE_DIRS if str(src_path).startswith(str(Path(s)))),
            str(src_path.parent),
        )
        target_dir = Path(source_root) / config.ORGANIZED_SUBFOLDER / category / year / month
    else:
        target_dir = src_path.parent

    # Collision handling: append _1, _2... if name already claimed this run
    # or already exists on disk (and isn't the same file).
    stem, dot, extension = new_name.rpartition(".")
    if not dot:
        stem, extension = new_name, ""
    candidate = new_name
    counter = 1
    target_path = target_dir / candidate
    key = str(target_path).lower()
    while key in used_names_in_dir or (target_path.exists() and target_path.resolve() != src_path.resolve()):
        candidate = f"{stem}_{counter}.{extension}" if extension else f"{stem}_{counter}"
        target_path = target_dir / candidate
        key = str(target_path).lower()
        counter += 1

    used_names_in_dir.add(key)
    return target_path


def dry_run():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """SELECT path, filename, extension, category, exif_date_taken, created, modified
           FROM files WHERE error IS NULL ORDER BY path"""
    )
    rows = cur.fetchall()
    conn.close()

    used_names = set()
    preview = []
    unchanged = 0

    for row in rows:
        new_path = build_new_name(row, used_names)
        old_path = Path(row["path"])
        if new_path.resolve() == old_path.resolve():
            unchanged += 1
            continue
        preview.append({
            "old_path": str(old_path),
            "new_path": str(new_path),
            "category": row["category"],
            "apply": "YES",
        })

    out_dir = Path(config.OUTPUT_DIR)
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "rename_preview.csv"

    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["old_path", "new_path", "category", "apply"])
        writer.writeheader()
        writer.writerows(preview)

    print(f"Files needing rename/move : {len(preview)}")
    print(f"Files already correctly named: {unchanged}")
    print(f"Preview written to        : {out_file}")
    print("\nReview this CSV. Set apply=NO on any row you want to skip, then run:")
    print("    python rename_classify.py --apply")


def apply():
    preview_file = Path(config.OUTPUT_DIR) / "rename_preview.csv"
    if not preview_file.exists():
        print(f"No preview file found at {preview_file}. Run without --apply first.")
        sys.exit(1)

    with open(preview_file, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    conn = sqlite3.connect(config.DB_PATH)
    cur = conn.cursor()

    applied, skipped, errors = 0, 0, 0
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
        if new_path.exists():
            print(f"[SKIP] Target already exists (re-run dry run to refresh): {new_path}")
            errors += 1
            continue

        try:
            new_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old_path), str(new_path))
            cur.execute("UPDATE files SET path=?, filename=? WHERE path=?",
                        (str(new_path), new_path.name, str(old_path)))
            applied += 1
        except OSError as e:
            print(f"[ERROR] {old_path} -> {new_path}: {e}")
            errors += 1

    conn.commit()
    conn.close()

    print(f"\nApplied: {applied}")
    print(f"Skipped (apply=NO): {skipped}")
    print(f"Errors: {errors}")


if __name__ == "__main__":
    if "--apply" in sys.argv:
        apply()
    else:
        dry_run()
