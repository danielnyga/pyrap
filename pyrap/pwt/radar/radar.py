import os

from dnutils.tools import ifnone
from pyrap import session, locations
from pyrap.communication import RWTCreateOperation, RWTCallOperation, \
    RWTSetOperation
from pyrap.ptypes import BitField
from pyrap.themes import WidgetTheme
from pyrap.widgets import Widget, constructor, checkwidget


class RadarChart(Widget):

    _rwt_class_name = 'pwt.customs.RadarChart'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('RadarChart')
    def __init__(self, parent, cssid=None, opts=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = RadarTheme(self, session.runtime.mngr.theme)
        self._requiredjs = [os.path.join(locations.trdparty, 'd3', 'd3.v3.min.js')]
        session.runtime.ensurejsresources(self._requiredjs)
        self._gwidth = None
        self._gheight = None
        self._data = []
        self._cssid = cssid
        self._opts = opts
        self._legend = None

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if self._cssid:
            options.cssid = self._cssid
        if self._opts:
            options.options = self._opts
        print(self._opts)
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)

    def compute_size(self):
        w, h = Widget.compute_size(self.parent)
        if self.gwidth is not None:
            w = self.gwidth
        if self.gheight is not None:
            h = self.gheight

        padding = self.theme.padding
        if padding:
            w += ifnone(padding.left, 0) + ifnone(padding.right, 0)
            h += ifnone(padding.top, 0) + ifnone(padding.bottom, 0)
        margin = self.theme.margin
        if margin:
            w += ifnone(margin.left, 0) + ifnone(margin.right, 0)
            h += ifnone(margin.top, 0) + ifnone(margin.bottom, 0)
        t, r, b, l = self.theme.borders
        w += ifnone(l, 0, lambda b: b.width) + ifnone(r, 0, lambda b: b.width)
        h += ifnone(t, 0, lambda b: b.width) + ifnone(b, 0, lambda b: b.width)

        return w, h

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


    def legend(self, text=None, entries=None):
        # self._legend = RadarLegend(text=text, entries=entries)
        session.runtime << RWTCallOperation(self.id, 'updateLegend', {'txt': text, 'opts': entries})

    def updatedata(self, data):
        session.runtime << RWTCallOperation(self.id, 'updateData', data)


class RadarTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'RadarChart')

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'RadarChart', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'RadarChart', self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def padding(self):
        return self._theme.get_property('padding', 'RadarChart', self.styles(), self.states())

    @property
    def font(self):
        return self._theme.get_property('font', 'RadarChart', self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'SVG', self.custom_variant(), self.styles(), self.states())