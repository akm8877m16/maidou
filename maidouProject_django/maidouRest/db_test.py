# -*- coding:utf-8 -*-
import sys
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
from tornado import gen, web
import pprint
from tornado.web import asynchronous
import motor.motor_tornado
from tornado.options import define, options
import tornado.websocket
import time
import datetime
import json
import paho.mqtt.client as mqtt
import os
import hashlib
import random
import uuid
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
from django.db import IntegrityError
import redis
sys.path.append('/home/webapps/maidouProjectDjango')
from utils.ajax import JsonResponse,JsonError
from sms.aliyunsdkdysmsapi.demo import send_sms
from pymongo import MongoClient
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'account.settings')
import django
if django.VERSION >= (1, 7):
    django.setup()
from customer.models import UserControl,Device,deviceControl
from django.db import connection

# keep mysql connect alive
def make_sure_mysql_usable():
    try:
        connection.connection.ping()
    except:
        connection.close()
'''
class addDeviceHandler(BaseHandler):
     @run_on_executor
     def post(self):
        self.make_sure_mysql_usable()
        sn = self.get_argument('sn', None)
        token = self.get_argument('token',None)
        try:
            uc = UserControl.objects.get(token=token)
            device = Device.objects.get(sn=sn)
            uc.device_set.add(device)
            dc = deviceControl.objects.get(device = device,user=uc)
            if not dc:
                dc = deviceControl(device = device,user=uc,right=2)
                dc.save()
            return self.write(JsonResponse('添加成功.'))
        except Device.DoesNotExist:
            device = Device.objects.create(type='1', sn=sn)
            uc.device_set.add(device)
            dc = deviceControl(device=device, user=uc, right=1)
            dc.save()
            self.write(JsonResponse('添加成功.'))
        except Exception as e:
            print e
            self.write(JsonError('设备添加失败. '+ e.__str__()))
'''

if __name__ == "__main__":
    queryTime = datetime.datetime.utcnow()
    print queryTime
    client = MongoClient('localhost', 27017)
    db = client["maidou"]  # database name: maidou
    dataHistoryHour = db["data_hour"]
    dataHistoryMonth = db["data_month"]
    sns = dataHistoryHour.distinct('sn')
    for month in range(2,12):
        starttime = datetime.datetime(queryTime.year, month-1, 1, 0, 0, 0)
        endtime = datetime.datetime(queryTime.year, month, 1, 0, 0, 0)
        print starttime
        print endtime

        for sn in sns:
            billMonth = {}
            result_last = dataHistoryHour.find_one(
            {'sn': sn, 'type': 'power', 'postTime': {"$lte": endtime}, 'postTime': {"$gte": starttime}},
            sort=[('postTime', -1)])
            result_first = dataHistoryHour.find_one(
            {'sn': sn, 'type': 'power', 'postTime': {"$lte": endtime}, 'postTime': {"$gte": starttime}},
            sort=[('postTime', 1)])
            if (result_first != None):
                consumeMonth = result_last["WpP"] - result_first["WpP"]
            else:
                consumeMonth = 0
            billMonth["power"] = consumeMonth
            billMonth["postTime"] = starttime
            billMonth["sn"] = sn
            intset_result2 = dataHistoryMonth.insert_one(billMonth)
            print (intset_result2.inserted_id)





