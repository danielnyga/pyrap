'''
Created on Oct 10, 2015

@author: nyga
'''
from pyrap.locations import pyrap_path
from cssutils import parseFile
import os
from cssutils.css.csscomment import CSSComment
from collections import defaultdict
from cssutils.css.value import Value, ColorValue, DimensionValue, URIValue,\
    CSSFunction
import uuid
import json
from pyrap import pyraplog
from logging import DEBUG
from pyrap.types import Color, Pixels, parse_value, Dim,\
    Font, Image, pc, Percent, px
from pyrap.types import BitField
import sys
from copy import copy, deepcopy
import re
from pyrap.constants import BORDER, GRADIENT, ANIMATION, FONT, SHADOW, CURSOR,\
    RWT
from pyrap.utils import out
import math

TYPE = 'type-selector'
PSEUDOCLASS = 'pseudo-class'
ATTRIBUTE = 'attribute-selector'
UNIVERSAL = 'universal'

logger = pyraplog.getlogger(__name__)

def isnone(cssval):
    if isinstance(cssval, Value):
        return cssval.value == 'none'
    elif type(cssval) is list and len(cssval) == 1:
        return isnone(cssval[0])
    else: return False
    
def none_or_value(values):
    if type(values) is not list:
        values = [values]
    ret = []
    for v in values:
        if isinstance(v, DimensionValue):
            ret.append(v.value)
        elif isinstance(v, Value) and v.cssText == 'none':
            ret.append('none')
        else:
            ret.append(str(v.cssText.encode('utf8')))
    if len(ret) == 1:return ret[0]
    else: return ret
        
    
    
def totuple(value):
    if type(value) is dict:
        return tuple([(totuple(k), totuple(value[k])) for k in sorted(value)])
    elif type(value) in (list, tuple):
        return tuple([totuple(e) for e in value])
    else:
        return value

def tostring(x):
    if type(x) in (list, tuple):
        return ' '.join(map(str, x))
    else: return str(x)

class Theme(object):
    
    def __init__(self, name):
        self.name = name
        self.rules = defaultdict(list)
        
    def extract(self, *types):
        theme = Theme('%s-%s' % (self.name, '/'.join(types)))
        for t in types:
            theme.rules[t] = deepcopy(self.rules[t])
        return theme
        
    def load(self, filename=None):
        if filename is None:
            filename = os.path.join(pyrap_path, 'css', 'default.css')
        csscontent = parseFile(filename, validate=False)
        self._build_theme_from_rules(csscontent.cssRules)
        return self

    def get_rule_exact(self, typ, attrs=set(), pcs=set()):
        ruleset = self.rules[typ]
        for rule in ruleset:
            if rule.perfect_match(attrs, pcs): return rule
        rule = ThemeRule(typ, set(attrs), set(pcs))
        ruleset.append(rule)
        return rule
    
    def _get_property(self, name, typ, attrs=set(), pcs=set()):
        ruleset = self.rules[typ]
        matches = []
        for rule in ruleset:
            match = rule.match(attrs, pcs)
            if match == (-1, -1): continue
            matches.append((rule, match))
        # sort the matches in ascending order
        matches = sorted(matches, key=lambda m: m[1][1], reverse=True)
        matches = sorted(matches, key=lambda m: m[1][0], reverse=True)
        while matches:
            m = matches.pop(0)
            r = m[0] # the rule
            if name in r.properties: 
                return r.properties[name]
        return None
    
    def get_property(self, name, typ, attrs=set(), pcs=set()):
        for args in ((attrs, pcs), (set(), pcs), (attrs, set()), (set(), set())):
            prop = self._get_property(name, typ, *args)
            if prop is not None: 
                return prop
        if typ == '*': return None
        return self.get_property(name, '*', attrs, pcs)
        
    
    def write(self, stream=sys.stdout):
        stream.write('<Theme "%s" %d rules>\n' % (self.name, len(self.rules)))
        for typ in sorted(self.rules): 
            for rule in self.rules[typ]:
                rule.write(stream)
                
        
    def _build_theme_from_rules(self, cssrules):
        for cssrule in cssrules:
            if isinstance(cssrule, CSSComment): continue
            selectors, properties = self._convert_css_rule(cssrule)
            for typ, attrs, pcs in selectors:
                rule = self.get_rule_exact(typ, attrs, pcs)
                for name, value in properties.iteritems():
                    if name == 'border':
                        for name in ('border-left', 'border-top', 'border-right', 'border-bottom'):
                            rule.properties[name] = copy(value)
                        continue
                    rule.properties[name] = copy(value)
            
        
    def _build_selector_triplets(self, selectors):
        typesel = []
        attrsel = []
        pseudosel = []
        curattr = []
        curpseudo = []
        for i, s in enumerate(selectors):
            if s[0] == TYPE:
                typesel.append(s[1])
                if i > 0:
                    attrsel.append(curattr)
                    pseudosel.append(curpseudo)
                    curattr = []
                    curpseudo = []
            elif s[0] == ATTRIBUTE:
                curattr.append('[' + s[1])
            elif s[0] == PSEUDOCLASS:
                curpseudo.append(s[1])
        attrsel.append(curattr)
        pseudosel.append(curpseudo)
        curattr = []
        curpseudo = []
        return [(t, set(a), set(p)) for t, p, a in zip(typesel, pseudosel, attrsel)]    
    
    def _convert_css_rule(self, cssrule):
        selectors = [(str(item.type), item.value) for selector in cssrule.selectorList for item in selector.seq if item.type in (TYPE, PSEUDOCLASS, ATTRIBUTE, UNIVERSAL)]
        selectors = tuple([(t if t != UNIVERSAL else TYPE, str(i[1]) if t in (TYPE, UNIVERSAL) else str(i)) for (t, i) in selectors])
        triplets = self._build_selector_triplets(selectors)
        properties = self._convert_css_properties(cssrule.style.getProperties(all=True))
        return triplets, properties
    
        
    def _convert_css_properties(self, props):
        return dict([self._convert_css_property(prop) for prop in props])
            
    
    def _convert_css_property(self, prop):
        name = prop.name
        values = [prop.propertyValue.item(i) for i in range(prop.propertyValue.length)]
        if name in ('border', 'border-left', 'border-top', 'border-right', 'border-bottom'):
            return name, self._build_border(values)
        elif 'color' in name:
            color = self._build_color(values)
            if type(color) is not Color:
                color = self._build_gradient(values)
            return name, color
        elif name in ('margin',):
            return name, self._build_margin(values)
        elif name in ('border-radius', 'border-topleft-radius', 'border-topright-radius', 'border-bottomright-radius', 'border-bottomleft-radius'):
            return name, self._build_border_radius(values)
        elif name in ('padding', 'padding-left', 'padding-right', 'padding-top', 'padding-bottom'):
            return name, self._build_padding(values)
        elif name in ('height', 'width', 'spacing', 'min-height', 'min-width', 'max-height', 'max-width'):
            return name, self._build_dim(values)
        elif name in ('opacity',):
            return name, self._build_percentage(values)
        elif name in ('cursor',):
            return name, self._build_cursor(values)
        elif name in ('font', 'rwt-fontlist'):
            return name, self._build_font(values)
        elif name in ('image', 'background-image', 'rwt-information-image', 'rwt-error-image', 'rwt-warning-image', 'rwt-working-image', 'rwt-question-image'):
            img = self._build_image(values)
            if type(img) is not Image:
                img = self._build_gradient(values)
            return name, img
        elif name.endswith('shadow'):
            return name, self._build_shadow(values)
        elif name == 'animation':
            return name, self._build_animation(values)
        else: return name, none_or_value(values)
        
        
    def _convert_fct(self, f):
        fct = Theme.Function(None, [])
        curarg = []
        for i in f.seq:
            if i.type == 'FUNCTION':
                fct.name = i.value[:-1] # function name
            elif i.type in ('CHAR'):
                if (i.value == u',' or i.value == u')') and curarg:
                    fct.args.append(curarg if len(curarg) > 1 else curarg[0])
                    curarg = []
            elif i.type.endswith('Value'):
                curarg.append(none_or_value(i.value))
            elif i.type == 'DIMENSION':
                if '%' in i.value.dimension:
                    curarg.append(pc(i.value.value))
                else:
                    curarg.append(i.value.value)
            elif i.type == 'Function':
                fct.args.append(self._convert_fct(i.value))
        return fct
    
    
    def _build_color(self, values):
        if len(values) != 1:
            raise Exception('Illegal color value: %s' % str(values))
        v = values[0] 
        if isinstance(v, ColorValue):
            m = re.match(r'rgb\((?P<r>\d+)\s*?,\s*?(?P<g>\d+)\s*?,\s*?(?P<b>\d+)\s*?\)', str(v.cssText))
            if m is not None:
                return Color(rgb=(float(m.group('r')) / 255, float(m.group('g'))/255, float(m.group('b'))/255))
            else:
                m = re.match(r'rgba\((?P<r>\d+)\s*?,\s*?(?P<g>\d+)\s*?,\s*?(?P<b>\d+)\s*?,\s*?(?P<a>.+)\s*?\)', str(v.cssText))
                if m is not None:
                    return Color(rgb=(float(m.group('r')) / 255, float(m.group('g'))/255, float(m.group('b'))/255), alpha=float(m.group('a')))
            v = parse_value(str(v.cssText))
            return v
        elif isinstance(v, CSSFunction):
            return Color(fct=self._convert_fct(v))
        v = none_or_value(v)
        return v
    
        
    def _build_border(self, values):
        color, width, style = None, 0, BORDER.NONE
        for v in values:
            if isinstance(v, ColorValue):
                color = v.cssText
            elif isinstance(v, DimensionValue):
                width = v.value
            elif isinstance(v, Value):
                if v.value == 'solid': style = BORDER.SOLID
                elif v.value == 'dotted': style = BORDER.DOTTED
                elif v.value == 'none': style = BORDER.NONE
        return Theme.Border(color=color, width=width, style=style)
        
    
    def _build_border_radius(self, values):
        if type(values) is not list or not all([isinstance(v, DimensionValue) for v in values]):
            return none_or_value(values)
        values = [v.value for v in values]
        return Theme.BorderRadius(*values)
    
    
    def _build_padding(self, values):
        if type(values) is not list or not all([isinstance(v, DimensionValue) for v in values]):
            return none_or_value(values)
        values = [v.value for v in values]
        return Theme.Padding(*values)
    
    
    def _build_margin(self, values):
        if type(values) is not list or not all([isinstance(v, DimensionValue) for v in values]):
            return none_or_value(values)
        values = [v.value for v in values]
        return Theme.Margin(*values)
    
        
        
    def _build_dim(self, values):
        if len(values) != 1:
            raise Exception('Illegal dimension value: %s' % '.'.join(map(str, values)))
        if not isinstance(values[0], DimensionValue):
            return none_or_value(values[0])
        return parse_value(values[0].value, Pixels)
    
    
    def _build_percentage(self, values):
        if len(values) != 1:
            raise Exception('Illegal dimension value: %s' % '.'.join(map(str, values)))
        if not isinstance(values[0], DimensionValue):
            return none_or_value(values[0])
        return Percent(values[0].value * 100.)
    
    
    def _build_cursor(self, values):
        if len(values) != 1 and not isinstance(values[0], Value):
            return none_or_value(None)
        style = {'default': CURSOR.DEFAULT, 'pointer': CURSOR.POINTER}
        return Theme.Cursor(style[values[0].cssText])
    
    
    def _build_font(self, values):
        size = None
        family = []
        style = BitField(FONT.NONE)
        for v in values:
            if isinstance(v, DimensionValue):
                size = v.value
            elif isinstance(v, Value):
                if v.cssText == 'italic': style |= FONT.IT
                if v.cssText == 'bold': style |= FONT.BF
                else:
                    family.append(str(v.value))
        if size is None or not family:
            raise Exception('Illegal font: %s' % ''.join([v.cssText for v in values]))
        return Font(family=family, size=size, style=style)
    
    
    def _build_image(self, values):
        if len(values) != 1:
            raise Exception('Illegal image value: %s' % values)
        if isinstance(values[0], URIValue):
            imgpath = os.path.join(pyrap_path, values[0].value)
            img = Image(imgpath)
            return img
        return none_or_value(values[0])
    
    
    def _build_shadow(self, values):
        if len(values) == 1: return Theme.Shadow(0, 0, 0, None, SHADOW.NONE) #none_or_value(values[0])
        dims, c, s = [0, 0, 0], 'black', SHADOW.OUT
        dimcount = 0
        for v in values:
            if isinstance(v, DimensionValue):
                dims[dimcount] = v.value
                dimcount += 1
            elif isinstance(v, ColorValue):
                c = Color(v.value)
            elif isinstance(v, Value) and v.value == 'inset': 
                s = SHADOW.IN
        return Theme.Shadow(x=dims[0], y=dims[1], r=dims[2], color=c, style=s)
     
     
    def _build_animation(self, values):
        if len(values) < 6:
            return none_or_value(values[0])
        a = {'in': [None, None], 'out': [None, None]}
        key = None
        for v in values:
            if isinstance(v, DimensionValue): a[key][0] = v.value
            elif isinstance(v, Value):
                if v.value == 'fadeIn': key = 'in'
                elif v.value == 'fadeOut': key = 'out'
                elif v.value == 'ease-in': a[key][1] = ANIMATION.EASE_IN
                elif v.value == 'ease-out': a[key][1] = ANIMATION.EASE_OUT
                elif v.value == 'linear': a[key][1] = ANIMATION.LINEAR
        return Theme.Animation(a['in'][1], a['out'][1], a['in'][0], a['out'][0])
                
    
    def _build_gradient(self, values):
        if len(values) != 1: raise Exception('Illegal gradient value')
        if not isinstance(values[0], CSSFunction):
            return none_or_value(values[0])#raise Exception('unexpected gradient value: %s' % values)
        val = values[0]
        fct = self._convert_fct(val)
        grad = self._build_gradient_rec(fct)
        return Theme.Gradient(grad['percents'], map(parse_value, grad['colors']), grad['orientation'])
    
    def _build_gradient_rec(self, fct, gradient=None):
        if fct.name == 'gradient':
            gradient = {'percents': [], 'colors': [], 'orientation': None}
            orientation = []
            style = None
            for arg in fct.args:
                if type(arg) is Theme.Function: self._build_gradient_rec(arg, gradient)
                elif arg == 'linear':
                    style = arg
                elif type(arg) is list and len(arg) == 2 and [a for a in arg if a in ('left', 'top', 'right', 'bottom')]:
                    if orientation:
                        if orientation[0] != arg[0]: gradient['orientation'] = GRADIENT.HORIZONTAL
                        elif orientation[1] != arg[1]: gradient['orientation'] = GRADIENT.VERTICAL
                    else:
                        orientation.append(arg[0])
                        orientation.append(arg[1])
        elif fct.name == 'from':
            percent = pc(0)
            color = None
            for arg in fct.args:
                if type(arg) is Percent:
                    percent = arg
                else:
                    color = arg
            gradient['percents'].append(percent)
            gradient['colors'].append(color)
        elif fct.name == 'to':
            percent = pc(100)
            color = None
            for arg in fct.args:
                if type(arg) is Percent:
                    percent = arg
                else:
                    color = arg
            gradient['percents'].append(percent)
            gradient['colors'].append(color)
        elif fct.name == 'color-stop':
            percent = pc(100)
            color = None
            for arg in fct.args:
                if type(arg) is Percent:
                    percent = arg
                else:
                    color = arg
            gradient['percents'].append(percent)
            gradient['colors'].append(color)
        return gradient

        
    class Dim4(object):
        def __init__(self, values):
            if len(values) != 4: raise Exception('Illegal value: %s' % str(values))
            self._v1, self._v2, self._v3, self._v4 = tuple(values)
        
        def __str__(self):
            return '%s %s %s %s' % (str(self._v1), str(self._v2), str(self._v3), str(self._v4))
        
        def __repr__(self):
            return '<%s[%s] at 0x%x>' % (type(self).__name__, str(self), hash(self))
        
        @property
        def values(self):
            return [self._v1, self._v2, self._v3, self._v4]

    class Border(object):
        def __init__(self, color='black', width=1, style=BORDER.SOLID):
            self._color = parse_value(color)
            self._width = parse_value(width, Pixels)
            self._style = style
            
        @property
        def color(self):
            return self._color
        
        @property
        def width(self):
            return self._width
        
        @property
        def style(self):
            return self._style
            
        def __str__(self):
            return '%s %s %s' % (self._width, self._style, self._color)
        
        def __repr__(self):
            return '<Border[%s] at 0x%x>' % (self, hash(self))
        
        
    class BorderRadius(Dim4):
        def __init__(self, topleft=None, topright=None, bottomright=None, bottomleft=None):
            values = [parse_value(v, Pixels) for v in (topleft, topright, bottomright, bottomleft) if v is not None]
            if len(values) == 1:
                values = [values[0]] * 4
            if len(values) != 4:
                raise Exception('Illegal value for border radius: %s' % values)
            Theme.Dim4.__init__(self, values)
        
        @property
        def topleft(self):
            return self._v1
        @property
        def topright(self):
            return self._v2
        @property
        def bottomright(self):
            return self._v3
        @property
        def bottomleft(self):
            return self._v4
        
            
    class Padding(Dim4):
        def __init__(self, top=None, right=None, bottom=None, left=None):
            values = [parse_value(v, Pixels) for v in (top, right, bottom, left) if v is not None]
            if len(values) == 1:
                values = [values[0]] * 4
            elif len(values) == 2:
                values = [values[0], values[1], values[0], values[1]]
            elif len(values) == 3:
                values = [values[0], values[1], values[2], values[1]]
            Theme.Dim4.__init__(self, values)

        @property
        def top(self):
            return self._v1
        @property
        def right(self):
            return self._v2
        @property
        def bottom(self):
            return self._v3
        @property
        def left(self):
            return self._v4
        
        
    class Margin(Dim4):
        def __init__(self, top=None, right=None, bottom=None, left=None):
            values = [parse_value(v, Pixels) for v in (top, right, bottom, left) if v is not None]
            if len(values) == 1:
                values = [values[0]] * 4
            elif len(values) == 2:
                values = [values[0], values[1], values[0], values[1]]
            elif len(values) == 3:
                values = [values[0], values[1], values[2], values[1]]
            Theme.Dim4.__init__(self, values)

        @property
        def top(self):
            return self._v1
        @property
        def right(self):
            return self._v2
        @property
        def bottom(self):
            return self._v3
        @property
        def left(self):
            return self._v4
        
        
    class Gradient(object):
        def __init__(self, percents, colors, orientation):
            self._percents = percents
            self._colors = colors
            self._orientation = orientation
            
        @property
        def percents(self):
            return self._percents
        
        @property
        def colors(self):
            return self._colors
        
        @property
        def orientation(self):
            return self._orientation
        
        def __str__(self):
            return 'percents: %s, colors: %s, orientation: %s' % (','.join(map(str, self.percents)), ','.join(map(str, self.colors)), self.orientation)
        
        
    class Shadow(object):
        def __init__(self, x, y, r, color, style=SHADOW.NONE):
            self._x = parse_value(x, Pixels)
            self._y = parse_value(y, Pixels)
            self._r = parse_value(r, Pixels)
            self._color = parse_value(color)
            self._style = style 
            
        @property
        def xoffset(self):
            return self._x
        
        @property
        def yoffset(self):
            return self._y
        
        @property
        def radius(self):
            return self._r
        
        @property
        def color(self):
            return self._color
        
        @property
        def style(self):
            return self._style
        
        def __str__(self):
            return '%s %s %s %s %s' % (self.style, self.xoffset, self.yoffset, self.radius, self.color)
        

    class Cursor(object):
    
        def __init__(self, style):
            self._style = style
            
        @property
        def style(self):
            return self._style

        def __str__(self):
            return CURSOR.str(self.style)
        
        
    class Animation(object):
        def __init__(self, instyle, outstyle, induration, outduration):
            self._in = instyle
            self._out = outstyle
            self._induration = induration
            self._outduration = outduration
                
        @property
        def instyle(self):
            return self._in
        
        @property
        def outstyle(self):
            return self._out
        
        @property
        def induration(self):
            return self._induration
        
        @property
        def outduration(self):
            return self._outduration
        
        def __str__(self):
            return json.dumps({'fade-in': [self.induration, self.instyle], 'fade-out': [self.outduration, self.outstyle]})
            
    class Function(object):
        '''
        Represents a symbolic function.
        '''
        
        def __init__(self, name, args):
            self._name = name
            self._args = args
            
        @property
        def name(self):
            return self._name
        
        @name.setter
        def name(self, n):
            self._name = n
            
        @property
        def args(self):
            return self._args
            
        def __str__(self):
            return '%s(%s)' % (self._name, ','.join(map(str, self._args)))
        
        
    
    class ValueMap(object):
        
        def __init__(self):
            self._values2hash = defaultdict(dict) # mapping from value tuples to hash ids
            self._hash2values = defaultdict(dict) # mapping from hash ids to value dicts
            self._hash2objects = defaultdict(dict) # mapping from hash ids to style objects
            
        def handle_value(self, value):
            category = None
            valdict = None
            if isinstance(value, Theme.Dim4) or isinstance(value, Theme.BorderRadius): 
                valdict = Theme.ValueMap._boxdim2json(value)
                category = 'boxdims'
            elif isinstance(value, Font): 
                valdict = Theme.ValueMap._font2json(value)
                category = 'fonts'
            elif isinstance(value, Color): 
                valdict = Theme.ValueMap._color2json(value)
                category = 'colors'
            elif isinstance(value, Theme.Border): 
                valdict = Theme.ValueMap._border2json(value)
                category = 'borders'
            elif isinstance(value, Theme.Animation) : 
                valdict = Theme.ValueMap._animation2json(value)
                category = 'animations'
            elif isinstance(value, Theme.Gradient) : 
                valdict = Theme.ValueMap._gradient2json(value)
                category = 'gradients'
            elif type(value) is Pixels : 
                valdict = Theme.ValueMap._dim2json(value)
                category = 'dimensions'
            elif isinstance(value, Theme.Shadow): 
                valdict = Theme.ValueMap._shadow2json(value)
                category = 'shadows'
            elif isinstance(value, Theme.Cursor) : 
                valdict = Theme.ValueMap._cursor2json(value)
                category = 'cursors'
            elif isinstance(value, Image) : 
                valdict = Theme.ValueMap._image2json(value)
                category = 'images'
            if category is None: return None
            key = str(value)
            if key in self._values2hash[category]:
                return self._values2hash[category][key]
            else:
                hashid = str(uuid.uuid1()).split('-')[0]
                if isinstance(value, Image): hashid += '.%s' % value.fileext
                self._values2hash[category][key] = hashid
                self._hash2values[category][hashid] = valdict
                self._hash2objects[category][hashid] = value
                return hashid
            
        @staticmethod
        def _border2json(border):
            return {'color': border.color.html if isinstance(border.color, Color) else border.color, 'width': border.width.value, 'style': BORDER.str(border.style)}
        
        @staticmethod    
        def _color2json(color):
            return ([int(v * 255) for v in color.rgb] + [color.alpha]) if isinstance(color, Color) else str(color)
                
        @staticmethod
        def _boxdim2json(dim4val):
            return [v.value for v in dim4val.values]
            
        @staticmethod
        def _dim2json(dim):
            return dim.value
        
        @staticmethod
        def _cursor2json(cur):
            return CURSOR.str(cur.style)
        
        @staticmethod
        def _font2json(font):
            return {'family': font.family, 'size': font.size.value, 'bold': font.bf, 'italic': font.it}
        
        @staticmethod
        def _image2json(img):
            return [img.width, img.height]
        
        @staticmethod
        def _gradient2json(grad):
            return {'percents': [p.value for p in grad.percents], 'colors': [c.html for c in grad.colors], 'vertical': GRADIENT.VERTICAL == grad.orientation}
                
        @staticmethod
        def _shadow2json(shw):
            if shw.style == SHADOW.NONE: return None
            return [shw.style == SHADOW.IN, shw.xoffset.value, shw.yoffset.value, shw.radius.value, 0, shw.color.html if isinstance(shw.color, Color) else str(shw.color) , 1]
         
        @staticmethod
        def _animation2json(anim):
            return {'fadeIn': [anim.induration, ANIMATION.str(anim.instyle)], 'fadeOut': [anim.outduration, ANIMATION.str(anim.outstyle)]}
        
        @property
        def images(self):
            for h, o in self._hash2objects['images'].iteritems(): yield h, o
            
        @property
        def fonts(self):
            for h, o in self._hash2objects['fonts'].iteritems(): yield h, o
        
        @property
        def values(self):
            return self._hash2values

    def compile(self):
        valuereg = Theme.ValueMap()
        theme = {}
        for typ, rules in self.rules.iteritems():
            properties = defaultdict(list)
            for rule in sorted(rules, key=lambda r: len(r.attrs) + len(r.pcs), reverse=True):
                selectors = sorted(list(rule.pcs)) + sorted(list(rule.attrs))
                for name, value in rule.properties.iteritems():
                    values = properties[name]
                    valuetuple = []
                    valuetuple.append(selectors)
                    mapped = valuereg.handle_value(value)
                    if mapped is not None: value = mapped
                    else:
                        if name == 'opacity': value = str(value.float)
                    valuetuple.append(value.value if isinstance(value, Dim) else tostring(value))
                    values.append(valuetuple)
            theme[typ] = properties
        return {'values': valuereg.values, 'theme': theme}, valuereg 
            
    
    def iterfonts(self):
        f = set()
        for rules in self.rules.values():
            for rule in rules:
                for propvalue in rule.properties.values():
                    if type(propvalue) is Font and str(propvalue) not in f: 
                        f.add(str(propvalue))
                        yield propvalue

    

class FontMetrics(object):
    
    SAMPLE = '!#$%&()*+,-./0123456789:;<=>?@AzByCxDwEvFuGtHsIrJqKpLoMnNmOlPkQjRiShTgUfVeWdXcYbZa[\\]^_`"\''
    
    def __init__(self, sample=SAMPLE, dimensions=None):
        self.sample = sample
        self.avgwidth = None
        self.x, self.y = None, None
        if dimensions is not None:
            self.dimensions = dimensions
    
    @property 
    def dimensions(self):
        return (px(self._x), px(self._y))
    
    @dimensions.setter
    def dimensions(self, dim):
        self._x, self._y = dim
        self.avgwidth = float(self._x) / len(self.sample)  
    
    def estimate(self, sample):
        return px(math.ceil(len(sample) * self.avgwidth)), px(math.ceil(self._y))
    
    
class WidgetTheme(object):
    def __init__(self, widget, theme, *types):
        self._theme = theme.extract(*types)
        self._widget = widget
        self._font = None
        self._padding = None
        self._margin = None
        self._border = None
        self._bg = None
        self._color = None
        
    def states(self):
        states = set()
        if self._widget.disabled:
            states.add(':disabled')
        if self._widget.focused:
            states.add(':focused')
        return states
    
    
    def styles(self):
        styles = set()
        if RWT.BORDER in self._widget.style:
            styles.add('[BORDER')
        return styles


class ComboTheme(WidgetTheme):
    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Combo', 'Combo-Button', 'Combo-List', 'Combo-Field')
        self.separator = None


    @property
    def btnwidth(self):
        return self._theme.get_property('width', 'Combo-Button', self.styles(), self.states())


    @property
    def font(self):
        return self._theme.get_property('font', 'Combo', self.styles(), self.states())


    @property
    def padding(self):
        return self._theme.get_property('padding', 'Combo', self.styles(), self.states())


    @property
    def borders(self):
        return [
            self._theme.get_property('border-%s' % b, 'Combo', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]


    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Combo', self.styles(), self.states())


    @bg.setter
    def bg(self, color):
        self._bg = color



class LabelTheme(WidgetTheme):
    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Label')
        self.separator = None
        
    @property
    def font(self):
        return self._theme.get_property('font', 'Label', self.styles(), self.states())
    
    @property
    def padding(self):
        return self._theme.get_property('padding', 'Label', self.styles(), self.states())
    
    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Label', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Label', self.styles(), self.states())
    
    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def color(self):
        if self._color: return self._color
        return self._theme.get_property('color', 'Label', self.styles(), self.states())

    @color.setter
    def color(self, color):
        out('setting color', color)
        self._color = color
        out(self._color)


class ButtonTheme(WidgetTheme):
    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Button', 'Button-ArrowIcon', 'Button-FocusIndicator')

    def states(self):
        states = WidgetTheme.states(self)
        return states

    def styles(self):
        styles = WidgetTheme.styles(self)
        styles.add('[PUSH')
        return styles
    
    @property
    def font(self):
        return self._theme.get_property('font', 'Button', self.styles(), self.states())
    
    @property
    def padding(self):
        return self._theme.get_property('padding', 'Button', self.styles(), self.states())
    
    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Button', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]
    
    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Button', self.styles(), self.states())
    
    @bg.setter
    def bg(self, color):
        self._bg = color 
    
class CheckboxTheme(WidgetTheme):
    
    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Button', 'Button-CheckIcon', 'Button-FocusIndicator')

    def states(self):
        states = WidgetTheme.states(self)
        return states

    def styles(self):
        styles = WidgetTheme.styles(self)
        styles.add('[CHECK')
        return styles

        
    @property
    def font(self):
        return self._theme.get_property('font', 'Button', self.styles(), self.states())
    
    @property
    def padding(self):
        return self._theme.get_property('padding', 'Button', self.styles(), self.states())
    
    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Button', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]
    
    @property
    def spacing(self):
        return self._theme.get_property('spacing', 'Button', self.styles(), self.states())
    
    @property
    def icon(self):
        return self._theme.get_property('background-image', 'Button-CheckIcon', self.styles(), self.states())
    
    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Label', self.styles(), self.states())
    
    @bg.setter
    def bg(self, color):
        self._bg = color 


class OptionTheme(WidgetTheme):
    
    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Button', 'Button-RadioIcon', 'Button-FocusIndicator')

    def states(self):
        states = WidgetTheme.states(self)
        return states

    def styles(self):
        styles = WidgetTheme.styles(self)
        styles.add('[RADIO')
        return styles

        
    @property
    def font(self):
        return self._theme.get_property('font', 'Button', self.styles(), self.states())
    
    @property
    def padding(self):
        return self._theme.get_property('padding', 'Button', self.styles(), self.states())
    
    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Button', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]
    
    @property
    def spacing(self):
        return self._theme.get_property('spacing', 'Button', self.styles(), self.states())
    
    @property
    def icon(self):
        return self._theme.get_property('background-image', 'Button-RadioIcon', self.styles(), self.states())
    
    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Button', self.styles(), self.states())
    
    @bg.setter
    def bg(self, color):
        self._bg = color 
        
        
class CompositeTheme(WidgetTheme):
    
    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Composite')
        self._bg = None
        
    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Composite', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]
    
    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Composite', self.styles(), self.states())
    
    @bg.setter
    def bg(self, color):
        self._bg = color



class TabFolderTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'TabFolder')
        self._bg = None


    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'TabFolder', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]


    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'TabFolder', self.styles(), self.states())


    @bg.setter
    def bg(self, color):
        self._bg = color



class TabItemTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'TabItem')
        self._bg = None


    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'TabItem', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]


    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'TabItem', self.styles(), self.states())


    @bg.setter
    def bg(self, color):
        self._bg = color



class ShellTheme(WidgetTheme):
    
    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Shell', 'Shell-Titlebar', 'Shell-CloseButton', 'Shell-DisplayOverlay', 'Shell-MinButton', 'Shell-MaxButton', 'Shell-CloseButton')
        
    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Shell', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]
    
    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Shell', self.styles(), self.states())
    
    @bg.setter
    def bg(self, color):
        self._bg = color
        
    @property
    def title_height(self):
        return self._theme.get_property('height', 'Shell-Titlebar', self.styles(), self.states())
        
    @property
    def padding(self):
        return self._theme.get_property('padding', 'Shell', self.styles(), self.states())
    

class EditTheme(WidgetTheme):
    
    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Text')
        
    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Text', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]
    
    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Text', self.styles(), self.states())
    
    @bg.setter
    def bg(self, color):
        self._bg = color
    
    @property
    def padding(self):
        return self._theme.get_property('padding', 'Text', self.styles(), self.states())
    
    @property
    def font(self):
        return self._theme.get_property('font', 'Text', self.styles(), self.states())
        
        
class ThemeRule(object):
    
    def __init__(self, typ='*', attrs=None, pcs=None):
        self.type = typ
        self.attrs = attrs
        self.pcs = pcs
        self.properties = {}
        
    
    def perfect_match(self, attrs=set(), pcs=set()):
        return set(attrs) == self.attrs and set(pcs) == self.pcs
    
    def match(self, attrs=set(), pcs=set()):
        if set(attrs).issuperset(self.attrs) and set(pcs).issuperset(self.pcs):
            return (len(self.attrs), len(self.pcs))
        else: return (-1, -1)
        
    def write(self, stream=sys.stdout):
        stream.write('<ThemeRule type=%s attributes={%s}, pseudoclasses={%s}>\n' % (self.type, ','.join(self.attrs), ','.join(self.pcs)))
        for name, value in self.properties.iteritems():
            stream.write('    %s = \t%s\n' % (name, repr(value)))
        
    def __deepcopy__(self, memo):
        rule = ThemeRule()
        rule.__dict__ = dict(self.__dict__)
        return rule
        


if __name__ == '__main__':
    pyraplog.level(DEBUG)
    theme = Theme('default').load()

    btn_theme = theme.extract('Label')#'Button', 'Button-CheckIcon', 'Button-RadioIcon', 'Button-ArrowIcon', 'Button-FocusIndicator')
    btn_theme.write()
    out(btn_theme.get_property('border-left', 'Label', ['[BORDER']))
    
    