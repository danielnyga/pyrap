import io
from io import BytesIO

import multipart
from dnutils.threads import ThreadInterrupt
from multipart.multipart import parse_options_header

from pyrap import web

from pyrap import session
from pyrap.utils import CaseInsensitiveDict


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
        try:
            session.runtime.push.wait()
            web.header('Content-Type', 'text/html')
            session.runtime.push.clear()
        except ThreadInterrupt:
            pass
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
        return token, 'pyrap?servicehandler={}&cid={}&token={}'.format(self.name, session.id, token)

    def run(self, headers, content, **kwargs):
        token = kwargs.get('token')
        if token not in self._files:
            #httpfehler fuer access denied
            raise Exception('Token unknown! {}. Available tokens: {}'.format(token, list(self._files.keys())))
        # retrieve file content
        class PseudoFile:
            def __init__(self):
                self._header = b''
                self.content = b''
                self.name = None
                self.type = None
        f = None
        files = []
        def on_part_begin():
            nonlocal f
            f = PseudoFile()

        def on_part_data(data, start, end):
            f._header += data[:start]
            f.content +=data[start:end]

        def on_part_end():
            tokens = f._header.split(b'\r\n')
            b = tokens[0]
            opts = CaseInsensitiveDict({k.strip(): v.strip() for k, v in [t.split(b':') for t in tokens[1:] if len(t.split(b':')) == 2]})
            del opts[b'content-disposition']
            _, o = parse_options_header(f._header)
            if o:
                o = CaseInsensitiveDict(o)
                opts['content-disposition'] = o
                f.name = o[b'filename'].decode()
            f.type = opts[b'content-type'].decode()
            files.append(f)

        callbacks = {
            'on_part_begin': on_part_begin,
            'on_part_data': on_part_data,
            'on_part_end': on_part_end,
        }
        ctype, pdict = parse_options_header(headers.get('CONTENT_TYPE'))
        stream = BytesIO(content)
        parser = multipart.MultipartParser(pdict[b'boundary'], callbacks=callbacks)
        size = headers.get('content-length')
        while 1:
            to_read = min(size, 1024 * 1024) if size is not None else 1024
            chunk = stream.read(to_read)
            if size is not None:
                size -= len(chunk)
            parser.write(chunk)
            if len(chunk) != to_read: break
        stream.close()
        self._files[token] = [{'filename': f.name, 'filetype': f.type, 'filecontent': f.content} for f in files]
        return ''
