import io
import cgi

import web

from pyrap import session


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

    def __init__(self):
        ServiceHandler.__init__(self, 'org.eclipse.rap.fileupload')
        self._files = {}

    @property
    def files(self):
        return self._files

    def accept(self, fnames):
        token = str(hash(''.join(fnames)))
        self._files[token] = None
        return token, 'pyrap?servicehandler={}&cid={}&token={}'.format(self.name, session.session_id, token)

    def run(self, *args, **kwargs):
        token = kwargs.get('kwargs').get('token')
        if token not in self._files:
            #httpfehler fuer access denied
            raise Exception('Token unknown! {}. Available tokens: {}'.format(token, list(self._files.keys())))

        # retrieve file content
        ctype, pdict = cgi.parse_header(args[1].get('CONTENT_TYPE'))
        cnt = args[0]
        s = io.StringIO()
        s.write(cnt)
        s.seek(0)
        multipart = cgi.parse_multipart(s, pdict)
        fargs = [x for x in cnt.split(pdict['boundary']) if 'Content-Disposition' in x]
        fcontents = multipart.get('file')
        files = list(zip(fargs, fcontents))

        tfiles = []
        for f in files:
            # retrieve filename and -type
            parsed = cgi.parse_header(f[0])
            fname = parsed[1]['filename'].split('\r\n')[0][1:-1]
            ftype = parsed[1]['filename'].split('\r\n')[1].split(': ')[1]
            tfiles.append({'filename': fname, 'filetype': ftype, 'filecontent': f[1]})
        self._files[token] = tfiles
        return ''
