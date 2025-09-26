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

# ====== EAR 계산 유틸 ======
def L2(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

# MediaPipe FaceMesh 인덱스 (좌/우 눈 핵심 포인트)
L_EYE = dict(
    left=33, right=133, top1=159, top2=160, bot1=145, bot2=144
)
R_EYE = dict(
    left=362, right=263, top1=386, top2=387, bot1=374, bot2=373
)

def eye_aspect_ratio(landmarks, w, h, eye):
    def P(i): return (landmarks[i].x*w, landmarks[i].y*h)
    # 수평
    pL, pR = P(eye["left"]), P(eye["right"])
    # 수직 두 쌍 평균
    pT1, pT2 = P(eye["top1"]), P(eye["top2"])
    pB1, pB2 = P(eye["bot1"]), P(eye["bot2"])
    horiz = L2(pL, pR) + 1e-6
    vert  = (L2(pT1, pB1) + L2(pT2, pB2)) / 2.0
    return vert / horiz

mp_face = mp.solutions.face_mesh

# ====== 카메라 ======
cap = cv2.VideoCapture(0)  # Win11 내장카메라면 백엔드 미지정 권장
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

last_sent = ""
last_time = 0
awake_cnt = 0
sleepy_cnt = 0
state = 'S'   # 'A' (awake) / 'S' (sleepy) / 'F' (no face)

with mp_face.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
) as fm:
    while True:
        ok, frame = cap.read()
        if not ok:
            print("cam read fail")
            break
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = fm.process(rgb)

        if res.multi_face_landmarks:
            lm = res.multi_face_landmarks[0].landmark

            ear_l = eye_aspect_ratio(lm, w, h, L_EYE)
            ear_r = eye_aspect_ratio(lm, w, h, R_EYE)
            ear   = (ear_l + ear_r) / 2.0

            # 연속 프레임 기반 상태 전이
            if ear >= EAR_TH:
                awake_cnt += 1
                sleepy_cnt = 0
            else:
                sleepy_cnt += 1
                awake_cnt = 0

            # 상태 갱신
            prev = state
            if awake_cnt >= AWAKE_FRAMES:
                state = 'A'  # 충분히 눈 크게 뜸 (깸)
            elif sleepy_cnt >= SLEEPY_FRAMES:
                state = 'S'  # 덜 깸
            # 얼굴 있음 but 결정 중인 과도구간은 이전 state 유지

            # 디버그 HUD
            cv2.putText(frame, f"EAR={ear:.3f} (TH={EAR_TH:.2f})",
                        (10, 30), 0, 0.7, (0,255,255), 2)
            cv2.putText(frame, f"awake_seq={awake_cnt}  sleepy_seq={sleepy_cnt}",
                        (10, 55), 0, 0.6, (200,255,200), 2)
            cv2.putText(frame, f"STATE: {'AWAKE' if state=='A' else 'SLEEPY'}",
                        (10, 80), 0, 0.8, (0,255,0) if state=='A' else (0,0,255), 2)

            # 랜드마크 간단 표시(원한다면)
            if SHOW_LANDMARKS:
                
                # 왼쪽 눈 영역 대략적 바운딩 박스
                lx = int(min(lm[i].x for i in L_EYE.values()) * w)
                ly = int(min(lm[i].y for i in L_EYE.values()) * h)
                rx = int(max(lm[i].x for i in L_EYE.values()) * w)
                ry = int(max(lm[i].y for i in L_EYE.values()) * h)
                cv2.rectangle(frame, (lx, ly), (rx, ry), (0,255,0), 1)

                # 오른쪽 눈 영역
                lx = int(min(lm[i].x for i in R_EYE.values()) * w)
                ly = int(min(lm[i].y for i in R_EYE.values()) * h)
                rx = int(max(lm[i].x for i in R_EYE.values()) * w)
                ry = int(max(lm[i].y for i in R_EYE.values()) * h)
                cv2.rectangle(frame, (lx, ly), (rx, ry), (0,255,0), 1)

                for idx in [*L_EYE.values(), *R_EYE.values()]:
                    x, y = int(lm[idx].x*w), int(lm[idx].y*h)
                    cv2.circle(frame, (x,y), 2, (0,255,0), -1)

        else:
            # 얼굴을 못 본다면 sleepy보다 더 강하게 실패로 간주
            state = 'F'
            awake_cnt = 0
            sleepy_cnt = 0
            cv2.putText(frame, "No face", (10, 30), 0, 0.8, (0,0,255), 2)

        # 시리얼 송신 (상태 변경 시에만)
        if ser and res and (state != last_sent):
            try:
                ser.write(state.encode('utf-8'))
                last_sent = state
                print("state : ", state)

            except serial.SerialTimeoutException:
                # 재시도 로직: 포트 재오픈
                print("Serial closed...")
                ser.close()
                time.sleep(0.5)
                print("Serial open")
                ser.open()

            except Exception as e:
                print(f"[ERR] Serial write failed: {e}")
                # if ser.is_open == False:
                #     try:
                #         ser = serial.Serial(SERIAL_PORT, BAUD, timeout=0.1)
                #         time.sleep(2)
                #         print(f"[SER] connected to {SERIAL_PORT}")
                #     except Exception as e:
                #         print("[SER] not connected:", e)


# if ser and res and (emotion != last_sent) and (now - last_time > SEND_COOLDOWN):
#             try:
#                 ser.write(emotion.encode("utf-8"))
#                 # ser.write(emotion)
#                 last_sent = emotion
#                 last_time = now
#             except Exception as e:
#                 print(f"[ERR] Serial write failed: {e}")
        

        cv2.imshow("Smart Morning Call (Eye-Open + Button)", frame)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC
            break

cap.release()
cv2.destroyAllWindows()
if ser: ser.close()
