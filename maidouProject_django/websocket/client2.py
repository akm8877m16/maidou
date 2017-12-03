import websocket
import time
import sys
import thread
import datetime
def on_message(ws, message):
    print(message)


def on_error(ws, error):
    print(error)


def on_close(ws):
    print("### closed ###")


def on_open(ws):
    print "client on open"
    timenow = datetime.datetime.utcnow()
    timestamp_now = time.mktime(timenow.timetuple())
    print timenow
    print  timestamp_now
    def run(*args):
        for i in range(3):
            time.sleep(2)
            ws.send("selfCheck,A020A632C8EF,"+str(timestamp_now))
        time.sleep(5)
        ws.close()
        print("thread terminating...")

    thread.start_new_thread(run, ())


if __name__ == "__main__":
    websocket.enableTrace(True)
    if len(sys.argv) < 2:
        host = "ws://localhost:8888/maidou/websocket"
    else:
        host = sys.argv[1]
    ws = websocket.WebSocketApp(host,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.on_open = on_open
    ws.run_forever()
