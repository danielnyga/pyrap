'''
Created on Oct 27, 2015

@author: nyga
'''
import web
import threading
import time
from web.utils import Storage
from copy import deepcopy
import urlparse
from web import utils
from pyrap.ptypes import Event
from pyrap.utils import RStorage
from pyrap import threads


class SessionKilled(Event):
    def _notify(self, listener, data):
        listener(data)
        

class Session(web.session.Session):
    '''
    Low-level implementation an HTTP user session.
    '''
    def __init__(self, server):
        web.session.Session.__init__(self, server, DictStore(), initializer=self._initialize_session)
        
    def _initialize_session(self):
        self.on_kill = SessionKilled()
        self.creation_time = time.time()
        self.ip = web.ctx.ip
        self.data = Storage()

        
    def _processor(self, handler):
        """Application processor to setup session for every request"""
        self._cleanup()
        self.client = Storage()
        useragent = web.ctx.env.get('HTTP_USER_AGENT')
        if useragent:
            self.useragent = Storage()
            self.useragent.str = useragent.encode('utf8')
            self.useragent.mobile = 'mobile' in self.useragent.str.lower()
        self.request = Storage()
        self.request.method = web.ctx.method
        self.request.query = dict([(str(k), str(v)) for k, v in urlparse.parse_qsl(web.ctx.query[1:], keep_blank_values=True)])
        self.session_id = self.request.query.get('cid', None)
        self.load()
        try:
            return handler()
        finally: pass
        
    def _save(self):
        self.store[self.session_id] = dict(self._data)

    def load(self):
        """Load the session from the store, by the id"""
        if self.session_id not in self.store: return
        d = self.store[self.session_id]
        self.update(d)
 
 
    def create(self):
        '''
        Create a new session
        '''
        self.session_id = self._generate_session_id()
        if self._initializer:
            if isinstance(self._initializer, dict):
                self.update(deepcopy(self._initializer))
            elif hasattr(self._initializer, '__call__'):
                self._initializer()

        
    @property
    def valid_id(self):
        if self.session_id:
            return utils.re_compile('^[0-9a-fA-F]+$').match(self.session_id)
        return True
    
    @property
    def valid_ip(self):
        if self.session_id and self.get('ip', None) is not None:
            return self.get('ip', None) != web.ctx.ip
        return True
        
    @property
    def expired(self):
        if self.session_id:
            if self.session_id not in self.store: return True
            if self.get('creation_time'):
                now = time.time()
                return self.get('_expired') or now - self.creation_time > self._config.timeout
        return False
        
    def _setcookie(self, session_id, expires='', **kw): raise
    
    def expire(self):
        """Expire the session, make it no longer available"""
        if self.session_id in self.store:
            del self.store[self.session_id]
        self._expired = True
        
        
class DictStore(web.session.Store):
    """Base class for session stores"""

    def __init__(self):
        self._dict = {}
        self._lock = threading.Lock()

    def __contains__(self, key):
        with self._lock:
            return key in self._dict

    def __getitem__(self, key):
        with self._lock:
            return self._dict.get(key)

    def __setitem__(self, key, value):
        with self._lock:
            self._dict[key] = value
            
    def __delitem__(self, key):
        with self._lock:
            del self._dict[key]

    def cleanup(self, timeout):
        now = time.time()
        for session_id, content in dict(self._dict).iteritems():
            if 'creation_time' not in content or (now - content['creation_time']) > timeout:
                if 'on_kill' in content:
                    content['on_kill'].notify(RStorage(content))
                if session_id in self:
                    del self[session_id]
                # clean up the SessionThreads belonging to this session
                for _, t in threads.iteractive():
                    if isinstance(t, threads.SessionThread) and t._session_id == session_id:
                        t.interrupt()
                        