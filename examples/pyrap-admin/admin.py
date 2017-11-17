import threading
from collections import OrderedDict

from dnutils import threads, out, edict
from dnutils.threads import current_thread, sleep, ThreadInterrupt

import pyrap
from pyrap import session
from pyrap.engine import PushService
from pyrap.layout import RowLayout, ColumnLayout
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

        session_options = Composite(container, layout=RowLayout(valign='fill', flexrows=1))
        Label(session_options, 'Operations:')
        btn_invalidate = Button(session_options, 'Invalidate Session', valign='top')
        btn_invalidate.on_select += self.invalidate_session

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
            out('invalidating session:', sel.session_id)
            edict(sel).pprint()
            del session.store[sel.session_id]
        except KeyError: pass

    def update_sessions(self):
        try:
            while not threads.interrupted():
                items = OrderedDict()
                for sid, session_ in session.store._dict.items():
                    items[sid] = RStorage(session_)
                self.sessionlist.items = items
                sleep(2)
                self.push.flush()
        except ThreadInterrupt:
            out('exiting session update thread')

    def update_processes(self):
        try:
            while not threads.interrupted():
                self.update_process_list()
                sleep(2)
        except ThreadInterrupt:
            out('exiting process update thread')

    def update_process_list(self):
        items = OrderedDict()
        for _, thread in threads.active().items():
            items['%s (%s)' % (thread.name, thread.ident)] = thread
        self.processlist.items = items
        self.push.flush()


if __name__ == '__main__':
    pyrap.register(clazz=PyRAPAdmin,
                   entrypoints={'main': PyRAPAdmin.main},
                   path='admin',
                   name='pyRAP Administration Tool')
    pyrap.run()
