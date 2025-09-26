import cv2, mediapipe as mp, math, time
import serial

# ====== 사용자 환경 설정 ======
SERIAL_PORT = "COM5"
BAUD = 9600
EAR_TH = 0.28          # 눈뜸 임계값(↑=더 크게 떠야 '깸'); 학생별로 보정
AWAKE_FRAMES = 20      # 연속 open 프레임(≈ 0.7~1초) 이상이면 '깸'
SLEEPY_FRAMES = 10     # 연속 closed 프레임이면 '덜깸'으로 전환
SHOW_LANDMARKS = True

# ====== 시리얼 연결 (없어도 영상 디버깅 가능) ======
ser = None
try:
    ser = serial.Serial(SERIAL_PORT, BAUD, timeout=0.1)
    time.sleep(2)
    print(f"[SER] connected to {SERIAL_PORT}")
except Exception as e:
    print("[SER] not connected:", e)

print(ser.is_open)

if ser: ser.close()
