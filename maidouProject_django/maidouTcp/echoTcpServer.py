# -*- coding:utf-8 -*-
import logging
from tornado.ioloop import IOLoop
from tornado import gen
from tornado.iostream import StreamClosedError
from tornado.tcpserver import TCPServer
import tornado.options
from tornado.options import options, define
import signal
import sys
sys.path.append('/home/webapps/maidouProjectDjango')
from maidouTcp.connection import connection

define("port", default=9888, help="TCP port to listen on")

class Server(TCPServer):
    """
        This is a TCP Server that listens to clients and handles their requests
        made using socket

    """
    def __init__(self, *args, **kwargs):
        super(Server, self).__init__(*args, **kwargs)

    @gen.coroutine
    def handle_stream(self, stream, address):
        print('New request has come from our {} buddy...'.format(address))
        connection(stream,address)

    @gen.coroutine
    def shutdown(self):
        print 'server shutdown'
        super(Server, self).stop()
        self.io_loop.stop()



if __name__ == "__main__":
    def sig_handler(sig, frame):
        print('Caught signal: {}'.format(sig))
        IOLoop.current().add_callback_from_signal(server.shutdown)


    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)
    tornado.options.parse_command_line()
    server = Server()
    server.listen(options.port)
    print('Starting the server...')
    IOLoop.current().start()
