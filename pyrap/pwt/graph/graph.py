from pyrap import session
from pyrap.communication import RWTCreateOperation, RWTSetOperation, \
    RWTCallOperation
from pyrap.ptypes import BitField
from pyrap.themes import WidgetTheme
from pyrap.utils import ifnone, out
from pyrap.widgets import Widget, constructor, checkwidget


class Graph(Widget):

    _rwt_class_name = 'pwt.customs.Graph'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('Graph')
    def __init__(self, parent, cssid=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = GraphTheme(self, session.runtime.mngr.theme)
        self._gwidth = None
        self._gheight = None
        self._links = []
        self._cssid = cssid

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if self._cssid:
            options.cssid = self._cssid
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)

    def compute_size(self):
        w, h = session.runtime.textsize_estimate(self.theme.font, 'XXX')
        padding = self.theme.padding
        if padding:
            w += ifnone(padding.left, 0) + ifnone(padding.right, 0)
            h += ifnone(padding.top, 0) + ifnone(padding.bottom, 0)
        t, r, b, l = self.theme.borders
        w += ifnone(l, 0, lambda b: b.width) + ifnone(r, 0, lambda b: b.width)
        h += ifnone(t, 0, lambda b: b.width) + ifnone(b, 0, lambda b: b.width)
        return w, h

    @property
    def links(self):
        return self._links

    @property
    def cssid(self):
        return self._cssid

    @cssid.setter
    def cssid(self, cssid):
        self._cssid = cssid

    @property
    def gwidth(self):
        return self._gwidth

    @gwidth.setter
    @checkwidget
    def gwidth(self, w):
        self._gwidth = w
        session.runtime << RWTSetOperation(self.id, {'width': self.gwidth})

    @property
    def gheight(self):
        return self._gheight

    @gheight.setter
    @checkwidget
    def gheight(self, h):
        self._gheight = h
        session.runtime << RWTSetOperation(self.id, {'height': self.gheight})

    def addlink(self, source=None, target=None, value=None):
        tmplink = GraphLink(source=source, target=target, value=value)
        if tmplink not in self.links:
            self.links.append(tmplink)
            return True
        return False

    def removelink(self, source=None, target=None, value=None):
        tmplink = GraphLink(source=source, target=target, value=value)
        if tmplink in self.links:
            self.links.remove(tmplink)
            return True
        return False

    def clear(self):
        session.runtime << RWTCallOperation(self.id, 'updateData', {'remove': self.links, 'add': []})
        self._links = []

    def updatedata(self, newlinks):
        remove = [x for x in self.links if x not in newlinks]
        add = [x for x in newlinks if x not in self.links]
        out(remove, add)
        session.runtime << RWTCallOperation(self.id, 'updateData', {'remove': remove, 'add': add})
        self._links = [x for x in self.links if x not in remove] + add
        return remove, add


class GraphLink(object):

    def __init__(self, source=None, target=None, value=None):
        self._source = source
        self._target = target
        self._value = value

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, s):
        self._source = s

    @property
    def target(self):
        return self._target

    @target.setter
    def target(self, t):
        self._target = t

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        self._value = v

    def __repr__(self):
        return '<Link [{} --{}--> {}] at 0x{}x>'.format(self.source, self.value, self.target, hash(self))

    def __str__(self):
        return '<Link [{} --{}--> {}]>'.format(self.source, self.value, self.target)

    def __eq__(self, y):
        return self.source == y.source and self.target == y.target and self.value == y.value

    def __neq__(self, y):
        return not self == y


class GraphTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Graph')

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Graph', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Graph', self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def padding(self):
        return self._theme.get_property('padding', 'Graph', self.styles(), self.states())

    @property
    def font(self):
        return self._theme.get_property('font', 'Graph', self.styles(), self.states())
