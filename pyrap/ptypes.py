'''
Created on Oct 18, 2015

@author: nyga
'''
import base64
import mimetypes
import os
from _pyio import BytesIO
from colorsys import hsv_to_rgb, rgb_to_hsv
import xml.etree.ElementTree as ET

from xml.dom import minidom

from PIL import Image as PILImage

from dnutils import Condition, ifnone
from pyrap.constants import FONT, style, defs
from pyrap.utils import BitMask
from functools import reduce


class Event(object):
    
    def __init__(self):
        self._listeners = []
        self._wait = Condition()
        
    def __iadd__(self, l):
        if l not in self._listeners:
            self._listeners.append(l)
        return self

    def __isub__(self, l):
        self._listeners.remove(l)
        return self

    def __contains__(self, l):
        return l in self._listeners

    def addall(self, listeners):
        if listeners is None: return self
        if type(listeners) is not list: listeners = [listeners]
        for l in listeners: self += l
        return self

    def removeall(self):
        self._listeners = []
        return self
            
    def notify(self, *args, **kwargs):
        with self._wait: self._wait.notify_all()
        for listener in self._listeners: self._notify(listener, *args, **kwargs)
        
    def _notify(self, listener, *args, **kwargs):
        raise Exception('Not implemented.')
    
    def wait(self):
        with self._wait: self._wait.wait()
    
    def __iter__(self):
        for l in self._listeners: yield l

    
class ValueChanged(Event):
    
    def _notify(self, listener, var, caller):
        listener(var, caller)


class DirtyState(Event):
    
    def _notify(self, listener, var, caller):
        listener(var, var.dirty, caller)


class VarCompound(object):
    
    def __init__(self, *vars):
        self.vars = vars
        
    @property
    def dirty(self):
        for v in self.vars:
            if v.dirty: return True
        return False
    
    def clean(self):
        for v in self.vars: v.clean()
        
    def all_defined(self):
        for v in self.vars:
            if v.value is None: return False
        return True
    
    def all_none(self):
        for v in self.vars:
            if v.value is not None: return False
        return True
        

class Var(object):
    '''
    Represents an abstract variable with a listen/notification interface,
    dirty flags, history, undo and redo functionality, and more.
    '''
    
    def __init__(self, value=None, track=False, typ=None, on_change=None, on_dirty=None):
        self.type = typ
        self._history = track
        self._values = [self._getval(value)]
        self._pointer = 0
        self.on_change = ValueChanged().addall(on_change)
        self.on_dirty = DirtyState().addall(on_dirty)
        self._init = self.value

    def __bool__(self):
        return bool(self.value)
    
    
    def _getval(self, other):
        return other.value if type(other) == type(self) else other
        
    @property
    def value(self):
        return self.get()
    
    @value.setter
    def value(self, v):
        self.set(v)
        
    @property
    def prev(self):
        if not self.hasprev:
            raise Exception('Variable has no previous value.')
        return self._values[self._pointer-1]
    
    @property
    def succ(self):
        if not self.hassucc:
            raise Exception('Variable has no succeeding value.') 
        return self._values[self._pointer+1]
    
    @property
    def hasprev(self):
        return self._pointer > 0

    @property
    def hassucc(self):
        return len(self._values) <= self._pointer

    def get(self):
        return self._values[self._pointer]

    def set(self, v, caller=None):
        v = self._getval(v)
        if v != self.value:
            dirty = self.dirty
            if self._history:
                self._pointer += 1
                self._values = self._values[:self._pointer] + [v]
            else:
                self._values[self._pointer] = v
            dirty = dirty != self.dirty
            self.on_change.notify(self, caller)
            if dirty: self.on_dirty.notify(self, caller)

    @property
    def dirty(self):
        return self._init != self.value
    
    @property
    def canundo(self):
        return self._pointer > 0
    
    @property
    def canredo(self):
        return self._pointer < len(self._values) - 1
            
    def undo(self, caller=None):
        if not self.canundo:
            raise Exception('There are no operations to undo.')
        dirty = self.dirty
        self._pointer -= 1
        dirty = dirty != self.dirty
        self.on_change.notify(self, caller)
        if dirty: self.on_dirty.notify(self, caller)
        return self
    
    def redo(self, caller=None):
        if not self.canredo:
            raise Exception('There are no operations to redo')
        dirty = self.dirty
        self._pointer += 1
        dirty = dirty != self.dirty
        self.on_change.notify(self, caller)
        if dirty: self.on_dirty.notify(self, caller)
        return self
    
    def __call__(self):
        return self.value
    
    def bind(self, var):
        if not type(var) is type(self):
            raise Exception('Can only bind variables of the same type')
        def set_mine(other, c):
            if c is self: return
            self.set(other.value, self)
        def set_other(me, c):
            if c is var: return
            var.set(me.value, var)
        var.on_change += set_mine
        self.on_change += set_other
        self.set(var.value, self)

    def unbind(self):
        self.on_change = ValueChanged().removeall()

    def clean(self):
        self._init = self.value
        
    def reset(self):
        self._values = [self.value]
        self._pointer = 0
        
    def __str__(self):
        return str(self.value)
    
    def __repr__(self):
        return '<%s[%s] at %s : %s>' % (self.__class__.__name__, type(self.value).__name__, hex(hash(self)), str(self.value))
    

class BitField(Var):
    '''
    A variable representing a field of bit flags.
    '''
    
    class _iterator():
        def __init__(self, v):
            self._v = v
        
        def __next__(self):
            if not self._v: raise StopIteration()
            b = self._v & (~self._v+1)
            self._v ^= b
            return b
        
        def __iter__(self): return self
    
    def setbit(self, bit, setorunset):
        if setorunset: self |= bit
        else: del self[bit]
        return self
    
    def __ior__(self, bits):
        self.value |= self._getval(bits)
        return self 
    
    def __or__(self, o):
        return self.value | self._getval(o)
    
    def __ror__(self, o):
        return self | o

    def __invert__(self):
        return ~self.value

    def __iand__(self, o):
        self.value = self.value & self._getval(o)
        return self
    
    def __and__(self, o):
        return self.value & self._getval(o)
    
    def __rand__(self, o):
        return self & o
    
    def __contains__(self, bits):
        if type(bits) in (list, tuple):
            return all([self._getval(b) in self for b in bits])
        else:
            return bool(self.value & self._getval(bits))
        
    def __delitem__(self, bits):
        if type(bits) in (list, tuple):
            newval = self.value
            for b in bits:
                newval &= ~self._getval(b)
            self.value = newval
        else:
            self.value = self.value & ~self._getval(bits) 
            
    def __iter__(self):
        return self._iterator(self.value)
         
    def __eq__(self, o):
        return self.value == self._getval(o)
    
    def __ne__(self, o):
        return not self == o
         
    def __str__(self):
        return bin(self.value)
    
    def readable(self, bitmask):
        return ' | '.join([bitmask[b] for b in self])
    
    
class BoolVar(Var):
    '''
    Represents a boolean variable.
    '''
    
    def __iand__(self, o):
        self.value = bool(self) and o
        return self
    
    def __ior__(self, o):
        self.value = bool(self) or o
        return self
    
    
    
class NumVar(Var):
    '''
    A variable representing a numeric value.
    '''    


    def __add__(self, o):
        return self.value + self._getval(o)
    
    def __radd__(self, o):
        return self + o
     
    def __sub__(self, o):
        return self.value - self._getval(o)
    
    def __rsub__(self, o):
        return self - o
     
    def __truediv__(self, o):
        return float(self.value) / self._getval(o)
    
    def __floordiv__(self, o):
        return self.value / self._getval(o)
    
    def __rdiv__(self, o):
        return o / self.value
     
    def __mul__(self, o):
        return self.value * self._getval(o)
    
    def __rmul__(self, o):
        return self * o
     
    def __iadd__(self, o):
        self.set(self + o)
        return self
         
    def __isub__(self, o):
        self.set(self.value - o)
        return self
     
    def __idiv__(self, o):
        self.set(self.value / o)
        return self
     
    def __imul__(self, o):
        self.set(self.value * o)
        return self
    
    def __eq__(self, o):
        return self.value == self._getval(o)
    
    def __ne__(self, o):
        return not self == o
    
    def round(self):
        return int(round(self.value))
    

class StringVar(Var):
    '''
    A variable representing a string.
    '''
    
    def __add__(self, o):
        return self.value + self._getval(o)
    
    def __radd__(self, o):
        return self._getval(o) + self.value
    
    def __iadd__(self, o):
        self.set(self + o)
        return self
    
    def __eq__(self, o):
        return self.value == self._getval(o)
    
    def __ne__(self, o):
        return not self == o
    
    
class BoundedDim(object):
    
    def __init__(self, _min, _max, value=None):
        self._min = Var(_min)
        self._max = Var(_max)
        self._value = Var(value)
        self.clean()
        
    def __call__(self):
        return self.value
        
    @property
    def min(self):
        return self._min()
    
    @min.setter
    def min(self, m):
        if m is not None and self.min is not None:
            m = max(m, self.min)
        self._min.set(m)
        if m == self.max:
            self._value.set(m)
        
    @property
    def max(self):
        return self._max()  
    
    @max.setter
    def max(self, m):
        if m is not None and self.max is not None:
            m = min(m, self.max)
        self._max.set(m)
        if m == self.min:
            self._value.set(m)
        
    @property
    def value(self):
        if self.min == self.max: return self.min
        return self._value()
        
    @value.setter
    def value(self, v):
        if v is not None:
            v = min(self.max, max(self.min, v))
#             if self.min is not None and self.min > v:
#                 raise ValueError('Value must not be smaller than minimum value: min: %s, value: %s' % (self.min, v))
#             if self.max is not None and self.max < v:
#                 raise ValueError('Value must not be larger than maximum value.')
        self._value.set(v)
        return self.value
        
    @property
    def dirty(self):
        return self._min.dirty or self._max.dirty or self._value.dirty
    
    def clean(self):
        self._min.clean()
        self._max.clean()
        self._value.clean()
    
    def __str__(self):
        return '<Dim[%s < %s < %s]>' % (self.min, self.value, self.max)
        

class Dim(object):
    '''
    Represents an abstract dimension value.
    '''
    
    def __init__(self, value):
        if value is None or type(value) not in (float, int):
            raise Exception('Illegal value for a dimension: %s' % repr(value))
        self._value = value
        
    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, v):
        self._value = v
        return self.value
        
    def __gt__(self, o):
        o = parse_value(o)
        return self._value > (o.value if isinstance(o, Dim) else o)
    
    def __lt__(self, o):
        o = parse_value(o)
        return self._value < (o.value if isinstance(o, Dim) else o)
    
    def __le__(self, o):
        o = parse_value(o)
        return self._value <= (o.value if isinstance(o, Dim) else o)
    
    def __ge__(self, o):
        o = parse_value(o)
        return self._value >= (o.value if isinstance(o, Dim) else o)
    
    def __eq__(self, o):
        o = parse_value(o)
        return self._value == (o.value if isinstance(o, Dim) else o)
    
    def __ne__(self, o):
        return not self == o
    
    def __add__(self, s):
        s = parse_value(s)
        if isinstance(s, Percent):
            return self + s.of(self.value)
        elif isinstance(s, type(self)):
            return self + s.value
        else:
            return type(self)(self.value + s)
        
    def __radd__(self, s):
        return self + s
    
    def __rsub__(self, s):
        return s - self.value
        
    def __sub__(self, s):
        s = parse_value(s)
        if isinstance(s, Percent):
            return self - s.of(self.value)
        elif isinstance(s, type(self)):
            return self - s.value
        else:
            return type(self)(self.value - s)
        
    def __mul__(self, t):
        t = parse_value(t)
        if isinstance(t, type(self)):
            return self * t.value
        else:
            return type(self)(self.value * t)
    
    def __rmul__(self, t):
        return self * t
        
    def __str__(self):
        return str(self._value)
        
    def __repr__(self):
        return '<%s[%s] at 0x%x>' % (type(self).__name__, str(self), id(self))

    
class Pixels(Dim):
    '''
    Represents a dimension of pixel units.
    '''
    
    def __init__(self, v):
        if isinstance(v, str):
            v = v.strip()
            if v.endswith('px'):
                Dim.__init__(self, int(v[:-2]))
            else:
                raise Exception('Illegal number format: %s' % repr(v))
        elif isinstance(v, Dim):
            Dim.__init__(self, v.value)
        else:
            Dim.__init__(self, v)

    def __round__(self):
        return px(int(round(self.value)))

    def __truediv__(self, d):
        s = parse_value(d)
        return px(int(round(self.value / (s.value if type(d) == Pixels else d))))
    
    def __add__(self, o):
        return px(int(round(Dim.__add__(self, o).value)))
    
    def __sub__(self, o):
        return px(int(round(Dim.__sub__(self, o).value)))

    def __mul__(self, o):
        return px(int(round(Dim.__mul__(self, o).value)))
    
    def __str__(self):
        return '%spx' % self._value

    def __call__(self):
        return self.value

    def __int__(self):
        return self.value

    def num(self):
        return self._num

    def __float__(self):
        return float(self.value)

#     @property
#     def json(self):
#         return self.value
    
    
def px(v):
    ''' Creates a new pixel dimension with the value v.'''
    if type(v) is Pixels: v = v.value
    return Pixels(v)


class Percent(Dim):
    '''Represents an abstract percentage value.'''
    
    def __init__(self, v):
        if isinstance(v, str):
            v = v.strip()
            if v.endswith('%'):
                Dim.__init__(self, float(v[:-1]))
            else:
                raise Exception('Illegal number format: %s' % v)
        else:
            Dim.__init__(self, v)
            
    def of(self, v):
        if type(v) is float:
            return self.value * v / 100.
        if type(v) is int:
            return int(round(self.value * v / 100.))
        if isinstance(v, str):
            v = parse_value(v)
        if isinstance(v, Pixels):
            return Pixels(int(round((v.value * self._value / 100.))))
        return type(v)((v.value if isinstance(v, Dim) else v) * self._value / 100.)
            
    def __str__(self):
        return '%f%%' % self._value
    
    @property
    def float(self):
        return self.value / 100.
    

def pc(v):
    ''' Creates a new percentage dimension with the value v.'''
    return Percent(v)
            
        
def color(c):
    if isinstance(c, Color): return c
    return Color(c)
    
class Color(object):
    
    names = {'red': '#C1351D', 
             'green': '#0f9d58',
             'light green': '#5FBA7D',
             'dark green': '#008000', 
             'blue': '#4285f4',
             'gray': '#8a8a8a', 
             'grey': '#8a8a8a',
             'light grey': '#c0c0c0',
             'light gray': '#c0c0c0',
             'dark grey': '#404040',
             'dark gray': '#404040',
             'white': '#FFF', 
             'yellow': '#f4b400', 
             'transp': '#FFFFFF00',
             'cyan': '#00acc1',
             'purple': '#ab47bc',
             'orange': '#ff7043',
             'marine': '#1e3f5a',
             'black': '#000'}
    
    
    def __init__(self, html=None, rgb=None, hsv=None, fct=None, alpha=None):
        if sum([1 for e in (html, rgb, hsv) if e is not None]) != 1:
            raise Exception('Need precisely one color value argument')
        if fct is not None:
            if fct.name == 'rgb': rgb = fct.args
            elif fct.name == 'hsv': hsv = fct.args
            else: raise Exception('Unknown color value function: %s' % str(fct))
        if html is not None:
            if html in Color.names: html = Color.names[html]
            if html.startswith('#'):
                if len(html) < 5: html += html[1:] # for short notations like #ccc
                self._r, self._g, self._b = int(html[1:3], base=16) / 255., int(html[3:5], base=16) / 255., int(html[5:7], base=16) / 255.
                self._a = float(int(html[7:9], base=16)) / 255. if len(html) > 7 else 1.
            else: raise Exception('Illegal color value: %s' % html)
        elif rgb is not None:
            self._r, self._g, self._b = rgb[:3]
            self._a = rgb[3] if len(rgb) > 3 else 1.
        elif hsv is not None:
            self._r, self._g, self._b = hsv_to_rgb(*hsv[:3])
            self._a = hsv[3] if len(hsv) > 3 else 1.
        else: raise Exception('Illegal color value: %s' % ' '.join(map(str, (html, rgb, hsv, fct, alpha))))
        if alpha is not None: self._a = alpha
    
    @property
    def red(self):
        return self._r
    
    @property
    def green(self):
        return self._g
    
    @property
    def blue(self):
        return self._b

    @property
    def hue(self):
        return rgb_to_hsv(*self.rgb)[0]
    
    @property
    def saturation(self):
        return rgb_to_hsv(*self.rgb)[1]
    
    @property
    def value(self):
        return rgb_to_hsv(*self.rgb)[2]
    
    @property
    def redi(self):
        return int(round(self._r * 255))
    
    @property
    def greeni(self):
        return int(round(self._g * 255))
    
    @property
    def bluei(self):
        return int(round(self._b * 255))

    @property
    def huei(self):
        return int(round(rgb_to_hsv(*self.rgb)[0] * 255))
    
    @property
    def saturationi(self):
        return int(round(rgb_to_hsv(*self.rgb)[1] * 255))
    
    @property
    def valuei(self):
        return int(round(rgb_to_hsv(*self.rgb)[2] * 255))
        
    @property
    def alpha(self):
        return self._a
    
    @property
    def alphai(self):
        return int(round(self._a * 255))
        
    @property
    def rgbi(self):
        return (self.redi, self.greeni, self.bluei)
        
    @property
    def rgb(self):
        return (self._r, self._g, self._b)
    
    @property
    def rgba(self):
        return (self._r, self._g, self._b, self._a)
    
    @property
    def hsv(self):
        return rgb_to_hsv(self._r, self._g, self._b)
        
    @property
    def html(self):
        return '#%.2x%.2x%.2x' % tuple([int(round(255 * x)) for x in self.rgb])
    
    @property
    def htmla(self):
        return self.html + '%.2x' % int(round((self._a * 255.)))
        
    def __str__(self):
        return self.htmla
    
    def __repr__(self):
        return '<Color[%s] at 0x%x>' % (str(self), hash(self))
    
    def __eq__(self, o):
        if isinstance(o, str):
            o = Color(html=o)
        return self.htmla == o.htmla
        
    def __ne__(self, o):
        return not self == o
    
    def darker(self, scale=.1):
        hsv = self.hsv
        return Color(hsv=(hsv[0], hsv[1] + (1 - hsv[1]) * scale, hsv[2] - hsv[2] * scale), alpha=self.alpha)
    
    def brighter(self, scale=.1):
        hsv = self.hsv
        return Color(hsv=(hsv[0], hsv[1] - hsv[1] * scale, hsv[2] + (1 - hsv[2]) * scale), alpha=self.alpha)
    
def parse_value(v, default=None):
    if isinstance(v, str):
        if v.endswith('px'): return Pixels(v)
        elif v.endswith('%'): return Percent(v)
        elif v.startswith('#') or (default is Color and v in Color.names): return Color(v)
    else: 
        return v if (default is None or v is None or type(v) is default) else default(v)
    

def toint(v):
    if isinstance(v, Dim): return v.value
    elif type(v) is int: return v
    elif type(v) is list: return [toint(e) for e in v]
    elif type(v) is tuple: return tuple([toint(e) for e in v])
    else: int(v)
    
 
class Font(object):
    
    def __init__(self, family='Arial', size='12px', style=FONT.NONE):
        family = [family] if type(family) is not list else family
        self._family = [f.strip('"\'') for f in family] 
        self._size = parse_value(size, Pixels)
        self._style = BitField(style, track=False)
        
    @property
    def bf(self):
        return FONT.BF in self._style
    
    @property
    def it(self):
        return FONT.IT in self._style
    
    @property
    def style(self):
        return self._style
    
    @property
    def family(self):
        return self._family
     
    @property
    def size(self):
        return self._size    

    def __str__(self):
        s = []
        s.append(str(self.size))
        if self.bf: s.append('bold')
        if self.it: s.append('italic')
        s.append(reduce(str.__add__, ', '.join([(('"%s"' % f) if ' ' in f else f) for f in self._family])))
        return ' '.join(s)

    def __repr__(self):
        return '<Font[%s] at 0x%x>' % (str(self), hash(self))
    
    def modify(self, family=None, size=None, it=None, bf=None):
        '''
        Creates a modified copy of this font, whose attributes are all the same
        as in the original font, but the attributes given in the parameters
        have been replaced by the given ones. The original font is not altered.
        '''
        style = BitField(self._style)
        if it is not None:
            style.setbit(FONT.IT, it)
        if bf is not None:
            style.setbit(FONT.BF, bf)
        return Font(family=ifnone(family, self.family), size=ifnone(size, self.size), style=style)


class SVG(object):

    def __init__(self):
        self.tree = None
        self.root = None
        self._content = None
        self.fpath = None
        self._width = None
        self._height = None
        self.namespaces = {'svg': "http://www.w3.org/2000/svg"}

    def load(self, cnt, w=None, h=None, css=None):
        self.root = ET.fromstring(cnt)

        if css is not None:
            with open(css) as fi:
                s = defs.format(fi.read())
                defstag = ET.fromstring(s)
                self.root.append(defstag)
        if 'viewBox' in self.root.attrib:
            w, h = self.root.attrib['viewBox'].split()[-2:]
        elif w is not None and h is not None:
            self.root.attrib.update({'width': '{}px'.format(w),
                                     'height': '{}px'.format(h),
                                     'viewBox': "0.0 0.0 {} {}".format(w, h)})
        else:
            self.root.attrib.update({'width': '900px',
                                     'height': '600px',
                                     'viewBox': "0.0 0.0 900.0 600.0"})
            w, h = (800, 600)
        if 'xmlns' not in self.root.attrib:
            self.root.attrib.update({'xmlns': "http://www.w3.org/2000/svg",
                                     'xmlns:xlink': "http://www.w3.org/1999/xlink"})

        self._width = int(float(w))
        self._height = int(float(h))
        stream = BytesIO()
        self.save(stream)
        self._content = str(stream.getvalue())
        stream.close()
        return self

    def open(self, fpath):
        self.fpath = fpath
        self.tree = ET.parse(fpath)
        self.root = self.tree.getroot()
        w, h = self.root.attrib['viewBox'].split()[-2:]
        self._width = int(w)
        self._height = int(h)
        stream = BytesIO()
        self.save(stream)
        self._content = str(stream.getvalue())
        stream.close()
        return self

    def close(self):
        pass

    def setattr(self, id, attr, val):
        elem = self.root.find('*//*[@id="{}"]'.format(id), self.namespaces)
        if elem is None:
            return self
        elem.set(attr, val)
        # self.tree.write(self.fpath)
        stream = BytesIO()
        self.save(stream)
        self._content = str(stream.getvalue())
        stream.close()
        return self

    @property
    def cnt(self):
        stream = BytesIO()
        self.save(stream)
        return stream.getvalue()

    @property
    def size(self):
        return px(self._width), px(self._height)

    def resize(self, w=None, h=None):
        self._width = w
        self._height = h
        return self

    def save(self, stream=None):
        stream.write(ET.tostring(self.root, encoding='utf-8'))


class Image(object):
    
    def __init__(self, filepath=None, content=None, mimetype=None):
        self._img = None
        self._filepath = filepath
        self._cnt = content
        if self.filepath is not None:
            self._mimetype = mimetypes.guess_type(' .' + self.fileext)[0]
        else:
            self._mimetype = mimetypes.guess_type(' .' + 'png')[0]
        if mimetype is not None:
            self._mimetype = mimetype
        self.load()
        self.close()
        
    def load(self):
        if self.filepath is None:
            if self._cnt is not None:
                try:
                    self._img = PILImage.open(BytesIO(self._cnt))
                    self._content = self._cnt
                except Exception:
                    try:
                        self._content = base64.b64decode(self._cnt)
                        self._img = PILImage.open(BytesIO(self._content))
                    except:
                        self._content = self._cnt
                        self._img = SVG().load(self._cnt)
                        self._mimetype = 'image/svg+xml'
                return self
            else:
                raise Exception('Unable to load Image without filepath or content!')
        if self.fileext == 'svg':
            self._img = SVG().open(self._filepath)
            with open(self.filepath) as f: self._content = f.read()
        else:
            self._img = PILImage.open(self._filepath)
            with open(self.filepath, 'rb') as f:
                self._content = f.read()
        return self
        
    def close(self):
        if self._img is not None:
            self._img.close()

    @property
    def mimetype(self):
        return self._mimetype
            
    @property
    def content(self):
        if hasattr(self._img, '_content'):
            return self._img._content
        return self._content

    @property
    def filename(self):
        if self.filepath is not None:
            return os.path.basename(self._filepath)
        return None

    @property
    def filepath(self):
        return self._filepath
        
    @property
    def fileext(self):
        if self._filepath is not None:
            return self._filepath.split('.')[-1]
        elif self._mimetype is not None:
            return mimetypes.guess_extension(self._mimetype).split('.')[-1]
        return None
        
    @property
    def width(self):
        return px(self._img.size[0])
    
    @width.setter
    def width(self, w):
        self.resize(width=w)
    
    @property
    def height(self):
        return px(self._img.size[1])
    
    @height.setter
    def height(self, h):
        self.resize(height=h)
    
    @property
    def size(self):
        return self.width, self.height

    @size.setter
    def size(self, s):
        w, h = s
        self.resize(width=w, height=h)
    
    def __repr__(self):
        return '<Image[%sx%s] "%s" at 0x%x>' % (self.width, self.height, self.filename, hash(self))
    
    def __str__(self):
        return '<Image[%sx%s] "%s">' % (self.width, self.height, self.filename)

    def resize(self, width=None, height=None):
        '''
        Scales this image according to the given parameters.
        
        If both ``width`` and ``height`` are given, the image is scaled accordingly.
        If only one of them is specified, the other one is computed proportionally.
        
        Both ``width`` and ``height`` can be either ``str``, ``int``, :class:`pyrap.Pixels`,
        or :class:`pyrap.Percent` values. If ``int``, they will be treated as pixel values
        
        :return:     this image instance.
        '''
        w = self.width
        h = self.height
        ratio = float(h.value) / float(w.value)
        # if either of them is int, convert to pixels by default
        if type(width) is int:
            width = px(width)
        if type(height) is int:
            height = px(height)
        # if either of them is string, parse the value
        if isinstance(width, str):
            width = parse_value(width)
        if isinstance(height, str):
            height = parse_value(height)
        if isinstance(width, Percent):
            w = width.of(w)
        else: w = width
        if isinstance(height, Percent):
            h = height.of(h)
        else:
            h = height
        if height is None:
            h = w * ratio
        elif width is None:
            w = h / ratio
        self.load()
        stream = BytesIO()
        if 'svg' in self.fileext:
            self._img = self._img.resize(w.value, h.value)
            self._img.save(stream)
        else:
            self._img = self._img.resize((w.value, h.value), PILImage.LANCZOS)
            ext = self.fileext.lower()
            self._img.save(stream, format=ext if ext != 'jpg' else 'jpeg')

        self._content = stream.getvalue()
        stream.close()
        return self

        
        

if __name__ == '__main__':
    
    print(Color('#0000ff'))
    
    exit(0)
    
    v1 = NumVar()
    v2 = NumVar()
    v3 = NumVar()
    v1.bind(v2)
    v3.bind(v2)
    v3.bind(v2)
    print(v1, v2, v3)
    v1.set(5)
    print(v1, v2, v3)
    v2.set(10)
    print(v1, v2, v3)
    b = BoolVar(False)
    b2 = BoolVar(True)
    print((not b)) 
    
    FONT = BitMask('IT', 'BF', "STRIKETHROUGH")

    bits = BitField(FONT.IT | FONT.BF)
    for b in bits: 
        out(FONT[b]) 
    print('|'.join([FONT[b] for b in bits]))
    
    print(bits.readable(FONT))
    exit(0)
    
    print(Font(style=FONT.IT | FONT.BF, family=['Arial', 'Nimbus Sans', 'sans-serif'], size=13))
    
    def getdirty(v, d, c):
        print((repr(v), 'is now', {True:'dirty', False:'clean'}[d], 'by', c))
    
    s = StringVar('hello', on_change=lambda v, c: out(repr(v), 'was modified by', c))
    s += ', world!'
    print(s)
    
    
    n1 = NumVar(1, history=True, on_dirty=getdirty)
    n2 = NumVar(7)
    print(n1 + 2 * n2)
    n1 += 5.
    n1 /= 10
    print(n1)
    print(n1.undo())
    print(n1)
    print(n1.redo())
    print(n1)
    print(n1._values)
