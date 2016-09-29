'''
Created on Aug 1, 2015

@author: nyga
'''

import web
from web.webapi import notfound
from pyrap import pyraplog
import urlparse 
from pyrap.sessions import Session
from pyrap.utils import RStorage

routes = (
    '/test', 'Test',
    '/(.*)/(.*)', 'RequestDispatcher',
    '/(.*)', 'RequestDispatcher',
)

web.config.debug = False
debug = True

class Test():
    def GET(self, *args, **kwargs):
        return str(session._data)


class PyRAPServer(web.application):

    def run(self, port=8080, *middleware):
        func = self.wsgifunc(*middleware)
        return web.httpserver.runsimple(func, ('0.0.0.0', port))


class ApplicationRegistry(object):
    '''
    Store for all PyRAP application managers.
    
    Every app that is being registered gets an :class:`ApplicationManager` 
    instance that is configured with the respective `config` dict.
    The :class:`ApplicationManager` instance unique for every application
    context, i.e. if you try to register two PyRap apps under the same
    path, PyRAP will raise an Exception.
    '''
    def __init__(self):
        self.apps = {}
        
    def register(self, config):
        from engine import ApplicationManager
        if config.path in self.apps:
            raise Exception('An application with the name "%s" is already running in context path "%s"' % (self.apps[config.path].name, config.path))
        mngr = ApplicationManager(config)
        self.apps[config.path] = mngr
        mngr._setup()
    
    def __getitem__(self, key):
        return self.apps.get(key)
    

_server = PyRAPServer(routes, globals())
session = Session(_server)
_registry = ApplicationRegistry()


def register_app(clazz, path, name, entrypoints, setup=None, default=None, theme=None, icon=None, requirejs=None, rcpath='rwt-resources'):
    '''
    Register a new PyRAP app.
    
    :param clazz:        the main class of the application of which a new instance
                         will be created by PyRAP for every user session.
                         
    :param path:         the path of the URL under which the application will be 
                         accessible on the server.
                         
    :param name:         the name of the app, which will be used as the page 
                         title in the browser.
                         
    :param entrypoints:  a dict that maps the name of an entrypoint to a function
                         that is executed in order to initialize a new session
                         of the app.
                         
    :param theme:        the path to a css file that specifies the theme that
                         is used for the app.
                         
    :param rcpath:       the subpath of the HTTP path under which resources are
                         made accessible.
                         
    :param setup:        pointer to a function that is called for initializing
                         the app. Here loading static contents and registering
                         resources can go, for instance.

    :param icon:         image path under which the application's icon can
                         be found.
    '''
    config = RStorage({'clazz': clazz,
                      'path': path,
                      'name': name,
                      'entrypoints': dict(entrypoints),
                      'theme': theme,
                      'rcpath': rcpath,
                      'setup': setup,
                      'default': default,
                      'icon': icon,
                      'requirejs': requirejs
                      })
    _registry.register(config)

def run(port=8080):
    _server.run(port=port)


class RequestDispatcher(object):
    '''
    The low-level component and interface to the webpy server dispatching
    every HTTP request to the application-specific request handlers. 
    
    Parses every request for its path, query and payload and is then dispatched
    to the respective application runtime.
    '''
    def GET(self, *args, **kwargs):
        return self.POST(*args, **kwargs)
    
    def POST(self, *args, **kwargs):
        # the query of the request
        query = dict([(str(k), str(v)) for k, v in urlparse.parse_qsl(web.ctx.query[1:], keep_blank_values=True)])
        # the payload
        content = web.data()
        # the path
        args = map(str, args)
        # there must be a path, otherwise report a 404 error
        if not args: raise notfound()
        if len(args) > 1: 
            # transform the path into a proper list, in case it comes in 
            # the form ['pyrap/subpath/folder', 'index.html'] 
            tail = args[0].split('/')
            args = tail + [args[-1]]
        app_context = str(args[0]) # first element of the path always identifies the app
        app_runtime = _registry[app_context]
        # if there is an app registered under the given context, dispatch the request
        # to the respective runtime, or report a 404 error, otherwise.
        if app_runtime is None:
            raise notfound()
        else:
            return app_runtime.handle_request(args[1:], query, content)
        

        
        

