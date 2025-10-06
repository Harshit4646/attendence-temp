# db_supabase.py
import os
import cv2
import numpy as np
from supabase import create_client, Client
from typing import Optional, Dict, List, Any
import bcrypt
import datetime as dt

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]  # server-only!
BUCKET = "student_images"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------- Utilities ----------------
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def check_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def cv2_to_jpg_bytes(image) -> Optional[bytes]:
    success, encoded = cv2.imencode(".jpg", image)
    if not success:
        return None
    return encoded.tobytes()

def download_image_as_cv2(path: str):
    """
    Downloads bytes from supabase storage and returns cv2 image (BGR).
    """
    result = supabase.storage.from_(BUCKET).download(path)
    # supabase Python client returns bytes for download
    if not result:
        return None
    arr = np.frombuffer(result, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return img
