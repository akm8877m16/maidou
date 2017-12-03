# -*- coding:utf-8 -*-
__author__ = 'wenhao Yin <akm8877m16@126.com>'
__copyright__ = 'Copyright 2016 wenhao'

'''
    mqtt client: receive mqtt messages and put them to rabbitmq

'''
import logging
import socket
import sys
import time
import paho.mqtt.client as mqtt
from tornado.options import options, define
import pika

sys.path.append('/home/webapps/maidouProject')

from CeleryTasks.tasks import showMessage

define("mqttPort", default=1883, help="mqtt port")
define("mqttServer", default="118.190.202.155")
logger = logging.getLogger(__name__)

hexTrans = lambda x: str(ord(x))


def on_connect(client, userdata, flags, rc):
    """
    Handle connections (or failures) to the broker.
    This is called after the client has received a CONNACK message
    from the broker in response to calling connect().

    The result_code is one of;
    0: Success
    1: Refused - unacceptable protocol version
    2: Refused - identifier rejected
    3: Refused - server unavailable
    4: Refused - bad user name or password (MQTT v3.1 broker only)
    5: Refused - not authorised (MQTT v3.1 broker only)
    """
    if rc == 0:
        logging.info("Connected to cloud broker, subscribing to topics...")
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        # 这里把需要订阅的消息取出进行订阅
        mqttc.subscribe('E/#')
	mqttc.subscribe('M/#')
        mqttc.publish(lwt, 'LWTALIVE', qos=0, retain=True)

    elif rc == 1:
        logging.info("Connection refused - unacceptable protocol version")
    elif rc == 2:
        logging.info("Connection refused - identifier rejected")
    elif rc == 3:
        logging.info("Connection refused - server unavailable")
    elif rc == 4:
        logging.info("Connection refused - bad user name or password")
    elif rc == 5:
        logging.info("Connection refused - not authorised")
    else:
        logging.warning("Connection failed - result code %d" % (rc))


def on_disconnect(client, userdata, rc):
    """
    Handle disconnections from the broker
    """
    if rc == 0:
        logging.warning("Clean disconnection from broker")
    else:
        logging.warning("Broker connection lost. Will attempt to reconnect in 5s...")
        time.sleep(5)


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    """
    Message received from the broker
    将消息加入rabbitmq
    """
    logging.info("Message received on %s: %s" % (msg.topic, repr(msg.payload)))
    message = ",".join([msg.topic, " ".join(map(hexTrans, msg.payload))])
    logging.info(message)

    #showMessage.delay(message)


# 主程序
if __name__ == '__main__':
    options.parse_command_line()
    mqttHost = options.mqttServer
    mqttPort = options.mqttPort
    lwt = 'mqtt start'
    mqttc = mqtt.Client()
    logging.info("Attempting connection to MQTT broker %s:%d..." % (mqttHost, int(mqttPort)))

    mqttc.on_connect = on_connect
    mqttc.on_message = on_message
    mqttc.on_disconnect = on_disconnect

    # 建立连接
    try:
        mqttc.connect(mqttHost, int(mqttPort))
    except Exception, e:
        logging.error("Cannot connect to MQTT broker at %s:%d: %s" % (mqttHost, int(mqttPort), str(e)))
        sys.exit(2)
    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        mqttc.loop_forever()

    except socket.error:
        logging.warning("MQTT server disconnected; sleeping")
        time.sleep(5)
    except (KeyboardInterrupt, SystemExit):
        logging.warning("Disconnecting from MQTT broker...")
        mqttc.loop_stop()
        mqttc.disconnect()
    except Exception as e:
        logging.error(e)
