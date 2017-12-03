# -*- coding:utf-8 -*-

from maidouTcp.logger import baseLogger

def messageHandler(message):
    '''
        handle message  put them to Celery tasks and return corresponding message
    :param message:
    :return:
    '''
    #功能码
    fucType = message[1]
    if fucType == 18:
        deviceId = " ".join(map(str,message[4:]))
        baseLogger.info("deviceId received: %s",deviceId)
        return

