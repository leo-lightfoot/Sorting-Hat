"""
Shared configuration for the archive tool scripts.
Edit this file before running scan_inventory.py (and later phases).
"""

# --- Source folders to scan ---
# Windows paths: use raw strings (r"...") so backslashes aren't treated as escapes.
SOURCE_DIRS = [
    r"C:\Users\abdul\Desktop\DCIM",
]

# --- Storage locations (created automatically) ---
DB_PATH = "inventory.db"
OUTPUT_DIR = "reports"

# --- Files/folders to skip ---
IGNORE_NAMES = {
    "thumbs.db", "desktop.ini", ".ds_store", "$recycle.bin",
    "system volume information",
}
IGNORE_EXTENSIONS = {".tmp", ".temp", ".part", ".crdownload"}

# --- File category mapping by extension ---
CATEGORY_MAP = {
    "Photo": {".jpg", ".jpeg", ".png", ".heic", ".gif", ".bmp", ".tiff", ".webp", ".raw", ".cr2", ".nef", ".dng"},
    "Video": {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".m4v", ".3gp", ".mts"},
    "Document": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".csv", ".odt"},
    "Audio": {".mp3", ".wav", ".flac", ".m4a", ".aac", ".wma"},
}

# --- Hashing ---
# Bytes read for the "quick" partial hash used to cheaply pre-group files.
PARTIAL_HASH_SIZE = 65536  # 64 KB

# --- Video metadata ---
# Requires ffprobe (part of ffmpeg) to be installed and on PATH.
# If not available, video duration/codec/resolution are simply left blank.
ENABLE_VIDEO_METADATA = True

# --- Phase 3: Renaming / classification ---
# Placeholders available: {date} {category} {basename} {ext}
# {date} uses EXIF date-taken for photos when available, else created/modified date.
RENAME_TEMPLATE = "{date}_{category}_{basename}{ext}"
DATE_FORMAT = "%Y-%m-%d"

# If True, files are also moved into a folder structure under each source
# directory: <source>/_Organized/<category>/<year>/<month>/<new_filename>
# If False, files are renamed in place (same folder, new filename only).
ORGANIZE_INTO_FOLDERS = True
ORGANIZED_SUBFOLDER = "_Organized"
MONTH_FOLDER_FORMAT = "%B"  # e.g. "March"; use "%m" for "03", "%m-%B" for "03-March"

# --- Phase 4: Face recognition ---
# Folder containing 5-10 clear, varied photos of the person to find
# (different angles/lighting; ideally one clearly visible face per photo).
REFERENCE_PHOTOS_DIR = "reference_photos"
REFERENCE_EMBEDDINGS_FILE = "reference_embeddings.json"

# Cosine similarity threshold for "this is a match" (range -1 to 1, higher =
# stricter). 0.45-0.5 is a reasonable starting point for insightface's
# buffalo_l model, but THIS NEEDS EMPIRICAL TUNING against your own photos -
# start here, review results, adjust up (fewer false positives) or down
# (fewer missed matches) as needed. Can be overridden per-run with
# --threshold without re-scanning.
FACE_MATCH_THRESHOLD = 0.45

# Face detector input size. Larger = more accurate on small/distant faces
# but slower. 640 is the insightface default.
FACE_DET_SIZE = 640
