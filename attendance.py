import cv2
import face_recognition
import numpy as np


def attendance(student_images):
    cap = cv2.VideoCapture(0)
    known_encodings = []
    known_names = []

    for name, image_blob in student_images:
        np_arr = np.frombuffer(image_blob, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            continue

        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encodings = face_recognition.face_encodings(rgb_img)
        if encodings:
            known_encodings.append(encodings[0])
            known_names.append(name)

    if not known_encodings:
        cap.release()
        cv2.destroyAllWindows()
        return {}

    attendance_dict = {name: False for name in known_names}

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        cv2.imshow("Attendance Capture", frame)
        key = cv2.waitKey(1)

        if key % 256 == 27:
            break

        elif key % 256 == 32:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

            if not face_encodings:
                continue

            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(known_encodings, face_encoding)
                face_distances = face_recognition.face_distance(known_encodings, face_encoding)

                best_match_index = None
                if matches:
                    match_indices = [i for i, val in enumerate(matches) if val]
                    if match_indices:
                        best_match_index = min(match_indices, key=lambda i: face_distances[i])

                if best_match_index is not None:
                    name = known_names[best_match_index]
                    attendance_dict[name] = True

            break

    cap.release()
    cv2.destroyAllWindows()
    return attendance_dict