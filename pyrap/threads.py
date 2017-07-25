import dnutils
import pyrap
import traceback

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
            self._session = pyrap.session
            self._session_id = pyrap.session.session_id
        except AttributeError:
            raise RuntimeError('%s can only be instatiated from a %s instance' % (self.__class__.__name__, self.__class__.__name__))

    def run(self):
        self.__sessionload()
        SuspendableThread.run(self)
    
    def __sessionload(self):
        pyrap.session.session_id = self._session_id
        pyrap.session.load()


class SessionThread(DetachedSessionThread):
    '''
    An interruptable thread class that inherits the session information
    from the parent thread. It may be attached to a request/response cycle in the pyRAP client/server model.
    In case it is attached, the HTTP server answering a request will block until it terminates. It has the
    '''
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None):
        DetachedSessionThread.__init__(self, target=target, name=name,
                 args=args, kwargs=kwargs)
        self.__detached = False
        self.__exception = None

    def suspend(self):
        if not self.__detached:
            pyrap.session.runtime.relay.dec()
        SuspendableThread.suspend(self)

    def resume(self):
        if not self.__detached: 
            pyrap.session.runtime.relay.inc()
        SuspendableThread.resume(self)

    def _stop(self):
        # if not self.__detached:
        #     pyrap.session.runtime.relay.dec()
        SuspendableThread._stop(self)

    def run(self):
        self._DetachedSessionThread__sessionload()
        try:
            DetachedSessionThread.run(self)
        except Exception as e:
            self.__exception = e
            traceback.print_exc()
            raise e
        finally:
            if not self.__detached:
                out('dec relay')
                pyrap.session.runtime.relay.dec()

    def start(self):
        # self.setresumed()
        if not self.__detached:
            pyrap.session.runtime.relay.inc()
        return SuspendableThread.start(self)
    
    def detach(self):
        with self._SuspendableThread__lock:
            if self.__detached:
                raise RuntimeError('Thread is already detached from session.')
            self.__detached = True
