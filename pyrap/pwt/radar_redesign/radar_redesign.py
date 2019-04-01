import os

from dnutils.tools import ifnone

from pyrap import session, locations
from pyrap.communication import RWTCreateOperation, RWTCallOperation, \
    RWTSetOperation
from pyrap.events import OnSelect, _rwt_event, OnSet
from pyrap.ptypes import BitField
from pyrap.pwt.pwtutils import downloadsvg, downloadpdf
from pyrap.themes import WidgetTheme
from pyrap.widgets import Widget, constructor, checkwidget
from pyrap.constants import d3wrapper


class RadarChartRed(Widget):

    _rwt_class_name = 'pwt.customs.RadarChartRed'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('RadarChartRed')
    def __init__(self, parent, legendtext=None, opts=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = RadarRedTheme(self, session.runtime.mngr.theme)
        self._requiredjs = [os.path.join(locations.trdparty, 'd3', 'd3.v3.min.js')]
        with open(os.path.join(locations.trdparty, 'd3', 'd3.v3.min.js'), 'r') as f:
            cnt = d3wrapper.format(**{'d3content': f.read()})
            session.runtime.ensurejsresources(cnt, name='d3.v3.min.js', force=True)
        with open(os.path.join(locations.pwt_loc, 'radar_redesign', 'radar_redesign.css')) as fi:
            session.runtime.requirecss(fi)
        self._axes = []
        self._data = {}
        self._opts = opts
        self._legendtext = legendtext
        self.on_select = OnSelect(self)
        self.on_set = OnSet(self)
        self.svg = None

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if self._opts:
            options.options = self._opts
        # options.d3 = self._d3
        options.legendtext = ifnone(self._legendtext, '')
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

    def _handle_set(self, op):
        Widget._handle_set(self, op)
        for key, value in op.args.items():
            if key == 'svg':
                downloadsvg(op.args['svg'], self.width.value, self.height.value, os.path.join(locations.pwt_loc, 'radar_redesign', 'radar_redesign.css'), name=__class__.__name__)
            if key == 'pdf':
                downloadpdf(op.args['pdf'], self.width.value, self.height.value, os.path.join(locations.pwt_loc, 'radar_redesign', 'radar_redesign.css'), name=__class__.__name__)
        self.on_set.notify(_rwt_event(op))

    def _handle_notify(self, op):
        events = {'Selection': self.on_select}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        else:
            if op.args.get('type', None) == 'remaxis':  # TODO: find a pretty solution for this
                idx = next(index for (index, d) in enumerate(self._axes) if d.name == op.args['dataset']['name'])
                self._axes.pop(idx)
                self._data = op.args['data']
            events[op.event].notify(_rwt_event(op))
        return True

    def addaxis(self, name, minval=None, maxval=None, unit='%', intervalmin=None, intervalmax=None):
        r = RadarRedAxis(name, minval=minval, maxval=maxval, unit=unit, intervalmin=intervalmin, intervalmax=intervalmax)
        self._axes.append(r)
        session.runtime << RWTCallOperation(self.id, 'addAxis', {'name': name,
                                                                 'limits': [minval, maxval],
                                                                 'unit': unit,
                                                                 'interval': [intervalmin, intervalmax]})
        return r

    @property
    def axes(self):
        return self._axes

    @property
    def data(self):
        return self._data

    def remaxis(self, axis):
        self._axes.remove(axis)
        session.runtime << RWTCallOperation(self.id, 'remAxis', axis)
        return True

    def clear(self):
        self._axes = []
        self._data = {}
        self._opts = []
        session.runtime << RWTCallOperation(self.id, 'clear', { })

    def interval(self, axis, minval=None, maxval=None):
        if minval is not None:
            axis.intervalmin = minval
        if maxval is not None:
            axis.intervalmax = maxval
        session.runtime << RWTCallOperation(self.id, 'updateAxis',{'axis': axis })

    def limits(self, axis, minval=None, maxval=None):
        if minval is not None:
            axis.minval = minval
        if maxval is not None:
            axis.maxval = maxval
        session.runtime << RWTCallOperation(self.id, 'updateAxis',{'axis': axis })

    def unit(self, axis, unit):
        axis.unit = unit
        session.runtime << RWTCallOperation(self.id, 'updateAxis',{'axis': axis })

    def setdata(self, data):
        self._data = data
        session.runtime << RWTSetOperation(self.id, {'data': data})

    def download(self, pdf=False):
        session.runtime << RWTCallOperation(self.id, 'retrievesvg', {'type': 'pdf' if pdf else 'svg'})


class RadarRedAxis(object):
    def __init__(self, name, minval=0, maxval=100, unit='%', intervalmin=None, intervalmax=None):
        self._name = name
        self._minval = minval
        self._maxval = maxval
        self._unit = unit
        self._intervalmin = intervalmin
        self._intervalmax = intervalmax

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, n):
        self._name = n

    @property
    def unit(self):
        return self._unit

    @unit.setter
    def unit(self, u):
        self._unit = u

    @property
    def minval(self):
        return self._minval

    @minval.setter
    def minval(self, m):
        self._minval = m

    @property
    def maxval(self):
        return self._maxval

    @maxval.setter
    def maxval(self, m):
        self._maxval = m

    @property
    def intervalmin(self):
        return self._intervalmin

    @intervalmin.setter
    def intervalmin(self, m):
        self._intervalmin = m

    @property
    def intervalmax(self):
        return self._intervalmax

    @intervalmax.setter
    def intervalmax(self, m):
        self._intervalmax = m

    def intervals(self):
        return self.intervalmin, self.intervalmax

    def __str__(self):
        return 'Axis {}({}), limits: [{},{}], interval: [{},{}]'.format(self.name, self.unit, self.minval, self.maxval, self.intervalmin, self.intervalmin)

    def __repr__(self):
        return '<Axis name={} at 0x{}>'.format(self.name, hash(self))


class RadarRedTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'RadarChartRed')

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'RadarChartRed', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'RadarChartRed', self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def padding(self):
        return self._theme.get_property('padding', 'RadarChartRed', self.styles(), self.states())

    @property
    def font(self):
        return self._theme.get_property('font', 'RadarChartRed', self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'SVG', self.custom_variant(), self.styles(), self.states())