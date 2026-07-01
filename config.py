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
