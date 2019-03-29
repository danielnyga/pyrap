import threading
from collections import OrderedDict

from dnutils import threads, out, edict
from dnutils.threads import current_thread, sleep, ThreadInterrupt, _DummyThread

import pyrap
from pyrap import session
from pyrap.engine import PushService
from pyrap.layout import RowLayout, ColumnLayout
from pyrap.sessions import SessionError
from pyrap.threads import DetachedSessionThread
from pyrap.utils import RStorage
from pyrap.widgets import Shell, Label, List, Rows, Composite, Button


class PyRAPAdmin:
    '''pyRAP administration and debugging tool'''

    def main(self, **kwargs):
        shell = Shell(titlebar=False, maximixed=True)
        shell.maximized = True
        self.push = PushService()

        container = Composite(shell.content, layout=ColumnLayout(valign='fill'))

        sessions = Composite(container, layout=RowLayout(valign='fill', flexrows=1))
        Label(sessions, 'Sessions:', halign='left')
        self.sessionlist = List(sessions, halign='fill', valign='fill', minwidth=300, vscroll=True)

        session_options = Composite(container, layout=RowLayout(valign='fill', flexrows=2))
        Label(session_options, 'Operations:')
        btn_invalidate = Button(session_options, 'Invalidate Session', valign='top')
        btn_invalidate.on_select += self.invalidate_session

        self.session_details = Label(session_options, valign='fill', halign='fill', wrap=True)

        def update_session_details(*_):
            self.session_details.text = str(self.sessionlist.selection.app)
        self.sessionlist.on_select += update_session_details

        processes = Composite(container, layout=RowLayout(valign='fill', flexrows=1))
        Label(processes, 'All pyRAP Threads:', halign='left')
        self.processlist = List(processes, halign='fill', valign='fill', minwidth=300, vscroll=True)
        shell.tabseq = (self.sessionlist, self.processlist,)

        shell.on_resize += shell.dolayout
        shell.show()

        self.push.start()
        self.count = 1
        self.process_thread = DetachedSessionThread(name='update_processes', target=self.update_processes)
        self.process_thread.start()
        self.session_thread = DetachedSessionThread(name='update_sessions', target=self.update_sessions)
        self.session_thread.start()

    def invalidate_session(self, data):
        try:
            sel = self.sessionlist.selection
            out('invalidating session:', sel.id)
            sel.expire()
            edict(sel._PyRAPSession__sessions).pprint()
        except KeyError: pass

    def update_sessions(self):
        try:
            out('started session update thread')
            while not threads.interrupted():
                items = OrderedDict()
                for sid, session_ in session._PyRAPSession__sessions.items():
                    items[sid] = session.fromid(sid)
                if set(self.sessionlist.items.keys()) != set(items.keys()):
                    out('sessions changed')
                    self.sessionlist.items = items
                    self.push.flush()
                sleep(2)
        except (ThreadInterrupt, SessionError) as e:
            out('exiting session update thread due to', type(e))

    def update_processes(self):
        try:
            while not threads.interrupted():
                self.update_process_list()
                sleep(2)
        except (ThreadInterrupt, SessionError) as e:
            out('exiting process update thread due to', type(e))

    def update_process_list(self):
        items = OrderedDict()
        for _, thread in threads.active().items():
            if type(thread) is threads._DummyThread: continue
            items['%s (%s)' % (thread.name, thread.ident)] = thread
        for thread in threading.enumerate():
            if type(thread) is threading._DummyThread: continue
            items['%s (%s)' % (thread.name, thread.ident)] = thread
        if set(items.keys()) != set(self.processlist.items.keys()):
            self.processlist.items = items
            out('processes changed')
            self.push.flush()


def main():
    pyrap.register(clazz=PyRAPAdmin,
                   entrypoints={'main': PyRAPAdmin.main},
                   path='admin',
                   name='pyRAP Administration Tool')
    pyrap.run()


if __name__ == '__main__':
    main()
