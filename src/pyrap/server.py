'''
The pyRAP WSGI server implementation

We take as a basis the original from web.py and modify it where necessary.
'''
import string
import sys
import urllib

from dnutils import getlogger, out

debug = True

printables = set(string.printable)

def runbasic(func, server_address=("0.0.0.0", 8080)):
    '''
    Runs a simple HTTP server hosting WSGI app `func`. The directory `static/`
    is hosted statically.

    Based on [WsgiServer][ws] from [Colin Stewart][cs].

    [ws]: http://www.owlfish.com/software/wsgiutils/documentation/wsgi-server-api.html
    [cs]: http://www.owlfish.com/
    '''
    # Copyright (c) 2004 Colin Stewart (http://www.owlfish.com/)
    # Modified somewhat for simplicity
    # Used under the modified BSD license:
    # http://www.xfree86.org/3.3.6/COPYRIGHT2.html#5
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import socketserver as SocketServer
    import socket, errno
    import traceback

    class WSGIHandler(BaseHTTPRequestHandler):

        def run_wsgi_app(self):
            protocol, host, path, parameters, query, fragment = urllib.parse.urlparse('http://dummyhost%s' % self.path)

            # we only use path, query
            env = {'wsgi.version': (1, 0)
                , 'wsgi.url_scheme': 'http'
                , 'wsgi.input': self.rfile
                , 'wsgi.errors': sys.stderr
                , 'wsgi.multithread': 1
                , 'wsgi.multiprocess': 0
                , 'wsgi.run_once': 0
                , 'REQUEST_METHOD': self.command
                , 'REQUEST_URI': self.path
                , 'PATH_INFO': path
                , 'QUERY_STRING': query
                , 'CONTENT_TYPE': self.headers.get('Content-Type', '')
                , 'CONTENT_LENGTH': self.headers.get('Content-Length', '')
                , 'REMOTE_ADDR': self.client_address[0]
                , 'SERVER_NAME': self.server.server_address[0]
                , 'SERVER_PORT': str(self.server.server_address[1])
                , 'SERVER_PROTOCOL': self.request_version
            }

            for http_header, http_value in self.headers.items():
                env['HTTP_%s' % http_header.replace('-', '_').upper()] = http_value

            # Setup the state
            self.wsgi_sent_headers = 0
            self.wsgi_headers = []

            try:
                # We have the environment, now invoke the application
                result = self.server.app(env, self.wsgi_start_response)
                try:
                    try:
                        for data in result:
                            if data:
                                self.wsgi_write_data(data)
                    finally:
                        if hasattr(result, 'close'):
                            result.close()
                except socket.error as socket_err:
                    # Catch common network errors and suppress them
                    if socket_err.args[0] in (errno.ECONNABORTED, errno.EPIPE): return
                except socket.timeout as socket_timeout:
                    return
            except:
                print >> debug, traceback.format_exc(),

            if not self.wsgi_sent_headers:
                # We must write out something!
                self.wsgi_write_data(" ".encode('utf8'))
            return

        do_POST = run_wsgi_app
        do_PUT = run_wsgi_app
        do_DELETE = run_wsgi_app

        def log_message(self, format, *args):
            msg = ''.join([c for c in ''.join(' - '.join(map(str, args))) if c in printables])
            getlogger('/pyrap/http').debug('[%s] %s' % (self.client_address[0], msg))

        def do_GET(self):
            # if self.path.startswith('/static/'):
            #     SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)
            # else:
            self.run_wsgi_app()

        def wsgi_start_response(self, response_status, response_headers, exc_info=None):
            if self.wsgi_sent_headers:
                raise Exception("Headers already sent and start_response called again!")
            # Should really take a copy to avoid changes in the application....
            self.wsgi_headers = response_status, response_headers
            return self.wsgi_write_data

        def wsgi_write_data(self, data):
            if not self.wsgi_sent_headers:
                status, headers = self.wsgi_headers
                # Need to send header prior to data
                status_code = status[:status.find(' ')]
                status_msg = status[status.find(' ') + 1:]
                self.send_response(int(status_code), status_msg)
                for header, value in headers:
                    self.send_header(header, value)
                self.end_headers()
                self.wsgi_sent_headers = 1
            # Send the data
            self.wfile.write(data)


    class WSGIServer(SocketServer.ThreadingMixIn, HTTPServer):

        def __init__(self, func, server_address):
            HTTPServer.__init__(self, server_address, WSGIHandler)
            self.app = func
            self.serverShuttingDown = 0

    getlogger('/pyrap/main').info("listening on %s, port %d" % server_address)
    WSGIServer(func, server_address).serve_forever()