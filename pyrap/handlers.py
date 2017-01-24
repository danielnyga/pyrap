import StringIO
import cgi

import web

from pyrap import session
from pyrap.threads import Event


class ServiceHandler(object):
    '''
    This class is the superclass for all service handlers.
    '''

    def __init__(self, name):
        self._name = name

    def run(self, *args, **kwargs):
        pass

    @property
    def name(self):
        return self._name


class PushServiceHandler(ServiceHandler):

    def __init__(self):
        ServiceHandler.__init__(self, 'org.eclipse.rap.serverpush')

    def run(self, *args, **kwargs):
        while not session.runtime.push.wait(2): pass
        web.header('Content-Type', 'text/html')
        session.runtime.push.clear()
        return ''


class FileUploadServiceHandler(ServiceHandler):

    def __init__(self, fname):
        ServiceHandler.__init__(self, 'org.eclipse.rap.fileupload')
        self._token = hash(fname)
        self._received = Event()
        self._fname = None
        self._cnt = None
        self._ftype = None

    @property
    def token(self):
        return self._token

    @token.setter
    def token(self, token):
        self._token = token

    @property
    def fname(self):
        return self._fname

    @fname.setter
    def fname(self, fname):
        self._fname = fname

    @property
    def cnt(self):
        return self._cnt

    @cnt.setter
    def cnt(self, cnt):
        self._cnt = cnt

    @property
    def ftype(self):
        return self._ftype

    @ftype.setter
    def ftype(self, ftype):
        self._ftype = ftype

    def run(self, *args, **kwargs):
        if self.token != int(kwargs.get('kwargs').get('token')):
            raise Exception('Token does not match FileuploadServiceHandler token! {} != {}'.format(self.token, int(kwargs.get('kwargs').get('token'))))

        # retrieve file content
        ctype, pdict = cgi.parse_header(args[1].get('CONTENT_TYPE'))
        cnt = args[0]
        s = StringIO.StringIO()
        s.write(cnt)
        s.seek(0)
        multipart = cgi.parse_multipart(s, pdict)
        self._cnt = multipart.get('file')

        # retrieve filename and -type
        parsed = cgi.parse_header(cnt)
        self._fname = parsed[1]['filename'].split('\r\n')[0][1:-1]
        self._ftype = parsed[1]['filename'].split('\r\n')[1].split(': ')[1]

        # notify all that upload is finished
        self._received.set()
        return ''
