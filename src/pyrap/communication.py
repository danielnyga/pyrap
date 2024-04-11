'''
Created on Aug 1, 2015

@author: nyga
'''
import threading
import json

import dnutils
from dnutils import ifnone
from pyrap import web

from pyrap.exceptions import forbidden
from pyrap.utils import RStorage, jsonify, rstorify
from pyrap.web import internalerror

logger = dnutils.getlogger(__name__)

class RWTMessage(RStorage):
    '''
    An abstract generic message in the RWT message format consisting of
    a header (dict) and a list of operations.
    '''
    
    __slots__ = RStorage.__slots__# + ['json']
    
    def __init__(self, head=None, operations=None):
        RStorage.__init__(self)
        self.head = ifnone(head, {})
        self.operations = ifnone(operations, [])
    
    @property
    def json(self):
        return jsonify(dict(self))
    
    
class RWTOperation(RStorage): 
    '''
    Abstract base class of every RWT operation class.
    '''


class RWTCreateOperation(RWTOperation):
    '''
    Represents an RWT "create" operation for creating a new widget of any
    type in the client window.
    
    :param id_:     the globally unique id of the window
    :param clazz:   the (java script) widget class of the new widget.
    :param options: additional options (like style attributes) of the widget.
    '''
    def __init__(self, id_, clazz, options=None):
        RWTOperation.__init__(self)
        self.id = id_
        self.clazz = clazz
        self.options = options
        
    @property
    def json(self):
        return jsonify(['create', self.id, self.clazz, ifnone(self.options, {})])


class RWTListenOperation(RWTOperation):
    '''
    This operation is used to subscribe to specific events of a widget, such
    as a click or resize event.
    
    :param target:        the widget whose events shall be listened to.
    :param events:        a list of events we want to receive events.
    '''
    def __init__(self, target, events):
        RWTOperation.__init__(self)
        self.target = target
        self.events = events
    
    @property
    def json(self):
        return jsonify(['listen', self.target, self.events])
        

class RWTSetOperation(RWTOperation):
    '''
    Operation for setting particular properties of a widget, such as its
    position, size, style etc.
    
    :param target:        the id of the widget whose properties shall be set.
    '''
    def __init__(self, target, args):
        RWTOperation.__init__(self)
        self.target = target
        self.args = args
        
    @property
    def json(self):
        return jsonify(['set', self.target, self.args])


class RWTCallOperation(RWTOperation): 
    '''
    An operation triggering the call of a routine on the client.
    
    :param target:    the target widget/object the call is issued to.
    :param method:    the method to be invoked.
    :param args:      arguments to be handed to the target method call.
    '''
    def __init__(self, target, method, args=None):
        RWTOperation.__init__(self)
        self.target = target
        self.method = method
        self.args = args

    @property
    def json(self):
        return jsonify(['call', self.target, self.method, ifnone(self.args, {})])


class RWTDestroyOperation(RWTOperation): 
    '''
    An operation the disposes a particular widget on the client side.
    
    :param target:    the id of the widget to be disposed.
    '''    
    def __init__(self, target):
        RWTOperation.__init__(self)
        self.target = target

    @property
    def json(self):
        return jsonify(['destroy', self.target])


class RWTNotifyOperation(RWTOperation):
    '''
    Event notification messages are encoded using this class.
    
    :param target:        the id of the widget the event belongs to.
    :param event:         the type of event that was fired.
    :param args:          more precise parameters of the event can be stored here.
    '''    
    def __init__(self, target, event, args=None):
        RWTOperation.__init__(self)
        self.target = target
        self.event = event
        self.args = args
    
    @property
    def json(self):
        return jsonify(['notify', self.target, self.event, ifnone(self.args, {})])
    
    
class RWTError(RWTMessage):
    '''
    Message for signalizing the client that an error has occurred.
    '''
    SESSION_EXPIRED = 'session timeout'
    SERVER_ERROR = 'request failed'
    
    def __init__(self, error):
        RWTMessage.__init__(self)
        self.head.error = error
    
    
def rwterror(error):
    '''
    Wrapper function for creating a :class:`RWTError` that can be raised.
    '''
    web.header('Content-Type', 'application/json; charset=UTF-8')
    if error in (RWTError.SESSION_EXPIRED,):
        return forbidden(json.dumps(RWTError(error).json))
    else:
        return internalerror(json.dumps(RWTError(error).json))
        

# class RWTEvent(Event):
#     
#     def __init__(self, target):
#         self._callbacks = []
#         self._target = target
#         
#     def __iadd__(self, c):
#         if not self._callbacks:
#             # register the listener
#             session.runtime << self.create_subscribe_msg()
#         if c not in self._callbacks:
#             self._callbacks.append(c)
#         return self
#             
#     def __isub__(self, c):
#         if c in self._callbacks:
#             self._callbacks.remove(c)
#         if not self._callbacks:
#             # unregister the listener
#             session.runtime << self.create_unsubscribe_msg()
#         return self
#             
#     def __contains__(self, c):
#         return c in self._callbacks
#     
#     def __iter__(self):
#         for c in self._callbacks: yield c
#         
#     def _create_subscribe_msg(self):
#         raise Exception('Not implemented.')
#     
#     def _create_unsubscribe_msg(self):
#         raise Exception('Not implemented.')


        

def parse_msg(content):
    data = rstorify(json.loads(content))
    operations = []
    for o in data.operations:
        operations.append(operation_from_storage(o))
    msg = RWTMessage(head=data.head, operations=operations)
    return msg
        

def operation_from_storage(data):
    if data[0] == 'set':
        return RWTSetOperation(target=data[1], args=data[2])
    elif data[0] == 'call':
        return RWTCallOperation(target=data[1], method=data[2], args=data[3])
    elif data[0] == 'listen':
        return RWTListenOperation(target=data[1], events=data[2])
    elif data[0] == 'notify':
        return RWTNotifyOperation(target=data[1], event=data[2], args=data[3])
    elif data[0] == 'create':
        return RWTCreateOperation(id_=data[1], clazz=data[2], options=data[3])
    
        
class ResumableThread(threading.Thread):
    
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = False  # OK for main to exit even if instance is still running
        self.paused = False
        self.state = threading.Condition()


    def run(self):
        raise Exception('Not implemented.')


    def resume(self):
        with self.state:
            self.paused = False
            self.state.notify()  # unblock self if waiting


    def pause(self):
        with self.state: 
            self.paused = True
            self.state.wait()
