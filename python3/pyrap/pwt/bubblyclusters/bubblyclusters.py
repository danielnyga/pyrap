import os

from dnutils.tools import ifnone
from pyrap import session, locations
from pyrap.communication import RWTCreateOperation, RWTCallOperation, \
    RWTSetOperation
from pyrap.events import OnSelect, _rwt_event
from pyrap.ptypes import BitField
from pyrap.themes import WidgetTheme
from pyrap.widgets import Widget, constructor, checkwidget

d3wrapper = '''if (typeof d3 === 'undefined') {{
    {d3content}
}}'''


class BubblyClusters(Widget):

    _rwt_class_name = 'pwt.customs.BubblyClusters'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('BubblyClusters')
    def __init__(self, parent, opts=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = BubblyClustersTheme(self, session.runtime.mngr.theme)
        self._requiredjs = [os.path.join(locations.trdparty, 'd3', 'd3.v3.min.js')]
        with open(os.path.join(locations.trdparty, 'd3', 'd3.v3.min.js'), 'r') as f:
            cnt = d3wrapper.format(**{'d3content': f.read()})
            session.runtime.ensurejsresources(cnt, name='d3.v3.min.js', force=False)
        self._data = {}
        self._opts = opts
        self.on_select = OnSelect(self)
        self._gwidth = None
        self._gheight = None

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if self._opts:
            options.options = self._opts
        session.runtime << RWTCreateOperation(self.id, self._rwt_class_name, options)

    def compute_size(self):
        w, h = Widget.compute_size(self.parent)

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

    def _handle_notify(self, op):
        events = {'Selection': self.on_select}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        else:
            events[op.event].notify(_rwt_event(op))
        return True

    @property
    def data(self):
        return self._data

    def clear(self):
        self._data = {}
        self._opts = []
        session.runtime << RWTCallOperation(self.id, 'clear', {})

    def setdata(self, data):
        self._data = data
        session.runtime << RWTSetOperation(self.id, {'data': data})


class BubblyClustersTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'BubblyClusters')

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'BubblyClusters', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'BubblyClusters', self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def padding(self):
        return self._theme.get_property('padding', 'BubblyClusters', self.styles(), self.states())

    @property
    def font(self):
        return self._theme.get_property('font', 'BubblyClusters', self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'SVG', self.custom_variant(), self.styles(), self.states())