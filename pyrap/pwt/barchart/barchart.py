import os
from dnutils import ifnone

from pyrap import session, locations
from pyrap.communication import RWTCreateOperation, RWTSetOperation, \
    RWTCallOperation
from pyrap.events import OnSelect, OnSet, _rwt_event
from pyrap.ptypes import BitField
from pyrap.pwt.pwtutils import downloadsvg, downloadpdf
from pyrap.themes import WidgetTheme
from pyrap.widgets import Widget, constructor
from pyrap.constants import d3wrapper


class BarChart(Widget):

    _rwt_class_name = 'pwt.customs.BarChart'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('BarChart')
    def __init__(self, parent, **options):
        Widget.__init__(self, parent, **options)
        self.theme = BarChartTheme(self, session.runtime.mngr.theme)
        with open(os.path.join(locations.trdparty, 'd3', 'd3.v3.min.js'), 'r') as f:
            cnt = d3wrapper.format(**{'d3content': f.read()})
            session.runtime.ensurejsresources(cnt, name='d3.v3.min.js', force=True)
        with open(os.path.join(locations.pwt_loc, 'barchart', 'barchart.css')) as fi:
            session.runtime.requirecss(fi)
        self._data = []
        self.on_select = OnSelect(self)
        self.on_set = OnSet(self)
        self.svg = None

    def _handle_notify(self, op):
        events = {'Selection': self.on_select}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        events[op.event].notify(_rwt_event(op))
        return True

    def _handle_set(self, op):
        Widget._handle_set(self, op)
        for key, value in op.args.items():
            if key == 'svg':
                downloadsvg(op.args['svg'], self.width.value, self.height.value, os.path.join(locations.pwt_loc, 'barchart', 'barchart.css'), name=__class__.__name__)
            if key == 'pdf':
                downloadpdf(op.args['pdf'], self.width.value, self.height.value, os.path.join(locations.pwt_loc, 'barchart', 'barchart.css'), name=__class__.__name__)
        self.on_set.notify(_rwt_event(op))

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
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

    def clear(self):
        session.runtime << RWTCallOperation(self.id, 'clear', {})
        self._data = []

    def data(self, data):
        session.runtime << RWTSetOperation(self.id, {'data': data})
        self._data = data

    def download(self, pdf=False):
        session.runtime << RWTCallOperation(self.id, 'retrievesvg', {'type': 'pdf' if pdf else 'svg'})


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