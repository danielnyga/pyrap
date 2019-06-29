'''
Created on Nov 10, 2015

@author: nyga
'''
import os
import sys

import collections
from dnutils import edict

#
# case-insensitive dict taken from requests
#
class CaseInsensitiveDict(collections.MutableMapping):
    """
    A case-insensitive ``dict``-like object.
    Implements all methods and operations of
    ``collections.MutableMapping`` as well as dict's ``copy``. Also
    provides ``lower_items``.
    All keys are expected to be strings. The structure remembers the
    case of the last key to be set, and ``iter(instance)``,
    ``keys()``, ``items()``, ``iterkeys()``, and ``iteritems()``
    will contain case-sensitive keys. However, querying and contains
    testing is case insensitive::
        cid = CaseInsensitiveDict()
        cid['Accept'] = 'application/json'
        cid['aCCEPT'] == 'application/json'  # True
        list(cid) == ['Accept']  # True
    For example, ``headers['content-encoding']`` will return the
    value of a ``'Content-Encoding'`` response header, regardless
    of how the header name was originally stored.
    If the constructor, ``.update``, or equality comparison
    operations are given keys that have equal ``.lower()``s, the
    behavior is undefined.
    """
    def __init__(self, data=None, **kwargs):
        self._store = dict()
        if data is None:
            data = {}
        self.update(data, **kwargs)

    def __setitem__(self, key, value):
        # Use the lowercased key for lookups, but store the actual
        # key alongside the value.
        self._store[key.lower()] = (key, value)

    def __getitem__(self, key):
        return self._store[key.lower()][1]

    def __delitem__(self, key):
        del self._store[key.lower()]

    def __iter__(self):
        return (casedkey for casedkey, mappedvalue in self._store.values())

    def __len__(self):
        return len(self._store)

    def lower_items(self):
        """Like iteritems(), but with all lowercase keys."""
        return (
            (lowerkey, keyval[1])
            for (lowerkey, keyval)
            in self._store.items()
        )

    def __eq__(self, other):
        if isinstance(other, collections.Mapping):
            other = CaseInsensitiveDict(other)
        else:
            return NotImplemented
        # Compare insensitively
        return dict(self.lower_items()) == dict(other.lower_items())

    # Copy is required
    def copy(self):
        return CaseInsensitiveDict(self._store.values())

    def __repr__(self):
        return str(dict(self.items()))


class RStorage(dict):
    '''
    Recursive extension of web.util.Storage that applies the Storage constructor
    recursively to all value elements that are dicts.
    '''
    __slots__ = []

    def __init__(self, d=None):
        if d is not None:
            for k, v in d.items(): self[k] = v
    
    def __setattr__(self, key, value):
        if key in self.__slots__:
            self.__dict__[key] = value
        else: 
            self[key] = value
            
    def __setitem__(self, key, value):
        dict.__setitem__(self, key, rstorify(value))
            
    def __getattr__(self, key):
        if key in type(self).__slots__: 
            return self.__dict__[key]
        else:
            try:
                return self[key]
            except KeyError as k:
                raise AttributeError(k)
            
    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError as k:
            raise AttributeError(k)
            
    def __repr__(self):     
        return ('<%s ' % type(self).__name__) + dict.__repr__(self) + '>'
        
        
def rstorify(e):
    if type(e) is dict:
        return RStorage(d=e)
    elif type(e) in (list, tuple):
        return [rstorify(i) for i in e]
    else: return e
        
def jsonify(o):
    if hasattr(o, 'json'): 
        return o.json
    elif isinstance(o, dict):
        return {str(k): jsonify(v) for k, v in o.items()}
    elif type(o) in (list, tuple, map):
        return [jsonify(e) for e in o]
    elif isinstance(o, (int, float, bool, str, type(None))):
        return o
    else:
        raise TypeError('object of type "%s" is not jsonifiable: %s' % (type(o), repr(o)))
    
        
class BiMap:
    '''
    Bi-directional mapping.
    '''
    
    def __init__(self, values=None):
        self._fwd = {}
        self._bwd = {}
        self += values
        self.__iter__ = self._fwd.__iter__
        self.items = self._fwd.items
        self.keys = self._fwd.keys
        self.values = self._fwd.values
        
    def __iadd__(self, values):
        if type(values) in (list, tuple):
            for f, b in values: self[f:b]
        elif isinstance(values, (dict, BiMap)):
            for f, b in values.items():
                self[f:b]
        return self
    
    def __add__(self, values):
        newmap = BiMap(self)
        newmap += values
        return newmap
     
    def __getitem__(self, s):
        if type(s) is slice:
            if not s.start and s.stop: return self._bwd[s.stop]
            if s.start and not s.stop: return self._fwd[s.start]
            if s.start and s.stop:
                self._fwd[s.start] = s.stop
                self._bwd[s.stop] = s.start
            else: raise AttributeError('Slice argument for BiMap cannot be empty')
        else: return self._fwd[s]

    def __contains__(self, e):
        return e in self._fwd or e in self._bwd

    def __str__(self):
        return ';'.join([str(e) for e in list(self._fwd.items())])


class BitMask(BiMap):
    def __init__(self, *values):
        BiMap.__init__(self)
        self._count = 0
        for v in values:
            numval = 1 << self._count
            setattr(self, v, numval)
            self._count += 1
            self[numval:v]


def pparti(number, proportions):
    '''
    Partition a number into a sum of n integers, proportionally to the ratios given in 
    proportions. 
    
    The result is guaranteed to sun up to ``number``, so it is cleaned wrt.
    to numerical instabilities.
    '''
    Z = sum(proportions)
    percents = [float(p) / Z for p in proportions]
    result = [max(0, int(round(p * number))) for p in percents[:-1]]
    return result + [number - sum(result)]
    

def bind(**kwargs):
    def wrap_f(function):
        def probeFunc(frame, event, arg):
            if event == 'call':
                frame.f_locals.update(kwargs)
                frame.f_globals.update(kwargs)
            elif event == 'return':
                for key in kwargs:
                    kwargs[key] = frame.f_locals[key]
                sys.settrace(None)
            return probeFunc
        def traced(*args, **kwargs):
            sys.settrace(probeFunc)
            function(*args, **kwargs)
        return traced
    return wrap_f


if __name__ == '__main__':
    print(pparti(10, [.2, .2, .1, .5]))
