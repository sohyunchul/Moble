from flask import Flask, render_template, request, flash, session, Response, jsonify
from urllib.parse import unquote
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import DB_Connect
import Object_Yolo
import numpy as np
from PIL import Image
import cv2

app = Flask(__name__)  # Initialise ap

# 전역변수
frame_data = 0
object_weight = 0
conveyor_running = ""
objects = ""
db_image_path = ""
res = ""
result = ""
date = ""

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
    global conveyor_running, object_weight
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
    response_data = {"message": conveyor_running, "object_weight": object_weight}
    # 컨베이어, 무게 설정 값 초기화
    object_weight = 0
    conveyor_running = ""
    return jsonify(response_data)

# video streaming을 사용하지 않고 데이터 통신할 때 활용하는 코드
@app.route('/data_streaming', methods=['POST'])
def data_streaming():
    global conveyor_running, object_weight
    # POST 데이터 가져오기
    data = request.data
    
    response_data = {"message": conveyor_running, "object_weight": object_weight}
    # 컨베이어, 무게 설정 값 초기화
    object_weight = 0
    conveyor_running = ""
    return jsonify(response_data)
    

@app.route('/start_conveyor', methods=['POST', 'GET'])
def start_conveyor():
    global conveyor_running
    data = request.get_json()
    conveyor_running = data.get('action')
    return "start"
    
@app.route('/stop_conveyor', methods=['POST', 'GET'])
def stop_conveyor():
    global conveyor_running
    data = request.get_json()
    conveyor_running = data.get('action')
    return "stop"

@app.route('/change_weight', methods=['POST'])
def change_weight():
    global object_weight
    data = request.get_json()
    object_weight = data.get('weight')
    return "change"
    

@app.route('/image_save', methods=['POST'])
def image_save():
    global res, objects, db_image_path, result, date
    local_image_dir = '/home/ubuntu/final_project/static/detect_images'  # 로컬 저장 디렉토리를 원하는 경로로 수정
    db_image_dir = '../static/detect_images'
    
    connect_db, cursor = DB_Connect.db_connect()
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
        result, objects = Object_Yolo.object_detect(image_path)
        # 이미지에서 불량 검출 YOLO
        # YOLO에서 PCB 불량이 검출 됐을 때
        if result != "" and objects == "PCB":
            DB_Connect.object_insert(cursor, connect_db, res, objects, 0, db_image_path, "반도체", result, False, date)
            response_data = {"message": "detect", "object": objects}
            return jsonify(response_data)
        # YOLO에서 오렌지팩 불량이 검출 됐을 때
        elif result != "" and objects == "orange_juice":
            DB_Connect.object_insert(cursor, connect_db, res, objects, 0, db_image_path, "쥬스", result, False, date)
            response_data = {"message": "detect", "object": objects}
            return jsonify(response_data)
        # YOLO 검출x PCB
        elif result == "" and objects == "PCB":
            DB_Connect.object_insert(cursor, connect_db, res, objects, 0, db_image_path, "반도체", result, True, date)
            response_data = {"message": "None", "object": objects}
            return jsonify(response_data)
        # YOLO 검출 x 오렌지 팩
        elif result == "" and objects == "orange_juice":
            response_data = {"message": "None", "object": objects}
            return jsonify(response_data)
        else:
            response_data = {"message": "None", "object": "None"}
            return jsonify(response_data)
    except Exception as e:
        response_data = {"message": "error", "object": "None","error_message": str(e)}
        return jsonify(response_data)

# object_server
@app.route('/object_save', methods=['POST'])
def object_save():
    global res, objects, db_image_path, result, date
    connect_db, cursor = DB_Connect.db_connect()
    message, weight = str(request.json["message"]), request.json["weight"]
    if message == "Good":
        DB_Connect.object_insert(cursor, connect_db, res, objects, weight, db_image_path, "쥬스", result, True, date)
    else:
        DB_Connect.object_insert(cursor, connect_db, res, objects, weight, db_image_path, "쥬스", "Bad_weight", False, date)
    return "good"

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
        
        connect_db, cursor = DB_Connect.db_connect()
        sql = "SELECT USERID, USERPW, NAME, AUTHORITY FROM USER WHERE USERID = %s"
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
                
        connect_db, cursor = DB_Connect.db_connect()
        sql = "SELECT COUNT(*) FROM USER WHERE USERID = %s"
        cursor.execute(sql, (userID,))
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
        cursor.execute(sql, (userID,userPassword,userName, userPhone, userBirth, userEmail,))
        connect_db.commit() 
        connect_db.close()
    return render_template("login.html")

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
        connect_db, cursor = DB_Connect.db_connect()
        sql = "SELECT USERID, NAME, AUTHORITY FROM USER WHERE AUTHORITY = '직원'"
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
        connect_db, cursor = DB_Connect.db_connect()
        sql = "UPDATE USER SET AUTHORITY = '대기' WHERE USERID = %s"
        cursor.execute(sql, (userid,))
        sql = "SELECT USERID, NAME, AUTHORITY FROM USER WHERE AUTHORITY = '직원'"
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
        connect_db, cursor = DB_Connect.db_connect()
        sql = "SELECT USERID, NAME, AUTHORITY FROM USER WHERE AUTHORITY = '대기'"
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
        print(userid)
        connect_db, cursor = DB_Connect.db_connect()
        sql = "UPDATE USER SET AUTHORITY = '직원' WHERE USERID = %s"
        cursor.execute(sql, (userid,))
        sql = "SELECT USERID, NAME, AUTHORITY FROM USER WHERE AUTHORITY = '대기'"
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
    connect_db, cursor = DB_Connect.db_connect()
    sql = "SELECT A.OB_NUM, OB_NAME, OB_WEIGHT, OB_TYPE, OB_STATE, OB_POOR, OB_DATE, OB_IMAGE FROM OBJECT A INNER JOIN OBJECT_LOG B ON A.OB_NUM = B.OB_NUM ORDER BY A.OB_NUM DESC"
    cursor.execute(sql)
    items = cursor.fetchall()
    
    sql = "SELECT DATE_FORMAT(OB_DATE, '%Y-%m-%d') AS OB_DATE, COUNT(*) AS COUNT FROM OBJECT_LOG WHERE OB_STATE = FALSE GROUP BY DATE_FORMAT(OB_DATE, '%Y-%m-%d') ORDER BY OB_DATE DESC LIMIT 7"
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
