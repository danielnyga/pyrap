import dnutils
from dnutils.threads import current_thread

import pyrap

from dnutils import SuspendableThread, out


def sessionthreads():
    d = {}
    for i, t in dnutils.threads.iteractive():
        if isinstance(t, SessionThread):
            d[i] = t
    return d


class DetachedSessionThread(SuspendableThread):
    '''
    A DetachedSessionThread is thread that has access to the HTTP session of pyRAP app instance.
    '''
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None):
        SuspendableThread.__init__(self, group=group, target=target, name=name, args=args, kwargs=kwargs)
        try:
            self.__session_id = pyrap.session.id
        except AttributeError:
            raise RuntimeError('%s can only be instatiated from a %s instance' % (self.__class__.__name__, self.__class__.__name__))

    def _run(self):
        self.__sessionload()
        try:
            pyrap.session._threads.append(current_thread())
            self.run()
        finally:
            pyrap.session._threads.remove(current_thread())

    def __sessionload(self):
        pyrap.session._PyRAPSession__locals['session_id'] = self.__session_id


class SessionThread(DetachedSessionThread):
    '''
    An interruptable thread class that inherits the session information
    from the parent thread. It may be attached to a request/response cycle in the pyRAP client/server model.
    In case it is attached, the HTTP server answering a request will block until it terminates. It has the
    '''
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None):
        DetachedSessionThread.__init__(self, target=target, name=name, args=args, kwargs=kwargs)
        self.__detached = False

    def suspend(self):
        if not self.__detached:
            pyrap.session.runtime.relay.dec()
        SuspendableThread.suspend(self)

    def resume(self):
        if not self.__detached:
            pyrap.session.runtime.relay.inc()
        SuspendableThread.resume(self)

    def _run(self):
        self._DetachedSessionThread__sessionload()
        try:
            DetachedSessionThread.run(self)
        finally:
            if not self.__detached:
                pyrap.session.runtime.relay.dec()

    def start(self):
        if not self.__detached:
            pyrap.session.runtime.relay.inc()
        return SuspendableThread.start(self)

    def detach(self):
        with self._SuspendableThread__lock:
            if self.__detached:
                raise RuntimeError('Thread is already detached from session.')
            self.__detached = True
