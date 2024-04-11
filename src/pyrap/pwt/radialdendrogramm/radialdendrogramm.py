import os

from pyrap import session, locations
from pyrap.communication import RWTCallOperation
from pyrap.ptypes import BitField
from pyrap.pwt.d3widget.d3widget import D3Widget
from pyrap.themes import WidgetTheme
from pyrap.widgets import Widget, constructor


class RadialDendrogramm(D3Widget):

    _rwt_class_name = 'pwt.customs.RadialDendrogramm'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('RadialDendrogramm')
    def __init__(self, parent, opts=None, css=None, **options):
        D3Widget.__init__(self, parent, os.path.join(locations.pwt_loc, 'radialdendrogramm', 'radialdendrogramm.css'), version=3, opts=opts, css=css, **options)
        self.theme = RadialDendrogrammTheme(self, session.runtime.mngr.theme)

    def highlight(self, el):
        session.runtime << RWTCallOperation(self.id, 'highlight', {'name': el})


class RadialDendrogrammTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'Cluster')

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'Cluster', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'Cluster', self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def padding(self):
        return self._theme.get_property('padding', 'Cluster', self.styles(), self.states())

    @property
    def font(self):
        return self._theme.get_property('font', 'Cluster', self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'SVG', self.custom_variant(), self.styles(), self.states())
