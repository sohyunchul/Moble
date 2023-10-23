import RPi.GPIO as GPIO
from time import sleep
from flask import request, Flask
from PIL import Image
import requests
import picamera
import time
import io

app = Flask(__name__)

# AWS 서버 엔드포인트 URL 설정
aws_server_image_url = 'http://3.34.107.119:5000/image_save'
aws_server_video_url = 'http://3.34.107.119:5000/video_save'
# 카메라 초기화
camera = picamera.PiCamera()

# GPIO 모드 설정 
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
conveyor_pin = 23
GPIO.setup(conveyor_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

#카메라
camera_pin = 24
GPIO.setup(camera_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

#서보모터
SERVO_PIN = 18
GPIO.setup(SERVO_PIN, GPIO.OUT)
p = GPIO.PWM(SERVO_PIN, 50)
p.start(0)

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
        setMotor(CH1, 100, FORWARD)
        setMotor(CH2, 100, FORWARD)
        CONVEYOR_RUNNING = True
    else:
        setMotor(CH1, 0, STOP)
        setMotor(CH2, 0, STOP)
        CONVEYOR_RUNNING = False

def camera_capture(channel):
    global camera
    camera.close()
    camera = picamera.PiCamera()
    camera.capture('image.jpg')  # 이미지를 원하는 경로에 저장

    image_file = "1.jpg"
    # 이미지 파일을 열고 바이너리 데이터로 읽기
    with open(image_file, 'rb') as image_file:
        image_data = image_file.read()

    # 데이터를 AWS 서버로 전송
    response = requests.post(aws_server_image_url, data=image_data)
    if response.status_code == 200:
        if response.json()["message"] == "detect":
            print("detect")
            p.ChangeDutyCycle(8.5) # 90도
            time.sleep(1)
        else:
            print("good")
            p.ChangeDutyCycle(3.5) # 0도
            time.sleep(1)
    else:
        print('데이터 전송 실패:', response.status_code, response.text)
    video_streaming()

# 버튼 핀에 이벤트 핸들러 연결
GPIO.add_event_detect(conveyor_pin, GPIO.RISING, callback=button_pressed, bouncetime=1000)
GPIO.add_event_detect(camera_pin, GPIO.RISING, callback=camera_capture, bouncetime=1000)

def video_streaming():
    global CONVEYOR_RUNNING
    # 스트리밍 루프
    try:
        stream = io.BytesIO()
        for _ in camera.capture_continuous(stream, format='jpeg'):
            # 이미지 데이터를 AWS 서버로 전송
            response = requests.post(aws_server_video_url, data=stream.getvalue())
            if response.status_code == 200:
                print('이미지 전송 성공')
                if response.json()["message"] == "start":
                    setMotor(CH1, 100, FORWARD)
                    setMotor(CH2, 100, FORWARD)
                    CONVEYOR_RUNNING = True
                elif response.json()["message"] == "stop":
                    setMotor(CH1, 0, STOP)
                    setMotor(CH2, 0, STOP)
                    CONVEYOR_RUNNING = False
            else:
                print('이미지 전송 실패:', response.status_code, response.text)
            stream.seek(0)
            stream.truncate()
        
    finally:
        camera.close()
        
video_streaming()

if __name__ == '__main__':
    app.run(host='0.0.0.0')  # 웹 서버 시작