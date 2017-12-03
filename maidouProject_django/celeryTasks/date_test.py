# -*- coding:utf-8 -*-
import datetime
# 主程序
if __name__ == '__main__':
    today = datetime.datetime.now()
    queryTime = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    starttime = datetime.datetime(queryTime.year, queryTime.month, queryTime.day, queryTime.hour)
    endtime = datetime.datetime(queryTime.year, queryTime.month, queryTime.day, queryTime.hour, 59, 59)
    print  today
    print queryTime
    print starttime
    print endtime