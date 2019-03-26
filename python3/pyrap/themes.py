'''
Created on Oct 10, 2015

@author: nyga
'''
import dnutils
from dnutils import ifnot, ifnone

from pyrap.locations import pyrap_path
from cssutils import parseFile
import os
from cssutils.css.csscomment import CSSComment
from collections import defaultdict
from cssutils.css.value import Value, ColorValue, DimensionValue, URIValue,\
    CSSFunction
import uuid
import json
from logging import DEBUG
from pyrap.ptypes import Color, Pixels, parse_value, Dim,\
    Font, Image, pc, Percent, px
from pyrap.ptypes import BitField
import sys
from copy import copy, deepcopy
import re
from pyrap.constants import BORDER, GRADIENT, ANIMATION, FONT, SHADOW, CURSOR,\
    RWT
import math
from cssutils.css.cssfontfacerule import CSSFontFaceRule
from pyparsing import Literal, alphanums, alphas, Word, ZeroOrMore, quotedString,\
    removeQuotes
from cssutils.css import value

TYPE = 'type-selector'
CLASS = 'class'
PSEUDOCLASS = 'pseudo-class'
ATTRIBUTE = 'attribute-selector'
UNIVERSAL = 'universal'

logger = dnutils.getlogger(__name__)


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
            ret.append(str(v.cssText))
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
        self.rcpath = None
        self.fontfaces = []
        self.logger = dnutils.getlogger(type(self).__name__, level=dnutils.INFO)

    def extract(self, *types):
        if '*' not in types: types = types + ('*',)
        theme = Theme('%s-%s' % (self.name, '/'.join(types)))
        for t in types:
            theme.rules[t] = deepcopy(self.rules[t])
        return theme

    def load(self, filename=None):
        if filename is None:
            filename = os.path.join(pyrap_path, 'resource', 'theme', 'default.css')
        filename = os.path.abspath(filename)
        csscontent = parseFile(filename, validate=False)
        theme = Theme(name=self.name)
        theme.rules = deepcopy(self.rules)
        theme.rcpath = os.path.split(filename)[-2]
        theme._build_theme_from_rules(csscontent.cssRules)
        return theme

    def get_rule_exact(self, typ, clazz=set(), attrs=set(), pcs=set()):
        ruleset = self.rules[typ]
        for rule in ruleset:
            if rule.perfect_match(clazz, attrs, pcs): return rule
        rule = ThemeRule(typ, set(clazz), set(attrs), set(pcs))
        ruleset.append(rule)
        return rule

    def _get_property(self, name, typ, clazz=set(), attrs=set(), pcs=set()):
        ruleset = self.rules[typ]
        matches = []
        for rule in ruleset:
            match = rule.match(clazz, attrs, pcs)
            if match == (-1, -1, -1): continue
            matches.append((rule, match))
        # sort the matches in ascending order
        matches = sorted(matches, key=lambda m: m[1][2], reverse=True)
        matches = sorted(matches, key=lambda m: m[1][1], reverse=True)
        matches = sorted(matches, key=lambda m: m[1][0], reverse=True)
        while matches:
            m = matches.pop(0)
            r = m[0] # the rule
            if name in r.properties:
                return r.properties[name]
        return None

    def get_property(self, name, typ, clazz=set(), attrs=set(), pcs=set()):
        _done = []
        for args in ((clazz, attrs, pcs), (clazz, set(), pcs), (clazz, attrs, set()), (clazz, set(), set()),
                     (set(), attrs, pcs), (set(), set(), pcs), (set(), attrs, set()), (set(), set(), set())):
            if args in _done: continue
            _done.append(args)
            prop = self._get_property(name, typ, *args)
            if prop is not None:
                return prop
        if typ == '*': return None
        return self.get_property(name, '*', clazz, attrs, pcs)


    def write(self, stream=sys.stdout):
        stream.write('<Theme "%s" %d rules>\n' % (self.name, len(self.rules)))
        for typ in sorted(self.rules):
            for rule in self.rules[typ]:
                rule.write(stream)
        for ff in self.fontfaces:
            stream.write(str(ff))


    def _build_theme_from_rules(self, cssrules):
        for cssrule in cssrules:
            if isinstance(cssrule, CSSComment): continue
            if isinstance(cssrule, CSSFontFaceRule):
                style = cssrule.style
                ff = FontFaceRule(family=ifnot(style['font-family'], None), 
                                  src=ifnot(style['src'], None), 
                                  stretch=ifnot(style['font-stretch'], None), 
                                  style=ifnot(style['font-style'], None), 
                                  weight=ifnot(style['font-weight'], None), 
                                  urange=ifnot(style['unicode-range'], None))
                if ff.src.islocal:
                    with open(os.path.join(self.rcpath, ff.src.url), 'rb') as f:
                        ff.content = f.read() 
                self.fontfaces.append(ff)
                continue
            selectors, properties = self._convert_css_rule(cssrule)
            for typ, clazz, attrs, pcs in selectors:
                rule = self.get_rule_exact(typ, clazz, attrs, pcs)
                for name, value in properties.items():
                    if name == 'border':
                        for name in ('border-left', 'border-top', 'border-right', 'border-bottom'):
                            rule.properties[name] = copy(value)
                        continue
                    rule.properties[name] = copy(value)


    def _build_selector_triplets(self, selectors):
        typesel = []
        clazzsel = []
        attrsel = []
        pseudosel = []
        curattr = []
        curpseudo = []
        curclazz = []
        for i, s in enumerate(selectors):
            if s[0] == TYPE:
                typesel.append(s[1])
                if i > 0:
                    clazzsel.append(curclazz)
                    attrsel.append(curattr)
                    pseudosel.append(curpseudo)
                    curattr = []
                    curpseudo = []
                    curclazz = []
            elif s[0] == CLASS:
                curclazz.append(s[1])
            elif s[0] == ATTRIBUTE:
                curattr.append('[' + s[1])
            elif s[0] == PSEUDOCLASS:
                curpseudo.append(s[1])
        clazzsel.append(curclazz)
        attrsel.append(curattr)
        pseudosel.append(curpseudo)
        curclazz = []
        curattr = []
        curpseudo = []
        return [(t, set(c), set(a), set(p)) for t, c, p, a in zip(typesel, clazzsel, pseudosel, attrsel)]


    def _convert_css_rule(self, cssrule):
        selectors = [(str(item.type), item.value) for selector in cssrule.selectorList for item in selector.seq if item.type in (TYPE, CLASS, PSEUDOCLASS, ATTRIBUTE, UNIVERSAL)]
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
        elif name in ('image', 'background-image', 'rwt-information-image', 'rwt-error-image', 'rwt-warning-image', 'rwt-working-image', 'rwt-question-image', 'rwt-accept-image'):
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
                if (i.value == ',' or i.value == ')') and curarg:
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
            v = parse_value(str(v.cssText), Color)
            return v
        elif isinstance(v, CSSFunction):
            return Color(fct=self._convert_fct(v))
        elif isinstance(v, Value):
            v_ = str(v.cssText).strip('"\\')
            if v_ in Color.names: 
                return Color(html=v_)
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
            imgpath = os.path.join(self.rcpath, values[0].value)
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
        return Theme.Gradient(grad['percents'], list(map(parse_value, grad['colors'])), grad['orientation'])

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

        def __repr__(self):
            return '<Gradient at 0x%x %s; %s; %s' % (hash(self), self.orientation, ','.join(map(str, self.percents)), ','.join(map(str, self.colors)))

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

        def handle_value(self, value, add=True):
            category = None
            valdict = None
            if isinstance(value, Theme.Dim4) or isinstance(value, Theme.BorderRadius):
                valdict = Theme.ValueMap._boxdim2json(value)
                category = 'boxdims'
            elif isinstance(value, Font):
                valdict = Theme.ValueMap._font2json(value)
                category = 'fonts'
            elif isinstance(value, Color) or isinstance(value, str) and value in ('inherit', 'transparent'):
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
            elif add:
                hashid = str(uuid.uuid1()).split('-')[0]
                if isinstance(value, Image): hashid += '.%s' % value.fileext
                self._values2hash[category][key] = hashid
                self._hash2values[category][hashid] = valdict
                self._hash2objects[category][hashid] = value
                return hashid
            return None

        @staticmethod
        def _border2json(border):
            return {'color': border.color.html if isinstance(border.color, Color) else border.color, 'width': border.width.value, 'style': BORDER.str(border.style)}

        @staticmethod
        def _color2json(color):
            if isinstance(color, Color):
                return ([int(v * 255) for v in color.rgb] + [color.alpha])
            elif color in ('inherit', 'transparent'):
                return 'undefined'

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
            return [img.width.value, img.height.value]

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
            for h, o in self._hash2objects['images'].items(): yield h, o

        @property
        def fonts(self):
            for h, o in self._hash2objects['fonts'].items(): yield h, o

        @property
        def values(self):
            return self._hash2values

    def compile(self):
        valuereg = Theme.ValueMap()
        theme = {}
        for typ in list(self.rules.keys()):
            rules = self.rules[typ]
            properties = defaultdict(list)
            for rule in sorted(rules, key=lambda r: len(r.clazz) + len(r.attrs) + len(r.pcs), reverse=True):
                selectors = sorted(list(rule.clazz)) + sorted(list(rule.pcs)) + sorted(list(rule.attrs))
                for name, value in rule.properties.items():
                    values = properties[name]
                    valuetuple = []
                    valuetuple.append(selectors)
                    mapped = valuereg.handle_value(value)
                    if mapped is not None: value = mapped
                    else:
                        if name == 'opacity': value = str(value.float)
                    valuetuple.append(value.value if isinstance(value, Dim) else tostring(value))
                    values.append(valuetuple)
            #===================================================================
            # ensure that a font is always among the properties
            #===================================================================
            if 'font' not in properties:
                properties['font'] = [[[], valuereg.handle_value(self.get_property('font', typ), add=False)]]
            theme[typ] = properties
        return {'values': valuereg.values, 'theme': theme}, valuereg


    def iterfonts(self):
        f = set()
        for rules in list(self.rules.values()):
            for rule in rules:
                for propvalue in list(rule.properties.values()):
                    if type(propvalue) is Font and str(propvalue) not in f:
                        f.add(str(propvalue))
                        yield propvalue



class FontMetrics(object):

    SAMPLE = '!#$%&()*+,-./0123456789:;<=>?@AzByCxDwEvFuGtHsIrJqKpLoMnNmOlPkQjRiShTgUfVeWdXcYbZa[\\]^_`"\''

    def __init__(self, sample=SAMPLE, dimensions=None):
        self.sample = sample
        self.avgwidth = None
        self._x, self._y = None, None
        if dimensions is not None:
            self.dimensions = dimensions

    @property
    def dimensions(self):
        x = px(self._x) if self._x is not None else None
        y = px(self._y) if self._y is not None else None 
        return x, y

    @dimensions.setter
    def dimensions(self, dim):
        self._x, self._y = dim
        self.avgwidth = 0 if not self.sample else float(self._x) / len(self.sample)

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
        self._bgimg = None
        self._color = None

    def custom_variant(self):
        variants = set(['.%s' % self._widget.css])
        return variants if self._widget.css is not None else set()

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


class CanvasTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Canvas')
        self.separator = None

    @property
    def padding(self):
        return self._theme.get_property('padding', 'Canvas', self.custom_variant(), self.styles(), self.states())

    @property
    def borders(self):
        return [
            self._theme.get_property('border-%s' % b, 'Canvas', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Canvas', self.custom_variant(), self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def margin(self):
        return self._theme.get_property('margin', 'Canvas', self.custom_variant(), self.styles(), self.states())


class DecoratorTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'ControlDecorator')

    @property
    def icon_accept(self):
        return self._theme.get_property('rwt-accept-image', 'ControlDecorator', self.custom_variant(), self.styles(), self.states())
    
    @property
    def icon_warning(self):
        return self._theme.get_property('rwt-warning-image', 'ControlDecorator', self.custom_variant(), self.styles(), self.states())
    
    @property
    def icon_error(self):
        return self._theme.get_property('rwt-error-image', 'ControlDecorator', self.custom_variant(), self.styles(), self.states())
    
    @property
    def icon_information(self):
        return self._theme.get_property('rwt-information-image', 'ControlDecorator', self.custom_variant(), self.styles(), self.states())

    @property
    def image_position(self):
        return self._theme.get_property('image-position', 'ControlDecorator', self.custom_variant(), self.styles(), self.states())

    @property
    def spacing(self):
        return px(self._theme.get_property('spacing', 'ControlDecorator', self.custom_variant(), self.styles(), self.states()))


class ComboTheme(WidgetTheme):
    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Combo', 'Combo-Button', 'Combo-List', 'Combo-Field', 'Combo-List-Item')
        self.separator = None

    @property
    def btnwidth(self):
        return self._theme.get_property('width', 'Combo-Button', self.custom_variant(), self.styles(), self.states())

    @property
    def font(self):
        return self._theme.get_property('font', 'Combo', self.custom_variant(), self.styles(), self.states())

    @property
    def padding(self):
        return self._theme.get_property('padding', 'Combo', self.custom_variant(), self.styles(), self.states())

    @property
    def borders(self):
        return [
            self._theme.get_property('border-%s' % b, 'Combo', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Combo', self.custom_variant(), self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def itempadding(self):
        return self._theme.get_property('padding', 'Combo-Field', self.custom_variant(), self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'Combo', self.custom_variant(), self.styles(), self.states())


class DropDownTheme(WidgetTheme):
    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'DropDown', 'DropDown-Item')
        self.separator = None

    @property
    def font(self):
        return self._theme.get_property('font', 'DropDown', self.custom_variant(), self.styles(), self.states())

    @property
    def padding(self):
        return self._theme.get_property('padding', 'DropDown', self.custom_variant(), self.styles(), self.states())

    @property
    def borders(self):
        return [
            self._theme.get_property('border-%s' % b, 'DropDown', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'DropDown', self.custom_variant(), self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def itempadding(self):
        return self._theme.get_property('padding', 'DropDown-Item', self.custom_variant(), self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'Composite', self.custom_variant(), self.styles(), self.states())


class DisplayTheme(WidgetTheme):
    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Display')
        
    @property
    def icon_info(self):
        return self._theme.get_property('rwt-information-image', 'Display', self.custom_variant(), self.styles(), self.states())
    
    @property
    def icon_warning(self):
        return self._theme.get_property('rwt-warning-image', 'Display', self.custom_variant(), self.styles(), self.states())
    
    @property
    def icon_question(self):
        return self._theme.get_property('rwt-question-image', 'Display', self.custom_variant(), self.styles(), self.states())
    
    @property
    def icon_error(self):
        return self._theme.get_property('rwt-error-image', 'Display', self.custom_variant(), self.styles(), self.states())
    

class ProgressBarTheme(WidgetTheme):
    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'ProgressBar', 'ProgressBar-Indicator')
        
    @property
    def indicator_img(self):
        return self._theme.get_property('background-image', 'ProgressBar', self.custom_variant(), self.styles(), self.states())
    
    @property
    def minwidth(self):
        return ifnone(self._theme.get_property('width', 'ProgressBar-Indicator', self.custom_variant(), self.styles(), self.states()), px(0))
    
    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'ProgressBar', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def padding(self):
        return self._theme.get_property('padding', 'ProgressBar', self.custom_variant(), self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'ProgressBar', self.custom_variant(), self.styles(), self.states())



class SpinnerTheme(WidgetTheme):
    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Spinner', 'Spinner-UpButton', 'Spinner-DownButton')
        
    @property
    def button_widths(self):
        upw = self._theme.get_property('width', 'Spinner-UpButton', self.custom_variant(), self.styles(), self.states())
        downw = self._theme.get_property('width', 'Spinner-DownButton', self.custom_variant(), self.styles(), self.states())
        return upw, downw
    
    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Spinner', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def font(self):
        return self._theme.get_property('font', 'Spinner', self.custom_variant(), self.styles(), self.states())

    @property
    def padding(self):
        return self._theme.get_property('padding', 'Spinner', self.custom_variant(), self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'Spinner', self.custom_variant(), self.styles(), self.states())


class SeparatorTheme(WidgetTheme):
    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Label-SeparatorLine')
    
    def styles(self):
        styles = WidgetTheme.styles(self)
        if RWT.HORIZONTAL in self._widget.style:
            styles.add('[HORIZONTAL')
        if RWT.VERTICAL in self._widget.style:
            styles.add('[VERTICAL')
        if RWT.SEPARATOR in self._widget.style:
            styles.add('[SEPARATOR')
        return styles

    @property
    def bg(self):
        return self._theme.get_property('background-color', 'Label-SeparatorLine', self.custom_variant(), self.styles(), self.states())
    
    @property
    def padding(self):
        return self._theme.get_property('padding', 'Label-SeparatorLine', self.custom_variant(), self.styles(), self.states())

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Label-SeparatorLine', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def margin(self):
        return self._theme.get_property('margin', 'Label', self.custom_variant(), self.styles(), self.states())

    @property
    def linewidth(self):
        return self._theme.get_property('width', 'Label-SeparatorLine', self.custom_variant(), self.styles(), self.states())


class SashTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Sash', 'Sash-Handle')

    def styles(self):
        styles = WidgetTheme.styles(self)
        if RWT.HORIZONTAL in self._widget.style:
            styles.add('[HORIZONTAL')
        if RWT.VERTICAL in self._widget.style:
            styles.add('[VERTICAL')
        return styles

    @property
    def padding(self):
        return self._theme.get_property('padding', 'Sash', self.custom_variant(), self.styles(), self.states())

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Sash', self.custom_variant(), self.styles(),
                                         self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def width(self):
        return self._theme.get_property('width', 'Sash', self.custom_variant(), self.styles(), self.states())


class LabelTheme(WidgetTheme):
    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Label', 'Label-SeparatorLine')
        
    @property
    def font(self):
        if self._font is not None: return self._font
        return self._theme.get_property('font', 'Label', self.custom_variant(), self.styles(), self.states())

    @property
    def padding(self):
        return self._theme.get_property('padding', 'Label', self.custom_variant(), self.styles(), self.states())

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Label', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        opacity = ifnone(self._theme.get_property('opacity', 'Label', self.custom_variant(), self.styles(), self.states()), 1.0)
        color = self._theme.get_property('background-color', 'Label', self.custom_variant(), self.styles(), self.states())
        color.alpha = opacity
        return color

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def color(self):
        if self._color: return self._color
        return self._theme.get_property('color', 'Label', self.custom_variant(), self.styles(), self.states())

    @color.setter
    def color(self, color):
        self._color = color

    @property
    def margin(self):
        return self._theme.get_property('margin', 'Label', self.custom_variant(), self.styles(), self.states())


class LinkTheme(WidgetTheme):
    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Link', 'Link-Hyperlink')


    @property
    def font(self):
        if self._font is not None: return self._font
        return self._theme.get_property('font', 'Link', self.custom_variant(), self.styles(), self.states())


    @property
    def padding(self):
        return self._theme.get_property('padding', 'Link', self.custom_variant(), self.styles(), self.states())


    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Link', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]


    @property
    def bg(self):
        if self._bg: return self._bg
        opacity = ifnone(self._theme.get_property('opacity', 'Link', self.custom_variant(), self.styles(), self.states()), 1.0)
        color = self._theme.get_property('background-color', 'Link', self.custom_variant(), self.styles(), self.states())
        color.alpha = opacity
        return color


    @bg.setter
    def bg(self, color):
        self._bg = color


    @property
    def color(self):
        if self._color: return self._color
        return self._theme.get_property('color', 'Link', self.custom_variant(), self.styles(), self.states())


    @color.setter
    def color(self, color):
        self._color = color


    @property
    def margin(self):
        return self._theme.get_property('margin', 'Link', self.custom_variant(), self.styles(), self.states())


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
        return self._theme.get_property('font', 'Button', self.custom_variant(), self.styles(), self.states())

    @property
    def padding(self):
        return self._theme.get_property('padding', 'Button', self.custom_variant(), self.styles(), self.states())

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Button', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Button', self.custom_variant(), self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def margin(self):
        return self._theme.get_property('margin', 'Button', self.custom_variant(), self.styles(), self.states())


class ToggleTheme(ButtonTheme):

    def styles(self):
        styles = ButtonTheme.styles(self)
        styles.add('[TOGGLE')
        return styles


class CheckboxTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Button', 'Button-CheckIcon', 'Button-FocusIndicator')

    def states(self):
        states = WidgetTheme.states(self)
        if self._widget.checked:
            states.add(':selected')
        return states

    def styles(self):
        styles = WidgetTheme.styles(self)
        styles.add('[CHECK')
        return styles


    @property
    def font(self):
        return self._theme.get_property('font', 'Button', self.custom_variant(), self.styles(), self.states())

    @property
    def padding(self):
        return self._theme.get_property('padding', 'Button', self.custom_variant(), self.styles(), self.states())

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Button', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def spacing(self):
        return self._theme.get_property('spacing', 'Button', self.custom_variant(), self.styles(), self.states())

    @property
    def icon(self):
        return self._theme.get_property('background-image', 'Button-CheckIcon', self.custom_variant(), self.styles(), self.states())

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Label', self.custom_variant(), self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def fipadding(self): # the focus indicator
        return self._theme.get_property('padding', 'Button-FocusIndicator', self.custom_variant(), self.styles(), self.states())

    @property
    def fiborders(self):
        return [self._theme.get_property('border-%s' % b, 'Button-FocusIndicator', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def margin(self):
        return self._theme.get_property('margin', 'Button', self.custom_variant(), self.styles(), self.states())


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
        return self._theme.get_property('font', 'Button', self.custom_variant(), self.styles(), self.states())

    @property
    def padding(self):
        return self._theme.get_property('padding', 'Button', self.custom_variant(), self.styles(), self.states())

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Button', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def spacing(self):
        return self._theme.get_property('spacing', 'Button', self.custom_variant(), self.styles(), self.states())

    @property
    def icon(self):
        return self._theme.get_property('background-image', 'Button-RadioIcon', self.custom_variant(), self.styles(), self.states())

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Button', self.custom_variant(), self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def fipadding(self): # the focus indicator
        return self._theme.get_property('padding', 'Button-FocusIndicator', self.custom_variant(), self.styles(), self.states())

    @property
    def fiborders(self):
        return [self._theme.get_property('border-%s' % b, 'Button-FocusIndicator', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def margin(self):
        return self._theme.get_property('margin', 'Button', self.custom_variant(), self.styles(), self.states())


class CompositeTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Composite')
        self._bg = None

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Composite', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def font(self):
        return self._theme.get_property('font', 'Composite', self.custom_variant(), self.styles(), self.states())

    @property
    def padding(self):
        return self._theme.get_property('padding', 'Composite', self.custom_variant(), self.styles(), self.states())

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Composite', self.custom_variant(), self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def bgimg(self):
        if self._bgimg: return self._bgimg
        return self._theme.get_property('background-image', 'Composite', self.custom_variant(), self.styles(), self.states())

    @bgimg.setter
    def bgimg(self, img):
        self._bgimg = img

    @property
    def margin(self):
        return self._theme.get_property('margin', 'Composite', self.custom_variant(), self.styles(), self.states())


class ScrolledCompositeTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'ScrolledComposite')
        self._bg = None

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'ScrolledComposite', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def font(self):
        return self._theme.get_property('font', 'ScrolledComposite', self.custom_variant(), self.styles(), self.states())

    @property
    def padding(self):
        return self._theme.get_property('padding', 'ScrolledComposite', self.custom_variant(), self.styles(), self.states())

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'ScrolledComposite', self.custom_variant(), self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def margin(self):
        return self._theme.get_property('margin', 'ScrolledComposite', self.custom_variant(), self.styles(), self.states())


class ScrollBarTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'ScrollBar', 'ScrollBar-Thumb')
        self._bg = None

    @property
    def margin(self):
        return self._theme.get_property('margin', 'ScrollBar', self.custom_variant(), self.styles(), self.states())

    @property
    def width(self):
        return self._theme.get_property('width', 'ScrollBar', self.custom_variant(), self.styles(), self.states())

    @property
    def minheight(self):
        return self._theme.get_property('min-height', 'ScrollBar-Thumb', self.custom_variant(), self.styles(), self.states())


class ScaleTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Scale', 'Scale-Thumb', 'Scale-Line')
        self._bg = None

    def styles(self):
        styles = WidgetTheme.styles(self)
        if RWT.HORIZONTAL in self._widget.style:
            styles.add('[HORIZONTAL')
        elif RWT.VERTICAL in self._widget.style:
            styles.add('[VERTICAL')
        return styles

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Scale', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def thumb_borders(self):
        return [self._theme.get_property('border-%s' % b, 'Scale-Thumb', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]


    @property
    def icon(self):
        return self._theme.get_property('background-image', 'Scale-Thumb', self.custom_variant(), self.styles(), self.states())

    @property
    def bgimg(self):
        return self._theme.get_property('background-image', 'Scale', self.custom_variant(), self.styles(), self.states())

    @property
    def lineimg(self):
        return self._theme.get_property('background-image', 'Scale-Line', self.custom_variant(), self.styles(), self.states())


    @property
    def padding(self):
        return self._theme.get_property('padding', 'Scale', self.custom_variant(), self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'Scale', self.custom_variant(), self.styles(), self.states())


class SliderTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Slider', 'Slider-Thumb', 'Slider-UpButton', 'Slider-DownButton', 'Slider-UpButton-Icon', 'Slider-DownButton-Icon')
        self._bg = None

    def styles(self):
        styles = WidgetTheme.styles(self)
        if RWT.HORIZONTAL in self._widget.style:
            styles.add('[HORIZONTAL')
        elif RWT.VERTICAL in self._widget.style:
            styles.add('[VERTICAL')
        return styles

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Slider', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bordersthumb(self):
        return [self._theme.get_property('border-%s' % b, 'Slider-Thumb', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def icons(self):
        return [self._theme.get_property('background-image', 'Slider-UpButton-Icon', self.custom_variant(), self.styles(), self.states()),
                self._theme.get_property('background-image', 'Slider-DownButton-Icon', self.custom_variant(), self.styles(), self.states()),
                self._theme.get_property('background-image', 'Slider-Thumb', self.custom_variant(), self.styles(), self.states())]

    @property
    def margin(self):
        return self._theme.get_property('margin', 'Slider', self.custom_variant(), self.styles(), self.states())

    @property
    def padding(self):
        return self._theme.get_property('padding', 'Slider', self.custom_variant(), self.styles(), self.states())

    @property
    def paddingicons(self):
        return [self._theme.get_property('padding', 'Slider-UpButton', self.custom_variant(), self.styles(), self.states()),
                self._theme.get_property('padding', 'Slider-DownButton', self.custom_variant(), self.styles(), self.states())]



class TabFolderTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'TabFolder', 'TabFolder-ContentContainer')
        self._bg = None

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'TabFolder', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'TabFolder', self.custom_variant(), self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def padding(self):
        return self._theme.get_property('padding', 'TabFolder', self.custom_variant(), self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'TabFolder', self.custom_variant(), self.styles(), self.states())

    @property
    def container_borders(self):
        return [self._theme.get_property('border-%s' % b, 'TabFolder-ContentContainer', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]


class TabItemTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'TabItem')
        self._bg = None

    def states(self):
        states = WidgetTheme.states(self)
        if self._widget.selected:
            states.add(':selected')
        return states

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'TabItem', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'TabItem', self.custom_variant(), self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def padding(self):
        return self._theme.get_property('padding', 'TabItem', self.custom_variant(), self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'TabItem', self.custom_variant(), self.styles(), self.states())

    @property
    def font(self):
        return self._theme.get_property('font', 'TabItem', self.custom_variant(), self.styles(), self.states())


class MenuTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Menu')
        self._bg = None

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Menu', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Menu', self.custom_variant(), self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def padding(self):
        return self._theme.get_property('padding', 'Menu', self.custom_variant(), self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'Menu', self.custom_variant(), self.styles(), self.states())


class MenuItemTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'MenuItem', 'MenuItem-CheckIcon', 'MenuItem-CascadeIcon')
        self._bg = None


    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'MenuItem', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'MenuItem', self.custom_variant(), self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def padding(self):
        return self._theme.get_property('padding', 'MenuItem', self.custom_variant(), self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'MenuItem', self.custom_variant(), self.styles(), self.states())

    @property
    def font(self):
        return self._theme.get_property('font', 'MenuItem', self.custom_variant(), self.styles(), self.states())


class ShellTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Shell', 'Shell-Titlebar', 'Shell-CloseButton', 'Shell-DisplayOverlay', 'Shell-MinButton', 'Shell-MaxButton', 'Shell-CloseButton')

    def styles(self):
        styles = WidgetTheme.styles(self)
        if RWT.TITLE in self._widget.style:
            styles.add('[TITLE')
        if RWT.TITLE in self._widget.style:
            styles.add('[BORDER')
        return styles

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Shell', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Shell', self.custom_variant(), self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def title_height(self):
        return self._theme.get_property('height', 'Shell-Titlebar', self.custom_variant(), self.styles(), self.states())

    @property
    def padding(self):
        return self._theme.get_property('padding', 'Shell', self.custom_variant(), self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'Shell', self.custom_variant(), self.styles(), self.states())


class EditTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Text')

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Text', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Text', self.custom_variant(), self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def padding(self):
        return self._theme.get_property('padding', 'Text', self.custom_variant(), self.styles(), self.states())

    @property
    def font(self):
        return self._theme.get_property('font', 'Text', self.custom_variant(), self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'Text', self.custom_variant(), self.styles(), self.states())


class GroupTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Group', 'Group-Frame', 'Group-Label')
        self._bg = None

    @property
    def padding(self):
        return self._theme.get_property('padding', 'Group', self.custom_variant(), self.styles(), self.states())

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Composite', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Composite', self.custom_variant(), self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def margin(self):
        return self._theme.get_property('margin', 'Group', self.custom_variant(), self.styles(), self.states())

    @property
    def frame_padding(self):
        return self._theme.get_property('padding', 'Group-Frame', self.custom_variant(), self.styles(), self.states())

    @property
    def label_padding(self):
        return self._theme.get_property('padding', 'Group-Label', self.custom_variant(), self.styles(), self.states())

    @property
    def frame_margin(self):
        return self._theme.get_property('margin', 'Group-Frame', self.custom_variant(), self.styles(), self.states())

    @property
    def label_margin(self):
        return self._theme.get_property('margin', 'Group-Label', self.custom_variant(), self.styles(), self.states())

    @property
    def frame_borders(self):
        return [self._theme.get_property('border-%s' % b, 'Group-Frame', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def label_borders(self):
        return [self._theme.get_property('border-%s' % b, 'Group-Label', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]



class BrowserTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Browser')
        self._bg = None

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Browser', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def margin(self):
        return self._theme.get_property('margin', 'Browser', self.custom_variant(), self.styles(), self.states())


class ListTheme(WidgetTheme):
    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'List-Item', 'List')

    @property
    def font(self):
        return self._theme.get_property('font', 'List-Item', self.custom_variant(), self.styles(), self.states())

    @property
    def padding(self):
        return self._theme.get_property('padding', 'List', self.custom_variant(), self.styles(), self.states())

    @property
    def item_padding(self):
        return self._theme.get_property('padding', 'List-Item', self.custom_variant(), self.styles(), self.states())


    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'List', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'List', self.custom_variant(), self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def color(self):
        if self._color: return self._color
        return self._theme.get_property('color', 'List', self.custom_variant(), self.styles(), self.states())

    @color.setter
    def color(self, color):
        self._color = color

    @property
    def margin(self):
        return self._theme.get_property('margin', 'List', self.custom_variant(), self.styles(), self.states())


class TableTheme(WidgetTheme):
    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Table', 'Table-Checkbox')

    @property
    def font(self):
        return self._theme.get_property('font', 'Table', self.custom_variant(), self.styles(), self.states())

    @property
    def padding(self):
        return self._theme.get_property('padding', 'Table', self.custom_variant(), self.styles(), self.states())

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Table', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Table', self.custom_variant(), self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def color(self):
        if self._color: return self._color
        return self._theme.get_property('color', 'Table', self.custom_variant(), self.styles(), self.states())

    @color.setter
    def color(self, color):
        self._color = color

    @property
    def margin(self):
        return self._theme.get_property('margin', 'Table', self.custom_variant(), self.styles(), self.states())

    @property
    def checkbox_width(self):
        return self._theme.get_property('width', 'Table-Checkbox', self.custom_variant(), self.styles(), self.states())

    @property
    def checkbox_width(self):
        return self._theme.get_property('width', 'Table-Checkbox', self.custom_variant(), self.styles(), self.states())

    @property
    def checkbox_margin(self):
        return self._theme.get_property('margin', 'Table-Checkbox', self.custom_variant(), self.styles(), self.states())


class TableColumnTheme(WidgetTheme):
    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'TableColumn')

    @property
    def font(self):
        return self._theme.get_property('font', 'TableColumn', self.custom_variant(), self.styles(), self.states())

    @property
    def padding(self):
        return self._theme.get_property('padding', 'TableColumn', self.custom_variant(), self.styles(), self.states())

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'TableColumn', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'TableColumn', self.custom_variant(), self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def color(self):
        if self._color: return self._color
        return self._theme.get_property('color', 'TableColumn', self.custom_variant(), self.styles(), self.states())

    @color.setter
    def color(self, color):
        self._color = color

    @property
    def margin(self):
        return self._theme.get_property('margin', 'TableColumn', self.custom_variant(), self.styles(), self.states())

    @property
    def spacing(self):
        return self._theme.get_property('spacing', 'TableColumn', self.custom_variant(), self.styles(), self.states())


class TableItemTheme(WidgetTheme):
    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'TableItem', 'Table-Cell')

    @property
    def font(self):
        return self._theme.get_property('font', 'TableItem', self.custom_variant(), self.styles(), self.states())

    @property
    def padding(self):
        return self._theme.get_property('padding', 'TableItem', self.custom_variant(), self.styles(), self.states())

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'TableItem', self.custom_variant(), self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'TableItem', self.custom_variant(), self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def color(self):
        if self._color: return self._color
        return self._theme.get_property('color', 'TableItem', self.custom_variant(), self.styles(), self.states())

    @color.setter
    def color(self, color):
        self._color = color

    @property
    def margin(self):
        return self._theme.get_property('margin', 'TableItem', self.custom_variant(), self.styles(), self.states())

    @property
    def cell_spacing(self):
        return self._theme.get_property('spacing', 'Table-Cell', self.custom_variant(), self.styles(), self.states())


class ThemeRule(object):

    def __init__(self, typ='*', clazz=None, attrs=None, pcs=None):
        self.type = typ
        self.clazz = clazz
        self.attrs = attrs
        self.pcs = pcs
        self.properties = {}


    def perfect_match(self, clazz=set(), attrs=set(), pcs=set()):
        return set(clazz) == self.clazz and set(attrs) == self.attrs and set(pcs) == self.pcs

    def match(self, clazz=set(), attrs=set(), pcs=set()):
        if set(clazz).issuperset(self.clazz) and set(attrs).issuperset(self.attrs) and set(pcs).issuperset(self.pcs):
            return (len(self.clazz), len(self.attrs), len(self.pcs))
        else: return (-1, -1, -1)

    def write(self, stream=sys.stdout):
        stream.write('<ThemeRule type=%s class={%s}, attributes={%s}, pseudoclasses={%s}>\n' % (self.type, ','.join(self.clazz), ','.join(self.attrs), ','.join(self.pcs)))
        for name, value in self.properties.items():
            stream.write('    %s = \t%s\n' % (name, repr(value)))

    def __deepcopy__(self, memo):
        rule = ThemeRule()
        rule.__dict__ = dict(self.__dict__)
        return rule
    
    
class FontFaceRule(object):
    
    class Source(object):
        def __init__(self, url, fformat=None, flocals=None):
            self.url = url
            self.format = ifnone(fformat, os.path.splitext(url)[-1].replace('.', ''))
            self.locals = ifnone(flocals, [])

        @property
        def islocal(self):
            return not self.url.startswith('http')
            
        @staticmethod
        def _parse_src(s):
            lpar = Literal('(')
            rpar = Literal(')')
            comma = Literal(',')
            delim = ZeroOrMore(' ') + comma + ZeroOrMore(' ')
            fdelim = delim | ZeroOrMore(' ')
            symb = Word(alphas + alphanums + '_' + '-')
            argsym = Word(alphas + alphanums + '_' + '-' + '/' + ':' + '.' + '-' + '?' + '&' + '=')
            arg = argsym | quotedString.setParseAction(removeQuotes)
            args = arg + ZeroOrMore(comma.suppress() + arg) 
            function = symb + lpar.suppress() + args + rpar.suppress()
            props = {'flocals': [], 'url': None, 'fformat': None}
            keymap = {'format': 'fformat', 'local': 'flocals', 'url': 'url'}
            def collect(s, parsed):
                fct, args = parsed[0], parsed[1:]
                if fct == 'local':
                    props[keymap[fct]].append(args[0])
                else:
                    props[keymap[fct]] = args[0]
            function.setParseAction(collect)
            flist = function + ZeroOrMore(fdelim.suppress() + function)
            flist.parseString(s)
            return FontFaceRule.Source(**props)
        
        
        def __str__(self):
            s = ''
            if self.locals:
                s += ', '.join(['local(%s)' % (l if ' ' not in l else '"%s"' % l) for l in self.locals])
            if self.url:
                if s: s += ', '
                s += 'url(%s)' % self.url
            if self.format:
                if s: s += ' '
                s += 'format("%s")' % self.format
            return s
            
            
        def __repr__(self):
            return '<FontFaceRule.Source: ' + str(self)


    def __init__(self, family, src, stretch=None, style=None, weight=None, urange=None):
        self.family = family.strip('"')
        self.src = src if isinstance(src, self.Source) else self.Source._parse_src(src)
        self.strectch = stretch
        self.style = style
        self.weight = weight
        self.urange = urange
        self.content = None
        
        
    def __str__(self):
        return '<FontFace font-family="%s", src="%s">' % (self.family, str(self.src))
        
    def tocss(self):
        values = ['font-family: "%s"' % self.family]
        if self.style:
            values.append('font-style: %s' % self.style)
        if self.weight:
            values.append('font-weight: %s' % self.weight)
        if self.src:
            values.append('src: %s' % str(self.src))
        return '@font-face {%s}' % ';'.join(values)
        


if __name__ == '__main__':
    theme = Theme('default').load('../resource/theme/default.css')
    theme = theme.extract('ControlDecorator')
    print(theme.get_property('spacing', 'ControlDecorator'))
#     btn_theme = theme.extract('List', 'List-Item')#'Button', 'Button-CheckIcon', 'Button-RadioIcon', 'Button-ArrowIcon', 'Button-FocusIndicator')
#     btn_theme.write()
#     out(btn_theme.get_property('font', 'List-Item', set([]), set(['[BORDER']), set([])))
