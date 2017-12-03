# -*- coding:utf-8 -*-
import logging
from tornado.ioloop import IOLoop
from tornado import gen
from tornado.iostream import StreamClosedError
from tornado.tcpserver import TCPServer
from tornado.options import options, define
from maidouTcp.connection import connection
import signal

define("port", default=9888, help="TCP port to listen on")
logger = logging.getLogger(__name__)

def hexString(x): return format(x, '02x')

class Server(TCPServer):
    """
        This is a TCP Server that listens to clients and handles their requests
        made using socket

    """
    def __init__(self, *args, **kwargs):
        super(Server, self).__init__(*args, **kwargs)
        self._connections = []


    @gen.coroutine
    def handle_stream(self, stream, address):
        print('New request has come from our {} buddy...'.format(address))
        deviceConnection = connection(stream,address)
        self._connections.append(connection)
        yield connection.run()
        self._connections.remove(connection)

    @gen.coroutine
    def shutdown(self):
        super(Server, self).stop()
        self.io_loop.stop()



if __name__ == "__main__":
    def sig_handler(sig, frame):
        print('Caught signal: {}'.format(sig))
        IOLoop.current().add_callback_from_signal(server.shutdown)


    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    server = Server()
    server.listen(5567)
    IOLoop.current().spawn_callback(server.subscribe, 'updates')

    print('Starting the server...')
    asyncio.get_event_loop().run_forever()
    print('Server has shut down.')