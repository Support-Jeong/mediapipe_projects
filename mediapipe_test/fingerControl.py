import cv2
import mediapipe as mp
import serial
import time
import math

# ====== 사용자 환경 설정 ======
SERIAL_PORT = "COM6"
BAUD = 9600
SHOW_LANDMARKS = True

isFinger1fold = isFinger2fold = isFinger3fold = isFinger4fold = isFinger5fold = False

finger0_x = finger4_x = finger8_x = finger9_x = finger12_x = finger16_x = finger20_x = 0
finger0_y = finger4_y = finger8_y = finger9_y = finger12_y = finger16_y = finger20_y = 0

webcam=cv2.VideoCapture(0)
mp_hands = mp.solutions.hands
# my_hands = mp.solutions.hands.Hands()
drawing_utils = mp.solutions.drawing_utils

arduino = None
try:
    arduino = serial.Serial(SERIAL_PORT, BAUD, timeout=0.1)
    time.sleep(2)
    print(f"[Serial] connected to {SERIAL_PORT}")
except Exception as e:
    print("[Serial] not connected:", e)


with mp_hands.Hands() as my_hands:
    
    while True:   
        ok, image = webcam.read()
        if not ok:
            print("cam read fail")
            break
        image = cv2.flip(image, 1)
        frame_height, frame_width, _ = image.shape
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        output = my_hands.process(rgb_image)
        hands = output.multi_hand_landmarks

        if hands:
            for hand in hands:
                drawing_utils.draw_landmarks(image, hand, mp_hands.HAND_CONNECTIONS)
                landmarks = hand.landmark
                for id, landmark in enumerate(landmarks):
                    x = int(landmark.x * frame_width)
                    y = int(landmark.y * frame_height)
                    if  id == 0:
                        finger0_x = x
                        finger0_y = y
                    if id == 4:
                        finger4_x = x
                        finger4_y = y
                    if id == 8:
                        finger8_x = x
                        finger8_y = y
                    if id == 9:
                        finger9_x = x
                        finger9_y = y
                    if id == 12:
                        finger12_x = x
                        finger12_y = y
                    if id == 16:
                        finger16_x = x
                        finger16_y = y
                    if id == 20:
                        finger20_x = x
                        finger20_y = y
                        
                    dist_1 = int(math.sqrt((finger4_x - finger9_x)**2 + (finger4_y - finger9_y)**2))
                    dist_2 = int(math.sqrt((finger8_x - finger0_x)**2 + (finger8_y - finger0_y)**2))
                    dist_3 = int(math.sqrt((finger12_x - finger0_x)**2 + (finger12_y - finger0_y)**2))
                    dist_4 = int(math.sqrt((finger16_x - finger0_x)**2 + (finger16_y - finger0_y)**2))
                    dist_5 = int(math.sqrt((finger20_x - finger0_x)**2 + (finger20_y - finger0_y)**2))

                    cv2.putText(
                        image, text='fng1=%d fng2=%d fng3=%d fng4=%d fng5=%d' % (dist_1,dist_2,dist_3,dist_4,dist_5), org=(10, 30),
                        fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=0.6,
                        color=(255,0,0), thickness=2)
                    
                    # 변경사항 발생할때만 회전
                    if arduino and output:
                        try:
                            if dist_1<=100 and isFinger1fold==False:
                                arduino.write(b'1')
                                print('arduino write 1')
                                isFinger1fold = True
                            elif dist_1 > 100 and isFinger1fold==True:
                                arduino.write(b'2')
                                print('arduino write 2')
                                isFinger1fold = False

                            if dist_2<=150 and isFinger2fold==False:
                                arduino.write(b'3')
                                print('arduino write 3')
                                isFinger2fold = True
                            elif dist_2 > 150 and isFinger2fold==True:
                                arduino.write(b'4')
                                print('arduino write 4')
                                isFinger2fold = False       

                            if dist_3<=150 and isFinger3fold==False:
                                arduino.write(b'5')
                                print('arduino write 5')
                                isFinger3fold = True
                            elif dist_3 > 150 and isFinger3fold==True:
                                arduino.write(b'6')
                                print('arduino write 6')
                                isFinger3fold = False

                            if dist_4<=150 and isFinger4fold==False:
                                arduino.write(b'7')
                                print('arduino write 7')
                                isFinger4fold = True
                            elif dist_4 > 150 and isFinger4fold==True:
                                arduino.write(b'8')
                                print('arduino write 8')
                                isFinger4fold = False

                            if dist_5<=150 and isFinger5fold==False:
                                arduino.write(b'9')
                                print('arduino write 9')
                                isFinger5fold = True
                            elif dist_5 > 100 and isFinger5fold==True:
                                arduino.write(b'0')
                                print('arduino write 0')
                                isFinger5fold = False

                        except serial.SerialTimeoutException:
                            # 재시도 로직: 포트 재오픈
                            print("Serial closed...")
                            arduino.close()
                            time.sleep(0.5)
                            print("Serial open")
                            arduino.open()

                        except Exception as e:
                            print(f"[ERR] Serial write failed: {e}")
                    

        cv2.imshow("Img", image)
        key = cv2.waitKey(10)

        if key == 27: #esc key
            break

webcam.release()
cv2.destroyAllWindows()
if arduino: arduino.close()
