import os

from pyrap import session, locations
from pyrap.communication import RWTCallOperation
from pyrap.events import _rwt_selection_event
from pyrap.ptypes import BitField
from pyrap.pwt.d3widget.d3widget import D3Widget
from pyrap.themes import WidgetTheme
from pyrap.widgets import Widget, constructor


class RadarSmoothed(D3Widget):

    _rwt_class_name = 'pwt.customs.RadarSmoothed'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('RadarSmoothed')
    def __init__(self, parent, legendtext=None, **options):
        D3Widget.__init__(self, parent, os.path.join(locations.pwt_loc, 'radar_smoothed', 'radar_smoothed.css'), version=3, **options)
        self.theme = RadarSmoothedTheme(self, session.runtime.mngr.theme)
        self._axes = []
        self._legendtext = legendtext

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

    def clear(self):
        self._axes = []
        D3Widget.clear(self)

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
        return '<Axis name={} at 0x{}>'.format(self.name, '')

    def __eq__(self, other):
        if self.name != other.name: return False
        if self.intervalmin != other.intervalmin: return False
        if self.intervalmax != other.intervalmax: return False
        if self.minval != other.minval: return False
        if self.maxval != other.maxval: return False
        if self.unit != other.unit: return False
        return True

    def __ne__(self, other):
        return not self == other

    def json(self):
        return {'name': self.name,
                'limits': [self.minval, self.maxval],
                'unit': self.unit,
                'interval': [self.intervalmin, self.intervalmax]}


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
