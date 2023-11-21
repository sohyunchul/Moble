from ultralytics import YOLO
import cv2
import numpy as np
from PIL import Image
import math
import cvzone


# Object 객체 선별
def object_detect(image_path):
    text_area = ""
    objects = "None"

    model = YOLO("Object.pt")
    classNames = [
    "PCB",
    "orange_juice",
    ]
    src = cv2.imread(image_path)
    results = model(src)
    for r in results:
        boxes = r.boxes
        for box in boxes:
            # Class Name
            cls = int(box.cls[0])
            currentClass = classNames[cls]
            objects = currentClass

            # PCB
            if objects == classNames[0]:
                text_area, src = pcb_detect(image_path, src)
                return text_area, objects
            # orange_juice
            elif objects == classNames[1]:
                text_area, src = orange_juice_detect(image_path, src)
                return text_area, objects
    return text_area, objects

# PCB YOLO
def pcb_detect(image_path, src):
    text_area = ""
    myColor = (0, 0, 255)
    model = YOLO("PCB.pt")
                
    classNames = [
    "missing_hole",
    "mouse_bite",
    "open_circuit",
    ]
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
            if conf > 0.6:
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
    return text_area, src

# orange_juice YOLO
def orange_juice_detect(image_path, src):
    text_area = ""
    myColor = (0, 0, 255)
    model = YOLO("Orange.pt")
                
    classNames = [
    "Bad_Image",
    "Bad_Packing",  
    ]
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
            if conf > 0.6:
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
    return text_area, src