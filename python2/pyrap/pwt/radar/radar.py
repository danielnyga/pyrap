import os

from dnutils.tools import ifnone
from pyrap import session, locations
from pyrap.communication import RWTCreateOperation, RWTCallOperation, \
    RWTSetOperation
from pyrap.events import OnSelect, _rwt_selection_event, _rwt_event
from pyrap.ptypes import BitField
from pyrap.themes import WidgetTheme
from pyrap.widgets import Widget, constructor, checkwidget


class RadarChart(Widget):

    _rwt_class_name = 'pwt.customs.RadarChart'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('RadarChart')
    def __init__(self, parent, legendtext=None, opts=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = RadarTheme(self, session.runtime.mngr.theme)
        self._requiredjs = [os.path.join(locations.trdparty, 'd3', 'd3.v3.min.js')]
        session.runtime.ensurejsresources(self._requiredjs)
        self._axes = []
        self._data = {}
        self._opts = opts
        self._legendtext = legendtext
        self.on_select = OnSelect(self)
        self._gwidth = None
        self._gheight = None

    def _create_rwt_widget(self):
        options = Widget._rwt_options(self)
        if self._opts:
            options.options = self._opts
        options.legendtext = ifnone(self._legendtext, '')
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


    @property
    def axes(self):
        return self._axes


    @property
    def data(self):
        return self._data


    def remaxis(self, axis):
        self._axes.remove(axis)
        session.runtime << RWTCallOperation(self.id, 'remAxis', {'name': axis.name})
        return True

    def remaxisbyname(self, axisname):
        for a in self._axes:
            if a.name == axisname:
                # self._axes.remove(a)
                session.runtime << RWTCallOperation(self.id, 'remAxis', {'name': axisname})
                return True
        return False

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


class RadarAxis(object):
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

    def __eq__(self, other):
        if self.name != other.name: return False
        if self.intervalmin != other.intervalmin: return False
        if self.intervalmax != other.intervalmax: return False
        if self.minval != other.minval: return False
        if self.maxval != other.maxval: return False
        if self.unit != other.unit: return False
        return True

    def __neq_(self, other):
        return not self == other



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