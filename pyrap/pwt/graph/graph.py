import os

from pyrap import session
from pyrap.communication import RWTCreateOperation
from pyrap.ptypes import BitField
from pyrap.themes import WidgetTheme
from pyrap.widgets import Widget, constructor


class Graph(Widget):

    _rwt_class_name = 'd3graph.Graph'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('Graph')
    def __init__(self, parent, cssid=None, cssclass=None, jsfiles=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = GraphTheme(self, session.runtime.mngr.theme)
        self._jsfiles = jsfiles
        self.ensurejsresources()
        self._links = []
        self._cssid = cssid
        self._cssclass = cssclass

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if self._cssid:
            options.cssid = self._cssid
        if self._cssclass:
            options.cssclass = self._cssclass
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)

    def compute_size(self):
        w, h = session.runtime.textsize_estimate(self.theme.font, 'XXX')
        return w, h

    def ensurejsresources(self):
        if self._jsfiles:
            if not isinstance(self._jsfiles, list):
                files = [self._jsfiles]
            else:
                files = self._jsfiles
            for p in files:
                if os.path.isfile(p):
                    session.runtime.requirejs(p)
                elif os.path.isdir(p):
                    for f in [x for x in os.listdir(p) if x.endswith('.js')]:
                        session.runtime.requirejs(f)


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
    def cssclass(self):
        return self._cssclass

    @cssclass.setter
    def cssclass(self, cl):
        self._cssclass = cl

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
