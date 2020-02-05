import threading
import cv2
import math
import argparse
import time 
import os
from cmd import commands

def highlightFace(net, frame, conf_threshold=0.6):
    frameOpencvDnn=frame.copy()
    frameHeight=frameOpencvDnn.shape[0]
    frameWidth=frameOpencvDnn.shape[1]
    blob=cv2.dnn.blobFromImage(frameOpencvDnn, 1.0, (300, 300), [104, 117, 123], True, False)

    net.setInput(blob)
    detections=net.forward()
    faceBoxes=[]
    for i in range(detections.shape[2]):
        confidence=detections[0,0,i,2]
        if confidence>conf_threshold:
            x1=int(detections[0,0,i,3]*frameWidth)
            y1=int(detections[0,0,i,4]*frameHeight)
            x2=int(detections[0,0,i,5]*frameWidth)
            y2=int(detections[0,0,i,6]*frameHeight)
            faceBoxes.append([x1,y1,x2,y2])
            cv2.rectangle(frameOpencvDnn, (x1,y1), (x2,y2), (0,255,0), int(round(frameHeight/150)), 8)
    return faceBoxes

def is_legal(age_list):  #if the sum is more than 0 than the age is iligal, else the age is ok
    res=0
    for i in age_list:
        res+=i
    if res > 0:
        return True
    return False


def start_cam(dns_lock,dns_db,blocked_urls):

    def block_unblock_dns(is_legal=True):
        # helper function that blocks or unblock dns urls
        try:
            # lock DNS
            dns_lock.acquire()  # type: threading.Lock
            #update DNS db
            if not is_legal:
                # block
                print("blocking dns for:{}".format(blocked_urls))
                dns_db['A'] = blocked_urls
            else:
                #unblock
                print("unblocking dns")
                dns_db['A'] = dict()
        except Exception as ex:
            print(ex)

        finally:
            commands.flush_dns()
            dns_lock.release()

    parser = argparse.ArgumentParser()
    parser.add_argument('--image')

    args = parser.parse_args()
    faceProto =  os.path.join(os.getcwd(),"face_detaction","face_detaction_data","opencv_face_detector.pbtxt")
    faceModel = os.path.join(os.getcwd(),"face_detaction","face_detaction_data","opencv_face_detector_uint8.pb")
    ageProto = os.path.join(os.getcwd(),"face_detaction","face_detaction_data","age_deploy.prototxt")
    ageModel = os.path.join(os.getcwd(),"face_detaction","face_detaction_data","age_net.caffemodel")


    MODEL_MEAN_VALUES = (78.4263377603, 87.7689143744, 114.895847746)
    ageList = [-1, -1, -1, -1, 1, 1, 1, 1]

    faceNet = cv2.dnn.readNet(faceModel, faceProto)
    ageNet = cv2.dnn.readNet(ageModel, ageProto)
 

    video = cv2.VideoCapture(args.image if args.image else 0)
    padding = 20
    i = 0
    age = [0,0,0,0,0,0,0,0,0,0]
    last_is_legal = None
    need_update = False
    while cv2.waitKey(1) < 0:
        if i % len(age) == len(age)-1:
            if is_legal(age):
                print('age over 18')
                if last_is_legal is None or not last_is_legal:
                    last_is_legal = True
                    need_update = True
                else:
                    need_update = False
                # tell to the prosses age > 18
            else:
                # tell to the prosses age < 18
                print('age under 18')
                if last_is_legal is None or last_is_legal:
                    last_is_legal = False
                    need_update = True
                else:
                    need_update = False
            if need_update:
                block_unblock_dns(last_is_legal)

        i+= 1
        hasFrame, frame = video.read()
        if not hasFrame:
            cv2.waitKey()
            break

        faceBoxes = highlightFace(faceNet, frame)
        if not faceBoxes:
            age = [0,0,0,0,0,0,0,0,0,0]

        for faceBox in faceBoxes:
            face = frame[max(0, faceBox[1] - padding):
                         min(faceBox[3] + padding, frame.shape[0] - 1), max(0, faceBox[0] - padding)
                                                                        :min(faceBox[2] + padding, frame.shape[1] - 1)]

            try:
                blob = cv2.dnn.blobFromImage(face, 1.0, (227, 227), MODEL_MEAN_VALUES, swapRB=False)
            except Exception as ex:
                print (ex)
                
            ageNet.setInput(blob)
            agePreds = ageNet.forward()
            age[i % len(age)] = ageList[agePreds[0].argmax()]
            print(age)
            time.sleep(0.5)

def start_cam_therad(dns_db,dns_lock,blocked_urls):
    thread = threading.Thread(name="cam thread",target=start_cam,args=(dns_lock,dns_db,blocked_urls))
    thread.daemon = True
    thread.start()
