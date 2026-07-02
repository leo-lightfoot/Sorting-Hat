"""
Run this FIRST, before find_faces.py, to confirm insightface/onnxruntime
are installed correctly and can actually detect a face - on a single image,
with clear output at every step. This is your safety check, since this
part of the toolkit couldn't be tested in the environment that built it.

Usage:
    python test_face_setup.py                          (uses first image in reference_photos/)
    python test_face_setup.py path/to/some_photo.jpg    (test a specific image)
"""
import sys
from pathlib import Path

import config


def main():
    print("Step 1/4: Checking required packages are installed...")
    try:
        import cv2
        import numpy as np
        from insightface.app import FaceAnalysis
        print("  [OK] opencv-python, numpy, insightface all import correctly.\n")
    except ImportError as e:
        print(f"  [FAIL] Missing package: {e}")
        print("  Run: pip install insightface onnxruntime opencv-python numpy")
        sys.exit(1)

    print("Step 2/4: Finding a test image...")
    if len(sys.argv) > 1:
        test_image = Path(sys.argv[1])
    else:
        ref_dir = Path(config.REFERENCE_PHOTOS_DIR)
        candidates = [p for p in ref_dir.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}] if ref_dir.exists() else []
        if not candidates:
            print(f"  [FAIL] No test image given and no images found in {ref_dir}/.")
            print(f"  Either put a photo in {ref_dir}/ or run: python test_face_setup.py path\\to\\photo.jpg")
            sys.exit(1)
        test_image = candidates[0]
    print(f"  Using: {test_image}\n")

    print("Step 3/4: Loading face model (this downloads ~300MB on first run - "
          "requires internet access, may take a few minutes)...")
    try:
        app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        app.prepare(ctx_id=0, det_size=(config.FACE_DET_SIZE, config.FACE_DET_SIZE))
        print("  [OK] Model loaded.\n")
    except Exception as e:
        print(f"  [FAIL] Could not load model: {e}")
        print("  Check your internet connection - the model downloads on first run.")
        sys.exit(1)

    print("Step 4/4: Detecting faces in the test image...")
    try:
        data = np.fromfile(str(test_image), dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if img is None:
            print(f"  [FAIL] Could not read image file: {test_image}")
            sys.exit(1)

        faces = app.get(img)
        print(f"  [OK] Detection ran without errors. Found {len(faces)} face(s).\n")

        if len(faces) == 0:
            print("No faces detected in this image. Try a clearer, more front-facing photo.")
        else:
            for i, face in enumerate(faces):
                emb_len = len(face.embedding) if hasattr(face, "embedding") else "?"
                print(f"  Face {i}: bbox={[round(float(x),1) for x in face.bbox]}, "
                      f"embedding length={emb_len}")
            print("\nSUCCESS - face detection is working. You can now run:")
            print("    python find_faces.py --build-reference")
    except Exception as e:
        print(f"  [FAIL] Detection failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
