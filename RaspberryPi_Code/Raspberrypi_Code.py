import RPi.GPIO as GPIO
from time import sleep
from flask import request, Flask
from hx711 import HX711
from PIL import Image
import requests
import picamera
import datetime
import time
import io

app = Flask(__name__)

# 이미지 중복 촬영 방지
current_time = datetime.datetime.now()
before_time = current_time.hour + current_time.minute + current_time.second

# 보정 값
referenceUnit = 474 
orange_pack = 205

# AWS 서버 엔드포인트 URL 설정
aws_server_image_url = 'http://Public_IP:Port_Number/image_save'
aws_server_video_url = 'http://Public_IP:Port_Number/video_save'
aws_server_object_url = 'http://Public_IP:Port_Number/object_save'
aws_server_data_streaming_url = 'http://Public_IP:Port_Number/data_streaming'

# 로드셀 GPIO 핀번호 (앞: DT, 뒤: SCK)   
hx=HX711(27,17)
hx.set_reading_format("MSB","MSB")
hx.set_reference_unit(referenceUnit)
hx.reset()
hx.tare()

# 카메라 초기화
camera = picamera.PiCamera()

# GPIO 모드 설정 
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

#컨베이어
conveyor_pin = 23
GPIO.setup(conveyor_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

#카메라
camera_pin = 24
GPIO.setup(camera_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# 컨베이어 서보모터
SERVO_PIN = 18
GPIO.setup(SERVO_PIN, GPIO.OUT)
conveyor_p = GPIO.PWM(SERVO_PIN, 50)
conveyor_p.start(0)

# LED
red_led_pin = 5
green_led_pin = 6
GPIO.setup(red_led_pin, GPIO.OUT)
GPIO.setup(green_led_pin, GPIO.OUT)

# 컨베이어 벨트 상태
CONVEYOR_RUNNING = False

# 컨베이어벨트
# 모터 상태
STOP  = 0
FORWARD  = 1
BACKWORD = 2

# 모터 채널
CH1 = 0
CH2 = 1

# PIN 입출력 설정
OUTPUT = 1
INPUT = 0

# PIN 설정
HIGH = 1
LOW = 0

# 실제 핀 정의
#PWM PIN
ENA = 16  #37 pin

#GPIO PIN
IN1 = 20  #37 pin
IN2 = 21  #35 pin

# 로드셀 서보모터
SERVO_PIN = 12
GPIO.setup(SERVO_PIN, GPIO.OUT)
loadcell_p = GPIO.PWM(SERVO_PIN, 50)
loadcell_p.start(0)

GPIO.output(red_led_pin, 0)
GPIO.output(green_led_pin, 0)

stop_video_streaming = False

# 핀 설정 함수
def setPinConfig(EN, INA, INB):        
    GPIO.setup(EN, GPIO.OUT)
    GPIO.setup(INA, GPIO.OUT)
    GPIO.setup(INB, GPIO.OUT)
    # 100khz 로 PWM 동작 시킴 
    pwm = GPIO.PWM(EN, 100) 
    # 우선 PWM 멈춤.   
    pwm.start(0) 
    return pwm

# 모터 제어 함수
def start_con(pwm, INA, INB, speed, stat):
    #모터 속도 제어 PWM
    pwm.ChangeDutyCycle(speed)  
    
    if stat == FORWARD:
        GPIO.output(INA, HIGH)
        GPIO.output(INB, LOW)
        
    #뒤로
    elif stat == BACKWORD:
        GPIO.output(INA, LOW)
        GPIO.output(INB, HIGH)
        
    #정지
    elif stat == STOP:
        GPIO.output(INA, LOW)
        GPIO.output(INB, LOW)

# 모터 제어함수 간단하게 사용하기 위해 한번더 래핑(감쌈)
def setMotor(ch, speed, stat):
    if ch == CH1:
        #pwmA는 핀 설정 후 pwm 핸들을 리턴 받은 값이다.
        start_con(pwmA, IN1, IN2, speed, stat)
     
#모터 핀 설정
#핀 설정후 PWM 핸들 얻어옴 
pwmA = setPinConfig(ENA, IN1, IN2)
    
# 버튼 이벤트 핸들러
def button_pressed(channel):
    global CONVEYOR_RUNNING
    if not CONVEYOR_RUNNING:
        setMotor(CH1, 100, BACKWORD)
        setMotor(CH2, 100, BACKWORD)
        CONVEYOR_RUNNING = True
    else:
        setMotor(CH1, 0, STOP)
        setMotor(CH2, 0, STOP)
        CONVEYOR_RUNNING = False

# video streaming() 메서드와 연관된 코드
# def camera_capture(channel):
#     global camera, CONVEYOR_RUNNING, stop_video_streaming, before_time
    
#     # 중복 촬영 방지
#     formatted_time = datetime.datetime.now()
#     formatted_time = formatted_time.hour + formatted_time.minute + formatted_time.second
#     if (formatted_time - before_time) < 10:
#         before_time = formatted_time
#         return 0
#     before_time = formatted_time
    
#     conveyor_p.ChangeDutyCycle(8.5) # 0도 리셋
#     stop_video_streaming = True  # video_streaming 중단 플래그 설정
#     if camera is not None:
#         camera.close()
#     camera = picamera.PiCamera()
#     camera.capture('image.jpg')  # 이미지를 원하는 경로에 저장

#     image_file = "image.jpg"
#     # 이미지 파일을 열고 바이너리 데이터로 읽기
#     with open(image_file, 'rb') as image_file:
#         image_data = image_file.read()

#     # 데이터를 AWS 서버로 전송
#     try:
#         response = requests.post(aws_server_image_url, data=image_data)
#         if response.status_code == 200:
#             print(response.json()["message"], response.json()["object"])
#             if response.json()["message"] == "detect":
#                 print("detect")
#                 conveyor_p.ChangeDutyCycle(3.5) # 90도
#                 GPIO.output(red_led_pin, 1)
#                 time.sleep(2)
#                 GPIO.output(red_led_pin, 0)
#             elif response.json()["object"] == "orange_juice":
#                 GPIO.output(green_led_pin, 1)
#                 time.sleep(2)
#                 GPIO.output(green_led_pin, 0)
#                 result, round_val = weight_start()
#                 response = requests.post(aws_server_object_url, json={"message" : result, "weight" : round_val})
#                 if response.status_code == 200:
#                     print("Success")
#                 else:
#                     print("Fail")
#             elif response.json()["message"] == "None" and response.json()["object"] == "None":
#                 print("No Object")
#             else:
#                 print("Good")
#                 conveyor_p.ChangeDutyCycle(8.5) # 0도
#                 GPIO.output(green_led_pin, 1)
#                 time.sleep(2)
#                 GPIO.output(green_led_pin, 0)
#         else:
#             print('데이터 전송 실패:', response.status_code, response.text)
#     except Exception as e:
#         print("capture 예외 발생:", e)
#     finally:
#         camera.close()
#         stop_video_streaming = False
#         video_streaming()

# def video_streaming():
#     global CONVEYOR_RUNNING, camera, stop_video_streaming
#     if camera is not None:
#         camera.close()
#         # 카메라 초기화
#     camera = picamera.PiCamera()
#     #스트리밍 루프
#     try:
#         stream = io.BytesIO()
#         for _ in camera.capture_continuous(stream, format='jpeg'):
#             if stop_video_streaming:
#                 break  # stop_video_streaming이 True이면 루프 종료
#             # 이미지 데이터를 AWS 서버로 전송
#             response = requests.post(aws_server_video_url, data=stream.getvalue())
#             if response.status_code == 200:
#                 print('이미지 전송 성공')
#                 if response.json()["message"] == "start":
#                     setMotor(CH1, 100, BACKWORD)
#                     setMotor(CH2, 100, BACKWORD)
#                     CONVEYOR_RUNNING = True
#                 elif response.json()["message"] == "stop":
#                     setMotor(CH1, 0, STOP)
#                     setMotor(CH2, 0, STOP)
#                     CONVEYOR_RUNNING = False
#                 if response.json()["object_weight"] != 0:
#                     orange_pack = response.json()["object_weight"]
#                     print("Change Weight : ", orange_pack)
#             else:
#                 print('이미지 전송 실패:', response.status_code, response.text)
#             stream.seek(0)
#             stream.truncate()
#     except Exception as e:
#         print("video 예외 발생:", e)
#     finally:
#         camera.close()

# data streaming() 메서드와 연관된 코드
def camera_capture(channel):
    global camera, CONVEYOR_RUNNING, before_time
    # 중복 촬영 방지
    formatted_time = datetime.datetime.now()
    formatted_time = formatted_time.hour + formatted_time.minute + formatted_time.second
    if (formatted_time - before_time) < 10:
        before_time = formatted_time
        return 0
    before_time = formatted_time
    
    conveyor_p.ChangeDutyCycle(8.5) # 0도 리셋
    camera.capture('image.jpg')  # 이미지를 원하는 경로에 저장

    image_file = "image.jpg"
    # 이미지 파일을 열고 바이너리 데이터로 읽기
    with open(image_file, 'rb') as image_file:
        image_data = image_file.read()

    # 데이터를 AWS 서버로 전송
    try:
        response = requests.post(aws_server_image_url, data=image_data)
        if response.status_code == 200:
            if response.json()["message"] == "detect":
                conveyor_p.ChangeDutyCycle(3.5) # 90도
                GPIO.output(red_led_pin, 1)
                time.sleep(2)
                GPIO.output(red_led_pin, 0)
            elif response.json()["object"] == "orange_juice":
                GPIO.output(green_led_pin, 1)
                time.sleep(2)
                GPIO.output(green_led_pin, 0)
                result, round_val = weight_start()
                response = requests.post(aws_server_object_url, json={"message" : result, "weight" : round_val})
                if response.status_code == 200:
                    print("무게 데이터 전송 성공")
                else:
                    print("무게 데이터 전송 실패")
            elif response.json()["message"] == "None" and response.json()["object"] == "None":
                print("No Object")
            else:
                conveyor_p.ChangeDutyCycle(8.5) # 0도
                GPIO.output(green_led_pin, 1)
                time.sleep(2)
                GPIO.output(green_led_pin, 0)
        else:
            print('데이터 전송 실패:', response.status_code, response.text)
    except Exception as e:
        print("capture 예외 발생:", e)
        
def data_streaming():
    global CONVEYOR_RUNNING, orange_pack
    #스트리밍 루프
    try:
        while True:
            time.sleep(1)
            response = requests.post(aws_server_data_streaming_url, data="data")
            if response.status_code == 200:
                print('data 전송 성공')
                if response.json()["message"] == "start":
                    setMotor(CH1, 100, BACKWORD)
                    setMotor(CH2, 100, BACKWORD)
                    CONVEYOR_RUNNING = True
                elif response.json()["message"] == "stop":
                    setMotor(CH1, 0, STOP)
                    setMotor(CH2, 0, STOP)
                    CONVEYOR_RUNNING = False
                if response.json()["object_weight"] != 0:
                    orange_pack = response.json()["object_weight"]
                    print("Change Weight : ", orange_pack)
            else:
                print('data 전송 실패:', response.status_code, response.text)
    except Exception as e:
        print("data 예외 발생:", e)

# 로드셀 측정
def weight_start():
    while True:
        val=hx.get_weight(5)
        round_val=round(val, 0)
        round_val = int(round_val)
        if round_val > 10:
            time.sleep(2)
            val=hx.get_weight(5)
            round_val=round(val, 0)
            round_val = int(round_val)
            if round_val > orange_pack - 5 and round_val < orange_pack + 5 and round_val != 0:
                print("Good")
                loadcell_p.ChangeDutyCycle(8.5)
                time.sleep(1)
                # 서버에 데이터 전송해서 DB에 값 저장하는 코드
                return "Good", round_val
            else:
                print("Detect")
                loadcell_p.ChangeDutyCycle(3.5)
                GPIO.output(red_led_pin, 1)
                time.sleep(1)
                GPIO.output(red_led_pin, 0)
                # 서버에 데이터 전송해서 DB에 값 저장하는 코드
                return "Bad", round_val
        hx.power_down()
        hx.power_up()
        time.sleep(0.001)


# 버튼 핀에 이벤트 핸들러 연결
GPIO.add_event_detect(conveyor_pin, GPIO.RISING, callback=button_pressed, bouncetime=1000)
GPIO.add_event_detect(camera_pin, GPIO.RISING, callback=camera_capture, bouncetime=1000)

data_streaming()
#video_streaming()

if __name__ == '__main__':
    app.run(host='0.0.0.0')  # 웹 서버 시작