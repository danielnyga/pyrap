'''
Created on Oct 2, 2015

@author: nyga
'''
import email
import json
from collections import defaultdict
from hashlib import md5
import mimetypes

import os
import traceback
import urllib.request, urllib.parse, urllib.error

import dnutils
from datetime import datetime
from pyrap.web.utils import storify, Storage
from pyrap.web.webapi import notfound, badrequest, seeother, notmodified

from dnutils import out, Relay, getlogger, RLock, first, ifnone, logs, Lock, Event
from pyrap import locations, threads, web
from pyrap.base import session
from pyrap.clientjs import gen_clientjs
from pyrap.communication import RWTMessage, RWTNotifyOperation, RWTSetOperation, RWTCallOperation, RWTOperation, \
    RWTError, rwterror, parse_msg, RWTListenOperation
from pyrap.constants import APPSTATE, inf
from pyrap.events import FocusEventData
from pyrap.exceptions import ResourceError
from pyrap.handlers import PushServiceHandler, FileUploadServiceHandler
from pyrap.ptypes import Image
from pyrap.sessions import SessionError
from pyrap.themes import Theme, FontMetrics
from pyrap.widgets import Display


class ApplicationManager(object):
    '''
    The :class:`ApplicationManager` implements the interface between the
    webpy server and every PyRAP application.
    
    Every application is initialized by instantiating an :class:`ApplicationManager`
    with the `config` that is specific to the app. It has a :class:`ResourceManager`
    that takes care of all resources that the app makes available for download
    by any client and manages instances of the app in form of :class:`SessionRuntime`s.
    
    It also manages the complete life cycle of an instance for it's taking 
    every single HTTP request that is issued by any client. It is responsible
    for creating new sessions, deleting old ones, initializing the apps, serving
    resources and much more.
    
    '''

    def __init__(self, config):
        self.config = storify(config)
        self.resources = ResourceManager(config.rcpath)
        self.runtimes = Storage()
        self.startup_page = None
        with open(os.path.join(locations.html_loc, 'pyrap.html')) as f:
            self.startup_page = f.read()
        self.log_ = getlogger('/pyrap/main')
        self.httplog = getlogger('/pyrap/http_msgs')

    def _install_theme(self, name, theme):
        '''
        Make all resources of a theme available as static resources.
        '''
        compiled, valuemap = theme.compile()
        # register the images so they are statically available
        for hashid, image in valuemap.images:
            self.resources.registerc('themes/images/%s' % str(hashid), image.mimetype, image.content)
        # make fonts available statically
        for ff in theme.fontfaces:
            if not ff.src.islocal: continue
            fileext = os.path.splitext(ff.src.url)[-1]
            r = self.resources.registerc('themes/fonts/%s%s' % (md5(ff.content).hexdigest(), fileext),
                                         mimetypes.types_map[fileext], ff.content)
            ff.src.url = r.location
        if not name.endswith('.json'): name += '.json'
        self.resources.registerc(name=name, content_type='application/json', content=json.dumps(compiled).encode('utf8'))

    def _setup(self):
        '''
        Initial setup of the application.
        
        This method is called by the :class:`ApplicationRegistry` when an app
        is newly registered. This method also calls the function that is 
        given in the `setup` field of the config. Here, the initial setup of
        an app should happen, which is independent of any instantiation of the app.
        For example, loading static resources that should be server later can be loaded here.
        '''
        self.resources.registerc('rap-client.js', 'application/javascript', gen_clientjs().encode('utf8'))
        with open(os.path.join(locations.rc_loc, 'static', 'image', 'blank.gif'), 'rb') as f:
            self.resources.registerf('resource/static/image/blank.gif', 'image/gif', f)

        if self.config.icon:
            if isinstance(self.config.icon, Image):
                self.icon = self.resources.registerc('resource/static/favicon.ico',
                                                     'image/%s' % self.config.icon.fileext, self.config.icon.content)
            else:
                with open(self.config.icon, 'rb') as f:
                    self.icon = self.resources.registerf('resource/static/favicon.ico', 'image/vnd.microsoft.icon', f)
        # =======================================================================
        # load the theme
        # =======================================================================
        fb_themepath = os.path.join(locations.pyrap_path, 'resource', 'theme', 'default.css')
        self.log_.debug('loading fallback theme from', fb_themepath)
        fallback_theme = Theme('default').load(fb_themepath)
        if self.config.theme is None:
            default_theme = fallback_theme
            self.log_.debug('No default theme given. Taking fallback theme.', fb_themepath)
        else:
            themename = os.path.split(self.config.theme)[-1]
            default_theme = fallback_theme.load(self.config.theme)
            self.log_.debug('Loading theme', themename)
        self.theme = default_theme
        self._install_theme('rap-rwt.theme.Default', self.theme)
        self._install_theme('rap-rwt.theme.Fallback', fallback_theme)
        # call the custom setup of the app
        if self.config.get('setup') is not None:
            self.config.setup(self)

    def _create_session(self):
        '''
        Create a new instance of the application, by instantiating the custom
        application `clazz` in from the config and attaching it to the HTTP session.
        '''
        session.new()
        session.on_kill += lambda *_: self.log_.info('killed', session.id)
        session._PyRAPSession__sessiondata.app = self
        session._PyRAPSession__sessiondata.runtime = SessionRuntime(self, self.config.clazz())

    def handle_request(self, args, query, content):
        '''
        This method is called for every request that is associated with the
        the context of this app. 
        
        :param args:        the "path" part of the request, which is a list of 
                            all constituents of the original path of the HTTP
                            request, without the first element, which is (was) the 
                            application context.
        :param query:       the "query" part of the request. This is a dict
                            holding key/value pairs of the parameters of this request.
        :param content:     in case of a "POST" request, this argument holds the 
                            payload of the request.
        '''
        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        # SERVE RESOURCES - WITHOUT SESSION
        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        if args and args[0] == self.config.rcpath:
            rcname = '/'.join(args[1:])
            return self.resources.serve(rcname)

        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        # LOAD EXISTING OR START NEW SESSION
        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        if session.id is not None:
            if not session.check_validity():  # session id has a wrong format or so.
                raise badrequest('invalid session id %s' % session.id)
            if session.expired:  # session id has expired
                self.log_.debug('session %s has expired' % session.id)
                raise rwterror(RWTError.SESSION_EXPIRED)
        else:
            self._create_session()
        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        # HANDLE SERVICES
        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        if 'servicehandler' in query:
            try:
                handler = session.runtime.servicehandlers.get(query['servicehandler'])
                if handler is not None:
                    return handler.run(web.ctx.environ, content, **query)
                else:
                    raise notfound()
            except SessionError:
                raise rwterror(RWTError.SESSION_EXPIRED)
        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        # LOAD EXISTING OR START NEW SESSION
        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        if web.ctx.method == 'GET':  # always start a new session
            if not args:
                raise seeother('%s/' % self.config.path)
            else:
                if not args[0]:  # no entrypoint is specified, so use the deafult one
                    default = ifnone(self.config.default, first(self.config.entrypoints.keys()))
                    if callable(default):
                        entrypoint = default()
                    elif default:
                        entrypoint = str(default)
                    else:
                        raise Exception('No entrypoint specified')
                else:
                    entrypoint = args[0]
                if entrypoint not in self.config.entrypoints:
                    raise badrequest('No such entrypoint: "%s"' % entrypoint)
                # send the parameterized the start page to the client
                return str(self.startup_page % (self.config.name, self.icon.location if hasattr(self, 'icon') else '', session.id, entrypoint, str(query)))
        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        # HANDLE THE RUNTIME MESSAGES
        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        try:
            if not args or args[0] != 'pyrap':  # this is a pyrap message (modify this in pyrap.html)
                raise notfound()
            session.runtime.relay.acquire()
            msg = parse_msg(content.decode('utf8'))
            self.httplog.debug('>>> ' + str(msg))
            session.runtime.relay.inc()
            # dispatch the event to the respective session
            session.runtime.handle_msg(msg)
            session.runtime.relay.dec()
            session.runtime.relay.wait()
            r = session.runtime.compose_msg()
            smsg = json.dumps(r.json)
            self.httplog.debug('<<< ' + smsg)
            web.header('Content-Type', 'application/json')
            return smsg
        except SessionError:
            raise rwterror(RWTError.SESSION_EXPIRED)
        except:
            traceback.print_exc()
            raise rwterror(RWTError.SERVER_ERROR)
        finally:
            session.runtime.relay.release()
            session.runtime.relay.reset()
        # we should never get here
        raise rwterror(RWTError.SERVER_ERROR)

    def __repr__(self):
        return '<ApplicationManager:%s>' % self.config


class WindowManager(object):
    '''
    A :class:`WindowManager` keeps track of all widgets of an application instance.
    '''

    def __init__(self):
        self._counter = 1
        self._lock = Lock()
        self.registry = {}
        self.children = []
        self._focus = None

    def register(self, wnd, parent):
        with self._lock:
            wid = 'w%d' % self._counter
            wnd.id = wid
            self._counter += 1
            self.registry[wid] = wnd
        return wid

    @property
    def focus(self):
        return self._focus

    @focus.setter
    def focus(self, wnd):
        self._set_focus(wnd)
        session.runtime << RWTSetOperation(self.display.id, {'focusControl': wnd.id})

    def _set_focus(self, wnd):
        if self.focus and self.focus is not wnd: self.focus.on_focus.notify(FocusEventData(wnd, gained=False))
        self._focus = wnd
        if self.focus: self.focus.on_focus.notify(FocusEventData(wnd, gained=True))

    @property
    def display(self):
        return self.children[0]

    def __getitem__(self, wid):
        return self.registry.get(wid)

    def __delitem__(self, wnd):
        if type(wnd) is not str:
            wnd = wnd.id
        del self.registry[wnd]

    def __contains__(self, wnd):
        if type(wnd) is not str:
            wnd = wnd.id
        return wnd in self.registry


class PushService(object):
    '''Helper class for managing server push sessions.'''
    # __lock = RLock()
    # __active = 0

    def __init__(self):
        if not hasattr(session, 'pushservice'):
            session.pushservice = Storage()
        try:
            self._lock = session.pushservice._lock
        except AttributeError:
            self._lock = session.pushservice._lock = RLock()
        try:
            self._active = session.pushservice._active
        except AttributeError:
            self._active = session.pushservice._active = 0

    def start(self):
        with self._lock:
            if 'org.eclipse.rap.pushsession' not in list(session.runtime.servicehandlers.handlers.keys()):
                session.runtime.servicehandlers.register(PushServiceHandler())
            if not self._active:
                session.runtime.activate_push(True)
            self._active += 1

    def stop(self):
        with self._lock:
            self._active -= 1
            if not self._active:
                session.runtime.activate_push(False)
                self.flush()

    def flush(self):
        with session.runtime.relay:
            session.runtime.push.set()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, e, t, tb):
        self.stop()


class SessionRuntime(object):
    '''
    This class represents an instance of an application attached to an HTTP 
    user session. 
    
    It coordinates all communication between the app instance running on the
    server and a client. It manages all UI elements and coordinates the disposition 
    of and response to :class:`RWTMessage`s coming from the client. 
    '''

    def __init__(self, mngr, app):
        self.lock = Lock()
        self.app = app
        self.mngr = mngr
        self.operations = []
        self.headers = {}
        self.windows = WindowManager()
        self.state = APPSTATE.UNINITIALIZED
        # the entrypoint and its arguments
        self.entrypoint = None
        self.entrypoint_args = None
        self.fontmetrics = {}
        self.default_font = None
        self.log_ = getlogger(type(self).__name__)
        self.relay = Relay()
        self.servicehandlers = ServiceHandlerManager()
        self.push = Event()
        self._layout_needed = defaultdict(set)
        self._dolayout = set()

    def put_operation(self, op):
        '''
        Appends a new operation `op` to the buffer of operations.
        
        :param op:    :class:`RWTOperation` instance of the operation to be sent to the client.
        '''
        with self.lock:
            for o in self.operations:
                if type(o) is RWTSetOperation and type(op) is RWTSetOperation:
                    if o.target == op.target:
                        o.args.update(op.args)
                        return
                elif type(o) is RWTListenOperation and type(op) is RWTListenOperation:
                    if o.target == op.target:
                        o.events.update(op.events)
                        return
            self.operations.append(op)

    def put_header(self, key, value):
        '''
        Append a key-value-pair to the current message header.
        '''
        with self.lock:
            self.headers[key] = value

    def __lshift__(self, o):
        if isinstance(o, RWTOperation):
            self.put_operation(o)
        elif type(o) in (list, tuple):
            for op in o:
                self.put_operation(op)

    def flush(self):
        '''
        Empty and return the operations and header buffer.
        '''
        with self.lock:
            ops = self.operations
            self.operations = []
            head = self.headers
            self.headers = {}
            return head, ops

    def compose_msg(self, **headers):
        '''
        Flushes the message buffer and returns an RWTMessage instance ready
        to be serialized and sent to the client.
        '''
        head, operations = self.flush()
        return RWTMessage(head=head, operations=operations)

    def handle_msg(self, msg):
        # first consolidate the operations to avoid duplicate computations
        if msg.head.get('shutdown', False):
            self.headers['cid'] = None
            session.expire()
            return
        ops = []
        for o in msg.operations:
            consolidated = False
            for o_ in ops:
                if type(o_) is RWTSetOperation and type(o) is RWTSetOperation and o_.target == o.target:
                    o_.args.update(o.args)
                    consolidated = True
                    break
                elif type(o_) is RWTNotifyOperation and type(
                        o) is RWTNotifyOperation and o_.target == o.target and o_.event == o.event:
                    o_.args.update(o.args)
                    consolidated = True
                    break
            if not consolidated:
                ops.append(o)
        if len(ops) > 1:
            session.touch()
        for o in sorted(ops, key=lambda o: {RWTSetOperation: 0, RWTNotifyOperation: 1, RWTCallOperation: 2}[type(o)]):
            self.log_.debug('   >>> ' + str(o))
            if isinstance(o, RWTNotifyOperation):
                wnd = self.windows[o.target]
                if wnd is None: continue
                # start a new session thread for processing the notify messages
                t = threads.SessionThread(target=wnd._handle_notify, args=(o,))
                block = Event()
                t.add_handler(dnutils.threads.SUSPEND, block.set)
                t.add_handler(dnutils.threads.TERM, block.set)
                t.start()
                block.wait()
                t.rm_handler(dnutils.threads.TERM, block.set)
                t.rm_handler(dnutils.threads.SUSPEND, block.set)
                # wnd._handle_notify(o)
            elif isinstance(o, RWTSetOperation):
                wnd = self.windows[o.target]
                if wnd is None: continue
                wnd._handle_set(o)
            elif isinstance(o, RWTCallOperation):
                target = self.windows[o.target]
                if target is None: target = self
                target._handle_call(o)
        if self._dolayout:
                while set(self._dolayout):
                    self.windows[self._dolayout.pop()].dolayout(None)

        if self.state == APPSTATE.INITIALIZED:
            self.log_.info('creating shell...')
            self.create_shell()
            self.state = APPSTATE.RUNNING

        if len(msg.operations) == 1 and self.state == APPSTATE.UNINITIALIZED:
            o = msg.operations[0]
            if isinstance(o, RWTCallOperation) and o.target == 'pyrap' and o.method == 'initialize':
                self.log_.info('initializing app...')
                self.initialize_app(o.args.entrypoint, o.args.args)
                self.state = APPSTATE.INITIALIZED

    def create_textsize_measurement_call(self, font, sample):
        hash_ = font
        if type(hash_) is not str:
            hash_ = str(font)
        hash_ += sample
        self.fontmetrics[hash_] = FontMetrics(sample=sample)
        return RWTCallOperation('rwt.client.TextSizeMeasurement', 'measureItems',
                                {'items': [[hash_, sample, font.family, font.size.value, font.bf, font.it, -1, True]]})

    def textsize_estimate(self, font, text, shell=None):
        hash_ = font
        if type(hash_) is not str:
            hash_ = str(font)
        hash_ += text
        if hash_ not in self.fontmetrics or self.fontmetrics[hash_].dimensions == (None, None):
            tm = self.create_textsize_measurement_call(font, text)
            self << tm
            if shell is not None:
                self._layout_needed[hash_].add(shell.id)
            return self.default_font.estimate(text)
        else:
            return self.fontmetrics[hash_].dimensions

    def _handle_call(self, op):
        if op.target == 'rwt.client.TextSizeMeasurement':
            if op.method == 'storeMeasurements':
                # for id_, dims in op.args.results.iteritems():
                for id_, dims in op.args.results.items():
                    self.fontmetrics[id_].dimensions = dims
                    if self.default_font is None:
                        self.default_font = self.fontmetrics[id_]
                    self._dolayout.update(self._layout_needed[id_])
                    del self._layout_needed[id_]

    def initialize_app(self, entrypoint, args):
        self.put_header('url', 'pyrap')
        self.put_header('cid', session.id)
        self.load_fallback_theme('rwt-resources/rap-rwt.theme.Fallback.json')
        self.load_active_theme('rwt-resources/rap-rwt.theme.Default.json')
        for ff in self.mngr.theme.fontfaces:
            self.loadstyle(ff.tocss())
        for font in self.mngr.theme.iterfonts():
            self << self.create_textsize_measurement_call(font, FontMetrics.SAMPLE)
        self.entrypoint = entrypoint
        self.args = args
        if self.mngr.config.requirejs:
            if not isinstance(self.mngr.config.requirejs, list):
                files = [self.mngr.config.requirejs]
            else:
                files = self.mngr.config.requirejs
            for p in files:
                if os.path.isfile(p):
                    self.requirejs(p)
                elif os.path.isdir(p):
                    for f in [x for x in os.listdir(p) if x.endswith('.js')]:
                        self.requirejs(f)
        if self.mngr.config.requirecss:
            if not isinstance(self.mngr.config.requirecss, list):
                files = [self.mngr.config.requirecss]
            else:
                files = self.mngr.config.requirecss
            for p in files:
                if os.path.isfile(p):
                    with open(p) as fi:
                        self.requirecss(fi)
                elif os.path.isdir(p):
                    for f in [x for x in os.listdir(p) if x.endswith('.css')]:
                        with open(f) as fi:
                            self.requirecss(fi)
        self.create_display()

    def ensurejsresources(self, jsfiles, name=None, force=False):
        if jsfiles:
            if not isinstance(jsfiles, list):
                files = [jsfiles]
            else:
                files = jsfiles
            for p in files:
                if os.path.isfile(p):
                    with open(p, encoding='utf8') as fi:
                        self.requirejs(fi, force=force)
                elif os.path.isdir(p):
                    for f in [x for x in os.listdir(p) if x.endswith('.js')]:
                        with open(f, encoding='utf8') as fi:
                            self.requirejs(fi, force=force)
                else:
                    try:
                        resource = session.runtime.mngr.resources.registerc(name, 'text/javascript', p.encode('utf8'), force=force)
                        self << RWTCallOperation('rwt.client.JavaScriptLoader', 'load', {'files': [resource.location]})
                    except:
                        raise Exception('Could not load file', p)

    def requirejs(self, f, force=False):
        resource = session.runtime.mngr.resources.registerf(os.path.basename(f.name), 'text/javascript', f, force=force)
        self << RWTCallOperation('rwt.client.JavaScriptLoader', 'load', {'files': [resource.location]})

    def requirejstag(self, code):
        self << RWTCallOperation('rwt.client.JavaScriptTagLoader', 'load', {'code': code})

    def requirecss(self, f, force=False):
        resource = session.runtime.mngr.resources.registerf(os.path.basename(f.name), 'text/css', f, force=force)
        self << RWTCallOperation('rwt.client.CSSLoader', 'linkCss', {'files': [resource.location]})

    def loadstyle(self, style):
        self << RWTCallOperation('rwt.client.CSSLoader', 'loadCss', {'content': style})

    def executejs(self, code):
        self << RWTCallOperation('rwt.client.JavaScriptExecutor', 'execute', {'content': code})

    def toclipboard(self, text):
        self << RWTCallOperation('rwt.client.CopyToClipboard', 'copy', {'text': text})

    def download(self, name, mimetype, cnt=None, force=False):
        if not hasattr(name, 'read') and os.path.isfile(name):
            with open(name, 'rb') as f:
                resource = session.runtime.mngr.resources.registerf(os.path.basename(name), mimetype, f, force=force)
                resource.download()
        else:
            resource = session.runtime.mngr.resources.registerc(name, mimetype, cnt, force=force)
            resource.download()


    def create_display(self):
        self.display = Display(self.windows)

    def create_shell(self):
        self.mngr.config.entrypoints[self.entrypoint](self.app, **self.args)
        self._initialized = True

    def load_fallback_theme(self, url):
        self << RWTCallOperation('rwt.theme.ThemeStore', 'loadFallbackTheme', {'url': url})

    def load_active_theme(self, url):
        self << RWTCallOperation('rwt.theme.ThemeStore', 'loadActiveTheme', {'url': url})

    def activate_push(self, active):
        self << RWTSetOperation('rwt.client.ServerPush', {'active': active})


class Resource(object):
    '''
    Represents any type of resource that can be requested by a client.
    
    Examples of such resources are static content, such as images part of the 
    GUI, but also dynamically generated content, which is made available
    for downloading for the client.
    
    A resource consists of a 
    :param name:            which is basically "filename" under which the resource
                            is made available. If the name is ``None``, then
                            the resource will be available under its md5 hash.
    :param content_type:    which represents the MIME type and encoding of the
                            of the resource
    :param content:         the raw content of the resource itself, such as the 
                            file content in case of a static file
                            
    The path from where the resource can be accessed from outside can be
    obtained by the `location` property.
    '''

    def __init__(self, registry, name, content_type, content, maxdl=inf):
        self.name = name
        self.content_type = content_type
        self.content = content
        self.registry = registry
        self.md5 = md5(content).hexdigest()
        if name is None:
            self.name = self.md5 + mimetypes.guess_extension(content_type)
        self.last_change = datetime.now()
        self.downloads = 0
        self.max_downloads = maxdl
        self.lock = Lock()

    @property
    def location(self):
        return urllib.parse.quote('%s/%s' % (self.registry.resourcepath, self.name))

    def download(self):
        session.runtime.executejs('window.open("{}", "_blank");'.format(self.location))


class ResourceManager(object):
    '''
    This class maintains all :class:`Resource`s of an application.
    
    New resources can be registered and thus made available to clients.
    '''

    def __init__(self, resourcepath):
        self.resources = {}
        self.resourcepath = resourcepath
        self.lock = Lock()

    def get(self, name):
        return self.resources.get(name)

    def getbycontent(self, content):
        for name in self.resources:
            if self.resources.get(name).content == content:
                return self.resources.get(name)
        return None

    def __getitem__(self, name):
        return self.get(name)

    def registerf(self, name, content_type, stream, force=False, limit=inf, encode=True):
        '''
        Make a file available for download under the given path.
        
        :param name:            the name of the resource under which it will be availble
                                for download to the outside.
        :param content_type:    the MIME type of the resource
        :param stream:          a file-like object that supports read(). Represents the content of the resource.
        :param force:           whether or not an already registered resource
                                under the same name shall be replaced.
        :param limit:           limit the number of downloads to the specified amount.
                                the resource will be unregistered after the
                                specified number of downloads has been reached.
        :param encode:          by default, it is assumed that the file content should be encoded
                                in UTF-8. Set to False for binary files such as videos.
        '''
        c = stream.read()
        if encode:
            if type(c) is str:
                try:
                    c = c.encode('utf8')
                except:
                    print('Could not encode, passing on') #TODO check if this is critical
        return self.registerc(name, content_type, c, force=force, limit=limit)

    def registerc(self, name, content_type, content, force=False, limit=inf):
        '''
        Makes the given content available for download under the given path
        and the given MIME type.
        '''
        with self.lock:
            resource_ = Resource(self, name, content_type, content)
            resource = self.resources.get(resource_.name)
            if resource is not None and (resource_.content_type != resource.content_type or
                                         resource_.md5 != resource.md5) and not force:
                raise ResourceError('A different resource with the name "%s" is already registered.' % name)
            else:
                self.resources[resource_.name] = resource_
                return resource_
            return resource

    def unregister(self, rc):
        if isinstance(rc, str):
            rc = self.get(rc)
        del self.resources[rc.name]

    def serve(self, rcname):
        resource = self.resources.get(rcname)
        if resource is None:
            raise notfound('Resource not available: %s' % rcname)
        with resource.lock:
            resource.downloads += 1
            if resource.downloads >= resource.max_downloads:
                self.unregister(resource)
        cache_date = web.ctx.env.get('HTTP_IF_MODIFIED_SINCE', 0)
        if cache_date:
            # check if the requested resource is younger than in the client's cache
            ttuple = email.utils.parsedate_tz(cache_date)
            cache_date = datetime.utcfromtimestamp(email.utils.mktime_tz(ttuple))
            if cache_date > resource.last_change:
                raise notmodified()
        web.modified(resource.last_change)
        web.header('Content-Type', resource.content_type)
        web.header('Content-Length', len(resource.content))
        return resource.content


class ServiceHandlerManager(object):
    '''
    This class maintains all :class:`Service Handlers` of an application.

    New Service handlers can be registered and thus made available to clients.
    '''

    def __init__(self):
        self.handlers = {}
        self.lock = Lock()
        self.register(FileUploadServiceHandler())

    def get(self, h):
        return self.handlers.get(h, None)

    @property
    def fileuploadhandler(self):
        return self.handlers.get('org.eclipse.rap.fileupload', None)

    def register(self, handler):
        self.handlers[handler.name] = handler
        return handler

    def unregister(self, handler):
        if handler.name in list(self.handlers.keys()):
            del self.handlers[handler.name]
            return True
        return False
