# -*- coding:utf-8 -*-
import sys
sys.path.append('/home/webapps/maidouProjectDjango')
from celeryTasks.tasks import showMessage

hexTrans = lambda x: str(ord(x))

def messageHandler(sn, message):
    '''
        handle message  put them to Celery tasks and return corresponding message
    :param sn:
    :param message:
    :return:
    '''
    fakeTopic = 'E/' + sn
    message = ",".join([fakeTopic, " ".join(map(hexTrans, message))])
    print message
    showMessage.delay(message)


