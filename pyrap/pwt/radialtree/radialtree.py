#  -*- coding: utf-8 -*-
#                                           _..._                       .-'''-.
#                                        .-'_..._''.           .---.   '   _    \
#   __  __   ___                       .' .'      '.\          |   | /   /` '.   \
#  |  |/  `.'   `.                    / .'                     |   |.   |     \  '
#  |   .-.  .-.   '              .|  . '                       |   ||   '      |  '
#  |  |  |  |  |  |    __      .' |_ | |                 __    |   |\    \     / /
#  |  |  |  |  |  | .:--.'.  .'     || |              .:--.'.  |   | `.   ` ..' /
#  |  |  |  |  |  |/ |   \ |'--.  .-'. '             / |   \ | |   |    '-...-'`
#  |  |  |  |  |  |`" __ | |   |  |   \ '.          .`" __ | | |   |
#  |__|  |__|  |__| .'.''| |   |  |    '. `._____.-'/ .'.''| | |   |
#                  / /   | |_  |  '.'    `-.______ / / /   | |_'---'
#                  \ \._,\ '/  |   /              `  \ \._,\ '/
#                   `--'  `"   `'-'                   `--'  `"
#  (C) 2017 by Mareike Picklum (mareikep@cs.uni-bremen.de)
# 
#  Permission is hereby granted, free of charge, to any person obtaining
#  a copy of this software and associated documentation files (the
#  "Software"), to deal in the Software without restriction, including
#  without limitation the rights to use, copy, modify, merge, publish,
#  distribute, sublicense, and/or sell copies of the Software, and to
#  permit persons to whom the Software is furnished to do so, subject to
#  the following conditions:
#  The above copyright notice and this permission notice shall be
#  included in all copies or substantial portions of the Software.
# 
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
#  CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
#  TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
#  SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os

from dnutils.tools import ifnone

from pyrap import session, locations
from pyrap.communication import RWTCreateOperation, RWTCallOperation, \
    RWTSetOperation
from pyrap.constants import d3v3
from pyrap.events import OnSelect, _rwt_event, OnSet, _rwt_selection_event
from pyrap.ptypes import BitField
from pyrap.pwt.pwtutils import downloadsvg, downloadpdf
from pyrap.themes import WidgetTheme
from pyrap.widgets import Widget, constructor


class RadialTree(Widget):

    _rwt_class_name = 'pwt.customs.RadialTree'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('RadialTree')
    def __init__(self, parent, opts=None, **options):
        Widget.__init__(self, parent, **options)
        self.theme = RadialTreeTheme(self, session.runtime.mngr.theme)
        with open(os.path.join(locations.trdparty, 'd3', 'd3.v3.min.js'), 'r') as f:
            cnt = d3v3.format(**{'d3content': f.read()})
            session.runtime.ensurejsresources(cnt, name='d3.v3.min.js', force=True)
        with open(os.path.join(locations.pwt_loc, 'radialtree', 'radialtree.css')) as fi:
            session.runtime.requirecss(fi)
        self._data = {}
        self._opts = opts
        self.on_select = OnSelect(self)
        self.on_set = OnSet(self)
        self.svg = None

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
        elif op.event == 'Selection':
            events[op.event].notify(_rwt_selection_event(op))
        else:
            events[op.event].notify(_rwt_event(op))
        return True

    def _handle_set(self, op):
        Widget._handle_set(self, op)
        for key, value in op.args.items():
            if key == 'svg':
                downloadsvg(op.args['svg'], self.width.value, self.height.value, os.path.join(locations.pwt_loc, 'radialtree', 'radialtree.css'), name=__class__.__name__)
            if key == 'pdf':
                downloadpdf(op.args['pdf'], self.width.value, self.height.value, os.path.join(locations.pwt_loc, 'radialtree', 'radialtree.css'), name=__class__.__name__)
        self.on_set.notify(_rwt_event(op))

    def play(self):
        session.runtime << RWTCallOperation(self.id, 'play', {})

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

    def download(self, pdf=False):
        session.runtime << RWTCallOperation(self.id, 'retrievesvg', {'type': 'pdf' if pdf else 'svg'})


class RadialTreeTheme(WidgetTheme):

    def __init__(self, widget, theme):
        WidgetTheme.__init__(self, widget, theme, 'RadialTree')

    @property
    def borders(self):
        return [self._theme.get_property('border-%s' % b, 'RadialTree', self.styles(), self.states()) for b in ('top', 'right', 'bottom', 'left')]

    @property
    def bg(self):
        if self._bg: return self._bg
        return self._theme.get_property('background-color', 'RadialTree', self.styles(), self.states())

    @bg.setter
    def bg(self, color):
        self._bg = color

    @property
    def padding(self):
        return self._theme.get_property('padding', 'RadialTree', self.styles(), self.states())

    @property
    def font(self):
        return self._theme.get_property('font', 'RadialTree', self.styles(), self.states())

    @property
    def margin(self):
        return self._theme.get_property('margin', 'SVG', self.custom_variant(), self.styles(), self.states())
