# -*- coding:utf-8 -*-
import datetime
from pymongo import MongoClient
#import sys
#sys.path.append('/home/webapps/maidouProject')
import pprint
# 主程序
if __name__ == '__main__':
    '''
    client = MongoClient('localhost', 27017)
    db = client["maidou"]  # database name: maidou
    # events = db.events  # 事件集合
    electricPower = db["electricPower"]  # 电度集合
    # analog = db.analog  # 模拟量
    post = {"sn": "H/234sdfsdf",
            "data": [12,34,23,123,123],
            "postTime": datetime.datetime.utcnow()}
    result = electricPower.insert_one(post)
    print result.inserted_id
    '''
    #showMessage.delay("H/123klsf,123 13 313 123 123 213 13")

    queryTime = datetime.datetime.now() - datetime.timedelta(hours=1)
    starttime = datetime.datetime(queryTime.year, queryTime.month, queryTime.day, queryTime.hour)
    endtime = datetime.datetime(queryTime.year, queryTime.month, queryTime.day, queryTime.hour, 59, 59)
    print starttime
    print endtime
    client = MongoClient('localhost', 27017)
    db = client["maidou"]  # database name: maidou
    dataCollection = db["data_real"]
    dataHistoryHour = db["data_hour"]
    sns = dataCollection.distinct('sn')
    for sn in sns:
        result = dataCollection.find_one(
            {'sn': sn, 'type': 'analog', 'postTime': {"$lte": endtime}, 'postTime': {"$gte": starttime}},
            sort=[('postTime', -1)])
        print sn
        if not result:
            print "no result"
        else:
            print(result)






