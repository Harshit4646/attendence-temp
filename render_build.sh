#!/usr/bin/env bash
set -e
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Ensure static folders exist..."
mkdir -p static/qrcodes

echo "Pre-downloading DeepFace model (Facenet) to reduce first-run time..."
python - <<'PY'
try:
    from deepface import DeepFace
    print("Building Facenet model (may take time)...")
    DeepFace.build_model("Facenet")
    print("Facenet model ready.")
except Exception as e:
    print("Could not pre-download model (non-fatal):", e)
PY

echo "Build script finished."
