import cv2

def register_face(roll_no):
    cap=cv2.VideoCapture(0)
    print("Press SPACE to capture image, ESC to cancel.")
    while True:
        ret, frame=cap.read()
        if(not ret):
            break
        cv2.imshow("Register Face - "+ roll_no, frame)
        key=cv2.waitKey(1)

        if key % 256 == 27:
            print("Registration cancelled.")
            break
        elif key % 256 == 32:
            return frame
    cap.release()
    cv2.destroyAllWindows()