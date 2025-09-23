import cv2
import mediapipe as mp
import serial
import time
import math

# === 설정값 ===
SERIAL_PORT = "COM6"
BAUD = 9600
SEND_COOLDOWN = 0.25    #  디바운싱
SMILE_TH = 0.57       # 기본 임계값(학생들이 본인 얼굴 기준으로 조정)
OPEN_TH  = 0.30

# === 유틸 ===
def dist(a, b):
    return math.dist(a, b)

mp_drawing = mp.solutions.drawing_utils
mp_face_mesh = mp.solutions.face_mesh

# 아두이노 연결 시도
ser = None
try:
    ser = serial.Serial(SERIAL_PORT, BAUD, timeout=0.1)
    time.sleep(2)  # 아두이노 리셋 대기
    print(f"[INFO] Serial connected on {SERIAL_PORT}")
except Exception as e:
    print(f"[WARN] Serial not connected: {e}\n")

# cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap = cv2.VideoCapture(0)
last_sent = ""
last_time = 0

with mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
) as face_mesh:

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame = cv2.flip(frame, 1)  # 거울 모드
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = face_mesh.process(rgb)

        emotion = "N"  # 기본값: Neutral
        text = "Neutral"

        if res.multi_face_landmarks:
            lm = res.multi_face_landmarks[0].landmark

            # 주요 포인트 (MediaPipe FaceMesh 인덱스)
            # 입 좌우: 61, 291 / 입 위아래: 13, 14 / 얼굴 가로 참조: 33, 263
            p61 = (lm[61].x * w, lm[61].y * h)
            p291 = (lm[291].x * w, lm[291].y * h)
            p13 = (lm[13].x * w, lm[13].y * h)
            p14 = (lm[14].x * w, lm[14].y * h)
            p33 = (lm[33].x * w, lm[33].y * h)
            p263 = (lm[263].x * w, lm[263].y * h)

            mouth_w = dist(p61, p291) + 1e-6
            mouth_h = dist(p13, p14)
            face_w  = dist(p33, p263) + 1e-6

            smile_ratio = mouth_w / face_w
            open_ratio  = mouth_h / mouth_w

            # 입 너비 기준으로 감정 분석
            # 임계값을 바꿔보도록 안내
            if open_ratio > OPEN_TH:
                emotion, text = "U", "Surprised"
            elif smile_ratio > SMILE_TH:
                emotion, text = "H", "Happy"
            else:
                emotion, text = "N", "Neutral"

            # 디버그 표시
            cv2.putText(frame, f"smile_ratio={smile_ratio:.2f}  open_ratio={open_ratio:.2f}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 2)
            cv2.putText(frame, f"Emotion: {text}",
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
            cv2.circle(frame, (int(p61[0]), int(p61[1])), 2, (0,255,0), -1)
            cv2.circle(frame, (int(p291[0]), int(p291[1])), 2, (0,255,0), -1)
            cv2.circle(frame, (int(p13[0]), int(p13[1])), 2, (255,0,0), -1)
            cv2.circle(frame, (int(p14[0]), int(p14[1])), 2, (255,0,0), -1)
            cv2.line(frame, (int(p61[0]), int(p61[1])), (int(p291[0]), int(p291[1])), (0,255,0), 1)
            cv2.line(frame, (int(p13[0]), int(p13[1])), (int(p14[0]), int(p14[1])), (255,0,0), 1)

        # 시리얼 송신(상태 변할 때만 송신 ==> 과도 송신 방지)
        now = time.time()
        if ser and res and (emotion != last_sent) and (now - last_time > SEND_COOLDOWN):
            try:
                ser.write(emotion.encode("utf-8"))
                # ser.write(emotion)
                last_sent = emotion
                last_time = now
            except Exception as e:
                print(f"[ERR] Serial write failed: {e}")

        cv2.imshow("MediaPipe Emotion Arduino", frame)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC 종료
            break

cap.release()
cv2.destroyAllWindows()
if ser:
    ser.close()