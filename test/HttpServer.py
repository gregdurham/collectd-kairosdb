import http.server
import socketserver
import logging
import threading


class HttpServer:
    """
        Test HTTP server
    """

    def __init__(self, port):
        self.handler = ServerHandler
        socketserver.TCPServer.allow_reuse_address = True  # Do not hold on to the port when done with resource
        self.httpd = socketserver.TCPServer(("", port), self.handler)
        self.thread = threading.Thread(target=self.thread)
        self.thread.setDaemon(True)
        self.thread.start()

    def thread(self):
        self.httpd.serve_forever()

    def get_data(self):
        return self.handler.get_data()

    def shutdown(self):
        self.httpd.shutdown()
        self.thread.join(timeout=3)
        logging.warning("=========== HTTP Server Shut Down ============")


class ServerHandler(http.server.SimpleHTTPRequestHandler):
    data = None

    def do_GET(self):
        http.server.SimpleHTTPRequestHandler.do_GET(self)

    # noinspection PyPep8Naming
    def do_POST(self):
        ServerHandler.data = self.rfile.read(int(self.headers.get('Content-Length')))
        logging.warning(ServerHandler.data)
        self.send_response(200)

    @staticmethod
    def get_data():
        d = ServerHandler.data
        ServerHandler.data = None
        return d


if __name__ == '__main__':
    HttpServer(8999)
