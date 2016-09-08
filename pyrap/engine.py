'''
Created on Oct 2, 2015

@author: nyga
'''
from threading import Lock
import web
from pyrap import pyraplog, locations
from web.webapi import notfound, badrequest, seeother
from pyrap.communication import RWTMessage, RWTCreateOperation, \
    RWTNotifyOperation, RWTSetOperation, RWTCallOperation, RWTOperation,\
    RWTError, rwterror, parse_msg
from pyrap.widgets import Display, Label, Shell
import pyrap
from pyrap.types import BitMask, Color
from web.utils import storify, Storage
import os
from pyrap.clientjs import gen_clientjs
from pyrap.themes import Theme, FontMetrics
from pyrap.base import session
import json
from web.session import SessionExpired
import traceback
from pyrap.utils import ifnone, out
import urllib
from pyrap.constants import APPSTATE
from pyrap.events import FocusEventData
from pyrap.layout import CellLayout
import md5
from pyrap.exceptions import ResourceError
from datetime import datetime
from pyrap.pyraplog import getlogger


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
        self.log_ = getlogger(self.__class__.__name__)
        
    
    def _install_theme(self, name, theme):
        compiled, valuemap = theme.compile()
        # register the images so they are statically available
        for hashid, image in valuemap.images:
            self.resources.registerc('themes/images/%s' % str(hashid), 'image/%s' % image.fileext, image.content)
        if not name.endswith('.json'): name += '.json'
        self.resources.registerc(name=name, content_type='application/json', content=json.dumps(compiled))
        
    
    def _setup(self):
        '''
        Initial setup of the application.
        
        This method is called by the :class:`ApplicationRegistry` when an app
        is newly registered. This method also calls the function that is 
        given in the `setup` field of the config. Here, the initial setup of
        an app should happen, which is independent of any instantiation of the app.
        For example, loading static resources that should be server later can be loaded here.
        '''
        self.resources.registerc('rap-client.js', 'application/javascript', gen_clientjs())
        self.resources.registerf('resource/static/image/blank.gif', 'image/gif', os.path.join(locations.rc_loc, 'static', 'image', 'blank.gif'))
        themepath = ifnone(self.config.theme, os.path.join(locations.css_loc, 'default.css')) 
        self.log_.debug('loading theme', themepath)
        self.theme = Theme(themepath).load(themepath)
        self._install_theme('rap-rwt.theme.Default', self.theme)
        self._install_theme('rap-rwt.theme.Fallback', self.theme)
        # call the custom setup of the app
        if self.config.get('setup') is not None: 
            self.config.setup(self)
        
        
    def _create_session(self):
        '''
        Create a new instance of the application, by instantiating the custom
        application `clazz` in from the config and attaching it to the HTTP session.
        '''
        session.create()
        session.on_kill += lambda: out('kill session', session.session_id)
        session.app = self
        session.runtime = SessionRuntime(session.session_id, self, self.config.clazz())
        session._save()
        
        
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
        if not session.valid_id: # session id has a wrong format or so.
            raise badrequest('invalid session id %s' % session.session_id)
        if session.expired: # session id has expired
            self.log_.debug('session %s has expired' % session.session_id)
            raise rwterror(RWTError.SESSION_EXPIRED)
        
        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        # SERVE RESOURCES
        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        if args and args[0] == self.config.rcpath:
            rcname = '/'.join(args[1:])
            resource = self.resources.get(rcname)
            if resource is None:
                raise notfound('Resource not available: %s' % rcname)
            web.modified(resource.last_change)
            web.header('Content-Type', resource.content_type)
            web.header('Content-Length', len(resource.content))
            return resource.content
        
        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        # START NEW SESSION
        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        sid = session.session_id
        if sid is None and web.ctx.method == 'GET': # always start a new sessionand sessionid not in self.sessions:
            if not args: 
                raise seeother('%s/' % self.config.path)
            else:
                if not args[0]: # no entrypoint is specified, so use the deafult one
                    default = self.config.default
                    if callable(default): entrypoint = default()
                    elif default: entrypoint = str(default)
                    else: raise Exception('No entrypoint specified')
                else:
                    entrypoint = args[0]
                if entrypoint not in self.config.entrypoints:
                    raise badrequest('No such entrypoint: "%s"' % entrypoint)
                # send the parameterized the start page to the client
                return str(self.startup_page % (self.config.name, entrypoint, str(query)))
            
        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        # HANDLE THE RUNTIME MESSAGES
        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        try:
            if args and args[0] == 'pyrap': # this is a pyrap message (modify this in pyrap.html)
                if sid is None : self._create_session()
                msg = parse_msg(content)
                self.log_.debug('>>> ' + str(msg))
                # dispatch the event to the respective session
                session.runtime.handle_msg(msg)
                r = session.runtime.compose_msg()
                smsg = json.dumps(r.json)
                return smsg
        except SessionExpired:
            raise rwterror(RWTError.SESSION_EXPIRED)
        except:
            traceback.print_exc()
            raise rwterror(RWTError.SERVER_ERROR)
        # we should never get here
        raise rwterror(RWTError.SERVER_ERROR)



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
        session.runtime << RWTSetOperation(self.display.id, {'focusControl': wnd.id})
        
    def _set_focus(self, wnd):
        if self.focus and self.focus is not wnd: self.focus.on_focus.notify(FocusEventData(gained=False))
        self._focus = wnd
        if self.focus: self.focus.on_focus.notify(FocusEventData(gained=True))
        
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
    
    
class SessionRuntime(object):
    '''
    This class represents an instance of an application attached to an HTTP 
    user session. 
    
    It coordinates all communication between the app instance running on the
    server and a client. It manages all UI elements and coordinates the disposition 
    of and response to :class:`RWTMessage`s coming from the client. 
    '''
    def __init__(self, sessionid, mngr, app):
        self.id = sessionid
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
        self.log_ = getlogger(type(self).__name__)
        
        
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
        head, operations  = self.flush() 
        return RWTMessage(head=head, operations=operations)
    
    
    def handle_msg(self, msg):
        # first consolidate the operations to avoid duplicate computations
        ops = []
        for o in msg.operations:
            consolidated = False
            for o_ in ops:
                if type(o_) is RWTSetOperation and type(o) is RWTSetOperation and o_.target == o.target:
                    o_.args.update(o.args)
                    consolidated = True
                    break
                elif type(o_) is RWTNotifyOperation and type(o) is RWTNotifyOperation and o_.target == o.target and o_.event == o.event:
                    o_.args.update(o.args)
                    consolidated = True
                    break
            if not consolidated:
                ops.append(o)
                    
        for o in ops:
            self.log_.info('   >>> ' + str(o))
            if isinstance(o, RWTNotifyOperation):
                wnd = self.windows[o.target]
                if wnd is None: continue
                wnd._handle_notify(o)
            elif isinstance(o, RWTSetOperation):
                wnd = self.windows[o.target]
                if wnd is None: continue
                wnd._handle_set(o)
            elif isinstance(o, RWTCallOperation):
                self._handle_call(o)
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
    
    @staticmethod
    def create_textsize_measurement_call(font, sample):
        return RWTCallOperation('rwt.client.TextSizeMeasurement', 'measureItems', {'items': [[str(font), sample, font.family, font.size.value, font.bf, font.it, -1, True]]})
    
    
    def textsize_estimate(self, font, text):
        if type(font) is not str: font = str(font)
        return self.fontmetrics[font].estimate(text)
    
    def _handle_call(self, op):
        if op.target == 'rwt.client.TextSizeMeasurement':
            if op.method == 'storeMeasurements':
                for id_, dims in op.args.results.iteritems():
                    self.fontmetrics[id_] = FontMetrics(FontMetrics.SAMPLE, dims)
                    
    
    def initialize_app(self, entrypoint, args):
        self.put_header('url', 'pyrap')
        self.put_header('cid', pyrap.session.session_id)
        for font in self.mngr.theme.iterfonts():
            self << SessionRuntime.create_textsize_measurement_call(font, FontMetrics.SAMPLE)
        self.entrypoint = entrypoint
        self.args = args
        self.create_display()
    
    
    def create_display(self):
        self.display = Display(self.windows)
    
    def create_shell(self):
        self.shell = Shell(self.display, maximized=True)
        self.shell.layout = CellLayout()
        self.shell.layout.valign = 'fill'
        self.shell.layout.halign = 'fill'
        self.shell.on_resize += self.onresize_shell
        self.shell.bounds = self.display.bounds
        self.shell.bg = Color('green')
        self.mngr.config.entrypoints[self.entrypoint](self.app, self.shell, **self.args)
        self.onresize_shell()
        self._initialized = True
        
    
    def install_fallback_theme(self):
        self << RWTCallOperation('rwt.theme.ThemeStore', 'loadFallbackTheme', {'url': 'rwt-resources/rap-rwt.theme.Fallback.json'})
        
    def install_default_theme(self):
        self << RWTCallOperation('rwt.theme.ThemeStore', 'loadDefaultTheme', {'url': 'rwt-resources/rap-rwt.theme.Default.json'})
        
        
    def onresize_shell(self):
        self.shell.layout.cell_minwidth = self.shell.bounds[2]
        self.shell.layout.cell_maxwidth = self.shell.bounds[2]
        self.shell.layout.cell_minheight = self.shell.bounds[3]
        self.shell.layout.cell_maxheight = self.shell.bounds[3]
        self.shell.dolayout()



class Resource(object):
    '''
    Represents any type of resource that can be requested by a client.
    
    Examples of such resources are static content, such as images part of the 
    GUI, but also dynamically generated content, which is made available
    for downloading for the client.
    
    A resource consists of a 
    :param name:            which is basically "filename" under which the resource
                            is made available
    :param content_type:    which represents the MIME type and encoding of the
                            of the resource
    :param content:         the raw content of the resource itself, such as the 
                            file content in case of a static file
                            
    The path from where the resource can be accessed from outside can be
    obtained by the `location` property.
    '''
    
    def __init__(self, registry, name, content_type, content):
        self.name = name
        self.content_type = content_type
        self.content = content
        self.registry = registry
        self.md5 = md5.new(content).digest()
        self.last_change = datetime.now()

    @property
    def location(self):
        return urllib.quote('%s/%s' % (self.registry.resourcepath, self.name))


    

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


    def __getitem__(self, name):
        return self.get(name)

    def registerf(self, name, content_type, filepath, force=False):
        with open(filepath) as f:
            self.registerc(name, content_type, f.read(), force=force)
        
        
    def registerc(self, name, content_type, content, force=False):
        with self.lock:
            resource = self.resources.get(name)
            resource_ = Resource(self, name, content_type, content)
            if resource is not None and (resource_.content_type != resource.content_type or \
                resource_.md5 != resource.md5) and not force:
                raise ResourceError('A different resource with the name "%s" is already registered.')
            else:
                self.resources[name] = resource_
                return resource_
            return resource
        
        

    
