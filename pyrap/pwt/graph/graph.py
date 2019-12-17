import os

from dnutils import ifnone
from pyrap import session, locations
from pyrap.communication import RWTSetOperation, \
    RWTCallOperation
from pyrap.ptypes import BitField
from pyrap.pwt.d3widget.d3widget import D3Widget
from pyrap.themes import WidgetTheme
from pyrap.widgets import Widget, constructor


class Graph(D3Widget):

    _rwt_class_name = 'pwt.customs.Graph'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('Graph')
    def __init__(self, parent, css=None, **options):
        D3Widget.__init__(self, parent, os.path.join(locations.pwt_loc, 'graph', 'graph.css'), version=3, css=css, **options)
        self.theme = GraphTheme(self, session.runtime.mngr.theme)
        self._links = []
        self._glow = False
        self._linkdist = None
        self._cradius = None

    @property
    def links(self):
        return self._links

    @property
    def linkdist(self):
        return self._linkdist

    @linkdist.setter
    def linkdist(self, linkdist):
        self._linkdist = linkdist
        session.runtime << RWTSetOperation(self.id, {'linkdistance': linkdist})

    @property
    def glow(self):
        return self._glow

    @glow.setter
    def glow(self, glow):
        self._glow = glow
        session.runtime << RWTSetOperation(self.id, {'glow': glow})

    @property
    def cradius(self):
        return self._cradius

    @cradius.setter
    def cradius(self, cradius):
        self._cradius = cradius
        session.runtime << RWTSetOperation(self.id, {'circleradius': cradius})

    @property
    def gravity(self):
        return self._gravity

    @gravity.setter
    def gravity(self, gravity):
        self._gravity = gravity
        session.runtime << RWTSetOperation(self.id, {'gravity': gravity})

    def arrow(self, arrowid):
        '''
        Appends a marker with the given id in the graph's definitions.

        :param arrowid:  string denoting a css id to manipulate the arrow heads of the graph.

        Example: set `arrowid` to e.g. 'fancy' and add the following lines to your
        .css file:
            marker#fancy {
              fill: none;
            }

            .link.fancy {
              stroke: yellow;
            }

        With the `arcstyle` of a link in the graph data set to 'fancy' as well,
        the respective link will be drawn yellow without a marker head.
        Set the `arcstyle` to 'dashed fancy' to draw a yellow dashed stroke
        without an arrow head.
        '''
        session.runtime << RWTSetOperation(self.id, {'arrow': arrowid})

    @property
    def charge(self):
        return self._charge

    @charge.setter
    def charge(self, charge):
        self._charge = charge
        session.runtime << RWTSetOperation(self.id, {'charge': charge})

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

    @property
    def margin(self):
        return self._theme.get_property('margin', 'SVG', self.custom_variant(), self.styles(), self.states())