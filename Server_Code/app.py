from flask import Flask, render_template, request, flash, session, Response, send_file
import requests 
from urllib.parse import urlencode, unquote
import json
from dotenv import load_dotenv
import os
import pymysql
import cv2
import threading

app = Flask(__name__)  # Initialise app

def generate_frames():
    while True:
        frame = cv2.imread('image.jpg')  # 이미지를 읽어옵니다.
        ret, buffer = cv2.imencode('.jpg', frame)
        if ret:
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/image')
def image():
    return send_file('image.jpg', mimetype='image/jpeg')

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
        
        connect_db = pymysql.connect(  
            user="root",
            password="1234",
            host="127.0.0.1",
            db="detection",
            charset="utf8",
        )
        #객체 생성
        cursor = connect_db.cursor()
        sql = "SELECT userid, userpw, name, authority FROM user WHERE USERID = %s"
        cursor.execute(sql, (userID))
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
                
        connect_db = pymysql.connect(  
            user="root",
            password="1234",
            host="127.0.0.1",
            db="detection",
            charset="utf8",
        )
        cursor = connect_db.cursor()
        sql = "SELECT count(*) FROM user WHERE USERID = %s"
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
        sql = "INSERT INTO user VALUES(%s, %s, %s, %s, %s, %s,'대기')"
        cursor.execute(sql, (userID,userPassword,userName, userPhone, userBirth, userEmail))
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
        connect_db = pymysql.connect(  
            user="root",
            password="1234",
            host="127.0.0.1",
            db="detection",
            charset="utf8",
        )
        cursor = connect_db.cursor()
        sql = "SELECT userid, name, authority FROM user WHERE authority = '직원'"
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
        connect_db = pymysql.connect(  
            user="root",
            password="1234",
            host="127.0.0.1",
            db="detection",
            charset="utf8",
        )
        cursor = connect_db.cursor()
        sql = "UPDATE user SET authority = '대기' WHERE userid = %s"
        cursor.execute(sql, (userid))
        sql = "SELECT userid, name, authority FROM user WHERE authority = '직원'"
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
        connect_db = pymysql.connect(  
            user="root",
            password="1234",
            host="127.0.0.1",
            db="detection",
            charset="utf8",
        )
        cursor = connect_db.cursor()
        sql = "SELECT userid, name, authority FROM user WHERE authority = '대기'"
        cursor.execute(sql)
        items = cursor.fetchall()
        item_count = int(len(items) / 10) if len(items) % 10 == 0 else int(len(items) / 10 + 1)
        items = items[(page - 1) * 10 : page * 10]
        
        connect_db.commit() 
        connect_db.close()
        return render_template(
            "admin.html",
            page = page,
            items = items,
            item_count = item_count,
            admin = "대기",
        )
    else:
        connect_db = pymysql.connect(  
            user="root",
            password="1234",
            host="127.0.0.1",
            db="detection",
            charset="utf8",
        )
        cursor = connect_db.cursor()
        sql = "UPDATE user SET authority = '직원' WHERE userid = %s"
        cursor.execute(sql, (userid))
        sql = "SELECT userid, name, authority FROM user WHERE authority = '대기'"
        cursor.execute(sql)
        items = cursor.fetchall()
        item_count = int(len(items) / 10) if len(items) % 10 == 0 else int(len(items) / 10 + 1)
        items = items[(page - 1) * 10 : page * 10]
        
        connect_db.commit()
        connect_db.close()
        return render_template(
            "admin.html",
            page = page,
            items = items,
            item_count = item_count,
            admin = "대기",
        )
        
# 메인 페이지
@app.route("/main", methods=["GET", "POST"])
def main():
    if 'userID' not in session:
        return render_template("login.html")
    connect_db = pymysql.connect(  
            user="root",
            password="1234",
            host="127.0.0.1",
            db="detection",
            charset="utf8",
    )
    cursor = connect_db.cursor()
    sql = "SELECT A.ob_num, ob_name, ob_weight, ob_type, ob_state, ob_poor, ob_date, ob_image FROM object A INNER JOIN object_log B ON A.ob_num = B.ob_num"
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
    app.run(port=5000, debug=True)
