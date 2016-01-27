import pyinotify
from tornado import ioloop, web
from tornado.websocket import WebSocketHandler

clients = []


# we actually don't care about which file has changed
#class CloseWriteHandler(pyinotify.ProcessEvent):
#    def process_IN_CLOSE_WRITE(self, event):
#        print("changed: {}".format(event.pathname))
#        for client in clients:
#            client.write_message('file changed: {}'.format(event.pathname))
def callback(notifier):
    for client in clients:
        client.notify()

wm = pyinotify.WatchManager()
notifier = pyinotify.TornadoAsyncNotifier(
    wm, ioloop.IOLoop.current(), callback, pyinotify.ProcessEvent())
wm.add_watch('/tmp', pyinotify.IN_CLOSE_WRITE)


class GTDSocketHandler(WebSocketHandler):
    def initialize(self, clients):
        self.clients = clients

    def open(self):
        self.clients.append(self)
        print("WebSocket opened")

    def on_message(self, message):
        self.write_message(u"You said: " + message)
        # handle the three messages (request_sync, get_state TAG, put_command)

    def notify(self):
        self.write_message('{"msg": "new_state"}')

    def on_close(self):
        self.clients.remove(self)
        print("WebSocket closed")


def make_app():
    return web.Application([
        (r'/gtd', GTDSocketHandler, {'clients': clients}),
    ])


def run():
    app = make_app()
    app.listen(9001, address='127.0.0.1')
    ioloop.IOLoop.current().start()


if __name__ == '__main__':
    run()
