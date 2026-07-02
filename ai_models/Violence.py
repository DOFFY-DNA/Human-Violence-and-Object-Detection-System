import cv2
from ultralytics import YOLO

# Load YOLO model (.pt)
model = YOLO("best2.pt")
print(model.names)

# DroidCam usually uses index 1
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Cannot open DroidCam")
    exit()

print("✅ Phone camera connected")

while True:
    ret, frame = cap.read()
    if not ret:
        continue

    # YOLO detection
    results = model(frame, conf=0.4, imgsz=640)
    annotated = results[0].plot()

    cv2.imshow("YOLO Phone Camera", annotated)

    # ESC to exit
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()