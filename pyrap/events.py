'''
Created on Nov 23, 2015

@author: nyga
'''
from pyrap.types import Event
from pyrap.communication import RWTListenOperation
from pyrap.base import session


class RWTEvent(Event):
    
    def __init__(self, event, widget):
        Event.__init__(self)
        self._listeners = []
        self._widget = widget
        self.event = event
        
    def __iadd__(self, l):
        if not self._listeners:
            # register the listener
            session.runtime << RWTListenOperation(self._widget.id, {self.event: True})
        if l not in self._listeners:
            self._listeners.append(l)
        return self
            
    def __isub__(self, l):
        if l in self._listeners:
            self._listeners.remove(l)
        if not self._listeners:
            # unregister the listener
            session.runtime << RWTListenOperation(self._widget.id, {self.event: False})
        return self
            

class OnResize(RWTEvent):
    def __init__(self, widget):
        RWTEvent.__init__(self, 'Resize', widget)
    
    def _create_subscribe_msg(self):
        return RWTListenOperation(self.target.id, {'Resize': True})
    
    def _create_unsubscribe_msg(self):
        return RWTListenOperation(self.target.id, {'Resize': False})
    
    def _notify(self, listener): listener()
    
class OnMouseDown(RWTEvent):
    def __init__(self, widget):
        RWTEvent.__init__(self, 'MouseDown', widget)
    
    def _create_subscribe_msg(self):
        return RWTListenOperation(self.target.id, {'MouseDown': True})
    
    def _create_unsubscribe_msg(self):
        return RWTListenOperation(self.target.id, {'MouseDown': False})
    
    def _notify(self, listener, data): listener(data)
    
class OnMouseUp(RWTEvent):
    def __init__(self, widget):
        RWTEvent.__init__(self, 'MouseUp', widget)
    
    def _create_subscribe_msg(self):
        return RWTListenOperation(self.target.id, {'MouseUp': True})
    
    def _create_unsubscribe_msg(self):
        return RWTListenOperation(self.target.id, {'MouseUp': False})
    
    def _notify(self, listener, data): listener(data)
    
class OnDblClick(RWTEvent):
    def __init__(self, widget):
        RWTEvent.__init__(self, 'MouseDoubleClick', widget)
    
    def _create_subscribe_msg(self):
        return RWTListenOperation(self.target.id, {'MouseDoubleClick': True})
    
    def _create_unsubscribe_msg(self):
        return RWTListenOperation(self.target.id, {'MouseDoubleClick': False})
    
    def _notify(self, listener, data): listener(data)
    
    
class OnSelect(RWTEvent):
    def __init__(self, widget):
        RWTEvent.__init__(self, 'Selection', widget)
    
    def _create_subscribe_msg(self):
        return RWTListenOperation(self.target.id, {'Selection': True, 'DefaultSelection': True})
    
    def _create_unsubscribe_msg(self):
        return RWTListenOperation(self.target.id, {'Selection': False})
    
    def _notify(self, listener, data): listener(data)


class OnClose(RWTEvent):
    def __init__(self, widget):
        RWTEvent.__init__(self, 'Close', widget)
    
    def _create_subscribe_msg(self):
        return RWTListenOperation(self.target.id, {'Close': True})
    
    def _create_unsubscribe_msg(self):
        return RWTListenOperation(self.target.id, {'Close': False})
    
    def _notify(self, listener): listener()
    

class OnMove(RWTEvent):
    def __init__(self, widget):
        RWTEvent.__init__(self, 'Move', widget)
    
    def _create_subscribe_msg(self):
        return RWTListenOperation(self.target.id, {'Move': True})
    
    def _create_unsubscribe_msg(self):
        return RWTListenOperation(self.target.id, {'Move': False})
    
    def _notify(self, listener): listener()    

class OnFocus(Event):
    def _notify(self, listener, focus_data): listener(focus_data)

class OnDispose(Event):
    def _notify(self, listener): listener()

class EventData(object): pass

class FocusEventData(EventData):
    def __init__(self, gained):
        self.gained = gained
    
    @property
    def lost(self): return not self.gained

class SelectionEventData(EventData):
    
    def __init__(self, button, ctrl, alt, shift):
        self.button = button
        self.ctrl = ctrl
        self.alt = alt
        self.shift = shift
        
class MouseEventData(EventData):
    
    def __init__(self, button, ctrl, alt, shift, timestamp, x, y):
        self.button = button
        self.ctrl = ctrl
        self.alt = alt
        self.shift = shift
        self.timestamp = timestamp
        self.x = x
        self.y = y
        
    @property
    def location(self):
        return (self.x, self.y)
    
def _rwt_selection_event(op):
        return SelectionEventData(op.args.get('button'), op.args.ctrlKey, op.args.altKey, op.args.shiftKey)
    
def _rwt_mouse_event(op):
    return MouseEventData(op.args.button, op.args.ctrlKey, op.args.altKey, op.args.shiftKey, op.args.time, op.args.x, op.args.y)
