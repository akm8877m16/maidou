# -*- coding:utf-8 -*-
from tornado import gen
from tornado.iostream import StreamClosedError
from messageHandler import messageHandler
import sys
sys.path.append('/home/webapps/maidouProjectDjango')
from celeryTasks.tasks import showMessage

class connection(object):
    """
    This class represents single socket connection.
    stream  iostream object
    id      unique string representing the connection device

    """
    clients = set()    #类变量  必须使用类对象更改，否则就会数据存储不一致，原因在于__dic__

    def __init__(self, stream, address):
        connection.clients.add(self)
        self._stream = stream
        self._address = address
        self._id = None
        print("New Connection from server: " + self._address[0])
        self._stream.set_close_callback(self.on_close)
        self.run()

    @gen.coroutine
    def run(self):
        """
        Main connection loop. Launches listen on given channel and keeps
        reading data from socket until it is closed.
        """
        #connectionConfirm = [0x00, 0x00, 0x00, 0x00, 0x00, 0x06, 0x01, 0x11, 0x00, 0x00, 0x00, 0x01]
        #ack = bytearray()
        #ack.extend(connectionConfirm)
        #yield self._stream.write(ack)
        try:
            while True:
                try:
                    dataHeader = yield self._stream.read_bytes(18)
                    print dataHeader
                    #print(data)
                    ascHeader = map(ord, dataHeader)
                    print ascHeader
                    if ascHeader[0] == 85 and ascHeader[1] == 170:
                        if self._id is None:
                            self._id = self.getSn(ascHeader)
                        datalength = ascHeader[17]
                        data = yield self._stream.read_bytes(datalength)
                        ascData = map(ord, data)
                        print self._id
                        print ascData
                        #yield self._stream.write(data)
                        #messageHandler(self._id,data)
                        fakeTopic = 'E/' + self._id
                        message = ",".join([fakeTopic, " ".join(map(str, ascData))])
                        print message
                        showMessage.delay(message)
                    elif ascHeader[0] == 170 and ascHeader[1] == 170:
                        #control command
                        device_sn_remote = self.getSn(ascHeader)
                        print 'target:  '+ device_sn_remote
                        datalength = ascHeader[17]
                        data = yield self._stream.read_bytes(datalength)
                        commandData = map(ord, data)
                        print commandData
                        target_connection = None
                        for tcp_connection in connection.clients:
                            print tcp_connection._id
                            if tcp_connection._id == device_sn_remote:
                                target_connection = tcp_connection
                                break
                        if target_connection is not None:
                            #command = dataHeader + data
                            print target_connection
                            yield target_connection._stream.write(data)
                except StreamClosedError:
                    print ("Lost client at host %s " + self._address[0])
                    break
                except Exception as e:
                    print(e)
        except Exception as e:
            if not isinstance(e, gen.Return):
                print("Connection loop has experienced an error.")
            else:
                print('Closing connection loop because socket was closed.')
        finally:
            print 'set close'
            self._stream.close(exc_info=True)

    def getSn(self,data):   #data 10进制list
        device_sn = ''
        for i in range(2, 17):
            temp = unichr(data[i])
            device_sn = device_sn + temp

        return device_sn.upper()

    def on_close(self):
        print("Server connection has been closed: " + self._address[0])
        connection.clients.remove(self)