import cv2
import numpy as np
from deepface import DeepFace


def attendance(student_images):
    """
    student_images: list of tuples (name, image_blob)
    Uses DeepFace (FaceNet) to perform real-time face recognition and mark attendance.
    """
    cap = cv2.VideoCapture(0)

    known_encodings = []
    known_names = []

    # Precompute embeddings for known students
    for name, image_blob in student_images:
        np_arr = np.frombuffer(image_blob, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            continue

        try:
            embedding_obj = DeepFace.represent(img_path=img, model_name="Facenet", enforce_detection=False)
            if embedding_obj and len(embedding_obj) > 0:
                known_encodings.append(np.array(embedding_obj[0]["embedding"]))
                known_names.append(name)
        except Exception as e:
            print(f"Error encoding {name}: {e}")

    if not known_encodings:
        cap.release()
        cv2.destroyAllWindows()
        print("No valid student encodings found.")
        return {}

    attendance_dict = {name: False for name in known_names}

    print("Press SPACE to capture and check attendance, or ESC to exit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        cv2.imshow("Attendance Capture (DeepFace - FaceNet)", frame)
        key = cv2.waitKey(1)

        # Exit with ESC
        if key % 256 == 27:
            break

        # SPACE to capture and check
        elif key % 256 == 32:
            try:
                detected_faces = DeepFace.extract_faces(frame, detector_backend="retinaface", enforce_detection=False)
            except Exception as e:
                print(f"Face detection error: {e}")
                continue

            if not detected_faces:
                print("No faces detected. Try again.")
                continue

            for face in detected_faces:
                face_img = (face["face"] * 255).astype("uint8")
                try:
                    emb_obj = DeepFace.represent(img_path=face_img, model_name="Facenet", enforce_detection=False)
                    if not emb_obj:
                        continue
                    face_embedding = np.array(emb_obj[0]["embedding"])

                    # Compare with known encodings
                    distances = [np.linalg.norm(face_embedding - enc) for enc in known_encodings]
                    best_match_index = int(np.argmin(distances))
                    min_distance = distances[best_match_index]

                    # You can tune the threshold (0.9–1.2 works for FaceNet)
                    if min_distance < 1.0:
                        matched_name = known_names[best_match_index]
                        attendance_dict[matched_name] = True
                        print(f"✅ Marked present: {matched_name}")
                    else:
                        print("❌ Unknown face detected.")

                except Exception as e:
                    print(f"Embedding error: {e}")

            break  # Remove this if you want to scan multiple faces continuously

    cap.release()
    cv2.destroyAllWindows()
    return attendance_dict
