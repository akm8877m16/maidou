# -*- coding:utf-8 -*-
from tornado import gen
from tornado.ioloop import IOLoop
from tornado.iostream import StreamClosedError
from logger import baseLogger
from maidouTcp.messageHandler import messageHandler

class connection(object):
    """
    This class represents single socket connection.
    stream  iostream object
    id      unique string representing the connection device

    """
    def __init__(self, stream, address):
        self._stream = stream
        self._address = address
        self._id = None


    @gen.coroutine
    def run(self):
        """
        Main connection loop. Launches listen on given channel and keeps
        reading data from socket until it is closed.
        """
        connectionConfirm = [0x00, 0x00, 0x00, 0x00, 0x00, 0x06, 0x01, 0x11, 0x00, 0x00, 0x00, 0x01]
        ack = bytearray()
        ack.extend(connectionConfirm)
        yield self._stream.write(ack)

        try:
            while True:
                try:
                    data = yield self._stream.read_bytes(6)
                    baseLogger.info(type(data))
                    ascHeader = map(ord, data)
                    baseLogger.info("Received bytes: %s", ascHeader)
                    if ((ascHeader[0] + ascHeader[1] + ascHeader[2] + ascHeader[3]) == 0):
                        datalength = ascHeader[4] * 256 + ascHeader[5]
                        data = yield self._stream.read_bytes(datalength)
                        ascData = map(ord, data)
                        baseLogger.info("Received bytes: %s", ascData)
                        messageHandler(ascData)
                except StreamClosedError:
                    baseLogger.info("Lost client at host %s", self._address[0])
                    break
                except Exception as e:
                    print(e)
                finally:
                    self._stream.close(exc_info=True)
        except Exception as e:
            if not isinstance(e, gen.Return):
                print("Connection loop has experienced an error.")
            else:
                print('Closing connection loop because socket was closed.')

