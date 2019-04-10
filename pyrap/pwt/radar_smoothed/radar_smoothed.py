import os

from dnutils.tools import ifnone
from pyrap.pwt.radar.radar import RadarAxis

from pyrap import session, locations
from pyrap.communication import RWTCreateOperation, RWTCallOperation, RWTSetOperation
from pyrap.constants import d3wrapper
from pyrap.events import OnSelect, _rwt_event, OnSet, _rwt_selection_event
from pyrap.ptypes import BitField
from pyrap.pwt.pwtutils import downloadsvg, downloadpdf
from pyrap.themes import WidgetTheme
from pyrap.widgets import Widget, constructor


class RadarSmoothed(Widget):

    _rwt_class_name = 'pwt.customs.RadarSmoothed'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('RadarSmoothed')
    def __init__(self, parent, legendtext=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = RadarSmoothedTheme(self, session.runtime.mngr.theme)
        self._requiredjs = [os.path.join(locations.trdparty, 'd3', 'd3.v3.min.js')]
        with open(os.path.join(locations.trdparty, 'd3', 'd3.v3.min.js'), 'r') as f:
            cnt = d3wrapper.format(**{'d3content': f.read()})
            session.runtime.ensurejsresources(cnt, name='d3.v3.min.js', force=True)
        with open(os.path.join(locations.pwt_loc, 'radar_smoothed', 'radar_smoothed.css')) as fi:
            session.runtime.requirecss(fi)
        self._axes = []
        self._data = {}
        self._legendtext = legendtext
        self.on_select = OnSelect(self)
        self.on_set = OnSet(self)
        self.svg = None

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
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
                downloadsvg(op.args['svg'], self.width.value, self.height.value, os.path.join(locations.pwt_loc, 'radar_smoothed', 'radar_smoothed.css'), name=__class__.__name__)
            if key == 'pdf':
                downloadpdf(op.args['pdf'], self.width.value, self.height.value, os.path.join(locations.pwt_loc, 'radar_smoothed', 'radar_smoothed.css'), name=__class__.__name__)
        self.on_set.notify(_rwt_event(op))

    def _handle_notify(self, op):
        events = {'Selection': self.on_select}
        if op.event not in events:
            return Widget._handle_notify(self, op)
        else:  # must be selection event
            if op.args.args.get('type', None) == 'rs_miniv':
                axis = self.axisbyname(op.args['args'].get('dataset')['name'])
                axis.intervalmin = op.args['args'].get('dataset')['interval'][0]

            elif op.args.args.get('type', None) == 'rs_maxiv':
                axis = self.axisbyname(op.args['args'].get('dataset')['name'])
                axis.intervalmax = op.args['args'].get('dataset')['interval'][1]
            events[op.event].notify(_rwt_selection_event(op))
        return True

    def addaxis(self, name, minval=None, maxval=None, unit='%', intervalmin=None, intervalmax=None):
        if isinstance(name, RadarAxis):
            if name in self._axes: return
            self._axes.append(name)
            session.runtime << RWTCallOperation(self.id, 'addAxis', {'name': name.name,
                                                                     'limits': [name.minval, name.maxval],
                                                                     'unit': name.unit,
                                                                     'interval': [name.intervalmin, name.intervalmax]})
            return name
        else:
            r = RadarAxis(name, minval=minval, maxval=maxval, unit=unit, intervalmin=intervalmin, intervalmax=intervalmax)
            if r in self._axes: return
            self._axes.append(r)
            session.runtime << RWTCallOperation(self.id, 'addAxis', {'name': name,
                                                                     'limits': [minval, maxval],
                                                                     'unit': unit,
                                                                     'interval': [intervalmin, intervalmax]})
            return r

    def axisbyname(self, name):
        for a in self._axes:
            if a.name == name:
                return a

    @property
    def axes(self):
        return self._axes

    def remaxis(self, axis):
        self._axes.remove(axis)
        session.runtime << RWTCallOperation(self.id, 'remAxis', {'name': axis.name})
        return True

    def remaxisbyname(self, axisname):
        for a in self._axes:
            if a.name == axisname:
                session.runtime << RWTCallOperation(self.id, 'remAxis', {'name': axisname})
                self._axes.remove(a)
                return True
        return False

    @property
    def data(self):
        return self._data

    def clear(self):
        self._axes = []
        self._data = {}
        session.runtime << RWTCallOperation(self.id, 'clear', { })

    def interval(self, axis, minval=None, maxval=None):
        x = self.axisbyname(axis)
        if minval is not None:
            x.intervalmin = minval
        if maxval is not None:
            x.intervalmax = maxval
        session.runtime << RWTCallOperation(self.id, 'updateAxis', {'axis': x.json() })

    def limits(self, axis, minval=None, maxval=None):
        if minval is not None:
            axis.minval = minval
        if maxval is not None:
            axis.maxval = maxval
        session.runtime << RWTCallOperation(self.id, 'updateAxis', {'axis': axis.json() })

    def unit(self, axis, unit):
        axis.unit = unit
        session.runtime << RWTCallOperation(self.id, 'updateAxis', {'axis': axis.json() })

    def setdata(self, data):
        self._data = data
        session.runtime << RWTSetOperation(self.id, {'data': data})

    def download(self, pdf=False):
        session.runtime << RWTCallOperation(self.id, 'retrievesvg', {'type': 'pdf' if pdf else 'svg'})


class RadarSmoothedTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'RadarSmoothed')

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'RadarSmoothed', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'RadarSmoothed', self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def padding(self):
        return self._theme.get_property('padding', 'RadarSmoothed', self.styles(), self.states())

    @property
    def font(self):
        return self._theme.get_property('font', 'RadarSmoothed', self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'SVG', self.custom_variant(), self.styles(), self.states())
