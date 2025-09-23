import cv2
import mediapipe as mp
mp_face_detection = mp.solutions.face_detection
my_face_detection = mp.solutions.face_detection.FaceDetection()
mp_drawing = mp.solutions.drawing_utils

# 웹캠, 영상 파일의 경우 이것을 사용하세요.:
cap = cv2.VideoCapture(0)
with mp_face_detection.FaceDetection(
    model_selection=0, min_detection_confidence=0.5) as face_detection:
  
  while cap.isOpened():
    success, image = cap.read()
    if not success:
      print("웹캠을 찾을 수 없습니다.")
      # 비디오 파일의 경우 'continue'를 사용하시고, 웹캠에 경우에는 'break'를 사용하세요.
      break

	# 보기 편하기 위해 이미지를 좌우를 반전하고, BGR 이미지를 RGB로 변환합니다.
    image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
	# 성능을 향상시키려면 이미지를 작성 여부를 False으로 설정하세요.
    image.flags.writeable = False
    results = face_detection.process(image)
    my_face = results.detections
     

    # 영상에 얼굴 감지 주석 그리기 기본값 : True.
    image.flags.writeable = True
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    if results.detections:
      for detection in results.detections:
        mp_drawing.draw_detection(image, detection)
        print(detection.location_data.relative_keypoints)
        


    cv2.imshow('MediaPipe Face Detection', image)

    if cv2.waitKey(5) & 0xFF == 27:     # esc key
      break
cap.release()