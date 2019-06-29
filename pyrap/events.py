'''
Created on Nov 23, 2015

@author: nyga
'''
import dnutils
from dnutils.threads import current_thread, SuspendableThread, RLock

from pyrap.base import session
from pyrap.ptypes import Event
from pyrap.communication import RWTListenOperation


class RWTEvent(Event):
    
    def __init__(self, event, widget):
        Event.__init__(self)
        self._lock = RLock()
        self._listeners = []
        self._waiters = []
        self._widget = widget
        self.event = event
    
    @property
    def widget(self):
        return self._widget
    
    @widget.setter
    def widget(self, w):
        self._widget = w
    
    def __iadd__(self, l):
        with self._lock:
            if not self._listeners:
                # register the listener
                session.runtime << self._create_subscribe_msg()
            if l not in self._listeners:
                self._listeners.append(l)
            return self
            
    def __isub__(self, l):
        with self._lock:
            if l in self._listeners:
                self._listeners.remove(l)
            if not self._listeners:
                # unregister the listener
                session.runtime << self._create_unsubscribe_msg()
            return self

    def wait(self):
        # override the wait protocol for RWT events to suspend the
        # the waiting thread. By notifying the event, the waiting
        # thread will be awoken.
        t = current_thread()
        if isinstance(t, SuspendableThread):
            with self._lock:
                if t not in self._waiters:
                    self._waiters.append(t)
            t.suspend()
        else:
            Event.wait(self)

    def notify(self, *args, **kwargs):
        # with self._wait:
        for w in self._waiters:
            # with self._lock:
            block = dnutils.Event()
            # w.add_handler(dnutils.threads.TERM, lambda: out('terminate'))
            w.add_handler(dnutils.threads.TERM, block.set)
            w.add_handler(dnutils.threads.SUSPEND, block.set)
            w.resume()
            block.wait()
            w.rm_handler(dnutils.threads.TERM, block.set)
            w.rm_handler(dnutils.threads.SUSPEND, block.set)
            self._waiters.remove(w)
        Event.notify(self, *args, **kwargs)
            

class OnResize(RWTEvent):
    def __init__(self, widget):
        RWTEvent.__init__(self, 'Resize', widget)
    
    def _create_subscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'Resize': True})
    
    def _create_unsubscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'Resize': False})
    
    def _notify(self, listener): listener()


class OnMouseOver(RWTEvent):
    def __init__(self, widget):
        RWTEvent.__init__(self, 'MouseOver', widget)

    def _create_subscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'MouseOver': True})

    def _create_unsubscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'MouseOver': False})

    def _notify(self, listener, data): listener(data)

    
class OnMouseDown(RWTEvent):
    def __init__(self, widget):
        RWTEvent.__init__(self, 'MouseDown', widget)
    
    def _create_subscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'MouseDown': True})
    
    def _create_unsubscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'MouseDown': False})
    
    def _notify(self, listener, data): listener(data)
    
    
class OnMouseUp(RWTEvent):
    def __init__(self, widget):
        RWTEvent.__init__(self, 'MouseUp', widget)
    
    def _create_subscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'MouseUp': True})
    
    def _create_unsubscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'MouseUp': False})
    
    def _notify(self, listener, data): listener(data)
    
    
class OnDblClick(RWTEvent):
    def __init__(self, widget):
        RWTEvent.__init__(self, 'MouseDoubleClick', widget)
    
    def _create_subscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'MouseDoubleClick': True})
    
    def _create_unsubscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'MouseDoubleClick': False})
    
    def _notify(self, listener, data): listener(data)
    
    
class OnSelect(RWTEvent):
    def __init__(self, widget):
        RWTEvent.__init__(self, 'Selection', widget)
    
    def _create_subscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'Selection': True, 'DefaultSelection': True})
    
    def _create_unsubscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'Selection': False, 'DefaultSelection': False})
    
    def _notify(self, listener, data): listener(data)


class OnSet(RWTEvent):
    def __init__(self, widget):
        RWTEvent.__init__(self, 'Set', widget)

    def _create_subscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'Set': True})

    def _create_unsubscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'Set': False})

    def _notify(self, listener, data): listener(data)


class OnLongClick(RWTEvent):
    def __init__(self, widget):
        RWTEvent.__init__(self, 'LongClick', widget)

    def _create_subscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'LongClick': True})

    def _create_unsubscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'LongClick': False})

    def _notify(self, listener, data): listener(data)


class OnNavigate(RWTEvent):
    def __init__(self, widget):
        RWTEvent.__init__(self, 'Navigation', widget)

    def _create_subscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'Navigation': True})

    def _create_unsubscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'Navigation': False})

    def _notify(self, listener, data): listener(data)


class OnClose(RWTEvent):
    def __init__(self, widget):
        RWTEvent.__init__(self, 'Close', widget)
    
    def _create_subscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'Close': True})
    
    def _create_unsubscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'Close': False})
    
    def _notify(self, listener): listener()
    

class OnMove(RWTEvent):
    def __init__(self, widget):
        RWTEvent.__init__(self, 'Move', widget)
    
    def _create_subscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'Move': True})
    
    def _create_unsubscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'Move': False})
    
    def _notify(self, listener): listener()    


class OnModify(RWTEvent):
    def __init__(self, widget):
        RWTEvent.__init__(self, 'Modify', widget)
    
    def _create_subscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'Modify': True})
    
    def _create_unsubscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'Modify': False})
    
    def _notify(self, listener, data): listener(data)


class OnFocus(RWTEvent):
    def __init__(self, widget):
        RWTEvent.__init__(self, ('FocusIn', 'FocusOut'), widget)
    
    def _create_subscribe_msg(self):
        return [RWTListenOperation(self.widget.id, {event: True}) for event in self.event]
    
    def _create_unsubscribe_msg(self):
        return [RWTListenOperation(self.widget.id, {event: False}) for event in self.event]

    def _notify(self, listener, focus_data): listener(focus_data)


class OnFinished(RWTEvent):
    def __init__(self, widget):
        RWTEvent.__init__(self, 'Finished', widget)
    
    def _create_subscribe_msg(self):
        return [RWTListenOperation(self.widget.id, {'Finished': True})]
    
    def _create_unsubscribe_msg(self):
        return [RWTListenOperation(self.widget.id, {'Finished': False})]

    def _notify(self, listener): listener()
    

class OnDispose(Event):
    def _notify(self, listener): listener()
    

class EventData(object):
    def __init__(self, widget, *args):
        self.widget = widget
        self.args = args


class FocusEventData(EventData):
    def __init__(self, widget, gained):
        EventData.__init__(self, widget)
        self.gained = gained
    
    @property
    def lost(self): return not self.gained


class SelectionEventData(EventData):
    
    def __init__(self, widget, button, ctrl, alt, shift, args=None, item=None, x=None, y=None):
        EventData.__init__(self, widget, args)
        self.button = button
        self.ctrl = ctrl
        self.alt = alt
        self.shift = shift
        self.item = item
        self.x = x
        self.y = y


class MouseEventData(EventData):
    
    def __init__(self, widget, button, ctrl, alt, shift, timestamp, x, y):
        EventData.__init__(self, widget)
        self.button = button
        self.ctrl = ctrl
        self.alt = alt
        self.shift = shift
        self.timestamp = timestamp
        self.x = x
        self.y = y
        
    @property
    def location(self):
        return self.x, self.y


def _rwt_selection_event(op):
    return SelectionEventData(session.runtime.windows[op.target],
                              op.args.get('button'),
                              op.args.get('ctrlKey'),
                              op.args.get('altKey'),
                              op.args.get('shiftKey'),
                              args=op.args.get('args'),
                              item=op.args.get('item'),
                              x=op.args.get('x'),
                              y=op.args.get('y'))


def _rwt_longlick_event(op):
    return SelectionEventData(session.runtime.windows[op.target],
                              op.args.get('button'),
                              op.args.get('ctrlKey'),
                              op.args.get('altKey'),
                              op.args.get('shiftKey'),
                              args=op.args.get('args'),
                              item=op.args.get('item'),
                              x=op.args.get('x'),
                              y=op.args.get('y'))


def _rwt_mouse_event(op):
    return MouseEventData(session.runtime.windows[op.target],
                          op.args.get('button'),
                          op.args.get('ctrlKey'),
                          op.args.get('altKey'),
                          op.args.get('shiftKey'),
                          op.args.get('time'),
                          op.args.get('x'),
                          op.args.get('y'))


def _rwt_event(op):
    return EventData(session.runtime.windows[op.target], op.args)
