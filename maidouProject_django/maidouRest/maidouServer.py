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
import calendar
import redis
sys.path.append('/home/webapps/maidouProjectDjango')
from utils.ajax import JsonResponse,JsonError
from sms.aliyunsdkdysmsapi.demo import send_sms
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
            (r"/maidou/billMonthHistory/(\w+)", billMonthHistoryHandler)
        ]
        settings = dict(

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
'''
class remoteControlHandler(BaseHandler):
    @asynchronous
    def get(self, sn, command):
        mqttClient = mqtt.Client()
        mqttClient.connect("118.190.202.155", 1883)
        if command == "open":
            openCommand = [0x00,0x00,0x00,0x00,0x00,0x06,0x01,0x05,0x00,0x00,0xAA,0xAA]
            ack = bytearray()
            ack.extend(openCommand)
            mqttClient.publish("M/"+sn, ack)
        elif command == "close":
            closeCommand = [0x00,0x00,0x00,0x00,0x00,0x06,0x01,0x05,0x00,0x00,0x55,0x55]
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
        self.finish()
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
                self.write(JsonError('请填写电话'))
            if password is None:
                self.write(JsonError('请填写密码'))

            uc = UserControl.objects.get(phone=username, password=hashlib.md5('hpy:' + password).hexdigest())

            self.write(JsonResponse({
                'msg': '登录成功',
                'token': uc.token
            }))
        except UserControl.DoesNotExist:
            self.write(JsonError('用户名密码错误'))
        except Exception as e:
            print e
            self.write(JsonError('登录失败'))
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
        if username is None:
            self.write(JsonError(u'注册账号请填写手机'))
        if password is None:
            self.write(JsonError(u'密码不允许为空'))
        r = redis.Redis(connection_pool=self.redisPool)
        smsCode = r.get(username)
        if smsCode is None:
            self.write(JsonError(u'验证码已过期'))
        elif int(code) == int(smsCode):
            #register when verification code in valid
            if UserControl.objects.filter(phone=username).exists():
                self.write(JsonError(u'注册失败,手机号已经存在.'))
            else:
                user = UserControl(phone=username)
                user.set_password(password)
                # 首次写入token令牌
                user.refreshToken()
                try:
                    user.save()
                    print "first save"
                    result = {
                        'msg': '注册成功',
                        'user_id': user.pk,
                        'token': user.token,
                        'token_refresh_at': user.token_refresh_at.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    self.write(JsonResponse(result))
                except IntegrityError:
                    self.write(JsonError(u'注册失败,请重试.'))
                except Exception as e:
                    print e
                    self.write(JsonError(u'注册失败,请重试. '))
        else:
            self.write(JsonError(u'验证码不匹配'))


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
        phone = self.get_argument('phone', None)
        code = self.get_argument('code', None)
        r = redis.Redis(connection_pool=self.redisPool)
        smsCode = r.get(phone)
        print smsCode
        if phone and code and newPass:
                if int(code) == int(smsCode):
                    try:
                        user = UserControl.objects.get(phone=phone)
                        user.set_password(newPass)
                        user.refreshToken()  # 刷新token
                        user.save()
                        self.write(JsonResponse(user.token))
                    except UserControl.DoesNotExist:
                        self.write(JsonError(u'用户不存在,请重新登入'))
                    except IntegrityError as e:
                        print e
                        self.write(JsonError(u'密码更改失败'))
                    except Exception as e:
                        print e
                        self.write(JsonError(u'密码更改失败 '))
                else:
                    self.write(JsonError(u'短信验证失败'))
        else:
            self.write(JsonError(u'参数错误'))

class quitHandler(BaseHandler):
    @run_on_executor
    def get(self, token):
        self.make_sure_mysql_usable()
        try:
            uc = UserControl.objects.get(token=token)
            uc.refreshToken()
            uc.save()
            self.write(JsonResponse(u'退出登录'))
        except Exception as e:
            self.write(JsonError('token 无效'))

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
        token = self.get_argument('token',None)
        try:
            uc = UserControl.objects.get(token=token)
            device = Device.objects.get(sn=sn)
            uc.device_set.add(device)
            dc = deviceControl.objects.filter(device = device,user=uc)
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
sn
token
'''
class delDeviceHandler(BaseHandler):
    @run_on_executor
    def post(self):
        self.make_sure_mysql_usable()
        sn = self.get_argument('sn', None)
        token = self.get_argument('token', None)
        try:
            uc = UserControl.objects.get(token=token)
            device = Device.objects.get(sn=sn)
            uc.device_set.remove(device)
            users = UserControl.objects.filter(device__sn = sn)
            if not users:
                device.delete()
            return self.write(JsonResponse('删除成功.'))
        except Device.DoesNotExist:
            self.write(JsonError('删除成功.设备已删除'))
        except Exception as e:
            print e
            self.write(JsonError('设备删除失败'))
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
            self.write(JsonResponse('设备信息更新成功'))
        except Exception as e:
            print e
            self.write(JsonError('设备信息更新失败'))
'''
sn
token
'''
class checkOwnerHandler(BaseHandler):
    @run_on_executor
    def post(self):
        self.make_sure_mysql_usable()
        sn = self.get_argument('sn', '')
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


def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.current().start()
    print ("http server start at "+ options.port)
if __name__ == "__main__":
    main()

