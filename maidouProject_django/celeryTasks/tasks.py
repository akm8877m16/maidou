# -*- coding:utf-8 -*-
__author__ = 'wenhao Yin <akm8877m16@126.com>'
__copyright__ = 'Copyright 2016 wenhao'


from mqttWorker import app
from pymongo import MongoClient
import datetime
import time
#from celery.utils.log import get_task_logger
from util.messageConst import CONST_DIC_ANALOG,CONST_DIC_POWER,CONST_DIC_ANALOG_RATIO,CONST_DIC_POWER_RATIO

from maidouTcp.logger import baseLogger
import pika

#events = db.events  # 事件集合
#electricPower = db["electricPower"]  # 电度集合
#analog = db.analog  # 模拟量

@app.task(bind=True)
def showMessage(self,message):
    #baseLogger.info(message)
    results = message.split(",")
    post = {}
    sn = results[0][2:]
    post["sn"] = sn
    data = results[1]
    #baseLogger.debug(data)
    dataArray = data.split(" ")
    dataArray = map(int,dataArray)
    messageType = dataArray[7]
    #baseLogger.debug(messageType)
    realDataArray = dataArray[10:]

    startIndex = dataArray[8]*256 + dataArray[9]
    #baseLogger.debug(startIndex)
    if(messageType == 12):       #模拟量
        dataLength = (dataArray[4] * 256 + dataArray[5] - 4) / 2
        for (k,v) in CONST_DIC_ANALOG.items():
            #baseLogger.debug(k)
            #baseLogger.debug(v)
            diff = startIndex -1
            if ((v-diff) > dataLength):  #not in range
                continue
            else:
                index = v-diff-1
                value = realDataArray[2*index]*256 + realDataArray[2*index+1]
                post[k] = value * CONST_DIC_ANALOG_RATIO[k]
                #baseLogger.debug(post[k])
        post["type"] = "analog"
        client = MongoClient('localhost', 27017)
        db = client["maidou"]  # database name: maidou
        realPowerConnectionName = "data_real"
        if realPowerConnectionName in db.collection_names():
            pass
            #baseLogger.debug("data_real"+":  exits")
        else:
            db.create_collection("data_real",capped=True, size=20000000000)
            #baseLogger.debug("data_real" + ":  created")
        realCollection = db["data_real"]
        post["postTime"] = datetime.datetime.utcnow()
        result = realCollection.insert_one(post)
        baseLogger.debug(result.inserted_id)
    elif(messageType == 13):     #电度
        dataLength = (dataArray[4] * 256 + dataArray[5] - 4) / 4
        for (k, v) in CONST_DIC_POWER.items():
            diff = startIndex - 1
            if ((v - diff) > dataLength):  # not in range
                continue
            else:
                index = v - diff - 1
                value = realDataArray[4 * index] * 16777216 + realDataArray[4 * index + 1]*65536+ realDataArray[4 * index + 2]*256+ realDataArray[4 * index + 3]
                post[k] = value * CONST_DIC_POWER_RATIO[k]
        post["type"] = "power"
        client = MongoClient('localhost', 27017)
        db = client["maidou"]  # database name: maidou
        realPowerConnectionName = "data_real"
        if realPowerConnectionName in db.collection_names():
            #pass
            baseLogger.debug("data_real"+":  exits")
        else:
            db.create_collection("data_real", capped=True, size=20000000000)
            # baseLogger.debug("data_real" + ":  created")
        realCollection = db["data_real"]
        post["postTime"] = datetime.datetime.utcnow()
        result = realCollection.insert_one(post)
        baseLogger.debug(result.inserted_id)
    elif(messageType == 14):      #event
        openStatue = dataArray[8] + dataArray[9]
        if(openStatue == 340):#断路器分状态
            post["open"] = True
        else:
            post["open"] = False
        post["happen_number"] = dataArray[10]*256+dataArray[11]
        post["event_number"] = dataArray[12]
        post["postTime"] = datetime.datetime.utcnow()
        client = MongoClient('localhost', 27017)
        db = client["maidou"]  # database name: maidou
        eventCollection = db["data_event"]
        result = eventCollection.insert_one(post)
        baseLogger.debug(result.inserted_id)
    elif(messageType == 11):     #断路器状态
        openStatue = dataArray[10] + dataArray[11]
        if (openStatue == 340):  # 断路器分状态
            post["open"] = True
        else:
            post["open"] = False
        post["postTime"] = datetime.datetime.utcnow()
        client = MongoClient('localhost', 27017)
        db = client["maidou"]  # database name: maidou
        eventCollection = db["data_event"]
        result = eventCollection.insert_one(post)
        baseLogger.debug(result.inserted_id)
    elif(messageType == 18):  #自检结果
        post["event_number"] = 170 #define first,if later conflict,changed
        post["postTime"] = datetime.datetime.utcnow()
        post["check1"] = False #过压检测
        post["check2"] = False #欠压检测
        post["check3"] = False #时钟检测
        post["check4"] = False # 通讯检测
        if(dataArray[8] == 170):
            post["check1"] = True
        if(dataArray[9] == 170):
            post["check2"] = True
        if(dataArray[10] == 170):
            post["check3"] = True
        if(dataArray[11] == 170):
            post["check4"] = True
        client = MongoClient('localhost', 27017)
        db = client["maidou"]  # database name: maidou
        eventCollection = db["data_event"]
        result = eventCollection.insert_one(post)
        baseLogger.debug(result.inserted_id)
'''
no open status found  1 分状态  0 合状态

check the latest device openstatus
'''
'''
@app.task
def getOpenStatus():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.queue_declare(queue="mqtt", durable=True)
    client = MongoClient('localhost', 27017)
    db = client["maidou"]  # database name: maidou
    eventCollection = db["data_event"]
    sns = eventCollection.distinct('sn')
    baseLogger.debug(sns)
    for sn in sns:
        result = eventCollection.find_one({'sn': sn}, sort=[('postTime', -1)])
        message = None
        if not result:
            baseLogger.debug("no result return")
            message=sn+","+"openStatusUnknown"
        elif(result["open"]):
            baseLogger.debug("open")
            message=sn + ","+"open"
        else:
            baseLogger.debug("close")
            message = sn + "," + "close"

        channel.basic_publish(exchange='',
                              routing_key="mqtt",
                              body=message,
                              properties=pika.BasicProperties(
                                  delivery_mode=2,  # make message persistent
                              ))
    connection.close()
'''
'''
check device on/offline status
default offline time window:20s
'''
'''
@app.task()
def getOnLineStatus():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.queue_declare(queue="mqtt", durable=True)
    client = MongoClient('localhost', 27017)
    db = client["maidou"]  # database name: maidou
    dataCollection = db["data_real"]
    sns = dataCollection.distinct('sn')
    baseLogger.debug(sns)
    timenow = datetime.datetime.utcnow()
    for sn in sns:
        result = dataCollection.find_one({'sn': sn}, sort=[('postTime', -1)])
        baseLogger.debug(result)
        message = None
        timestamp_now = time.mktime(timenow.timetuple())
        if not result:
            baseLogger.debug("no result return")
            message = sn + "," + "offline"
        else:
            latestRecordTime = result["postTime"]
            timestamp_latest = time.mktime(latestRecordTime.timetuple())
            if(timestamp_now > (timestamp_latest + 20) ):
                message = sn + "," + "offline"
            else:
                message = sn + "," + "online"
        channel.basic_publish(exchange='',
                              routing_key="mqtt",
                              body=message,
                              properties=pika.BasicProperties(
                                  delivery_mode=2,  # make message persistent
                              ))
    connection.close()
'''
'''
get hour history from mongodb
'''
@app.task()
def getHourHistory():
    queryTime = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    starttime = datetime.datetime(queryTime.year, queryTime.month, queryTime.day, queryTime.hour)
    endtime = datetime.datetime(queryTime.year, queryTime.month, queryTime.day, queryTime.hour, 59, 59)
    client = MongoClient('localhost', 27017)
    db = client["maidou"]  # database name: maidou
    dataCollection = db["data_real"]
    dataHistoryHour = db["data_hour"]
    sns = dataCollection.distinct('sn')
    for sn in sns:
        result = dataCollection.find_one({'sn': sn,'type':'power','postTime': {"$lte": endtime},'postTime': {"$gte": starttime}}, sort=[('postTime', -1)])
        baseLogger.debug(result)
        hisRecordPower = {}
        hisRecordAnalog = {}
        if not result:
            for (k, v) in CONST_DIC_POWER.items():
                hisRecordPower[k]=0
                hisRecordPower["type"] = "power"
                hisRecordPower["postTime"] = starttime
                hisRecordPower["sn"] = sn
        else:
            for (k, v) in result.items():
                hisRecordPower[k] = v
                hisRecordPower["postTime"] = starttime

        intset_result = dataHistoryHour.insert_one(hisRecordPower)
        baseLogger.debug(intset_result.inserted_id)

        result2 = dataCollection.find_one({'sn': sn,'type':'analog','postTime': {"$lte": endtime},'postTime': {"$gte": starttime}}, sort=[('postTime', -1)])
        baseLogger.debug(result2)
        if not result2:
            for (k, v) in CONST_DIC_ANALOG.items():
                hisRecordAnalog[k]=0
                hisRecordAnalog["type"] = "analog"
                hisRecordAnalog["postTime"] = starttime
                hisRecordAnalog["sn"] = sn
        else:
            for (k, v) in result2.items():
                hisRecordAnalog[k] = v
                hisRecordAnalog["postTime"] = starttime
        intset_result2 = dataHistoryHour.insert_one(hisRecordAnalog)
        baseLogger.debug(intset_result2.inserted_id)

'''
get month history for WpP from mongodb
计算每月电费  月结尾ie-月开头
'''
@app.task()
def getBillMonth():
    queryTime = datetime.datetime.utcnow()
    if queryTime.month == 1:
        starttime = datetime.datetime(queryTime.year-1, 12, 1, 0, 0, 0)
        endtime = datetime.datetime(queryTime.year, 1, 1, 0, 0, 0)
    else:
        starttime = datetime.datetime(queryTime.year, queryTime.month-1, 1, 0, 0, 0)
        endtime = datetime.datetime(queryTime.year, queryTime.month, 1, 0, 0, 0)
    client = MongoClient('localhost', 27017)
    db = client["maidou"]  # database name: maidou
    dataHistoryHour = db["data_hour"]
    dataHistoryMonth = db["data_month"]
    sns = dataHistoryHour.distinct('sn')
    for sn in sns:
        billMonth={}
        result_last = dataHistoryHour.find_one({'sn': sn,'type':'power','postTime': {"$lte": endtime},'postTime': {"$gte": starttime}}, sort=[('postTime', -1)])
        result_first = dataHistoryHour.find_one({'sn': sn,'type':'power','postTime': {"$lte": endtime},'postTime': {"$gte": starttime}}, sort=[('postTime', 1)])
        if (result_first != None):
            consumeMonth = result_last["WpP"] - result_first["WpP"]
        else:
            consumeMonth = 0
        billMonth["power"] = consumeMonth
        billMonth["postTime"] = starttime
        billMonth["sn"] = sn
        intset_result2 = dataHistoryMonth.insert_one(billMonth)
        baseLogger.debug(intset_result2.inserted_id)

