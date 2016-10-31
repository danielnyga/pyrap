'''
Created on Nov 23, 2015

@author: nyga
'''
from pyrap.ptypes import Event
from pyrap.communication import RWTListenOperation
from pyrap.base import session


class RWTEvent(Event):
    
    def __init__(self, event, widget):
        Event.__init__(self)
        self._listeners = []
        self._widget = widget
        self.event = event
    
    @property
    def widget(self):
        return self._widget
    
    @widget.setter
    def widget(self, w):
        self._widget = w
    
    def __iadd__(self, l):
        if not self._listeners:
            # register the listener
#             session.runtime << RWTListenOperation(self._widget.id, {self.event: True})
            session.runtime << self._create_subscribe_msg()
        if l not in self._listeners:
            self._listeners.append(l)
        return self
            
    def __isub__(self, l):
        if l in self._listeners:
            self._listeners.remove(l)
        if not self._listeners:
            # unregister the listener
#             session.runtime << RWTListenOperation(self._widget.id, {self.event: False})
            session.runtime << self._create_unsubscribe_msg()
        return self
            

class OnResize(RWTEvent):
    def __init__(self, widget):
        RWTEvent.__init__(self, 'Resize', widget)
    
    def _create_subscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'Resize': True})
    
    def _create_unsubscribe_msg(self):
        return RWTListenOperation(self.widget.id, {'Resize': False})
    
    def _notify(self, listener): listener()
    
    
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
        return RWTListenOperation(self.widget.id, {'Selection': False})
    
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
    
    def _notify(self, listener): listener()    


class OnFocus(RWTEvent):
    def __init__(self, widget):
        RWTEvent.__init__(self, ('FocusIn', 'FocusOut'), widget)
    
    def _create_subscribe_msg(self):
        return [RWTListenOperation(self.widget.id, {event: True}) for event in self.event]
    
    def _create_unsubscribe_msg(self):
        return [RWTListenOperation(self.widget.id, {event: False}) for event in self.event]

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
