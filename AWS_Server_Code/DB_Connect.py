from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import mysql.connector

def db_connect():
    db_config = {
            'user':'admin',
            'password':'1234',
            'host':'AWS RDS ANDPOINT',
            'db':'database_name',
        }
    connect_db = mysql.connector.connect(**db_config)
    #객체 생성
    cursor = connect_db.cursor()
    return connect_db, cursor

def object_insert(cursor, connect_db, res, objects, weight, db_image_path, category, result, status, date):
    sql = "INSERT INTO OBJECT VALUES(%s, %s, %s, 0.1, %s, %s)"
    cursor.execute(sql, (res, objects, weight, db_image_path, category))
    sql = "INSERT INTO OBJECT_LOG VALUES(%s, %s, %s, %s)"
    cursor.execute(sql, (res, status, result, date))
    connect_db.commit() 
    connect_db.close() 
    
    