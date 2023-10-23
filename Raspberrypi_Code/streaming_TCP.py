import io
import picamera
import requests
from PIL import Image

# AWS 서버 엔드포인트 URL 설정
aws_server_url = 'http://3.34.107.119:5000/video_save'

# 카메라 초기화
camera = picamera.PiCamera()
camera.resolution = (640, 480)

# 스트리밍 루프
try:
    stream = io.BytesIO()
    for _ in camera.capture_continuous(stream, format='jpeg'):
        # 이미지 데이터를 AWS 서버로 전송
        response = requests.post(aws_server_url, data=stream.getvalue())
        if response.status_code == 200:
            print('이미지 전송 성공')

        else:
            print('이미지 전송 실패:', response.status_code, response.text)
        stream.seek(0)
        stream.truncate()
       
finally:
    camera.close()