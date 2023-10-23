from flask import Flask, render_template, request, flash, session, Response, send_file, jsonify
from urllib.parse import urlencode, unquote
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from ultralytics import YOLO
from datetime import datetime
import cv2
import mysql.connector
import numpy as np
from PIL import Image
import math
import cvzone

app = Flask(__name__)  # Initialise ap

frame_data = 0
conveyor_running = ""

def gen():
    while True:
        global frame_data
    
        yield (b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')

# 라즈베리 파이에서 POST 요청을 수신하여 영상 처리 및 스트리밍
@app.route('/video_feed', methods=['GET', 'POST'])
def video_stream():
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

# 라즈베리 파이에서 POST 요청을 수신하여 영상 처리 및 스트리밍
@app.route('/video_save', methods=['POST'])
def video_save():
    global conveyor_running
    # POST 요청에서 이미지 데이터를 읽어옵니다.
    image_data = request.data
    image_array = np.frombuffer(image_data, dtype=np.uint8)
    
    # 이미지 데이터를 OpenCV 형식으로 변환
    frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    
    # OpenCV 이미지를 PIL 이미지로 변환
    image_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    image_pil.save('captured_image.jpg', 'JPEG') 
    
    global frame_data
    with open('captured_image.jpg', 'rb') as file:
        frame_data = file.read()
    response_data = {"message": conveyor_running}
    conveyor_running = ""
    return jsonify(response_data)

@app.route('/start_conveyor', methods=['POST', 'GET'])
def start_conveyor():
    global conveyor_running
    data = request.get_json()
    conveyor_running = data.get('action')
    
@app.route('/stop_conveyor', methods=['POST', 'GET'])
def stop_conveyor():
    global conveyor_running
    data = request.get_json()
    conveyor_running = data.get('action')

@app.route('/image_save', methods=['POST'])
def image_save():
    local_image_dir = '/home/ubuntu/object_defect/static/detect_images'  # 로컬 저장 디렉토리를 원하는 경로로 수정
    db_image_dir = '../static/detect_images'
    db_config = {
            'user':'root',
            'password':'1234567890',
            'host':'object-detection.cezh1qqs7zdc.ap-northeast-2.rds.amazonaws.com',
            'db':'detection',
        }
    connect_db = mysql.connector.connect(**db_config)
    #객체 생성
    cursor = connect_db.cursor()
    sql = "SELECT COUNT(*) FROM OBJECT"
    cursor.execute(sql)
    res = cursor.fetchall()
    res = str(res[0][0]+1)
        
    try:
        current_time = datetime.now()
        image_file = f'{current_time.strftime("%Y-%m-%d_%H-%M-%S")}.jpg'  # 형식에 맞게 파일 이름 생성
        date = current_time.strftime("%Y-%m-%d %H:%M:%S")
        # POST 요청에서 이미지 데이터를 읽어옵니다.
        image_data = request.data
        image_array = np.frombuffer(image_data, dtype=np.uint8)
        
        # 이미지 데이터를 OpenCV 형식으로 변환
        frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        
        # OpenCV 이미지를 PIL 이미지로 변환
        image_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        image_path = f'{local_image_dir}/{image_file}'
        image_pil.save(image_path)
        
        db_image_path = f'{db_image_dir}/{image_file}'
        result = object_detect(image_path)
        sql = "INSERT INTO OBJECT VALUES(%s, 'PCB', 10, 0.1, %s, '반도체')"
        cursor.execute(sql, (res, db_image_path))
        
        # 이미지에서 불량 검출 YOLO
        if result != "":
            sql = "INSERT INTO OBJECT_LOG VALUES(%s, false, %s, %s)"
            cursor.execute(sql, (res, result, date))
            connect_db.commit() 
            connect_db.close() 
            response_data = {"message": "detect"}
            return jsonify(response_data)
        else:
            sql = "INSERT INTO OBJECT_LOG VALUES(%s, true, %s, %s)"
            cursor.execute(sql, (res, result, date))
            connect_db.commit() 
            connect_db.close() 
            response_data = {"message": "None"}
            return jsonify(response_data)
    except Exception as e:
        response_data = {"message": "error", "error_message": str(e)}
        return jsonify(response_data)
    
# PCB 불량 검출
def object_detect(image_path):
    myColor = (0, 0, 255)
    text_area = ""
    model = YOLO("best.pt")
    
    classNames = [
    "missing_hole",
    "mouse_bite",
    "open_circuit",
    "short",
    ]
    src = cv2.imread(image_path)
    results = model(src)
    for r in results:
        boxes = r.boxes
        for box in boxes:
            # Bounding Box
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            # Confidence
            conf = math.ceil((box.conf[0] * 100)) / 100
            # Class Name
            cls = int(box.cls[0])
            currentClass = classNames[cls]
            if conf > 0.5:
                if (
                    currentClass == "missing_hole"
                    or currentClass == "mouse_bite"
                    or currentClass == "open_circuit"
                    or currentClass == "short"
                ):
                    cvzone.putTextRect(
                        src,
                        f"{currentClass} {conf}",
                        (max(0, x1), max(35, y1 - 7)),
                        scale=1,
                        thickness=1,
                        colorB=myColor,
                        colorT=(255, 255, 255),
                        colorR=myColor,
                        offset=5,
                    )
                    cv2.rectangle(src, (x1, y1), (x2, y2), myColor, 3)
                    if text_area == "":
                        text_area = currentClass
                    else:
                        text_area = text_area + ", " + currentClass
    cv2.imwrite(image_path, src)
    return text_area
    
@app.route("/")
def index():
    return render_template("login.html")

# 로그인 페이지
@app.route("/login")
def login():
    return render_template("login.html")

# 회원가입 페이지
@app.route("/join")
def join():
    return render_template("join.html")

# 로그인 액션
@app.route("/login/action", methods=["GET", "POST"])
def login_action():
    if request.method == "POST":
        userID = request.form["userID"]
        userPassword = request.form["userPassword"]
        
        db_config = {
            'user':'root',
            'password':'1234567890',
            'host':'object-detection.cezh1qqs7zdc.ap-northeast-2.rds.amazonaws.com',
            'db':'detection',
        }
        connect_db = mysql.connector.connect(**db_config)
        #객체 생성
        cursor = connect_db.cursor()
        sql = "SELECT userid, userpw, name, authority FROM USER WHERE USERID = %s"
        cursor.execute(sql, (userID,))
        res = cursor.fetchall()
        db_userid, db_userpw, db_authority, db_name = 0, 0, 0, 0
        for userid, userpw, name, authority in res:
            db_userid, db_userpw, db_name, db_authority = userid, userpw, name, authority
        connect_db.commit() 
        connect_db.close() 
        
        if userID is None or userPassword is None or userID == "" or userPassword == "":
            flash("입력 안된 사항이 있습니다.", category="error")
        elif userID != db_userid or userPassword != db_userpw:
            flash("일치하지 않습니다.", category="error")
        elif db_authority == "대기":
            flash("로그인 권한이 없습니다.", category="error")
        elif userID == db_userid and userPassword == db_userpw:
            session['userID'] = db_userid
            session['name'] = db_name
            session['authority'] = db_authority
            return main()
        return render_template("login.html")
    
# 로그아웃
@app.route('/logout')
def logout():
    session.clear()
    return render_template("login.html")
    
# 회원가입 액션
@app.route("/join/action", methods=["GET", "POST"])
def join_action():
    if request.method == "POST":
        userID = request.form["userID"]
        userPassword = request.form["userPassword"]
        userName = request.form["userName"]
        userBirthyy=request.form["userBirthyy"]
        userBirthmm=request.form["userBirthmm"]
        userBirthdd=request.form["userBirthdd"]
        userPhone=request.form["userPhone"]
        userEmail=request.form["userEmail"]
        userBirth=userBirthyy+"-"+userBirthmm+"-"+userBirthdd
                
        db_config = {
            'user':'root',
            'password':'1234567890',
            'host':'object-detection.cezh1qqs7zdc.ap-northeast-2.rds.amazonaws.com',
            'db':'detection',
        }
        connect_db = mysql.connector.connect(**db_config)
        cursor = connect_db.cursor()
        sql = "SELECT count(*) FROM USER WHERE USERID = %s"
        cursor.execute(sql, (userID))
        res = cursor.fetchall()
        cnt = 0
        for value in res:
            cnt = value[0]
        if (userID is None or userPassword is None or userBirthyy is None or userBirthmm is None or userBirthdd is None or userEmail is None or
            userName is None or userPhone is None or userID == "" or userPassword == "" or userBirthyy == "" or userBirthmm == "" or 
            userBirthdd == "" or userEmail == "" or userName == "" or userPhone==""):
            flash("입력 안된 사항이 있습니다.", category="error")
            return render_template("join.html")
        elif cnt > 0:
            flash("이미 존재하는 아이디 입니다.", category="error")
            return render_template("join.html")
        #객체 생성
        cursor = connect_db.cursor()
        sql = "INSERT INTO USER VALUES(%s, %s, %s, %s, %s, %s,'대기')"
        cursor.execute(sql, (userID,userPassword,userName, userPhone, userBirth, userEmail))
        connect_db.commit() 
        connect_db.close()
    return render_template("index.html")

# 관리자 페이지(직원)
@app.route("/admin/employee", methods=["GET", "POST"])
def admin_employee():
    if 'userID' not in session:
        return render_template("login.html")
    elif session['authority'] != '관리자':
        return main()
    
    userid = request.args.get('userid', type=str)
    page = request.args.get('page', type=int, default=1)
    if userid is None or userid == "":
        db_config = {
            'user':'root',
            'password':'1234567890',
            'host':'object-detection.cezh1qqs7zdc.ap-northeast-2.rds.amazonaws.com',
            'db':'detection',
        }
        connect_db = mysql.connector.connect(**db_config)
        cursor = connect_db.cursor()
        sql = "SELECT userid, name, authority FROM USER WHERE authority = '직원'"
        cursor.execute(sql)
        items = cursor.fetchall()
        
        connect_db.commit()
        connect_db.close()
        return render_template(
            "admin.html",
            page = page,
            items = items,
            admin = "직원",
        )
    else:
        db_config = {
            'user':'root',
            'password':'1234567890',
            'host':'object-detection.cezh1qqs7zdc.ap-northeast-2.rds.amazonaws.com',
            'db':'detection',
        }
        connect_db = mysql.connector.connect(**db_config)
        cursor = connect_db.cursor()
        sql = "UPDATE USER SET authority = '대기' WHERE userid = %s"
        cursor.execute(sql, (userid))
        sql = "SELECT userid, name, authority FROM USER WHERE authority = '직원'"
        cursor.execute(sql)
        items = cursor.fetchall()
        
        connect_db.commit() 
        connect_db.close()
        return render_template(
            "admin.html",
            page = page,
            items = items,
            admin = "직원",
        )
 
# 관리자 페이지(대기)     
@app.route("/admin/wait", methods=["GET", "POST"])
def admin_wait():
    if 'userID' not in session:
        return render_template("login.html")
    elif session['authority'] != '관리자':
        return main()
    
    userid = request.args.get('userid', type=str)
    page = request.args.get('page', type=int, default=1)
    if userid is None or userid == "":
        db_config = {
            'user':'root',
            'password':'1234567890',
            'host':'object-detection.cezh1qqs7zdc.ap-northeast-2.rds.amazonaws.com',
            'db':'detection',
        }
        connect_db = mysql.connector.connect(**db_config)
        cursor = connect_db.cursor()
        sql = "SELECT userid, name, authority FROM USER WHERE authority = '대기'"
        cursor.execute(sql)
        items = cursor.fetchall()
        
        connect_db.commit() 
        connect_db.close()
        return render_template(
            "admin.html",
            page = page,
            items = items,
            admin = "대기",
        )
    else:
        db_config = {
            'user':'root',
            'password':'1234567890',
            'host':'object-detection.cezh1qqs7zdc.ap-northeast-2.rds.amazonaws.com',
            'db':'detection',
        }
        connect_db = mysql.connector.connect(**db_config)
        cursor = connect_db.cursor()
        sql = "UPDATE USER SET authority = '직원' WHERE userid = %s"
        cursor.execute(sql, (userid))
        sql = "SELECT userid, name, authority FROM USER WHERE authority = '대기'"
        cursor.execute(sql)
        items = cursor.fetchall()
        
        connect_db.commit()
        connect_db.close()
        return render_template(
            "admin.html",
            page = page,
            items = items,
            admin = "대기",
        )
        
# 메인 페이지
@app.route("/main", methods=["GET", "POST"])
def main():
    if 'userID' not in session:
        return render_template("login.html")
    db_config = {
            'user':'root',
            'password':'1234567890',
            'host':'object-detection.cezh1qqs7zdc.ap-northeast-2.rds.amazonaws.com',
            'db':'detection',
        }
    connect_db = mysql.connector.connect(**db_config)
    cursor = connect_db.cursor()
    sql = "SELECT A.ob_num, ob_name, ob_weight, ob_type, ob_state, ob_poor, ob_date, ob_image FROM OBJECT A INNER JOIN OBJECT_LOG B ON A.ob_num = B.ob_num"
    cursor.execute(sql)
    items = cursor.fetchall()
    
    sql = "SELECT DATE_FORMAT(ob_date, '%Y-%m-%d') AS ob_date, COUNT(*) AS count FROM OBJECT_LOG WHERE OB_STATE = FALSE GROUP BY DATE_FORMAT(ob_date, '%Y-%m-%d') ORDER BY ob_date DESC LIMIT 7"
    cursor.execute(sql)
    chart_items = cursor.fetchall()
    connect_db.commit()
    connect_db.close()
    return render_template(
        "index.html",
        items = items,
        chart_items = chart_items,
    )
    

if __name__=="__main__":
    app.secret_key = 'super secret key'
    app.config['SESSION_TYPE'] = 'filesystem'
    app.run(host="0.0.0.0", port="5000", debug=True)