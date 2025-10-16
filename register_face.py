import cv2
import numpy as np
import base64

def register_face_from_base64(base64_image):
    """
    Decode base64 image string to OpenCV image.
    """
    try:
        # Remove prefix (data:image/jpeg;base64,...) if present
        if ',' in base64_image:
            base64_image = base64_image.split(',')[1]
        img_bytes = base64.b64decode(base64_image)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        print("Error decoding image:", e)
        return None
