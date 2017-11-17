'''
Created on Oct 27, 2015

@author: nyga
'''
import datetime
import re
from _sha1 import sha1
from pprint import pprint

import os

from dnutils.threads import current_thread

import web
import time

from dnutils import Lock, out, RLock, ifnone
import dnutils
from pyrap import threads
from web.py3helpers import PY2
from web.utils import Storage
from copy import deepcopy
import urllib.parse
from web import utils
from pyrap.ptypes import Event
from pyrap.utils import RStorage

_defconf = utils.storage({
    'cookie_name': 'webpy_session_id',
    'cookie_domain': None,
    'cookie_path' : None,
    'timeout': 86400, #24 * 60 * 60, # 24 hours in seconds
    'ignore_expiry': True,
    'ignore_change_ip': True,
    'secret_key': 'fLjUfxqXtfNoIldA0A0J',
    'expired_message': 'Session expired',
    'httponly': True,
    'secure': False
})


_idregex = re.compile('^[0-9a-fA-F]+$')


class SessionKilled(Event):
    def _notify(self, listener, data):
        listener(data)


class PyRAPSession:
    '''
    Session management for pyRAP.
    '''

    def __init__(self, server, config=None):
        server.add_processor(self._prepare_thread)
        self.__lock = RLock()
        self.__sessions = {}
        self.__locals = web.threadeddict()
        self._config = ifnone(config, _defconf)

    def _prepare_thread(self, handler):
        out('preparing thread...')
        request = Storage()
        request.query = {str(k): str(v) for k, v in urllib.parse.parse_qsl(web.ctx.query[1:], keep_blank_values=True)}
        cookie_name = self._config.cookie_name
        sid = web.cookies().get(cookie_name)

        # protection against session_id tampering
        if sid and not PyRAPSession.check_id(sid):
            sid = None

        # get the session or create a new one if necessary
        if sid in self.__sessions:
            self.__locals['session_id'] = sid

        # self.__locals['ip'] = web.ctx.ip
        out('thread', current_thread().name, 'successfully prepared (session id %s)' % self.id)
        return handler()

    def new(self):
        sid = self.__generate_session_id()
        self.__locals['session_id'] = sid
        self.__init_session(sid)
        cookie_name = self._config.cookie_name
        cookie_domain = self._config.cookie_domain
        cookie_path = self._config.cookie_path
        httponly = self._config.httponly
        secure = self._config.secure
        web.setcookie(cookie_name, sid, expires='', domain=cookie_domain, httponly=httponly,
                      secure=secure, path=cookie_path)

    @property
    def _threads(self):
        return self.__sessiondata.threads

    def __init_session(self, sid):
        store = Storage()
        self.__sessions[sid] = store
        store.on_kill = SessionKilled()
        store.ip = web.ctx.ip
        store.expired = False
        store.ctime = datetime.datetime.now()

    @property
    def __sessiondata(self):
        return self.__sessions[self.__locals['session_id']]

    def __generate_session_id(self):
        """Generate a random id for session"""
        while True:
            rand = os.urandom(16)
            now = time.time()
            secret_key = self._config.secret_key
            hashable = "%s%s%s%s" %(rand, now, utils.safestr(web.ctx.ip), secret_key)
            sid = sha1(hashable if PY2 else hashable.encode('utf-8')) #TODO maybe a better way to deal with this, without using an if-statement
            sid = sid.hexdigest()
            if sid not in self.__sessions:
                break
        return sid

    @property
    def on_kill(self):
        return self.__sessiondata.on_kill

    @on_kill.setter
    def on_kill(self, e):
        if not isinstance(e, SessionKilled):
            raise ValueError('on_kill event cannot be set to value %s' % str(e))
        self.__sessiondata.on_kill = e

    @property
    def ctime(self):
        return self.__sessiondata.ctime

    @property
    def runtime(self):
        return self.__sessiondata.runtime

    @property
    def id(self):
        return self.__locals.get('session_id')

    @property
    def ip(self):
        return self.__sessiondata.ip

    def check_validity(self):
        return PyRAPSession.check_id(self.id) and self.check_ip()

    @staticmethod
    def check_id(sid):
        return _idregex.match(sid)

    def check_ip(self):
        return self.ip == web.ctx.ip or self._config.ignore_change_ip

    @property
    def expired(self):
        if self.id not in self.__sessions or self.__sessiondata.expired:
            return True
        if self.ctime:
            now = datetime.datetime.now()
            return (now - self.ctime).seconds > self._config.timeout
        return False
        
    # def _setcookie(self, session_id, expires='', **kw): raise
    
    def expire(self):
        """Expire the session, make it no longer available"""
        self.__sessiondata.expired = True

    def __str__(self):
        return '<Session id:%s ctime:%s>' % (self.id, self.ctime.strftime('%Y-%m-%d %H:%M:%S'))

    def __repr__(self):
        return str(self)


            # def cleanup(self, timeout):
    #     now = time.time()
    #     for session_id, content in dict(self._dict).items():
    #         if 'creation_time' not in content or (now - content['creation_time']) > timeout or content['_expired']:
    #             if 'on_kill' in content:
    #                 content['on_kill'].notify(RStorage(content))
    #             if session_id in self:
    #                 del self[session_id]
    #             # clean up the SessionThreads belonging to this session
    #             for _, t in dnutils.threads.iteractive():
    #                 out('killing?')
    #                 if isinstance(t, threads.DetachedSessionThread) and t._session_id == session_id:
    #                     out('killing!')
    #                     t.interrupt()
        
        
class DictStore(web.session.Store):
    """Base class for session stores"""

    def __init__(self):
        self._dict = Storage()
        # self._lock = Lock()

    def __contains__(self, key):
        # with self._lock:
        return key in self._dict

    def __getitem__(self, key):
        # with self._lock:
        return self._dict.get(key)

    def __setitem__(self, key, value):
        # with self._lock:
         self._dict[key] = value
            
    def __delitem__(self, key):
        # with self._lock:
        del self._dict[key]

    def cleanup(self, timeout):
        now = time.time()
        for session_id, content in dict(self._dict).items():
            pprint(content)
            if 'creation_time' not in content or (now - content['creation_time']) > timeout or content['_expired']:
                if 'on_kill' in content:
                    content['on_kill'].notify(RStorage(content))
                if session_id in self:
                    del self[session_id]
                # clean up the SessionThreads belonging to this session
                for _, t in dnutils.threads.iteractive():
                    out('killing?')
                    if isinstance(t, threads.DetachedSessionThread) and t._session_id == session_id:
                        out('killing!')
                        t.interrupt()
                        