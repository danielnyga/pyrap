import os

from pyrap import session, locations
from pyrap.ptypes import BitField
from pyrap.pwt.d3widget.d3widget import D3Widget
from pyrap.themes import WidgetTheme
from pyrap.widgets import Widget, constructor


class BarChart(D3Widget):

    _rwt_class_name = 'pwt.customs.BarChart'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('BarChart')
    def __init__(self, parent, **options):
        D3Widget.__init__(self, parent, os.path.join(locations.pwt_loc, 'barchart', 'barchart.css'), version=3, **options)
        self.theme = BarChartTheme(self, session.runtime.mngr.theme)


class BarChartTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'BarChart')

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'BarChart', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'BarChart', self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def padding(self):
        return self._theme.get_property('padding', 'BarChart', self.styles(), self.states())

    @property
    def font(self):
        return self._theme.get_property('font', 'BarChart', self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'SVG', self.custom_variant(), self.styles(), self.states())