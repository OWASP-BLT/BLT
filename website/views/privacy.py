import cv2


def overlay_faces(img, color=(255, 255, 255)):
    """Apply white rectangles over detected faces in an image."""
    if img is None:
        raise ValueError("Invalid image input - image could not be decoded")

    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif len(img.shape) == 3 and img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    if face_cascade.empty():
        return img

    # Detect faces with tuned parameters
    faces = face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30), flags=cv2.CASCADE_SCALE_IMAGE
    )

    if len(faces) == 0:
        return img

    for x, y, w, h in faces:
        cv2.rectangle(img, (x, y), (x + w, y + h), color, thickness=cv2.FILLED)
    return img
