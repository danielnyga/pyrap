from threading import Thread

from pyrap import session


class UIThread(Thread):

    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        Thread.__init__(self)
        self._session = session
        self._session_id = session.session_id

    def run(self):
        session.session_id = self._session_id
        session.load()
        self._run()
        print session
        print session.store._dict
        print session.session_id


