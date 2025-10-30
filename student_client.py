import cv2
import requests
import time
import sys
import numpy as np
import pyvirtualcam # Make sure you did 'pip install pyvirtualcam'

# --- CASCADE AND STATUS VARIABLES ---
try:
    face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
    eye_cascade = cv2.CascadeClassifier('haarcascade_eye.xml')
except cv2.error as e:
    print("!!! ERROR: Could not load cascade files.")
    print("!!! Make sure 'haarcascade_frontalface_default.xml' and 'haarcascade_eye.xml' are in the same folder as this script.")
    sys.exit()

STATUS_ENGAGED = "Engaged"
STATUS_ZONED_OUT = "Zoned Out"
current_status = STATUS_ENGAGED
time_last_seen = time.time()
ZONED_OUT_THRESHOLD = 2.0 # 2 seconds

def get_engagement_status(frame):
    global current_status, time_last_seen
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # 1. Detect faces
    faces = face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50)
    )

    found_face = False
    found_eyes = False

    if len(faces) > 0:
        found_face = True
        (x, y, w, h) = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)[0]
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
        
        roi_gray = gray[y:y+h, x:x+w]
        roi_color = frame[y:y+h, x:x+w]

        # 2. Detect eyes
        eyes = eye_cascade.detectMultiScale(
            roi_gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )
        
        if len(eyes) >= 1:
            found_eyes = True
            for (ex, ey, ew, eh) in eyes:
                cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh), (0, 255, 0), 2)

    # 3. Update Engagement Logic
    if found_face and found_eyes:
        time_last_seen = time.time()
        current_status = STATUS_ENGAGED
    else:
        time_since_last_seen = time.time() - time_last_seen
        if time_since_last_seen > ZONED_OUT_THRESHOLD:
            current_status = STATUS_ZONED_OUT
            
    return current_status
# --- END OF CV SECTION ---


# --- SERVER AND STUDENT ID ---
SERVER_URL = 'http://127.0.0.1:5000/update_status'
try:
    STUDENT_ID = sys.argv[1]
except IndexError:
    print("!!! ERROR: You must provide a student name.")
    print("!!! Run like this: python student_client.py Leona")
    sys.exit()

print(f"Starting client for student: {STUDENT_ID}")

# Start REAL webcam
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("!!! ERROR: Cannot open webcam.")
    sys.exit()

# Get webcam dimensions
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)
if fps == 0:
    fps = 20 # Default fallback

print(f"Webcam opened ({width}x{height} @ {fps}fps). Press 'q' to quit.")

# Timer for server updates
last_update_time = time.time()
UPDATE_INTERVAL = 3.0

# --- NEW VIRTUAL CAMERA SETUP ---
try:
    with pyvirtualcam.Camera(width=width, height=height, fps=fps) as cam:
        print(f"\nSUCCESS: Virtual camera '{cam.device}' created.")
        print("--- PLEASE SELECT THIS CAMERA IN ZOOM/GOOGLE MEET ---")
        
        while True:
            # 1. Read frame from REAL webcam
            ret, frame = cap.read()
            if not ret:
                print("Error: Can't receive frame from camera.")
                break

            # 2. Analyze the frame (this function also draws on the frame)
            status = get_engagement_status(frame)

            # 3. Send status to server (every 3 seconds)
            current_time = time.time()
            if current_time - last_update_time > UPDATE_INTERVAL:
                try:
                    payload = {"student_id": STUDENT_ID, "status": status}
                    requests.post(SERVER_URL, json=payload, timeout=2.0)
                    print(f"[{time.strftime('%H:%M:%S')}] Sent status to dashboard: {status}")
                    last_update_time = current_time
                except requests.exceptions.RequestException:
                    print("Error: Could not connect to server.")

            # 4. Add text to the frame
            display_text = f"Status: {status}"
            color = (0, 255, 0) if status == STATUS_ENGAGED else (0, 0, 255)
            cv2.putText(frame, display_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

            # 5. Show the student their OWN video (optional, good for demo)
            cv2.imshow('Your Monitor (Private)', frame)

            # 6. Send the MODIFIED frame to the VIRTUAL camera
            # Must convert from BGR (OpenCV) to RGB (pyvirtualcam)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            cam.send(frame_rgb)
            cam.sleep_until_next_frame() # Wait for the next frame time

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

except RuntimeError as e:
    print(f"!!! VIRTUAL CAMERA ERROR: {e}")
    print("!!! On Linux/macOS, you may need to install OBS Studio and its virtual camera plugin first.")
    
# Clean up
cap.release()
cv2.destroyAllWindows()
print(f"Client for {STUDENT_ID} stopped.")