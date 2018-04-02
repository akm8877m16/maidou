# -*- coding:utf-8 -*-
import sys
import tornado.escape
import tornado.httpserver
from tornado.web import URLSpec
from tornado.web import StaticFileHandler
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
import pprint
import functools
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
from django.db import IntegrityError
import calendar
import redis
sys.path.append('/home/webapps/maidouProjectDjango')
from config import UPLOAD_IMAGE_PATH
from utils.ajax import JsonResponse,JsonError
from utils.helperFuncs import isEmail, isMobilePhone
from sms.aliyunsdkdysmsapi.demo import send_sms
from celeryTasks.tasks import sendMessage, sendMail
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'account.settings')
import django
if django.VERSION >= (1, 7):
    django.setup()
from customer.models import UserControl,Device,deviceControl
from django.db import connection
#from maidouTcp.logger import baseLogger
define("port", default=8888, help="run on the given port", type=int)
define ("sign_name", default='麦豆matis',help="短信签名", type=str)
define ("template_code", default='SMS_110830099',help="短信模板", type=str)
MAX_WORKERS = 5
waiters = set() #websocket client set
class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/maidou/openStatus/(\w+)", openStatusHandler), #get device open status
            (r"/maidou/event/(\w+)", eventHandler),
            (r"/maidou/realData/(\w+)", realDataHandler),
            (r"/maidou/websocket", webSocketHandler),
            (r"/maidou/historyHour/(\w+)/(\w+)", historyHourHandler),
            (r"/maidou/valueMonthFirst/(\w+)/(\w+)",firstMonthValueHandler),
            (r"/maidou/control/(\w+)/(\w+)",remoteControlHandler),
            (r"/maidou/login", loginHandler),
            (r"/maidou/register", registerHandler),
            (r"/maidou/sms/(\w+)", smsHandler),
            (r"/maidou/resetPass", resetPassHandler),
            (r"/maidou/quit/(\w+)", quitHandler),
            (r"/maidou/device/(\w+)", deviceHandler),
            (r"/maidou/addDevice", addDeviceHandler),
            (r"/maidou/delDevice", delDeviceHandler),
            (r"/maidou/updateDevice", updateDeviceHandler),
            (r"/maidou/checkOwner", checkOwnerHandler),
            (r"/maidou/billMonth/(\w+)", billMonthHandler),#获取当前月的电量统计
            (r"/maidou/billMonthHistory/(\w+)", billMonthHistoryHandler),
            (r"/maidou/headImage", headImageHandler),
            (r"/maidou/sendEmail", mailHandler),
            (r"/maidou/changeName", changeNameHandler),
        ]
        settings = dict(
            static_path="static",
        )
        super(Application, self).__init__(handlers, **settings)
        # Have one global connection to the blog DB across all handlers
        conn = motor.motor_tornado.MotorClient('localhost', 27017)
        self.db = conn["maidou"]
        self.redisPool = redis.ConnectionPool(host='localhost', port=6379, decode_responses=True)
class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.db

    @property
    def redisPool(self):
        return self.application.redisPool

    # keep mysql connect alive
    def make_sure_mysql_usable(self):
        try:
            connection.connection.ping()
        except:
            connection.close()

    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

class openStatusHandler(BaseHandler):
    @asynchronous
    @gen.coroutine
    def get(self,sn):
        sn = sn.upper()
        result = yield self.db.data_event.find_one({'sn': sn,'open': { '$exists': True }}, sort=[('postTime', -1)])
        response = {}
        if not result:
            response["message"] = "no data found"
        else:
            response["message"] = "success"
            response["open"] = result["open"]
            statusTime = result["postTime"]
            response["postTime"] = int(time.mktime(statusTime.timetuple()))
        #pprint.pprint(result)
        self.write(response)
        self.finish()


#默认最多返回100条记录
class eventHandler(BaseHandler):
    @asynchronous
    @gen.coroutine
    def get(self, sn):
        sn = sn.upper()
        response = {}
        eventArray = [];
        cursor = self.db.data_event.find({'sn': sn,'event_number': { '$gt': 0 },'event_number': { '$lt': 170 } }, sort=[('postTime', -1)]).limit(100)
        for document in (yield cursor.to_list(length=100)):
            #pprint.pprint(document)
            eventD = {}
            eventD["event_number"] = document["event_number"]
            statusTime = document["postTime"]
            eventD["postTime"] = int(time.mktime(statusTime.timetuple()))
            eventArray.append(eventD)
        response["events"] = eventArray
        self.write(response)
        self.finish()



class realDataHandler(BaseHandler):
    @asynchronous
    @gen.coroutine
    def get(self,sn):
        sn = sn.upper()
        result_a = yield self.db.data_real.find_one({"sn": sn, "type": "analog"}, sort=[("postTime", -1)])
        result_p= yield self.db.data_real.find_one({'sn': sn, 'type': 'power'}, sort=[('postTime', -1)])
        #pprint.pprint(result_a)
        #pprint.pprint(result_p)
        response = {}
        if result_a != None:
            response["FR"]= result_a["FR"]
            response["UA"] = result_a["UA"]
            response["IA"] = result_a["IA"]
            response["P"] = result_a["P"]
            response["Q"] =4
        else:
            response["FR"] = 0
            response["UA"] = 0
            response["IA"] = 0
            response["P"] = 0
        if result_p != None:
            response["WpP"] = result_p["WpP"]
        else:
            response["WpP"] = 0
        self.write(response)
        self.finish()


class webSocketHandler(tornado.websocket.WebSocketHandler):

    def get_compression_options(self):
        # Non-None enables compression with default options.
        return {}

    def open(self):
        waiters.add(self)
        print "open connection"
        print(waiters.__len__())

    def on_close(self):
        waiters.remove(self)
        print "close connection"
        print(waiters.__len__())

    @gen.coroutine
    def on_message(self, message):
            print message
            results = message.split(",")
            command = results[0]
            sn = results[1]
            sn = sn.upper()
            response={}
            if(command == "ifOnline"): #check if device online
                result =  yield self.application.db.data_real.find_one({"sn": sn}, sort=[("postTime", -1)])
                if result != None:
                    timenow = datetime.datetime.utcnow()
                    timestamp_now = time.mktime(timenow.timetuple())
                    latestRecordTime = result["postTime"]
                    timestamp_latest = time.mktime(latestRecordTime.timetuple())
                    if (timestamp_now > (timestamp_latest + 20)):
                        response["message"] = "offline"
                    else:
                        response["message"] = "online"
                else:
                    response["message"] = "offline"
            elif(command == "realData"):#request for latest data
                result_a = yield self.application.db.data_real.find_one({"sn": sn, "type": "analog"}, sort=[("postTime", -1)])
                result_p = yield self.application.db.data_real.find_one({'sn': sn, 'type': 'power'}, sort=[('postTime', -1)])
                if result_a != None:
                    response["FR"] = result_a["FR"]
                    response["UA"] = result_a["UA"]
                    response["IA"] = result_a["IA"]
                    response["P"] = result_a["P"]
                    response["Q"] = 4
                if result_p != None:
                    response["WpP"] = result_p["WpP"]
            elif(command == "ifOpen"):
                result = yield self.application.db.data_event.find_one({'sn': sn, 'open': {'$exists': True}},sort=[('postTime', -1)])
                if result != None:
                    response["message"] = "success"
                    response["open"] = result["open"]
                else:
                    response["message"] = "no data found"
            elif(command == "selfCheck"):
                timestamp = float(results[2])
                time_check = datetime.datetime.utcfromtimestamp(timestamp)
                print timestamp
                print time_check
                result = yield self.application.db.data_event.find_one({'sn': sn, "event_number":170,'postTime': {"$gte": time_check}})
                if result != None:
                    response["message"] = "success"
                    response["check1"] = result["check1"]
                    response["check2"] = result["check2"]
                    response["check3"] = result["check3"]
                    response["check4"] = result["check4"]
                else:
                    response["message"] = "no_result"

            responseMessage = json.dumps(response)
            try:
                self.write_message(responseMessage)
            except:
                print("Error sending message " + message)



'''
get 100 records at most
'''
class historyHourHandler(BaseHandler):
    @asynchronous
    @gen.coroutine
    def get(self, sn, type):
        sn = sn.upper()
        response = {}
        cursor = self.db.data_hour.find({"sn": sn, "type": type}, sort=[("postTime", -1)]).limit(100)
        historyArray = [];
        for document in (yield cursor.to_list(length=100)):
            #pprint.pprint(document)
            hisD = {}
            for (k, v) in document.items():
                if k != "_id":
                    hisD[k] = v
            statusTime = document["postTime"]
            hisD["postTime"] = int(time.mktime(statusTime.timetuple()))
            historyArray.append(hisD)
        response["history"] = historyArray
        self.write(response)
        self.finish()
'''
get the first WpP value of the month
'''
class firstMonthValueHandler(BaseHandler):
    @asynchronous
    @gen.coroutine
    def get(self, sn, month):
        sn = sn.upper()
        monthV = int(month)
        queryTime = datetime.datetime.now()
        response = {}
        if monthV == 12:
            starttime = datetime.datetime(queryTime.year, 12, 1, 0, 0, 0)
            endtime = datetime.datetime(queryTime.year+1, 1, 1, 0, 0, 0)
        else:
            starttime = datetime.datetime(queryTime.year, monthV, 1, 0, 0, 0)
            endtime = datetime.datetime(queryTime.year, monthV+1, 1, 0, 0, 0)
        print  starttime
        print  endtime
        result= yield self.db.data_hour.find_one({'sn': sn, 'type': 'power', 'postTime': {"$lte": endtime},'postTime': {"$gte": starttime}}, sort=[('postTime', 1)])
        if(result != None):
            response["WpP"] = result["WpP"]
            response["message"] = "fetch success"
        else:
            response["WpP"] = 0
            response["message"] = "fetch success"
        self.write(response)
        self.finish()

'''
    instead of sending command through mqtt directly,now command was sent 
    by server itself
    command: open, close
    2017/12/15 add remote control type default wifi control  0      tcp controller 1   
'''
class remoteControlHandler(BaseHandler):
    def get(self, sn, command):
        sn = sn.upper()
        controlType = self.get_argument('type', 0)
        if controlType == '1':
            sendMessage.delay(sn, command)
            response = {}
            response["message"] = "success"
            self.write(response)
        else:
            mqttClient = mqtt.Client()
            mqttClient.connect("118.190.202.155", 1883)
            if command == "open":
                openCommand = [0x00, 0x00, 0x00, 0x00, 0x00, 0x06, 0x01, 0x05, 0x00, 0x00, 0xAA, 0xAA]
                ack = bytearray()
                ack.extend(openCommand)
                mqttClient.publish("M/" + sn, ack)
            elif command == "close":
                closeCommand = [0x00, 0x00, 0x00, 0x00, 0x00, 0x06, 0x01, 0x05, 0x00, 0x00, 0x55, 0x55]
                ack = bytearray()
                ack.extend(closeCommand)
                mqttClient.publish("M/" + sn, ack)
            elif command == "selfCheck":
                closeCommand = [0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x01, 0x11]
                ack = bytearray()
                ack.extend(closeCommand)
                mqttClient.publish("M/" + sn, ack)
            mqttClient.disconnect()
            response = {}
            response["message"] = "success"
            self.write(response)

    def sendTcp(self, message):
        print message
        sendMessage.delay(message)
        print 'testtest'
'''
user login 
password
username
'''
class loginHandler(BaseHandler):
    @run_on_executor()
    def post(self):
        try:
            self.make_sure_mysql_usable()
            param = self.request.body.decode('utf-8')
            print self.get_argument('password', '')
            print self.get_argument('username', '')
            password = self.get_argument('password', None)
            username = self.get_argument('username', None)  #phone number for now
            if username is None:
                self.write(JsonError('login_user_name_error'))
            if password is None:
                self.write(JsonError('password_empty'))
            if isMobilePhone(username):
                uc = UserControl.objects.get(phone=username, password=hashlib.md5('hpy:' + password).hexdigest())
            elif isEmail(username):
                uc = UserControl.objects.get(email=username, password=hashlib.md5('hpy:' + password).hexdigest())
            else:
                self.write(JsonError('user_name_error'))
                return
            if not uc.user_name:
                userName = ''
            else:
                userName = uc.user_name
            self.write(JsonResponse({
                'msg': 'success',
                'token': uc.token,
                'username': userName
            }))
        except UserControl.DoesNotExist:
            self.write(JsonError('no_user'))
        except Exception as e:
            print e
            self.write(JsonError('login_failed'))
'''
register
username
password
code
'''
class registerHandler(BaseHandler):
    @run_on_executor()
    def post(self):
        self.make_sure_mysql_usable()
        password = self.get_argument('password', None)
        username = self.get_argument('username', None) # phone number for now
        print username
        code = self.get_argument('code', None)
        r = redis.Redis(connection_pool=self.redisPool)
        smsCode = r.get(username)
        if smsCode is None:
            self.write(JsonError('code_expire'))
        elif int(code) == int(smsCode):
            #register when verification code in valid
            if isMobilePhone(username):
                if UserControl.objects.filter(phone=username).exists():
                    self.write(JsonError('user_exist'))
                else:
                    user = UserControl(phone=username,user_name=username)
                    user.set_password(password)
                    # 首次写入token令牌
                    user.refreshToken()
                    try:
                        user.save()
                        result = {
                            'msg': 'register_success',
                            'user_id': user.pk,
                            'token': user.token,
                            'token_refresh_at': user.token_refresh_at.strftime('%Y-%m-%d %H:%M:%S')
                        }
                        self.write(JsonResponse(result))
                    except IntegrityError:
                        self.write(JsonError('register_fail'))
                    except Exception as e:
                        print e
                        self.write(JsonError('register_fail'))

            elif isEmail(username):
                if UserControl.objects.filter(email=username).exists():
                    self.write(JsonError('user_exist'))
                else:
                    user = UserControl(email=username, user_name=username)
                    user.set_password(password)
                    # 首次写入token令牌
                    user.refreshToken()
                    try:
                        user.save()
                        result = {
                            'msg': 'register_success',
                            'user_id': user.pk,
                            'token': user.token,
                            'token_refresh_at': user.token_refresh_at.strftime('%Y-%m-%d %H:%M:%S')
                        }
                        self.write(JsonResponse(result))
                    except IntegrityError:
                        self.write(JsonError('register_fail'))
                    except Exception as e:
                        print e
                        self.write(JsonError('register_fail'))
        else:
            self.write(JsonError('code_wrong'))


'''
send sms verification code
'''
class smsHandler(BaseHandler):
    @run_on_executor
    def background_task(self, phone):
        """ This will be executed in `executor` pool. """
        code = random.randint(100000, 999999)
        print options.sign_name
        print options.template_code
        params = "{\"code\":\"" + str(code) + "\"}"
        print params;
        __business_id = uuid.uuid1()
        response = send_sms(__business_id, phone, options.sign_name, options.template_code, params)
        res = eval(response)
        if(res['Message'] == 'OK'):
            #write code to redis
            r = redis.Redis(connection_pool=self.redisPool)
            r.set(phone, code, ex=360)   #expire 6 min

        return response

    @tornado.gen.coroutine
    def get(self,phone):
        res = yield self.background_task(phone)
        response = eval(res)
        self.write(JsonResponse({
                'msg': response['Message']
            }))
'''
reset password
code 
newPass
phone
'''
class resetPassHandler(BaseHandler):
    @run_on_executor()
    def post(self):
        """忘记密码 通过手机验证修改密码
           post  {'phone': '18767100996', 'code': code, 'newPWD': 'xxxx'}
        """
        self.make_sure_mysql_usable()
        newPass = self.get_argument('newPass', None)
        phone = self.get_argument('phone', None) #接口更新，这个phone可以是手机号码或者邮箱
        code = self.get_argument('code', None)
        r = redis.Redis(connection_pool=self.redisPool)
        smsCode = r.get(phone)
        print smsCode
        if not smsCode:
            self.write(JsonError('code_wrong'))
        elif phone and code and newPass:
                if int(code) == int(smsCode):
                        try:
                            if isMobilePhone(phone):
                                user = UserControl.objects.get(phone=phone)
                            elif isEmail(phone):
                                user = UserControl.objects.get(email=phone)
                            user.set_password(newPass)
                            user.refreshToken()  # 刷新token
                            user.save()
                            self.write(JsonResponse(user.token))
                        except UserControl.DoesNotExist:
                            self.write(JsonError('no_user'))
                        except IntegrityError as e:
                            print e
                            self.write(JsonError('password_change_fail'))
                        except Exception as e:
                            print e
                            self.write(JsonError('password_change_fail'))
                else:
                    self.write(JsonError('code_wrong'))
        else:
            self.write(JsonError('wrong_parameters'))

class quitHandler(BaseHandler):
    @run_on_executor
    def get(self, token):
        self.make_sure_mysql_usable()
        try:
            uc = UserControl.objects.get(token=token)
            uc.refreshToken()
            uc.save()
            self.write(JsonResponse('quit'))
        except Exception as e:
            self.write(JsonError('token_invalid'))

class deviceHandler(BaseHandler):
    @run_on_executor
    def get(self, token):
        self.make_sure_mysql_usable()
        try:
            devices =Device.objects.filter(user__token=token).all()
            lists = []
            if not devices:
                self.write(JsonResponse(lists))
            else:
                for device in devices:
                    lists.append({
                    'sn': device.sn,
                    'name': device.name,
                    'type': device.type,
                    'address': device.address,
                    'controlPass': device.controlPass
                    })
                self.write(JsonResponse(lists))
        except Exception as e:
            print e
            self.write(JsonError('ERROR.'+e.__str__()))

'''
sn
token

'''
class addDeviceHandler(BaseHandler):
     @run_on_executor
     def post(self):
        self.make_sure_mysql_usable()
        sn = self.get_argument('sn', None)
        if sn is not None:
            sn = sn.upper()
        token = self.get_argument('token',None)
        try:
            uc = UserControl.objects.get(token=token)
            device = Device.objects.get(sn=sn)
            uc.device_set.add(device)
            dc = deviceControl.objects.filter(device = device,user=uc)
            if not dc:
                dc = deviceControl(device = device,user=uc,right=2)
                dc.save()
            return self.write(JsonResponse('device_add_success'))
        except Device.DoesNotExist:
            device = Device.objects.create(type='1', sn=sn)
            uc.device_set.add(device)
            dc = deviceControl(device=device, user=uc, right=1)
            dc.save()
            self.write(JsonResponse('device_add_success'))
        except Exception as e:
            print e
            self.write(JsonError('device_add_fail'))

'''
sn
token
'''
class delDeviceHandler(BaseHandler):
    @run_on_executor
    def post(self):
        self.make_sure_mysql_usable()
        sn = self.get_argument('sn', None)
        if sn is not None:
            sn = sn.upper()
        token = self.get_argument('token', None)
        try:
            uc = UserControl.objects.get(token=token)
            device = Device.objects.get(sn=sn)
            uc.device_set.remove(device)
            users = UserControl.objects.filter(device__sn = sn)
            if not users:
                device.delete()
            return self.write(JsonResponse('unbind_device_success'))
        except Device.DoesNotExist:
            self.write(JsonError('unbind_device_success'))
        except Exception as e:
            print e
            self.write(JsonError('unbind_device_fail'))
'''
name
address
controlPass
sn
'''
class updateDeviceHandler(BaseHandler):
    @run_on_executor
    def post(self):
        self.make_sure_mysql_usable()
        name = self.get_argument('name', '')
        address = self.get_argument('address', '')
        controlPass = self.get_argument('controlPass', '')
        sn = self.get_argument('sn', None)
        if sn is not None:
            sn = sn.upper()
        token = self.get_argument('token', None)
        try:
            uc = UserControl.objects.get(token=token)
            device = Device.objects.get(sn=sn)
            dc = deviceControl.objects.get(device=device,user=uc)
            #if dc.right == 2:
            #    self.write(JsonError('无设备信息更新权限'))
            #else:
            device.name=name
            device.address = address
            device.controlPass = controlPass
            device.save()
            self.write(JsonResponse('update_device_info_success'))
        except Exception as e:
            print e
            self.write(JsonError('update_device_info_fail'))
'''
sn
token
'''
class checkOwnerHandler(BaseHandler):
    @run_on_executor
    def post(self):
        self.make_sure_mysql_usable()
        sn = self.get_argument('sn', '')
        if sn != '':
            sn = sn.upper()
        token = self.get_argument('token', '')
        try:
            uc = UserControl.objects.get(token=token)
            device = Device.objects.get(sn=sn)
            dc = deviceControl.objects.get(device=device, user=uc)
            if not dc:
                self.write(JsonError('权限查询失败'))
            else:
                right = dc.right
                self.write(JsonResponse({'right':right}))
        except Exception as e:
            print e
            self.write(JsonError('权限查询失败'))

class billMonthHandler(BaseHandler):
    @asynchronous
    @gen.coroutine
    def get(self,sn):
        sn = sn.upper()
        queryTime = datetime.datetime.utcnow()
        currentMonth = queryTime.month
        print queryTime
        print currentMonth
        billMonth = {}
        starttime = datetime.datetime(queryTime.year, currentMonth, 1, 0, 0, 0)
        result_first = yield self.db.data_hour.find_one(
                {'sn': sn, 'type': 'power', 'postTime': {"$lte": queryTime}, 'postTime': {"$gte": starttime}},
                sort=[('postTime', 1)])
        result_last = yield self.db.data_hour.find_one(
                {'sn': sn, 'type': 'power', 'postTime': {"$lte": queryTime}, 'postTime': {"$gte": starttime}},
                sort=[('postTime', -1)])
        if (result_first != None):
            consumeMonth = result_last["WpP"]-result_first["WpP"]
        else:
            consumeMonth = 0
        billMonth["power"] = consumeMonth
        billMonth["month"] = currentMonth
        billMonth["sn"]= sn
        self.write(JsonResponse(billMonth))
        self.finish()
'''
获取当前月之前的月电量消耗记录
'''
class billMonthHistoryHandler(BaseHandler):
    @asynchronous
    @gen.coroutine
    def get(self, sn):
        sn = sn.upper()
        queryTime = datetime.datetime.utcnow()
        billHistory = []
        starttime = datetime.datetime(queryTime.year, 1, 1, 0, 0, 0)
        cursor = self.db.data_month.find(
            {'sn': sn, 'postTime': {"$lte": queryTime}, 'postTime': {"$gte": starttime}},
            sort=[('postTime', 1)])
        for document in (yield cursor.to_list(length=100)):
            pprint.pprint(document)
            billMonth = {}
            postTime = document["postTime"]
            billMonth["month"] = postTime.month
            billMonth["power"] = document["power"]
            billHistory.append(billMonth)
        self.write(JsonResponse(billHistory))
        self.finish()

'''
头像接口
'''
class headImageHandler(BaseHandler):

    @run_on_executor()
    def get(self):
        self.make_sure_mysql_usable()
        token = self.get_argument('token', None)
        try:
            uc = UserControl.objects.get(token=token)
            if not uc.headerImage:
                self.write(JsonResponse('nothing'))
            else:
                self.write(JsonResponse(uc.headerImage))
        except UserControl.DoesNotExist:
            self.write(JsonError('need login in'))



    @run_on_executor
    def post(self):
        filesList = self.request.files.items()
        uploadFile = filesList[0]
        info = uploadFile[1][0]
        filename, content_type = info['filename'], info['content_type']
        body = info['body']
        print('POST "%s" "%s" %d bytes',filename, content_type, len(body))
        self.make_sure_mysql_usable()
        token = self.get_argument('token', None)
        try:
            uc = UserControl.objects.get(token=token)
            uc.headerImage = filename
            uc.save()
            with open(os.path.join(UPLOAD_IMAGE_PATH, filename), 'wb') as up:  # os拼接文件保存路径，以字节码模式打开
                up.write(body)  # 将文件写入到保存路径目录
            self.write(JsonResponse(filename))
        except UserControl.DoesNotExist:
            self.write(JsonError('need login in'))
        except Exception as e:
            self.write(JsonError(e.__str__()))

class mailHandler(BaseHandler):
    def post(self):
        userEmail = self.get_argument('email', None)
        if userEmail is not None:
            code = random.randint(100000, 999999)
            sendMail.delay(userEmail,str(code));
            r = redis.Redis(connection_pool=self.redisPool)
            r.set(userEmail, code, ex=600)  # expire 6 min
            self.write(JsonResponse("success"))
        else:
            self.write(JsonError("no email input"))

class changeNameHandler(BaseHandler):
    @run_on_executor
    def post(self):
        token = self.get_argument('token', None)
        newName = self.get_argument('newName', None)
        try:
            user = UserControl.objects.get(token=token)
            user.user_name = newName
            user.save()
            self.write(JsonResponse({'name':newName}))
        except Exception as e:
            print e
            self.write(JsonError('chane new name failed'))




def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.current().start()
    print ("http server start at "+ options.port)
if __name__ == "__main__":
    main()

